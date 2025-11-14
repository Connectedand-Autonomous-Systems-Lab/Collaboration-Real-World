#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
import sensor_msgs_py.point_cloud2 as pc2
import csv
import hashlib
import os

class PointCloudLogger(Node):
    def __init__(self):
        super().__init__('pointcloud_logger')
        self.subscription = self.create_subscription(
            PointCloud2,
            '/point_cloud2',  # <-- change to your topic name
            self.pointcloud_callback,
            10
        )

        self.csv_file = 'pointcloud_log.csv'
        self.last_hash = None
        self.get_logger().info(f"Logging to {self.csv_file}")

        # Create file if not exists
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['x', 'y', 'z'])

    def pointcloud_callback(self, msg):
        # Convert PointCloud2 to list of points
        points = list(pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True))

        # Compute hash to detect changes
        cloud_hash = hashlib.sha256(str(points).encode()).hexdigest()

        if cloud_hash != self.last_hash:
            self.last_hash = cloud_hash
            self.save_to_csv(points)
            self.get_logger().info(f"Saved new point cloud with {len(points)} points.")
        else:
            self.get_logger().debug("PointCloud unchanged, skipping save.")

    def save_to_csv(self, points):
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            for p in points:
                writer.writerow(p)

def main(args=None):
    rclpy.init(args=args)
    node = PointCloudLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
