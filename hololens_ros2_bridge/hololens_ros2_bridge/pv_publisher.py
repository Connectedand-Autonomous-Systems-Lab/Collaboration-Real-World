import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time
from sensor_msgs.msg import Image
import numpy as np

# Replace with actual client
from tools.hl2ss_bridge import pv_client, time_client

def get_windows_filetime() -> int:
    WINDOWS_TICKS_PER_SECOND = 10_000_000  # 100 ns units
    WINDOWS_EPOCH_DIFFERENCE = 11644473600  # seconds between 1601-01-01 and 1970-01-01
    unix_time = time.time()  # seconds since 1970-01-01 UTC (float)
    return int(unix_time + WINDOWS_EPOCH_DIFFERENCE)

class PvPublisher(Node):
    def __init__(self):
        super().__init__('pv_publisher')
        self.pv_publisher_ = self.create_publisher(Image, 'hololens/pv', 10)
        self.time_client = time_client()
        self.utc_offset = self.time_client.get_time() 
        self.client = pv_client()
        # time.sleep(3)  # Allow client to initialize
        self.create_timer(0.05, self.publish_pv)

    def publish_pv(self):
        
        try:
            frame, recieved_time = self.client.get_frame()  # [x, y, z]
            recieved_utc_time = self.utc_offset + recieved_time
            msg = Image()
            # print(frame.dtype)
            
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "hololens"
            # print(frame.shape)
            msg.height, msg.width, _ = frame.shape
            msg.encoding = "bgr8"
            msg.is_bigendian = False
            msg.step = msg.width * 3 * frame.dtype.itemsize # three channels
            msg.data = np.array(frame).tobytes()

            self.pv_publisher_.publish(msg)
            self.get_logger().info(f"Published pv frame with a delay of {(get_windows_filetime() - recieved_utc_time/10000000):.3f} seconds")
            # self.get_logger().info(f"received_utc_time: {recieved_utc_time/10000000}, current_utc_time: {get_windows_filetime()}, delay: {(get_windows_filetime()) - recieved_utc_time/10000000} ticks")

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
