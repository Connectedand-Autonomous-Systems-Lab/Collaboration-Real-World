import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import TransformStamped
import numpy as np
import tf2_ros
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
        self.declare_parameter('map1_x_offset', 0.0)
        self.declare_parameter('map1_y_offset', 0.0)
        self.declare_parameter('map1_rotate_180', False)
        self.declare_parameter('map2_x_offset', 0.0)
        self.declare_parameter('map2_y_offset', 10.0)

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
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.publish_timer = self.create_timer(self.publish_period, self.try_merge_maps)
        # Store maps
        self.map1 = None
        self.map2 = None
        self.map_placements = {}

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
    
    def try_merge_map_orig(self):
        if self.map1 is None or self.map2 is None:
            return

        if self.map1.info.resolution != self.map2.info.resolution:
            self.get_logger().warn('Source maps have different resolutions; skipping merge')
            return

        resolution = self.map1.info.resolution
        map1_origin_x = self.map1.info.origin.position.x + self.get_parameter('map1_x_offset').value
        map1_origin_y = self.map1.info.origin.position.y + self.get_parameter('map1_y_offset').value
        map2_origin_x = self.map2.info.origin.position.x + self.get_parameter('map2_x_offset').value
        map2_origin_y = self.map2.info.origin.position.y + self.get_parameter('map2_y_offset').value

        min_x = min(map1_origin_x, map2_origin_x)
        min_y = min(map1_origin_y, map2_origin_y)
        max_x = max(
            map1_origin_x + self.map1.info.width * resolution,
            map2_origin_x + self.map2.info.width * resolution
        )
        max_y = max(
            map1_origin_y + self.map1.info.height * resolution,
            map2_origin_y + self.map2.info.height * resolution
        )

        merged_width = math.ceil((max_x - min_x) / resolution)
        merged_height = math.ceil((max_y - min_y) / resolution)
        merged_data = np.full((merged_height, merged_width), -1, dtype=np.int8)
        self.map_placements = {}

        self.get_logger().debug(
            'Effective map origins after offsets: '
            f'map1=({map1_origin_x:.3f}, {map1_origin_y:.3f}), '
            f'map2=({map2_origin_x:.3f}, {map2_origin_y:.3f}), '
            f'resolution={resolution:.3f}'
        )

        for name, delta_x, delta_y in (
            ('map1', self.get_parameter('map1_x_offset').value, self.get_parameter('map1_y_offset').value),
            ('map2', self.get_parameter('map2_x_offset').value, self.get_parameter('map2_y_offset').value),
        ):
            if not math.isclose(delta_x / resolution, round(delta_x / resolution), abs_tol=1e-6):
                self.get_logger().warn(
                    f'{name}_x_offset={delta_x:.3f} m is not aligned to the map resolution '
                    f'({resolution:.3f} m), so placement will be rounded to the nearest cell'
                )
            if not math.isclose(delta_y / resolution, round(delta_y / resolution), abs_tol=1e-6):
                self.get_logger().warn(
                    f'{name}_y_offset={delta_y:.3f} m is not aligned to the map resolution '
                    f'({resolution:.3f} m), so placement will be rounded to the nearest cell'
                )

        def place_map(map_msg, origin_x, origin_y, rotate_180=False):
            offset_x = int(round((origin_x - min_x) / resolution))
            offset_y = int(round((origin_y - min_y) / resolution))
            h = map_msg.info.height
            w = map_msg.info.width
            frame_id = map_msg.header.frame_id

            map_data = np.array(map_msg.data, dtype=np.int8).reshape((h, w))
            if rotate_180:
                map_data = np.rot90(map_data, 2)
            max_y_merge = merged_data.shape[0]
            max_x_merge = merged_data.shape[1]

            clip_h = min(h, max_y_merge - offset_y)
            clip_w = min(w, max_x_merge - offset_x)

            if clip_h <= 0 or clip_w <= 0:
                self.get_logger().warn('Map placement is completely outside merged area; skipping')
                return

            clipped_map = map_data[:clip_h, :clip_w]
            valid_mask = clipped_map != -1
            target = merged_data[offset_y:offset_y + clip_h, offset_x:offset_x + clip_w]
            np.putmask(target, valid_mask, np.maximum(target, clipped_map))

            if frame_id:
                placement_x = offset_x * resolution
                placement_y = offset_y * resolution
                yaw = math.pi if rotate_180 else 0.0

                if rotate_180:
                    placement_x += w * resolution
                    placement_y += h * resolution

                self.map_placements[frame_id] = {
                    'x': placement_x,
                    'y': placement_y,
                    'yaw': yaw,
                }

        place_map(
            self.map1,
            map1_origin_x,
            map1_origin_y,
            rotate_180=self.get_parameter('map1_rotate_180').value,
        )
        place_map(self.map2, map2_origin_x, map2_origin_y)

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
        self.publish_map_transforms()
        self.get_logger().debug('Published merged map')

    def try_merge_maps(self):
        if self.map1 is None or self.map2 is None:
            return

        if self.map1.info.resolution != self.map2.info.resolution:
            self.get_logger().warn('Source maps have different resolutions; skipping merge')
            return

        resolution = self.map1.info.resolution
        map1_origin_x = self.map1.info.origin.position.x + self.get_parameter('map1_x_offset').value
        map1_origin_y = self.map1.info.origin.position.y + self.get_parameter('map1_y_offset').value
        map2_origin_x = self.map2.info.origin.position.x + self.get_parameter('map2_x_offset').value
        map2_origin_y = self.map2.info.origin.position.y + self.get_parameter('map2_y_offset').value

        # min_x = min(map1_origin_x, map2_origin_x)
        # min_y = min(map1_origin_y, map2_origin_y)
        min_x = -50.0
        min_y = -50.0
        merged_width = 2000
        merged_height = 2000
        merged_data = np.full((merged_height, merged_width), -1, dtype=np.int8)
        self.map_placements = {}

        def place_map(map_msg, origin_x, origin_y, rotate_180=False):
            
            h = map_msg.info.height
            w = map_msg.info.width
            frame_id = map_msg.header.frame_id
            top_right = [origin_x + w * resolution, origin_y + h * resolution]
            max_x = min_x + merged_width * resolution
            max_y = min_y + merged_height * resolution

            map_data = np.array(map_msg.data, dtype=np.int8).reshape((h, w))
            if rotate_180:
                map_data = np.rot90(map_data, 2)
                map_data = self.mark_corners_with_cross(map_data, value_bl=1, value_tr=100, size=10, thickness=3)    
                offset_x = int(round((max_x - top_right[0]) / resolution))
                offset_y = int(round((max_y - top_right[1]) / resolution))
            else:
                map_data = self.mark_corners_with_cross(map_data)    
                offset_x = int(round((origin_x - min_x) / resolution))
                offset_y = int(round((origin_y - min_y) / resolution))

            max_y_merge = merged_data.shape[0]
            max_x_merge = merged_data.shape[1]

            clip_h = min(h, max_y_merge - offset_y)
            clip_w = min(w, max_x_merge - offset_x)

            if clip_h <= 0 or clip_w <= 0:
                self.get_logger().warn('Map placement is completely outside merged area; skipping')
                return

            clipped_map = map_data[:clip_h, :clip_w]
            valid_mask = clipped_map != -1
            target = merged_data[offset_y:offset_y + clip_h, offset_x:offset_x + clip_w]
            np.putmask(target, valid_mask, np.maximum(target, clipped_map))

            if frame_id:
                placement_x = offset_x * resolution
                placement_y = offset_y * resolution
                yaw = math.pi if rotate_180 else 0.0

                if rotate_180:
                    placement_x += w * resolution
                    placement_y += h * resolution

                self.map_placements[frame_id] = {
                    'x': placement_x,
                    'y': placement_y,
                    'yaw': yaw,
                }

        place_map(
            self.map1,
            map1_origin_x,
            map1_origin_y,
            rotate_180=self.get_parameter('map1_rotate_180').value,
        )
        place_map(self.map2, map2_origin_x, map2_origin_y)

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
        self.publish_map_transforms()
        self.get_logger().debug('Published merged map')

    def publish_map_transforms(self):
        for frame_id, placement in self.map_placements.items():
            transform = TransformStamped()
            transform.header.stamp = self.get_clock().now().to_msg()
            transform.header.frame_id = self.merged_map_frame
            transform.child_frame_id = frame_id
            transform.transform.translation.x = placement['x']
            transform.transform.translation.y = placement['y']
            transform.transform.translation.z = 0.0
            yaw = placement.get('yaw', 0.0)
            transform.transform.rotation.x = 0.0
            transform.transform.rotation.y = 0.0
            transform.transform.rotation.z = math.sin(yaw / 2.0)
            transform.transform.rotation.w = math.cos(yaw / 2.0)
            self.tf_broadcaster.sendTransform(transform)

def main(args=None):
    rclpy.init(args=args)
    node = MapMerger()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
