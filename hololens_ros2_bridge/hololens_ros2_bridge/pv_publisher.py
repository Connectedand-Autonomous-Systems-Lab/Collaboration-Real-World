import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time
from sensor_msgs.msg import Image
import numpy as np

# Replace with actual client
from tools.hl2ss_bridge import pv_client

class PvPublisher(Node):
    def __init__(self):
        super().__init__('pv_publisher')
        self.pv_publisher_ = self.create_publisher(Image, 'hololens/pv', 10)
        self.client = pv_client()
        time.sleep(3)  # Allow client to initialize
        self.create_timer(0.5, self.publish_pv)

    def publish_pv(self):
        
        try:
            frame = self.client.get_frame()  # [x, y, z]
            msg = Image()
            # print(frame.dtype)
            
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "hololens"
            # print(frame.shape)
            msg.height, msg.width, _ = frame.shape
            msg.encoding = "bgr8"
            msg.is_bigendian = False
            msg.step = msg.width * frame.dtype.itemsize
            msg.data = np.array(frame).tobytes()

            self.pv_publisher_.publish(msg)
            self.get_logger().debug(f"Published pv frame")

        except Exception as e:
            self.get_logger().warn(f"PV frame publish failed: {e}", throttle_duration_sec=1)
    
    def stop(self):
        self.client.end_thread()


def main(args=None):
    rclpy.init(args=args)
    node = PvPublisher()
    rclpy.spin(node)
    node.stop()
    node.destroy_node()
    rclpy.shutdown()
