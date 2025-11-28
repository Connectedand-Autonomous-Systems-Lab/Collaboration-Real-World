from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction

def generate_launch_description():
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('turtlebot4_navigation'),
                'launch',
                'slam.launch.py'
            ])
        ])
        # launch_arguments={
        #     'use_sim_time': 'true',
        #     'slam_params_file': os.path.join(get_package_share_directory('basic_turtlebot4'), 'config', 'tb.yaml'),
        # }.items()
    )

    # tf_relay = Node(
    #     package="tf_relay",
    #     executable="relay",
    #     name="relay"        
    # )

    tf_relay = Node(
        package='tf_relay',
        executable='relay',
        name='tf_relay_tb',
        arguments=['tb', '1'],  # same as: ros2 run tf_relay relay 'tb' 1
        output='screen',
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('turtlebot4_navigation'),
                'launch',
                'nav2.launch.py'
            ])
        ])
    )

    depth_image_to_laserscan_node = Node(
        package='depthimage_to_laserscan',
        executable='depthimage_to_laserscan_node',
        name='depth_image_to_laserscan',
        remappings=[
            ('depth', 'hololens/depth'),
            ('depth_camera_info', 'hololens/depth_cameraInfo'),
        ],  
        parameters=[{
            'output_frame': 'hololens',
        }],
        )

    rviz2 = ExecuteProcess(
        cmd=['rviz2', '-d','/home/mayooran/Documents/hololens_ros2_bridge/src/basic_turtlebot4/rviz2/basic_setup.rviz'],
        output='screen'
    )

    return LaunchDescription([
        GroupAction([
            PushRosNamespace('tb_0/'),
            # SetRemap(src='/tf', dst='/tb/tf'),
            # SetRemap(src='/tf_static', dst='/tb/tf_static'),
            slam_launch,
            # nav2
        ]),

        # slam_launch,
        # nav2,
        rviz2,
        tf_relay
        # depth_image_to_laserscan_node
    ])
