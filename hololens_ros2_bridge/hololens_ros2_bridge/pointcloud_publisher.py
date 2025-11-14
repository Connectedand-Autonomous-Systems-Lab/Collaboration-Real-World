import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header, String
import struct
import numpy as np
import csv
import os
from tools.hl2ss_bridge import sm_client

class PointCloudPublisher(Node):
    def __init__(self):
        super().__init__('dummy_pointcloud_publisher')
        self.publisher = self.create_publisher(PointCloud2, 'point_cloud2', 10)
        self.timer = self.create_timer(0.5, self.publish_pointcloud)
        self.pcd_subscriber_ = self.create_subscription(String, 'hololens/sm/pcd', self.pcd_callback, 10)
        self.sm = sm_client()
        self.pcd_list = None

        self.csv_path = 'pointcloud_log.csv'
        self.frame_counter = 0

        # Create the CSV file if it doesn't exist
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame_id', 'point_data'])  # header

    def publish_pointcloud(self):
        if self.pcd_list is None:
            return

        msg = PointCloud2()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'

        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1)
        ]

        points = []
        flat_xyz = []

        for point in self.pcd_list:  # [x, y, z]
            x, y, z = point
            intensity = 0.0
            points.append(struct.pack('ffff', float(x), float(y), float(z), intensity))

            # Flatten for CSV logging
            flat_xyz.extend([x, y, z])

        data = b''.join(points)

        msg.fields = fields
        msg.height = 1
        msg.width = len(self.pcd_list)
        msg.is_dense = True
        msg.is_bigendian = False
        msg.point_step = 16
        msg.row_step = 16 * msg.width
        msg.data = data

        self.publisher.publish(msg)

        # Save the flattened point cloud row to CSV
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([self.frame_counter] + flat_xyz)

        self.frame_counter += 1

    def pcd_callback(self, msg):
        try:
            self.pcd_list = eval(msg.data)
        except Exception as e:
            self.get_logger().warn(f"Failed to parse point cloud: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = PointCloudPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
