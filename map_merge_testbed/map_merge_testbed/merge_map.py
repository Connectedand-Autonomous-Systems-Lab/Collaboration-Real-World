import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import TransformStamped
import numpy as np
from tf2_ros import Buffer, TransformListener
import math

class MapMerger(Node):
    def __init__(self):
        super().__init__('map_merger')
        self.get_logger().info('Map_merger started!')

        self.declare_parameter('publish_period', 0.05)
        self.declare_parameter('map1_topic', '/robot1/map')
        self.declare_parameter('map2_topic', '/robot2/map')
        self.declare_parameter('merged_map_topic', '/merged_map')
        self.declare_parameter('merged_map_frame', 'map')

        self.publish_period = self.get_parameter('publish_period').value
        self.map1_topic = self.get_parameter('map1_topic').value
        self.map2_topic = self.get_parameter('map2_topic').value
        self.merged_map_topic = self.get_parameter('merged_map_topic').value
        self.merged_map_frame = self.get_parameter('merged_map_frame').value

        # Subscriptions to the two map topics
        self.sub_map1 = self.create_subscription(
            OccupancyGrid,
            self.map1_topic,
            self.map1_callback,
            10
        )
        self.sub_map2 = self.create_subscription(
            OccupancyGrid,
            self.map2_topic,
            self.map2_callback,
            10
        )
        self.pub_merged_map = self.create_publisher(OccupancyGrid, self.merged_map_topic, 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.publish_timer = self.create_timer(self.publish_period, self.try_merge_maps)
        # Store maps
        self.map1 = None
        self.map2 = None

    def map1_callback(self, msg):
        self.map1 = msg
        self.try_merge_maps()

    def map2_callback(self, msg):
        self.map2 = msg
        self.try_merge_maps()

    def mark_corners_with_cross(self, map_data, 
                                value_bl=1, value_tr=1, 
                                size=20, thickness=5):
        """
        Draw crosses at bottom-left and top-right with controllable thickness.

        Args:
            map_data: 2D numpy array (H, W)
            value_bl: value for bottom-left cross
            value_tr: value for top-right cross
            size: half-length of cross arms
            thickness: thickness of the lines (in pixels)

        Returns:
            modified map_data (in-place)
        """

        h, w = map_data.shape

        # Bottom-left (world convention)
        bl_y, bl_x = h - 1, 0

        # Top-right
        tr_y, tr_x = 0, w - 1

        def draw_cross(y, x, val):
            # Vertical bar
            for dy in range(-size, size + 1):
                for t in range(-thickness // 2, thickness // 2 + 1):
                    yy = y + dy
                    xx = x + t
                    if 0 <= yy < h and 0 <= xx < w:
                        map_data[yy, xx] = val

            # Horizontal bar
            for dx in range(-size, size + 1):
                for t in range(-thickness // 2, thickness // 2 + 1):
                    yy = y + t
                    xx = x + dx
                    if 0 <= yy < h and 0 <= xx < w:
                        map_data[yy, xx] = val

        draw_cross(bl_y, bl_x, value_bl)
        draw_cross(tr_y, tr_x, value_tr)

        return map_data
    
    def try_merge_maps(self):
        if self.map1 is None or self.map2 is None:
            return

        if self.map1.info.resolution != self.map2.info.resolution:
            self.get_logger().warn('Source maps have different resolutions; skipping merge')
            return

        resolution = self.map1.info.resolution

        min_x = -50.0
        min_y = -50.0
        merged_width = 2000
        merged_height = 2000
        merged_data = np.full((merged_height, merged_width), -1, dtype=np.int8)

        def place_map(map_msg):
            h = map_msg.info.height
            w = map_msg.info.width
            frame_id = map_msg.header.frame_id

            try:
                tf = self.tf_buffer.lookup_transform(
                    self.merged_map_frame,
                    frame_id,
                    rclpy.time.Time()
                )
            except Exception:
                self.get_logger().warn(f'No TF from {frame_id} to {self.merged_map_frame}')
                return

            tx = tf.transform.translation.x
            ty = tf.transform.translation.y
            qx = tf.transform.rotation.x
            qy = tf.transform.rotation.y
            qz = tf.transform.rotation.z
            qw = tf.transform.rotation.w

            yaw = math.atan2(
                2.0 * (qw * qz + qx * qy),
                1.0 - 2.0 * (qy * qy + qz * qz)
            )

            cos_yaw = math.cos(yaw)
            sin_yaw = math.sin(yaw)

            ox = map_msg.info.origin.position.x
            oy = map_msg.info.origin.position.y

            map_data = np.array(map_msg.data, dtype=np.int8).reshape((h, w))

            for row in range(h):
                for col in range(w):
                    value = map_data[row, col]
                    if value == -1:
                        continue

                    x_local = ox + (col + 0.5) * resolution
                    y_local = oy + (row + 0.5) * resolution

                    x_merged = tx + cos_yaw * x_local - sin_yaw * y_local
                    y_merged = ty + sin_yaw * x_local + cos_yaw * y_local

                    mx = int((x_merged - min_x) / resolution)
                    my = int((y_merged - min_y) / resolution)

                    if 0 <= mx < merged_width and 0 <= my < merged_height:
                        merged_data[my, mx] = max(merged_data[my, mx], value)

        place_map(self.map1)
        place_map(self.map2)

        merged_msg = OccupancyGrid()
        merged_msg.header.stamp = self.get_clock().now().to_msg()
        merged_msg.header.frame_id = self.merged_map_frame
        merged_msg.info.resolution = resolution
        merged_msg.info.width = merged_width
        merged_msg.info.height = merged_height
        merged_msg.info.origin.position.x = min_x
        merged_msg.info.origin.position.y = min_y
        merged_msg.info.origin.position.z = 0.0
        merged_msg.info.origin.orientation.x = 0.0
        merged_msg.info.origin.orientation.y = 0.0
        merged_msg.info.origin.orientation.z = 0.0
        merged_msg.info.origin.orientation.w = 1.0
        merged_msg.data = merged_data.flatten().tolist()

        self.pub_merged_map.publish(merged_msg)
        self.get_logger().debug('Published merged map')

def main(args=None):
    rclpy.init(args=args)
    node = MapMerger()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
