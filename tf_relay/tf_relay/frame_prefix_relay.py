"""Republish stamped topics with their header.frame_id prefixed.

Companion to jackal_relay: once the Jackal's TF frames are relayed to the
global /tf as  <prefix>X , the data still says frame_id 'X' (e.g. 'lidar3d_0_link',
'jackal_map'), which doesn't exist in the global tree. This node copies each
listed topic to  <output_ns><topic>  with frame_id rewritten to  <prefix>X ,
so RViz on the global /tf can transform it.

  /j100_0953/sensors/lidar3d_0/points  ->  /global/j100_0953/sensors/lidar3d_0/points

Works for any message with a top-level std_msgs/Header (PointCloud2, LaserScan,
OccupancyGrid, Odometry, Path, Image, ...). Message types are discovered at runtime.
QoS (reliability + durability) is copied from the source publisher, so latched
maps stay latched and best-effort sensor streams stay best-effort.

Usage:
  ros2 run tf_relay frame_prefix_relay --ros-args -p topics:="[
      '/j100_0953/map',
      '/j100_0953/sensors/lidar3d_0/points',
      '/j100_0953/sensors/lidar3d_0/scan']"
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosidl_runtime_py.utilities import get_message


class FramePrefixRelay(Node):

    def __init__(self):
        super().__init__('frame_prefix_relay')
        ns = self.declare_parameter('namespace', 'j100_0953').value.strip('/')
        prefix = self.declare_parameter('frame_prefix', '').value
        self.prefix = prefix if prefix else ns + '/'
        self.output_ns = '/' + self.declare_parameter('output_ns', 'global').value.strip('/')
        self.global_frames = set(
            self.declare_parameter('global_frames', ['']).value) - {''}
        topics = self.declare_parameter('topics', [
            f'/{ns}/map',
            f'/{ns}/sensors/lidar3d_0/points',
            f'/{ns}/sensors/lidar3d_0/scan',
        ]).value

        self.pending = {'/' + t.strip('/') for t in topics if t}
        self.relays = {}  # in_topic -> (sub, pub)
        # Topics may not exist yet (robot not up), so keep retrying until all are found.
        self.timer = self.create_timer(1.0, self.discover)
        self.discover()

    def rename(self, frame):
        frame = frame.lstrip('/')
        if not frame or frame in self.global_frames or frame.startswith(self.prefix):
            return frame
        return self.prefix + frame

    def source_qos(self, topic):
        infos = self.get_publishers_info_by_topic(topic)
        reliable = any(i.qos_profile.reliability == ReliabilityPolicy.RELIABLE for i in infos)
        latched = bool(infos) and all(
            i.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL for i in infos)
        # Subscribing BEST_EFFORT/VOLATILE matches any publisher; only ask for
        # more when every publisher offers it.
        all_reliable = bool(infos) and all(
            i.qos_profile.reliability == ReliabilityPolicy.RELIABLE for i in infos)
        sub = QoSProfile(
            depth=1 if latched else 5, history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.RELIABLE if all_reliable else ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL if latched else DurabilityPolicy.VOLATILE)
        pub = QoSProfile(
            depth=1 if latched else 5, history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.RELIABLE if reliable else ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL if latched else DurabilityPolicy.VOLATILE)
        return sub, pub, latched

    def discover(self):
        if not self.pending:
            self.timer.cancel()
            return
        types = dict(self.get_topic_names_and_types())
        for topic in sorted(self.pending):
            if topic not in types or not self.get_publishers_info_by_topic(topic):
                continue
            msg_type = get_message(types[topic][0])
            if not hasattr(msg_type(), 'header'):
                self.get_logger().error(f'{topic} ({types[topic][0]}) has no header; skipping')
                self.pending.discard(topic)
                continue
            out_topic = self.output_ns + topic
            sub_qos, pub_qos, latched = self.source_qos(topic)
            pub = self.create_publisher(msg_type, out_topic, pub_qos)

            def callback(msg, pub=pub):
                msg.header.frame_id = self.rename(msg.header.frame_id)
                pub.publish(msg)

            sub = self.create_subscription(msg_type, topic, callback, sub_qos)
            self.relays[topic] = (sub, pub)
            self.pending.discard(topic)
            self.get_logger().info(
                f'{topic} -> {out_topic} [{types[topic][0]}'
                f'{", latched" if latched else ""}]')
        if self.pending:
            self.get_logger().info(
                f'Waiting for: {", ".join(sorted(self.pending))}', throttle_duration_sec=10.0)


def main():
    rclpy.init()
    node = FramePrefixRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
