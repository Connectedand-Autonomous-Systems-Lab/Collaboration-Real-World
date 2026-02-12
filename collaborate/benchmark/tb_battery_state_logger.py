#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import os
import signal
import time
from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from sensor_msgs.msg import BatteryState


def _is_valid_float(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x) and not math.isnan(x)


def stamp_to_ns(stamp) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def stamp_to_time_s(stamp) -> float:
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


@dataclass
class Acc:
    # sample counters
    samples_total: int = 0
    samples_with_current: int = 0
    samples_with_power: int = 0

    # voltage stats (assume mostly present)
    v_sum: float = 0.0
    v_min: float = 1e18
    v_max: float = -1e18

    # current stats (only valid current samples)
    i_sum: float = 0.0
    i_min: float = 1e18
    i_max: float = -1e18

    # power stats (we use absolute power for "consumption")
    p_sum: float = 0.0
    p_min: float = 1e18
    p_max: float = -1e18

    # latency stats (ms) if header stamp available
    lat_sum: float = 0.0
    lat_min: float = 1e18
    lat_max: float = -1e18
    lat_n: int = 0

    # Energy estimate (Wh), trapezoid integration on absolute power
    energy_Wh_abs: float = 0.0
    last_t_s: Optional[float] = None
    last_p_abs: Optional[float] = None

    def add_sample(
        self,
        t_s: float,
        voltage: Optional[float],
        current: Optional[float],
        power_abs: Optional[float],
        latency_ms: Optional[float],
    ) -> None:
        self.samples_total += 1

        if voltage is not None:
            self.v_sum += voltage
            self.v_min = min(self.v_min, voltage)
            self.v_max = max(self.v_max, voltage)

        if current is not None:
            self.samples_with_current += 1
            self.i_sum += current
            self.i_min = min(self.i_min, current)
            self.i_max = max(self.i_max, current)

        if latency_ms is not None:
            self.lat_n += 1
            self.lat_sum += latency_ms
            self.lat_min = min(self.lat_min, latency_ms)
            self.lat_max = max(self.lat_max, latency_ms)

        if power_abs is not None:
            self.samples_with_power += 1
            self.p_sum += power_abs
            self.p_min = min(self.p_min, power_abs)
            self.p_max = max(self.p_max, power_abs)

            # trapezoid integration
            if self.last_t_s is not None and self.last_p_abs is not None:
                dt = t_s - self.last_t_s
                if dt > 0:
                    self.energy_Wh_abs += (0.5 * (self.last_p_abs + power_abs) * dt) / 3600.0

            self.last_t_s = t_s
            self.last_p_abs = power_abs


class BatteryPowerLogger(Node):
    """
    Logs power derived from sensor_msgs/BatteryState on a topic (default /robot_0/battery_state)
    to a CSV file and appends a summary at the end.

    Logged fields include:
      - header stamp ns
      - rx time ns
      - latency_ms
      - voltage/current
      - power_W (signed) and power_abs_W
      - charge/capacity/percentage/temperature
    """

    def __init__(self) -> None:
        super().__init__("battery_power_logger")

        # Parameters
        self.declare_parameter("topic", "/robot_0/battery_state")
        self.declare_parameter("csv_path", "TB_battery_monitor.csv")
        self.declare_parameter("idle_seconds_to_stop", 2.0)
        self.declare_parameter("reliability", "best_effort")  # or "reliable"

        self.topic = str(self.get_parameter("topic").value)
        self.csv_path = str(self.get_parameter("csv_path").value)
        self.idle_seconds_to_stop = float(self.get_parameter("idle_seconds_to_stop").value)
        self.idle_ns_to_stop = int(self.idle_seconds_to_stop * 1e9)
        reliability_str = str(self.get_parameter("reliability").value).lower().strip()

        reliability = ReliabilityPolicy.BEST_EFFORT
        if reliability_str == "reliable":
            reliability = ReliabilityPolicy.RELIABLE

        self.qos = QoSProfile(
            reliability=reliability,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=50,
        )

        # State
        self.acc = Acc()
        self.last_msg_rx_ns: Optional[int] = None

        # CSV setup
        os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
        self._csv_f = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_f)
        self._csv.writerow([
            "wall_time_s",
            "rx_ros_time_ns",
            "header_stamp_ns",
            "latency_ms",
            "voltage_V",
            "current_A",
            "power_W",
            "power_abs_W",
            "temperature_C",
            "charge_Ah",
            "capacity_Ah",
            "design_capacity_Ah",
            "percentage",
            "power_supply_status",
            "power_supply_health",
            "power_supply_technology",
            "present",
        ])
        self._csv_f.flush()

        # Subscriber
        self.sub = self.create_subscription(BatteryState, self.topic, self._cb, self.qos)

        # Timer to detect end of playback (idle + no publishers)
        self._stop_timer = self.create_timer(0.25, self._check_stop_condition)

        # Signals: ensure summary on external kill (best effort)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self.get_logger().info(f"Subscribing to: {self.topic}")
        self.get_logger().info(f"Logging CSV to: {self.csv_path}")
        self.get_logger().info("Power computed as: power_W = voltage_V * current_A; also logs power_abs_W = voltage*abs(current)")

    def _handle_signal(self, sig, frame):
        self.get_logger().info("Signal received. Writing summary and shutting down...")
        self._write_summary_and_close()
        rclpy.shutdown()

    def _cb(self, msg: BatteryState) -> None:
        wall_s = time.time()
        rx_ros_ns = self.get_clock().now().nanoseconds
        self.last_msg_rx_ns = rx_ros_ns

        # Header stamp / latency
        header_ns = stamp_to_ns(msg.header.stamp) if hasattr(msg, "header") else 0
        latency_ms: Optional[float] = None
        if header_ns > 0:
            latency_ms = (rx_ros_ns - header_ns) / 1e6

        # Core values
        v = float(msg.voltage) if _is_valid_float(msg.voltage) else None
        i = float(msg.current) if _is_valid_float(msg.current) else None
        temp = float(msg.temperature) if _is_valid_float(msg.temperature) else None

        p = (v * i) if (v is not None and i is not None) else None
        p_abs = (v * abs(i)) if (v is not None and i is not None) else None

        charge = float(msg.charge) if _is_valid_float(msg.charge) else None
        capacity = float(msg.capacity) if _is_valid_float(msg.capacity) else None
        design_capacity = float(msg.design_capacity) if _is_valid_float(msg.design_capacity) else None
        percentage = float(msg.percentage) if _is_valid_float(msg.percentage) else None

        # Write row
        self._csv.writerow([
            f"{wall_s:.6f}",
            rx_ros_ns,
            header_ns if header_ns > 0 else "",
            "" if latency_ms is None else f"{latency_ms:.3f}",
            "" if v is None else f"{v:.6f}",
            "" if i is None else f"{i:.6f}",
            "" if p is None else f"{p:.6f}",
            "" if p_abs is None else f"{p_abs:.6f}",
            "" if temp is None else f"{temp:.6f}",
            "" if charge is None else f"{charge:.6f}",
            "" if capacity is None else f"{capacity:.6f}",
            "" if design_capacity is None else f"{design_capacity:.6f}",
            "" if percentage is None else f"{percentage:.6f}",
            int(msg.power_supply_status),
            int(msg.power_supply_health),
            int(msg.power_supply_technology),
            bool(msg.present),
        ])

        # Use header time for integration if available; else wall time
        t_s = stamp_to_time_s(msg.header.stamp) if header_ns > 0 else wall_s

        # Accumulate stats using absolute power for "consumption"
        self.acc.add_sample(
            t_s=t_s,
            voltage=v,
            current=i,
            power_abs=p_abs,
            latency_ms=latency_ms,
        )

        # Flush sometimes
        if (self.acc.samples_total % 50) == 0:
            self._csv_f.flush()

    def _check_stop_condition(self) -> None:
        if self.last_msg_rx_ns is None:
            return

        now_ns = self.get_clock().now().nanoseconds
        if (now_ns - self.last_msg_rx_ns) < self.idle_ns_to_stop:
            return

        # If the publisher disappeared (useful for rosbag play end)
        try:
            if self.count_publishers(self.topic) == 0:
                self.get_logger().info(
                    f"Idle for {self.idle_seconds_to_stop}s and no publishers remain. Finalizing."
                )
                self._write_summary_and_close()
                rclpy.shutdown()
        except Exception:
            # If introspection fails, do nothing
            pass

    def _write_summary_and_close(self) -> None:
        try:
            self._csv_f.flush()
            self._csv.writerow([])
            self._csv.writerow(["SUMMARY"])

            self._csv.writerow(["samples_total", self.acc.samples_total])

            # Voltage
            if self.acc.samples_total > 0:
                v_avg = self.acc.v_sum / self.acc.samples_total
                self._csv.writerow(["voltage_avg_V", f"{v_avg:.6f}"])
                self._csv.writerow(["voltage_min_V", f"{self.acc.v_min:.6f}"])
                self._csv.writerow(["voltage_max_V", f"{self.acc.v_max:.6f}"])

            # Current
            if self.acc.samples_with_current > 0:
                i_avg = self.acc.i_sum / self.acc.samples_with_current
                self._csv.writerow(["current_avg_A", f"{i_avg:.6f}"])
                self._csv.writerow(["current_min_A", f"{self.acc.i_min:.6f}"])
                self._csv.writerow(["current_max_A", f"{self.acc.i_max:.6f}"])
            else:
                self._csv.writerow(["current_note", "No valid current samples (current may be NaN)."])

            # Power (absolute)
            if self.acc.samples_with_power > 0:
                p_avg = self.acc.p_sum / self.acc.samples_with_power
                self._csv.writerow(["power_abs_avg_W", f"{p_avg:.6f}"])
                self._csv.writerow(["power_abs_min_W", f"{self.acc.p_min:.6f}"])
                self._csv.writerow(["power_abs_max_W", f"{self.acc.p_max:.6f}"])
                self._csv.writerow(["energy_Wh_est_abs", f"{self.acc.energy_Wh_abs:.9f}"])
            else:
                self._csv.writerow(["power_note", "No power samples (need valid voltage and current)."])

            # Latency
            if self.acc.lat_n > 0:
                lat_avg = self.acc.lat_sum / self.acc.lat_n
                self._csv.writerow(["latency_avg_ms", f"{lat_avg:.3f}"])
                self._csv.writerow(["latency_min_ms", f"{self.acc.lat_min:.3f}"])
                self._csv.writerow(["latency_max_ms", f"{self.acc.lat_max:.3f}"])
            else:
                self._csv.writerow(["latency_note", "No valid header stamps to compute latency."])

            self._csv_f.flush()
            self.get_logger().info(f"Summary appended to {self.csv_path}")
        finally:
            try:
                self._csv_f.close()
            except Exception:
                pass


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = BatteryPowerLogger()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info("Interrupted. Writing summary...")
            node._write_summary_and_close()
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
