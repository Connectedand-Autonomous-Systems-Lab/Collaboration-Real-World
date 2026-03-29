#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from datetime import datetime, timezone


class KeyboardPublisher(Node):
    def __init__(self):
        super().__init__('keyboard_publisher')
        self.publisher_ = self.create_publisher(String, 'detections', 10)
        self.get_logger().info("KeyboardPublisher node started. Type messages and press Enter.")
        self.get_logger().info("Type 'quit' or 'exit' to stop.")

    def publish_message(self, text: str):
        # Get current UTC time
        now_utc = datetime.now(timezone.utc)

        # Build timestamp like 20251204_175916203 (YYYYMMDD_HHMMSSmmm)
        # %f is microseconds -> convert to milliseconds (3 digits)
        ms = now_utc.microsecond // 1000
        ts = now_utc.strftime("%Y%m%d_%H%M%S") + f"{ms:03d}"

        msg = String()
        msg.data = f"[{ts}] {text}"   # embed UTC timestamp in the string

        self.publisher_.publish(msg)
        self.get_logger().info(f'Published: "{msg.data}"')


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardPublisher()

    try:
        while rclpy.ok():
            try:
                user_input = input('> ')
            except (EOFError, KeyboardInterrupt):
                break

            if user_input.lower() in ('quit', 'exit'):
                break

            node.publish_message(user_input)

    finally:
        node.get_logger().info("Shutting down KeyboardPublisher...")
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
