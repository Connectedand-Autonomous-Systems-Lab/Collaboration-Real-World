import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

# Replace with actual client
from tools.hl2ss_bridge import si_client, time_client

class ThreadPublisher(Node):
    def __init__(self):
        super().__init__('counter_publisher')
        self.counter_publisher_ = self.create_publisher(String, 'counter', 10)
        # self.client = si_client()
        self.create_timer(0.5, self.publish_counter)

    def publish_counter(self):
        try:
            msg = String()
            msg.data = "Hello from thread publisher!"
            self.counter_publisher_.publish(msg)
            self.get_logger().info("Counter published!")
        except Exception as e:
            self.get_logger().warn(f"Counter publish failed: {e}",throttle_duration_sec=1)

    def stop(self):
        print("Stopping SI Publisher and client thread...")


def main(args=None):
    rclpy.init(args=args)
    node = ThreadPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.stop()
    node.destroy_node()
    # rclpy.shutdown()
