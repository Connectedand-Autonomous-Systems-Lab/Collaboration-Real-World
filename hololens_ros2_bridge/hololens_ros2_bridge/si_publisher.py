import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import numpy as np
import asyncio
import socket
import json
import threading

class SiPublisher(Node):
    def __init__(self):
        super().__init__('si_publisher')
        self.head_pos_publisher_ = self.create_publisher(String, 'hololens/si/head_position', 10)
        self.head_orientation_publisher_ = self.create_publisher(String, 'hololens/si/head_orientation', 10)
        # self.eye_publisher_ = self.create_publisher(String, 'hololens/si/eye',10)
        # self.hand_publisher_ = self.create_publisher(String, 'hololens/si/hand',10)

        self.done = False
        self.payload = {}
        self.previous_head_position = None
        
        HOST = "127.0.0.1"
        PORT = 9999

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((HOST, PORT))
        self.sock.setblocking(False)
        self.get_logger().info(f"SI Publisher listening on {HOST}:{PORT}")

        self.create_timer(0.1, self.get_payload)
        self.create_timer(0.1, self.publish_head_position)
        self.create_timer(0.1, self.publish_head_orientation)
        # self.create_timer(0.05, self.publish_eye)
        # self.create_timer(0.05, self.publish_hand)

    def get_payload(self):
        try:
            data, _ = self.sock.recvfrom(65535)
        except BlockingIOError:
            return
        except OSError as exc:
            self.get_logger().error(f"Socket receive failed: {exc}", throttle_duration_sec=1)
            return

        try:
            self.payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self.get_logger().warn(f"Invalid SI payload: {exc}", throttle_duration_sec=1)
            
    def publish_head_position(self):
        try:
            head_position = self.payload.get("Head Position")
            head_position = [
                    head_position.get("x"),
                    head_position.get("y"),
                    head_position.get("z"),
                ]

            if not len(head_position)==3:
                self.get_logger().warn(f"Position list length incorrect: {head_position}",throttle_duration_sec=1)
                return
            pos_str = str(head_position)  # e.g., "[1.23, 4.56, 7.89]"
            msg = String()
            msg.data = pos_str
            if self.previous_head_position == head_position:
                self.get_logger().debug("Head position unchanged, not publishing", throttle_duration_sec=1)
            self.previous_head_position = head_position
            self.head_pos_publisher_.publish(msg)
            self.get_logger().info(f"Head position published! : {msg.data}", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Position list publish failed: {e}",throttle_duration_sec=1)

    def publish_head_orientation(self):
        try:
                #        ↑ Y (up)
                #        |
                #        |
                #        *----→ X (right)
                #       /
                #      /
                #  -Z (forward)
            
            forward = self.payload.get("Head Forward")
            up = self.payload.get("Head Up")
            if forward is None or up is None:
                self.get_logger().warn(f"Orientation data missing: forward={forward}, up={up}",throttle_duration_sec=1)
                return
            forward = np.array([
                    forward.get("x"),   
                    forward.get("y"),
                    forward.get("z"),
                ], dtype=float)
            up = np.array([
                    up.get("x"),
                    up.get("y"),
                    up.get("z"),
                ], dtype=float)

            forward_norm = np.linalg.norm(forward)
            up_norm = np.linalg.norm(up)
            if forward_norm == 0 or up_norm == 0:
                self.get_logger().warn("Head orientation vector has zero magnitude", throttle_duration_sec=1)
                return

            forward /= forward_norm
            up /= up_norm
            right = np.cross(up, -forward)

            # Create a 3x3 rotation matrix with basis vectors as columns
            rot3 = np.column_stack((right, up, forward))  # align with ROS frame: X, Y, Z

            # Convert to 4x4 homogeneous matrix
            rot4 = np.eye(4)
            rot4[:3, :3] = rot3
            self.previous_head_orientation = rot4

            orientation_str = str(rot4) 
            msg = String()
            msg.data = orientation_str
            self.head_orientation_publisher_.publish(msg)
            # self.get_logger().info(f"Head orientation published! : {msg.data}", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Orientation list publish failed: {e}",throttle_duration_sec=1)
    
    def publish_eye(self):
        try:
            json = {"origin": self.payload.get("Eye Origin"), "direction": self.payload.get("Eye Direction"), "distance": self.payload.get("Eye Distance")}
            msg = String()
            msg.data = str(json)
            self.eye_publisher_.publish(msg)
            # self.get_logger().info(f"Eye published! {msg.data}", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Eye publish failed: {e}",throttle_duration_sec=1)

    def publish_hand(self):
        try:
            hand_right = self.payload.get("Right Hand")

            hand_left = self.payload.get("Left Hand") 
                
            json = {"right": hand_right, "left": hand_left}

            msg = String()
            msg.data = str(json)
            self.hand_publisher_.publish(msg)
            # self.get_logger().info(f"Hand published! {msg.data}", throttle_duration_sec=1)
        except Exception as e:
            self.get_logger().warn(f"Hand publish failed: {e}",throttle_duration_sec=1)

    def stop(self):
        self.done = True
        self.get_logger().info("SI client stopped................................................")

def main(args=None):
    rclpy.init(args=args)
    node = SiPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.stop()
    node.destroy_node()
    # rclpy.shutdown()
