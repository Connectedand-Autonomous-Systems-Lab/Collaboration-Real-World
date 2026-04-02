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
    map1_rotate_180 = LaunchConfiguration('map1_rotate_180')
    # map1_x_offset = LaunchConfiguration('map1_x_offset')
    # map1_y_offset = LaunchConfiguration('map1_y_offset')
    # map2_x_offset = LaunchConfiguration('map2_x_offset')
    # map2_y_offset = LaunchConfiguration('map2_y_offset')

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

    merge_map = Node(
        package='map_merge_testbed',
        executable='map_merge',
        name='map_merge',
        output='screen',
        parameters=[
            {
                'map1_topic': '/robot1/map',
                'map2_topic': '/robot2/map',
                'merged_map_topic': '/merged_map',
                'merged_map_frame': 'map',
                'publish_period': 1.0,
                'map1_x_offset': 0.0,
                'map1_y_offset': 0.0,
                'map1_rotate_180': map1_rotate_180,
                'map2_x_offset': 0.0,
                'map2_y_offset': 10.0,
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

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', '/home/mayooran/.rviz2/merged_map_test.rviz'],
    )   

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'publish_period',
                default_value='1.0',
                description='Seconds between map republishes.',
            ),
            DeclareLaunchArgument(
                'map1_rotate_180',
                default_value='true',
                description='Rotate map1 by 180 degrees before merging.',
            ),
            DeclareLaunchArgument(
                'map1_x_offset',
                default_value='0.0',
                description='Additional X offset in meters applied to map1 before merge.',
            ),
            DeclareLaunchArgument(
                'map1_y_offset',
                default_value='0.0',
                description='Additional Y offset in meters applied to map1 before merge.',
            ),
            DeclareLaunchArgument(
                'map2_x_offset',
                default_value='0.0',
                description='Additional X offset in meters applied to map2 before merge.',
            ),
            DeclareLaunchArgument(
                'map2_y_offset',
                default_value='0.0',
                description='Additional Y offset in meters applied to map2 before merge.',
            ),
            robot1_publisher,
            robot2_publisher,
            robot1_tf,
            robot2_tf,
            rviz2,
            merge_map,
        ]
    )
