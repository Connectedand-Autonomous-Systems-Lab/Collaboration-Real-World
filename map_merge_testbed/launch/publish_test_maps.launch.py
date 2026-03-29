import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory('map_merge_testbed')
    robot1_map = os.path.join(package_share, 'maps', 'map_a.yaml')
    robot2_map = os.path.join(package_share, 'maps', 'map_b.yaml')
    publish_period = LaunchConfiguration('publish_period')

    robot1_publisher = Node(
        package='map_merge_testbed',
        executable='occupancy_grid_publisher',
        namespace='robot1',
        name='map_publisher',
        output='screen',
        parameters=[
            {
                'map_yaml': robot1_map,
                'topic_name': 'map',
                'frame_id': 'robot1_map',
                'publish_period': publish_period,
            }
        ],
    )

    robot2_publisher = Node(
        package='map_merge_testbed',
        executable='occupancy_grid_publisher',
        namespace='robot2',
        name='map_publisher',
        output='screen',
        parameters=[
            {
                'map_yaml': robot2_map,
                'topic_name': 'map',
                'frame_id': 'robot2_map',
                'publish_period': publish_period,
            }
        ],
    )

    robot1_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='robot1_map_tf',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'robot1_map',  'robot1_odom'],
    )

    robot2_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='robot2_map_tf',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'robot2_map', 'robot2_odom'],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'publish_period',
                default_value='1.0',
                description='Seconds between map republishes.',
            ),
            robot1_publisher,
            robot2_publisher,
            robot1_tf,
            robot2_tf,
        ]
    )
