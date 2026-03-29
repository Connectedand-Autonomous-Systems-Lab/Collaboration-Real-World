#!/usr/bin/env python3

import os
from pathlib import Path
import cv2
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import qos_profile_sensor_data
import numpy as np

class ImageSaver(Node):
    def __init__(self) -> None:
        super().__init__('image_saver')

        self.declare_parameter('image_topic', '/oak/stereo/image_raw')
        self.declare_parameter('output_dir', '/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge/rosbag/hl_depth_calibration')
        self.declare_parameter('image_encoding', 'passthrough')
        self.declare_parameter('file_prefix', 'frame')
        self.declare_parameter('file_extension', 'png')

        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        self.output_dir = Path(
            self.get_parameter('output_dir').get_parameter_value().string_value
        )
        self.image_encoding = (
            self.get_parameter('image_encoding').get_parameter_value().string_value
        )
        self.file_prefix = (
            self.get_parameter('file_prefix').get_parameter_value().string_value
        )
        self.file_ext = (
            self.get_parameter('file_extension').get_parameter_value().string_value
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.bridge = CvBridge()
        self.counter = 0
        self.saved_first_image = False

        self.subscription = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            qos_profile_sensor_data
        )

        self.get_logger().info(
            f'Subscribing to: {image_topic}, saving to: {self.output_dir}'
        )

    def image_callback(self, msg: Image):
        if self.saved_first_image:
            return

        image_encoding = self.image_encoding
        if image_encoding == 'passthrough':
            image_encoding = msg.encoding

        print(msg.encoding)
        print(msg.data)
        print(np.unique(msg.data))
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding=image_encoding)
        except CvBridgeError as e:
            self.get_logger().error(f'cv_bridge conversion failed: {e}')
            self.get_logger().error(
                f'msg.encoding={msg.encoding}, requested_encoding={self.image_encoding}'
            )
            return

        stamp = msg.header.stamp
        filename = f"{self.file_prefix}_{stamp.sec}_{stamp.nanosec:09d}_{self.counter}.{self.file_ext}"
        path = str(self.output_dir / filename)

        success = cv2.imwrite(path, cv_image)
        if success:
            self.get_logger().info(f'Saved image: {path}')
            self.saved_first_image = True
            self.destroy_subscription(self.subscription)
        else:
            self.get_logger().error(f'Failed to save image: {path}')


def main(args=None):
    rclpy.init(args=args)
    node = ImageSaver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
