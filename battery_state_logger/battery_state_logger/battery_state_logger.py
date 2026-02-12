#!/usr/bin/env python3
import csv
import math
import os
import time
from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import BatteryState


@dataclass
class SummaryAcc:
    n: int = 0
    power_sum: float = 0.0
    power_min: float = 1e9
    power_max: float = -1e9
    power_n: int = 0

    voltage_sum: float = 0.0
    voltage_min: float = 1e9
    voltage_max: float = -1e9
    voltage_n: int = 0

    current_sum: float = 0.0
    current_min: float = 1e9
    current_max: float = -1e9
    current_n: int = 0

    def add(self, voltage_v: Optional[float], current_a: Optional[float], power_w: Optional[float]) -> None:
        self.n += 1

        if voltage_v is not None:
            self.voltage_n += 1
            self.voltage_sum += voltage_v
            self.voltage_min = min(self.voltage_min, voltage_v)
            self.voltage_max = max(self.voltage_max, voltage_v)

        if current_a is not None:
            self.current_n += 1
            self.current_sum += current_a
            self.current_min = min(self.current_min, current_a)
            self.current_max = max(self.current_max, current_a)

        if power_w is not None:
            self.power_n += 1
            self.power_sum += power_w
            self.power_min = min(self.power_min, power_w)
            self.power_max = max(self.power_max, power_w)


class BatteryStateLogger(Node):
    def __init__(self) -> None:
        super().__init__('battery_state_logger')

        self.declare_parameter('topic', '/robot_0/battery_state')
        self.declare_parameter('out', 'battery_state.csv')
        self.declare_parameter('flush_every', 10)
        self.declare_parameter('use_msg_time', True)

        self._topic = self.get_parameter('topic').get_parameter_value().string_value
        self._out = self.get_parameter('out').get_parameter_value().string_value
        self._flush_every = max(1, int(self.get_parameter('flush_every').get_parameter_value().integer_value))
        self._use_msg_time = bool(self.get_parameter('use_msg_time').get_parameter_value().bool_value)

        out_dir = os.path.dirname(self._out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        self._file = open(self._out, 'w', newline='', encoding='utf-8')
        self._writer = csv.writer(self._file)
        self._writer.writerow([
            'wall_time_s',
            'msg_time_s',
            'voltage_v',
            'current_a',
            'power_w',
            'charge_ah',
            'capacity_ah',
            'design_capacity_ah',
            'energy_wh',
            'energy_capacity_wh',
            'energy_design_wh',
            'percentage',
            'temperature_c',
            'power_supply_status',
            'power_supply_health',
            'power_supply_technology',
        ])
        self._file.flush()

        self._acc = SummaryAcc()
        self._msg_count = 0

        self._sub = self.create_subscription(
            BatteryState,
            self._topic,
            self._on_battery_state,
            10,
        )

        self.get_logger().info(f'Logging {self._topic} to {self._out}')

    def _safe_float(self, v: float) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, float) and math.isfinite(v):
            return v
        return None

    def _msg_time_s(self, msg: BatteryState) -> Optional[float]:
        if not self._use_msg_time:
            return None
        try:
            return Time.from_msg(msg.header.stamp).nanoseconds / 1e9
        except Exception:
            return None

    def _on_battery_state(self, msg: BatteryState) -> None:
        wall_time_s = time.time()
        msg_time_s = self._msg_time_s(msg)

        voltage_v = self._safe_float(msg.voltage)
        current_a = self._safe_float(msg.current)

        power_w = None
        if voltage_v is not None and current_a is not None:
            power_w = voltage_v * current_a

        charge_ah = self._safe_float(msg.charge)
        capacity_ah = self._safe_float(msg.capacity)
        design_capacity_ah = self._safe_float(msg.design_capacity)
        energy_wh = self._safe_float(msg.energy)
        energy_capacity_wh = self._safe_float(msg.energy_capacity)
        energy_design_wh = self._safe_float(msg.energy_design)
        percentage = self._safe_float(msg.percentage)
        temperature_c = self._safe_float(msg.temperature)

        self._writer.writerow([
            f'{wall_time_s:.6f}',
            '' if msg_time_s is None else f'{msg_time_s:.6f}',
            '' if voltage_v is None else f'{voltage_v:.3f}',
            '' if current_a is None else f'{current_a:.3f}',
            '' if power_w is None else f'{power_w:.3f}',
            '' if charge_ah is None else f'{charge_ah:.6f}',
            '' if capacity_ah is None else f'{capacity_ah:.6f}',
            '' if design_capacity_ah is None else f'{design_capacity_ah:.6f}',
            '' if energy_wh is None else f'{energy_wh:.6f}',
            '' if energy_capacity_wh is None else f'{energy_capacity_wh:.6f}',
            '' if energy_design_wh is None else f'{energy_design_wh:.6f}',
            '' if percentage is None else f'{percentage:.6f}',
            '' if temperature_c is None else f'{temperature_c:.3f}',
            int(msg.power_supply_status),
            int(msg.power_supply_health),
            int(msg.power_supply_technology),
        ])

        self._acc.add(voltage_v=voltage_v, current_a=current_a, power_w=power_w)
        self._msg_count += 1

        if (self._msg_count % self._flush_every) == 0:
            self._file.flush()

    def _write_summary(self) -> None:
        self._file.flush()
        self._writer.writerow([])
        self._writer.writerow(['SUMMARY'])
        self._writer.writerow(['samples', self._acc.n])

        if self._acc.voltage_n > 0:
            self._writer.writerow(['voltage_avg_v', f'{self._acc.voltage_sum / self._acc.voltage_n:.6f}'])
            self._writer.writerow(['voltage_min_v', f'{self._acc.voltage_min:.6f}'])
            self._writer.writerow(['voltage_max_v', f'{self._acc.voltage_max:.6f}'])
        else:
            self._writer.writerow(['voltage_note', 'voltage not available'])

        if self._acc.current_n > 0:
            self._writer.writerow(['current_avg_a', f'{self._acc.current_sum / self._acc.current_n:.6f}'])
            self._writer.writerow(['current_min_a', f'{self._acc.current_min:.6f}'])
            self._writer.writerow(['current_max_a', f'{self._acc.current_max:.6f}'])
        else:
            self._writer.writerow(['current_note', 'current not available'])

        if self._acc.power_n > 0:
            self._writer.writerow(['power_avg_w', f'{self._acc.power_sum / self._acc.power_n:.6f}'])
            self._writer.writerow(['power_min_w', f'{self._acc.power_min:.6f}'])
            self._writer.writerow(['power_max_w', f'{self._acc.power_max:.6f}'])
        else:
            self._writer.writerow(['power_note', 'power not available (need voltage and current)'])

        self._file.flush()

    def destroy_node(self) -> bool:
        try:
            self._write_summary()
        except Exception as exc:
            self.get_logger().error(f'Failed to write summary: {exc}')
        try:
            self._file.close()
        except Exception:
            pass
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = BatteryStateLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
