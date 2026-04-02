import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
import numpy as np


class RotateMapNode(Node):
    def __init__(self) -> None:
        super().__init__('rotate_map_node')

        self.declare_parameter('input_topic', '/robot_0/map')
        self.declare_parameter('output_topic', '/robot_0/map_rotated')

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value

        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.subscription = self.create_subscription(
            OccupancyGrid,
            input_topic,
            self.map_callback,
            qos,
        )
        self.publisher = self.create_publisher(OccupancyGrid, output_topic, qos)

        self.get_logger().info(
            f'Rotating occupancy grids from "{input_topic}" to "{output_topic}"'
        )

    def map_callback(self, msg: OccupancyGrid) -> None:
        height = msg.info.height
        width = msg.info.width

        rotated_msg = OccupancyGrid()
        rotated_msg.header = msg.header
        rotated_msg.info = msg.info
        rotated_msg.data = msg.data
        rotated_msg.info.origin.orientation.z = 1.0 # rotate 180 degrees (quaternion z component for 180 deg around Z axis)
        rotated_msg.info.origin.orientation.w = 0.0 # rotate 180 degrees (quaternion w component for 180 deg around Z axis)

        self.publisher.publish(rotated_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RotateMapNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
