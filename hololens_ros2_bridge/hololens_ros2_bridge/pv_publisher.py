import rclpy
from rclpy.node import Node
import time
from sensor_msgs.msg import Image
import numpy as np
import sys
sys.path.append('/home/mayooran/Documents/hl2ss/viewer')
import hl2ss
import hl2ss_lnm
import time 
import numpy as np
import cv2

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
        
        host = "10.0.0.13"
        hl2ss_lnm.start_subsystem_pv(host, hl2ss.StreamPort.PERSONAL_VIDEO, enable_mrc=False, shared=False)
        self.pv_client = hl2ss_lnm.rx_pv(host, hl2ss.StreamPort.PERSONAL_VIDEO, mode=hl2ss.StreamMode.MODE_1, width=1920, height=1080, framerate=30, profile=hl2ss.VideoProfile.H265_MAIN, bitrate=None, decoded_format='bgr24')
        self.pv_client.open()
        self.done = False
        self.counter = 0
        self.get_logger().info("PV client started...")
        # time.sleep(3)  # Allow client to initialize
        self.create_timer(0.01, self.get_pv)
        self.create_timer(0.05, self.publish_pv)

    def get_pv(self):
        
        try:
            data = self.pv_client.get_next_packet()
            received_time = data.timestamp
            self.frame = data.payload.image
            self.received_utc_time = self.utc_offset + received_time
            # self.publish_pv(frame, received_utc_time)
            
        except Exception as e:
            self.get_logger().warn(f"PV frame publish failed: {e}", throttle_duration_sec=1)
    
    def publish_pv(self):
        msg = Image()
        # print(frame.dtype)
        scale = 0.1
        self.frame = cv2.resize(self.frame, (0, 0), fx=scale, fy=scale)  

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "hololens"
        # print(frame.shape)
        msg.height, msg.width, _ = self.frame.shape
        msg.encoding = "bgr8"
        msg.is_bigendian = False
        msg.step = msg.width * 3 * self.frame.dtype.itemsize # three channels

        
        msg.data = self.frame.tobytes()

        self.pv_publisher_.publish(msg)
        # self.get_logger().info(f"Published pv frame {self.counter} ! {time.time()} ")
        self.counter += 1
        self.get_logger().info(f"Published pv frame with a delay of {(get_windows_filetime() - self.received_utc_time/10000000):.3f} seconds", throttle_duration_sec=1)
        # self.get_logger().info(f"received_utc_time: {recieved_utc_time/10000000}, current_utc_time: {get_windows_filetime()}, delay: {(get_windows_filetime()) - recieved_utc_time/10000000} ticks")


    def stop(self):
        self.pv_client.close()
        self.get_logger().info("PV client closed...................................")


def main(args=None):
    rclpy.init(args=args)
    node = PvPublisher()
    rclpy.spin(node)
    node.stop()
    node.destroy_node()
    # rclpy.shutdown()
