#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import time
import yaml
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from rclpy.serialization import serialize_message

from rosidl_runtime_py.utilities import get_message
from rosbag2_py import Info


def stamp_to_ns(stamp) -> Optional[int]:
    try:
        return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
    except Exception:
        return None


def extract_msg_stamp_ns(msg) -> Optional[int]:
    try:
        if hasattr(msg, "header") and hasattr(msg.header, "stamp"):
            return stamp_to_ns(msg.header.stamp)
    except Exception:
        pass
    try:
        if hasattr(msg, "stamp"):
            return stamp_to_ns(msg.stamp)
    except Exception:
        pass
    return None


def guess_storage_id_from_metadata_yaml(bag_path: str) -> Optional[str]:
    """
    Try to read storage_id from <bag_path>/metadata.yaml
    rosbag2 metadata.yaml typically contains 'storage_identifier' or similar.
    """
    md_path = os.path.join(bag_path, "metadata.yaml")
    if not os.path.exists(md_path):
        return None
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md = yaml.safe_load(f)
        # Different ROS2 versions may name this field slightly differently:
        # common: md["rosbag2_bagfile_information"]["storage_identifier"]
        r = md.get("rosbag2_bagfile_information", md)
        for key in ("storage_identifier", "storage_id", "storage"):
            if isinstance(r, dict) and key in r and isinstance(r[key], str):
                return r[key]
    except Exception:
        return None
    return None


@dataclass
class TopicStats:
    topic: str
    type_str: str

    msg_count: int = 0
    byte_count: int = 0
    estimated_missed: int = 0

    first_rx_ns: Optional[int] = None
    last_rx_ns: Optional[int] = None
    interval_hist_ns: Deque[int] = field(default_factory=lambda: deque(maxlen=50))

    latency_sum_ms: float = 0.0
    latency_sq_sum_ms: float = 0.0
    latency_count: int = 0
    latency_min_ms: Optional[float] = None
    latency_max_ms: Optional[float] = None


class BagMetricsLoggerNode(Node):
    def __init__(self) -> None:
        super().__init__("bag_metrics_logger")

        # Params
        self.declare_parameter("bag_path", "/home/mayooran/Documents/hololens_ros2_bridge/src/collaborate/benchmark/rosbags/TB_raw")
        self.declare_parameter("csv_path", "TB_raw.csv")
        self.declare_parameter("idle_seconds_to_stop", 2.0)
        self.declare_parameter("qos_depth", 50)
        self.declare_parameter("miss_threshold", 1.8)
        self.declare_parameter("reliability", "best_effort")  # or "reliable"
        self.declare_parameter("storage_id", "")  # e.g. sqlite3, mcap

        self.bag_path = self.get_parameter("bag_path").value
        self.csv_path = self.get_parameter("csv_path").value
        self.idle_seconds_to_stop = float(self.get_parameter("idle_seconds_to_stop").value)
        self.qos_depth = int(self.get_parameter("qos_depth").value)
        self.miss_threshold = float(self.get_parameter("miss_threshold").value)
        reliability_str = str(self.get_parameter("reliability").value).lower().strip()
        storage_id = str(self.get_parameter("storage_id").value).strip()

        if not self.bag_path or not os.path.isdir(self.bag_path):
            raise RuntimeError(
                f"Parameter 'bag_path' must be a rosbag2 directory. Got: {self.bag_path}"
            )

        # Auto-detect storage_id if not provided
        if not storage_id:
            storage_id = guess_storage_id_from_metadata_yaml(self.bag_path) or "sqlite3"
        self.storage_id = storage_id

        self.idle_ns_to_stop = int(self.idle_seconds_to_stop * 1e9)

        reliability = ReliabilityPolicy.BEST_EFFORT
        if reliability_str == "reliable":
            reliability = ReliabilityPolicy.RELIABLE

        self.qos = QoSProfile(
            reliability=reliability,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=self.qos_depth,
        )

        # State
        self.stats: Dict[str, TopicStats] = {}
        self.subs = []
        self.last_any_msg_ns: Optional[int] = None

        # CSV open
        self._csv_f = open(self.csv_path, "w", newline="")
        self._csv = csv.writer(self._csv_f)
        self._csv.writerow([
            "wall_time_s",
            "rx_time_ns",
            "topic",
            "type",
            "msg_size_bytes",
            "inst_freq_hz",
            "inst_bandwidth_Bps",
            "latency_ms",
            "estimated_missed_total",
        ])
        self._csv_f.flush()

        # Read topics from metadata
        topics = self._read_bag_topics(self.bag_path, self.storage_id)
        if not topics:
            raise RuntimeError(f"No topics found in bag metadata at {self.bag_path}")

        subscribed = 0
        for topic_name, type_str in topics.items():
            try:
                msg_cls = get_message(type_str)
            except Exception as e:
                self.get_logger().warn(f"Skipping {topic_name} ({type_str}) - cannot import type: {e}")
                continue

            self.stats[topic_name] = TopicStats(topic=topic_name, type_str=type_str)
            sub = self.create_subscription(
                msg_cls,
                topic_name,
                lambda msg, tn=topic_name: self._on_msg(tn, msg),
                self.qos,
            )
            self.subs.append(sub)
            subscribed += 1

        self.get_logger().info(
            f"bag_path={self.bag_path} storage_id={self.storage_id} | "
            f"Subscribed to {subscribed}/{len(topics)} topics. Logging to {self.csv_path}"
        )

        self._stop_timer = self.create_timer(0.25, self._check_stop_condition)

    def _read_bag_topics(self, bag_path: str, storage_id: str) -> Dict[str, str]:
        info = Info()
        # ✅ FIX: your ROS2 expects (uri, storage_id)
        metadata = info.read_metadata(bag_path, storage_id)

        out: Dict[str, str] = {}
        for twmc in metadata.topics_with_message_count:
            md = twmc.topic_metadata
            out[md.name] = md.type
        return out

    def _on_msg(self, topic: str, msg) -> None:
        rx_ns = self.get_clock().now().nanoseconds
        wall_s = time.time()
        self.last_any_msg_ns = rx_ns

        st = self.stats[topic]
        st.msg_count += 1

        try:
            size_b = len(serialize_message(msg))
        except Exception:
            size_b = 0
        st.byte_count += size_b

        if st.first_rx_ns is None:
            st.first_rx_ns = rx_ns

        inst_freq_hz = 0.0
        inst_bw_bps = 0.0

        if st.last_rx_ns is not None:
            dt_ns = rx_ns - st.last_rx_ns
            if dt_ns > 0:
                inst_freq_hz = 1e9 / dt_ns
                inst_bw_bps = size_b * (1e9 / dt_ns)

                st.interval_hist_ns.append(dt_ns)
                if len(st.interval_hist_ns) >= 5:
                    med_ns = sorted(st.interval_hist_ns)[len(st.interval_hist_ns) // 2]
                    if med_ns > 0 and dt_ns > self.miss_threshold * med_ns:
                        est = int(round(dt_ns / med_ns)) - 1
                        if est > 0:
                            st.estimated_missed += est

        st.last_rx_ns = rx_ns

        latency_ms = ""
        stamp_ns = extract_msg_stamp_ns(msg)
        if stamp_ns is not None and stamp_ns > 0:
            lat_ms = (rx_ns - stamp_ns) / 1e6
            latency_ms = f"{lat_ms:.3f}"

            st.latency_count += 1
            st.latency_sum_ms += lat_ms
            st.latency_sq_sum_ms += lat_ms * lat_ms
            st.latency_min_ms = lat_ms if st.latency_min_ms is None else min(st.latency_min_ms, lat_ms)
            st.latency_max_ms = lat_ms if st.latency_max_ms is None else max(st.latency_max_ms, lat_ms)

        self._csv.writerow([
            f"{wall_s:.6f}",
            rx_ns,
            topic,
            st.type_str,
            size_b,
            f"{inst_freq_hz:.3f}",
            f"{inst_bw_bps:.3f}",
            latency_ms,
            st.estimated_missed,
        ])

        if (st.msg_count % 200) == 0:
            self._csv_f.flush()

    def _check_stop_condition(self) -> None:
        if self.last_any_msg_ns is None:
            return

        now_ns = self.get_clock().now().nanoseconds
        if (now_ns - self.last_any_msg_ns) < self.idle_ns_to_stop:
            return

        all_zero = True
        for topic in self.stats.keys():
            try:
                if self.count_publishers(topic) > 0:
                    all_zero = False
                    break
            except Exception:
                all_zero = False
                break

        if all_zero:
            self.get_logger().info("Playback appears ended. Writing summary and shutting down.")
            self._write_summary_and_close()
            rclpy.shutdown()

    def _write_summary_and_close(self) -> None:
        try:
            self._csv_f.flush()
            self._csv.writerow([])
            self._csv.writerow(["SUMMARY"])
            self._csv.writerow([
                "topic", "type", "msg_count", "estimated_missed", "duration_s",
                "avg_freq_hz", "avg_bandwidth_Bps",
                "latency_avg_ms", "latency_std_ms", "latency_min_ms", "latency_max_ms",
            ])

            overall_msgs = overall_bytes = overall_missed = 0
            overall_first = overall_last = None

            for topic, st in sorted(self.stats.items(), key=lambda kv: kv[0]):
                if st.msg_count == 0 or st.first_rx_ns is None or st.last_rx_ns is None:
                    duration_s = avg_freq = avg_bw = 0.0
                else:
                    duration_s = max(0.0, (st.last_rx_ns - st.first_rx_ns) / 1e9)
                    avg_freq = (st.msg_count / duration_s) if duration_s > 0 else 0.0
                    avg_bw = (st.byte_count / duration_s) if duration_s > 0 else 0.0

                lat_avg = lat_std = lat_min = lat_max = ""
                if st.latency_count > 0:
                    mean = st.latency_sum_ms / st.latency_count
                    var = max(0.0, (st.latency_sq_sum_ms / st.latency_count) - (mean * mean))
                    std = var ** 0.5
                    lat_avg = f"{mean:.3f}"
                    lat_std = f"{std:.3f}"
                    lat_min = f"{st.latency_min_ms:.3f}" if st.latency_min_ms is not None else ""
                    lat_max = f"{st.latency_max_ms:.3f}" if st.latency_max_ms is not None else ""

                self._csv.writerow([
                    topic, st.type_str, st.msg_count, st.estimated_missed,
                    f"{duration_s:.3f}", f"{avg_freq:.3f}", f"{avg_bw:.3f}",
                    lat_avg, lat_std, lat_min, lat_max
                ])

                overall_msgs += st.msg_count
                overall_bytes += st.byte_count
                overall_missed += st.estimated_missed
                if st.first_rx_ns is not None:
                    overall_first = st.first_rx_ns if overall_first is None else min(overall_first, st.first_rx_ns)
                if st.last_rx_ns is not None:
                    overall_last = st.last_rx_ns if overall_last is None else max(overall_last, st.last_rx_ns)

            overall_dur_s = 0.0
            if overall_first is not None and overall_last is not None and overall_last > overall_first:
                overall_dur_s = (overall_last - overall_first) / 1e9

            overall_avg_freq = (overall_msgs / overall_dur_s) if overall_dur_s > 0 else 0.0
            overall_avg_bw = (overall_bytes / overall_dur_s) if overall_dur_s > 0 else 0.0

            self._csv.writerow([])
            self._csv.writerow([
                "OVERALL", "", overall_msgs, overall_missed,
                f"{overall_dur_s:.3f}", f"{overall_avg_freq:.3f}", f"{overall_avg_bw:.3f}",
            ])

            self._csv_f.flush()
            self.get_logger().info(f"Wrote summary into {self.csv_path}")
        finally:
            try:
                self._csv_f.close()
            except Exception:
                pass


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = BagMetricsLoggerNode()
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
