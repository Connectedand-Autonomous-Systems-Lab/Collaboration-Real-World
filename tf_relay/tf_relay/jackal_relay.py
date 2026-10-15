"""Relay a namespaced TF tree into the global /tf with prefixed frame names.

  /<namespace>/tf         ->  /tf         (every frame X becomes <prefix>X)
  /<namespace>/tf_static  ->  /tf_static  (same, re-latched as one full set)

Optionally also publishes a static "glue" transform
  <world_frame> -> <prefix><root_frame>
so the robot's subtree is connected to the rest of the global tree.

Usage:
  ros2 run tf_relay jackal_relay
  ros2 run tf_relay jackal_relay --ros-args \
      -p namespace:=j100_0953 -p world_frame:=map -p root_frame:=map \
      -p x:=0.0 -p y:=0.0 -p yaw:=0.0
"""
import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage


class PrefixTFRelay(Node):

    def __init__(self):
        super().__init__('jackal_tf_relay')

        ns = self.declare_parameter('namespace', 'j100_0953').value.strip('/')
        prefix = self.declare_parameter('frame_prefix', '').value
        self.prefix = prefix if prefix else ns + '/'
        # Frames that are shared and must NOT be prefixed (e.g. a common 'world').
        self.global_frames = set(
            self.declare_parameter('global_frames', ['']).value) - {''}

        # Optional glue transform: world_frame -> <prefix><root_frame>.
        self.world_frame = self.declare_parameter('world_frame', '').value
        self.root_frame = self.declare_parameter('root_frame', 'map').value
        self.glue = [self.declare_parameter(k, 0.0).value
                     for k in ('x', 'y', 'z', 'roll', 'pitch', 'yaw')]

        dyn_qos = QoSProfile(depth=100, history=HistoryPolicy.KEEP_LAST,
                             reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.VOLATILE)
        static_qos = QoSProfile(depth=1, history=HistoryPolicy.KEEP_LAST,
                                reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        static_sub_qos = QoSProfile(depth=100, history=HistoryPolicy.KEEP_LAST,
                                    reliability=ReliabilityPolicy.RELIABLE,
                                    durability=DurabilityPolicy.TRANSIENT_LOCAL)

        self.pub_tf = self.create_publisher(TFMessage, '/tf', dyn_qos)
        self.pub_static = self.create_publisher(TFMessage, '/tf_static', static_qos)

        self.create_subscription(TFMessage, f'/{ns}/tf', self.on_tf, dyn_qos)
        self.create_subscription(TFMessage, f'/{ns}/tf_static', self.on_static,
                                 static_sub_qos)

        # Each static publisher on the robot latches its own message. Because we
        # republish through ONE latched publisher (depth 1), we keep the full
        # set and always send all of it, so late joiners get every frame.
        self.static_set = {}
        if self.world_frame:
            glue = self.make_glue()
            self.static_set[glue.child_frame_id] = glue
            self.publish_static()

        self.get_logger().info(
            f"Relaying /{ns}/tf(_static) -> /tf(_static) with prefix '{self.prefix}'"
            + (f", glue {self.world_frame} -> {self.prefix}{self.root_frame}"
               if self.world_frame else ''))

    def rename(self, frame):
        frame = frame.lstrip('/')
        if not frame or frame in self.global_frames or frame.startswith(self.prefix):
            return frame
        return self.prefix + frame

    def on_tf(self, msg):
        for t in msg.transforms:
            t.header.frame_id = self.rename(t.header.frame_id)
            t.child_frame_id = self.rename(t.child_frame_id)
        self.pub_tf.publish(msg)

    def on_static(self, msg):
        for t in msg.transforms:
            t.header.frame_id = self.rename(t.header.frame_id)
            t.child_frame_id = self.rename(t.child_frame_id)
            self.static_set[t.child_frame_id] = t
        self.publish_static()

    def publish_static(self):
        self.pub_static.publish(TFMessage(transforms=list(self.static_set.values())))

    def make_glue(self):
        x, y, z, roll, pitch, yaw = self.glue
        cr, sr = math.cos(roll / 2), math.sin(roll / 2)
        cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
        cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = self.world_frame
        t.child_frame_id = self.rename(self.root_frame)
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        t.transform.rotation.w = cr * cp * cy + sr * sp * sy
        t.transform.rotation.x = sr * cp * cy - cr * sp * sy
        t.transform.rotation.y = cr * sp * cy + sr * cp * sy
        t.transform.rotation.z = cr * cp * sy - sr * sp * cy
        return t


def main():
    rclpy.init()
    node = PrefixTFRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
