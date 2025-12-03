import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster
# import math
# import time
# import threading
# from tools.hl2ss_bridge import si_client 
from tf_transformations import quaternion_from_matrix
import numpy as np

class TFPublisher(Node):
    def __init__(self):
        super().__init__('hololens_tf_broadcaster')
        self.br = TransformBroadcaster(self)
        
        self.head_position_subscriber_ = self.create_subscription(String, 'hololens/si/head_position', self.position_callback ,10)
        self.head_orientation_subscriber_ = self.create_subscription(String, 'hololens/si/head_orientation', self.orientation_callback ,10)
        self.head_position = None
        self.head_orientation = None
        self.previous_t = None
        self.timer = self.create_timer(0.1, self.broadcast_tf)  # 10 Hz

    def broadcast_tf(self):
        try:
            t = TransformStamped()

            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = 'odom'
            t.child_frame_id = 'hololens'

            position = self.head_position
            rot4 = self.head_orientation

            if position == None or rot4 == None:
                if position == None:
                    self.get_logger().warn(f"null position: {self.head_position}", throttle_duration_sec=1)
                else: self.get_logger().warn(f"null orientation: {self.head_orientation}", throttle_duration_sec=1)
                # self.get_logger().warn("No SI data yet")
                return
        
            t.transform.translation.x = float(position[2])
            t.transform.translation.y = float(position[0])
            t.transform.translation.z = float(position[1])  # Height of Hololens from ground (example)

            
            qx, qy, qz, qw = quaternion_from_matrix(rot4)
            t.transform.rotation.x = qz
            t.transform.rotation.y = qx
            t.transform.rotation.z = qy
            t.transform.rotation.w = qw

            if self.previous_t == t:
                self.get_logger().debug("TF unchanged, not publishing", throttle_duration_sec=1)
            self.previous_t = t 

            self.br.sendTransform(t)
            # self.get_logger().info("TF published!", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().debug(f"TF publish failed: {e}")
    
    def position_callback(self, msg):
        try:
            self.head_position = eval(msg.data)
        except Exception as e:
            self.get_logger().warn(f"Position callback failed: {e}")
        # self.get_logger().info(f"got position: {self.head_position}")

    def orientation_callback(self, msg):
        # print(msg.data)
        # Convert to NumPy array
        try:
            cleaned = msg.data.replace('[', '').replace(']', '')
            matrix = np.fromstring(cleaned, sep=' ').reshape((4, 4))

            # print(matrix)
            # If you want a list instead:
            matrix_list = matrix.tolist()
            self.head_orientation = matrix_list
            # self.get_logger().info("got orientation")
        except Exception as e:
            self.get_logger().debug(f"TF publish failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = TFPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    # rclpy.shutdown()

if __name__ == '__main__':
    main()
