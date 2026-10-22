"""Publish /clock from the header stamps of a topic (e.g. one played from a rosbag).

Every message on `source_topic` sets the clock to its header.stamp. Between
messages the clock is advanced at wall rate (at `rate` Hz) so time keeps moving
smoothly, but never more than `max_extrapolation` seconds past the last stamp.
The clock never goes backwards, except after a jump back larger than
`reset_threshold` (e.g. the bag was restarted or looped).

This node itself runs on wall time; every OTHER node should use use_sim_time:=true.

Usage:
  ros2 run collaborate bag_clock --ros-args -p source_topic:=/j100_0953/platform/odom
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from rclpy.time import Time
from rosgraph_msgs.msg import Clock
from rosidl_runtime_py.utilities import get_message


class BagClock(Node):

    def __init__(self):
        super().__init__('bag_clock')
        self.topic = self.declare_parameter('source_topic', '/j100_0953/platform/odom').value
        self.rate = float(self.declare_parameter('rate', 100.0).value)
        self.max_extra = float(self.declare_parameter('max_extrapolation', 0.5).value)
        self.reset_threshold = float(self.declare_parameter('reset_threshold', 1.0).value)
        reliable = self.declare_parameter('reliable', True).value

        if self.get_parameter('use_sim_time').value:
            self.get_logger().error('bag_clock must run with use_sim_time:=false')

        self.qos = QoSProfile(
            depth=10, history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.RELIABLE if reliable else ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE)
        clock_qos = QoSProfile(depth=1, history=HistoryPolicy.KEEP_LAST,
                               reliability=ReliabilityPolicy.BEST_EFFORT,
                               durability=DurabilityPolicy.VOLATILE)
        self.pub = self.create_publisher(Clock, '/clock', clock_qos)

        self.sub = None
        self.last_stamp_ns = None   # latest source header stamp
        self.last_wall_ns = None    # wall time when it arrived
        self.last_pub_ns = None     # last /clock value published

        # The message type is discovered at runtime, so any topic with a header works.
        self.discover_timer = self.create_timer(1.0, self.discover)
        self.create_timer(1.0 / self.rate, self.tick)
        self.discover()

    def discover(self):
        if self.sub is not None:
            return
        types = dict(self.get_topic_names_and_types())
        if self.topic not in types:
            self.get_logger().info(f'Waiting for {self.topic} ...', throttle_duration_sec=5.0)
            return
        msg_type = get_message(types[self.topic][0])
        if not hasattr(msg_type(), 'header'):
            self.get_logger().error(f'{self.topic} ({types[self.topic][0]}) has no header')
            return
        self.sub = self.create_subscription(msg_type, self.topic, self.on_msg, self.qos)
        self.discover_timer.cancel()
        self.get_logger().info(f'Publishing /clock from {self.topic} [{types[self.topic][0]}]')

    def wall_ns(self):
        return self.get_clock().now().nanoseconds  # wall time (use_sim_time is false)

    def on_msg(self, msg):
        stamp = Time.from_msg(msg.header.stamp).nanoseconds
        if stamp == 0:
            return
        if self.last_stamp_ns is not None and \
                stamp < self.last_stamp_ns - self.reset_threshold * 1e9:
            self.get_logger().warn('Source time jumped back; resetting clock')
            self.last_pub_ns = None
        elif self.last_stamp_ns is not None and stamp < self.last_stamp_ns:
            return  # small out-of-order stamp, ignore
        self.last_stamp_ns = stamp
        self.last_wall_ns = self.wall_ns()
        self.publish(stamp)

    def tick(self):
        if self.last_stamp_ns is None:
            return
        extra = min(self.wall_ns() - self.last_wall_ns, int(self.max_extra * 1e9))
        self.publish(self.last_stamp_ns + extra)

    def publish(self, t_ns):
        if self.last_pub_ns is not None and t_ns <= self.last_pub_ns:
            return  # never go backwards
        self.last_pub_ns = t_ns
        msg = Clock()
        msg.clock = Time(nanoseconds=t_ns).to_msg()
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = BagClock()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
