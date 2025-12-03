import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

# Replace with actual client
from tools.hl2ss_bridge import sm_client

class SmPublisher(Node):
    def __init__(self):
        super().__init__('sm_publisher')
        self.sm_publisher_ = self.create_publisher(String, 'hololens/sm/pcd', 10)
        self.si_subscriber_ = self.create_subscription(String, 'hololens/si/head_position', self.si_callback ,10)
        self.get_logger().info("Initializing SM client...")
        self.client = sm_client()
        self.get_logger().info("SM Publisher node started")
        time.sleep(1)  # Allow client to initialize
        self.create_timer(0.05, self.publish_sm)

    def publish_sm(self):
        try:
            pcd = self.client.get_pcd(self.si)
            pcd_str = str(pcd)
            msg = String()
            msg.data = pcd_str
            self.sm_publisher_.publish(msg)
            self.get_logger().debug("Published SM point cloud", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Position list publish failed: {e}")
    
    def si_callback(self, msg):
        self.si = eval(msg.data)

def main(args=None):
    rclpy.init(args=args)
    node = SmPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
