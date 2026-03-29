import os
from typing import List, Tuple

import rclpy
import yaml
from nav_msgs.msg import MapMetaData, OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


def _tokenize_pgm(raw_bytes: bytes) -> List[str]:
    tokens: List[str] = []
    current = bytearray()
    in_comment = False

    for byte in raw_bytes:
        char = chr(byte)
        if in_comment:
            if char == '\n':
                in_comment = False
            continue
        if char == '#':
            in_comment = True
            continue
        if char.isspace():
            if current:
                tokens.append(current.decode('ascii'))
                current.clear()
            continue
        current.append(byte)

    if current:
        tokens.append(current.decode('ascii'))

    return tokens


def load_ascii_pgm(path: str) -> Tuple[int, int, int, List[int]]:
    with open(path, 'rb') as pgm_file:
        tokens = _tokenize_pgm(pgm_file.read())

    if len(tokens) < 4:
        raise ValueError(f'Invalid PGM file: {path}')
    if tokens[0] != 'P2':
        raise ValueError(
            f'Unsupported PGM format in {path}: {tokens[0]}. '
            'This test package expects ASCII P2 PGM files.'
        )

    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    pixels = [int(value) for value in tokens[4:]]

    if len(pixels) != width * height:
        raise ValueError(
            f'PGM pixel count mismatch in {path}: '
            f'expected {width * height}, got {len(pixels)}'
        )

    return width, height, max_value, pixels


def pgm_to_occupancy(
    pixels: List[int],
    max_value: int,
    occupied_thresh: float,
    free_thresh: float,
    negate: bool,
) -> List[int]:
    occupancy_values: List[int] = []

    for pixel in pixels:
        normalized = float(pixel) / float(max_value)
        if negate:
            normalized = 1.0 - normalized

        occupancy_probability = 1.0 - normalized

        if occupancy_probability >= occupied_thresh:
            occupancy_values.append(100)
        elif occupancy_probability <= free_thresh:
            occupancy_values.append(0)
        else:
            occupancy_values.append(-1)

    return occupancy_values


class OccupancyGridPublisher(Node):
    def __init__(self) -> None:
        super().__init__('occupancy_grid_publisher')

        self.declare_parameter('map_yaml', '')
        self.declare_parameter('topic_name', 'map')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('publish_period', 1.0)

        map_yaml = self.get_parameter('map_yaml').get_parameter_value().string_value
        topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        publish_period = (
            self.get_parameter('publish_period').get_parameter_value().double_value
        )

        if not map_yaml:
            raise ValueError('Parameter "map_yaml" is required.')

        qos_profile = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(OccupancyGrid, topic_name, qos_profile)
        self.map_message = self._load_map_message(map_yaml, frame_id)

        self.publish_map()
        self.timer = self.create_timer(publish_period, self.publish_map)

        self.get_logger().info(
            f'Publishing {map_yaml} on "{self.publisher.topic_name}" '
            f'with frame "{frame_id}" every {publish_period:.2f}s'
        )

    def _load_map_message(self, map_yaml_path: str, frame_id: str) -> OccupancyGrid:
        with open(map_yaml_path, 'r', encoding='utf-8') as yaml_file:
            metadata = yaml.safe_load(yaml_file)

        image_path = metadata['image']
        if not os.path.isabs(image_path):
            image_path = os.path.join(os.path.dirname(map_yaml_path), image_path)

        width, height, max_value, pixels = load_ascii_pgm(image_path)
        occupancy_data = pgm_to_occupancy(
            pixels=pixels,
            max_value=max_value,
            occupied_thresh=float(metadata['occupied_thresh']),
            free_thresh=float(metadata['free_thresh']),
            negate=bool(metadata.get('negate', 0)),
        )

        map_message = OccupancyGrid()
        map_message.header.frame_id = frame_id

        info = MapMetaData()
        info.resolution = float(metadata['resolution'])
        info.width = width
        info.height = height
        info.origin.position.x = float(metadata['origin'][0])
        info.origin.position.y = float(metadata['origin'][1])
        info.origin.position.z = 0.0
        info.origin.orientation.w = 1.0
        map_message.info = info
        map_message.data = occupancy_data

        return map_message

    def publish_map(self) -> None:
        self.map_message.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(self.map_message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = OccupancyGridPublisher()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
