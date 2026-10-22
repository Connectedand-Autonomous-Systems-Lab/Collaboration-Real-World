"""Bring up Jackal RViz, SLAM and Nav2 together.

Equivalent to running, in order:
  ros2 launch clearpath_viz view_navigation.launch.py namespace:=/j100_0953
  ros2 launch clearpath_nav2_demos slam.launch.py setup_path:=... scan_topic:=...
  ros2 launch clearpath_nav2_demos nav2.launch.py setup_path:=... scan_topic:=...

Usage:
  ros2 launch collaborate jackal_nav.launch.py
  ros2 launch collaborate jackal_nav.launch.py nav2_delay:=10.0
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    setup_path = LaunchConfiguration('setup_path')
    scan_topic = LaunchConfiguration('scan_topic')
    nav2_delay = LaunchConfiguration('nav2_delay')

    args = [
        DeclareLaunchArgument('namespace', default_value='/j100_0953'),
        DeclareLaunchArgument(
            'setup_path',
            default_value='/home/mayooran/Documents/Jackal_startup/clearpath/'),
        DeclareLaunchArgument(
            'scan_topic',
            default_value='/j100_0953/sensors/lidar3d_0/scan'),
        DeclareLaunchArgument(
            'nav2_delay', default_value='5.0',
            description='Seconds to wait after SLAM starts before launching Nav2'),
    ]

    viz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('clearpath_viz'), 'launch', 'view_navigation.launch.py'])),
        launch_arguments={
            'namespace': namespace,
            'config': '/home/mayooran/Documents/Concord_realworld/src/collaborate/rviz/jackal_nav.rviz',
        }.items(),
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('collaborate'), 'launch', 'slam.launch.py'])),
        launch_arguments={'setup_path': setup_path,
                          'scan_topic': scan_topic}.items(),
    )

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('collaborate'), 'launch', 'jackal_slam_toolbox.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'slam_params_file': os.path.join(get_package_share_directory('collaborate'), 'config', 'jackal.yaml'),
        }.items()
    )   

    static_tf_scan = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='scan_to_jackal_scan',
        arguments=[
            '--x', '0.0', '--y', '0.0', '--z', '0.0',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',   # radians
            '--frame-id', 'j100_0953/lidar3d_0_scan_link',               # parent
            '--child-frame-id', 'lidar3d_0_scan_link',  # child
        ],
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', 'src/hololens_ros2_bridge/rviz/collaborate.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time': False}]
    )

    tf_relay = Node(
        package='tf_relay',
        executable='jackal_relay',
    )   

    # Nav2 starts after a delay so SLAM has time to publish map -> odom.
    nav2 = TimerAction(
        period=nav2_delay,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('collaborate'), 'launch', 'nav2.launch.py'])),
            launch_arguments={'setup_path': setup_path,
                              'scan_topic': scan_topic}.items(),
        )],
    )

    # return LaunchDescription(args + [rviz2, static_tf_scan, slam_toolbox])
    return LaunchDescription(args + [rviz2, static_tf_scan, tf_relay, slam_toolbox, nav2])
    # return LaunchDescription(args + [viz])
    # return LaunchDescription(args + [slam, viz])
    # return LaunchDescription(args + [slam, nav2])
    # return LaunchDescription(args + [viz, slam])
    # return LaunchDescription(args + [viz, slam, nav2])