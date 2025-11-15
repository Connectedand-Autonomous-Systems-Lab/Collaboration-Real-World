import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

# Replace with actual client
from tools.hl2ss_bridge import si_client, time_client

class SiPublisher(Node):
    def __init__(self):
        super().__init__('si_publisher')
        self.head_pos_publisher_ = self.create_publisher(String, 'hololens/si/head_position', 10)
        self.head_orientation_publisher_ = self.create_publisher(String, 'hololens/si/head_orientation', 10)
        self.eye_publisher_ = self.create_publisher(String, 'hololens/si/eye',10)
        self.hand_publisher_ = self.create_publisher(String, 'hololens/si/hand',10)
        # self.time_client = time_client()
        self.client = si_client()
        time.sleep(3)  # Allow client to initialize
        self.create_timer(0.05, self.publish_head_position)
        self.create_timer(0.05, self.publish_head_orientation)
        self.create_timer(0.05, self.publish_eye)
        self.create_timer(0.05, self.publish_hand)


    def publish_head_position(self):
        try:
            pos = self.client.get_position()  # [x, y, z]
            # print(pos)
            pos_str = str(pos)  # e.g., "[1.23, 4.56, 7.89]"
            msg = String()
            msg.data = pos_str
            self.head_pos_publisher_.publish(msg)
            # self.get_logger().info("Head position published!")
        except Exception as e:
            self.get_logger().warn(f"Position list publish failed: {e}",throttle_duration_sec=1)

    def publish_head_orientation(self):
        try:
            orientation = self.client.get_orientation()  # rot4 matrix
            orientation_str = str(orientation) 
            msg = String()
            msg.data = orientation_str
            self.head_orientation_publisher_.publish(msg)
        except Exception as e:
            self.get_logger().warn(f"Orientation list publish failed: {e}",throttle_duration_sec=1)
    
    def publish_eye(self):
        try:
            msg = String()
            msg.data = self.client.get_eye()
            self.eye_publisher_.publish(msg)
            # self.get_logger().info(f"Eye published! {msg.data}", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Eye publish failed: {e}",throttle_duration_sec=1)

    def publish_hand(self):
        try:
            msg = String()
            msg.data = self.client.get_hand()
            self.hand_publisher_.publish(msg)
            # self.get_logger().info(f"Hand published! {msg.data}", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Hand publish failed: {e}",throttle_duration_sec=1)

    def stop(self):
        print("Stopping SI Publisher and client thread...")
        self.client.end_thread()


def main(args=None):
    rclpy.init(args=args)
    node = SiPublisher()
    rclpy.spin(node)
    node.stop()
    node.destroy_node()
    rclpy.shutdown()
