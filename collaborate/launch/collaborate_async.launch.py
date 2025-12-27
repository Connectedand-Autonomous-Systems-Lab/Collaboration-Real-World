from launch import LaunchDescription
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch import LaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.actions import IncludeLaunchDescription, GroupAction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    
    hololens_bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('hololens_ros2_bridge'), 'launch', 'hololens_ros2_bridge.launch.py'
        ))
    )

    tf_relay = Node(
            package='tf_relay',
            executable='relay',
            name='tf_relay_tb',
            arguments=['tb', '1'],  # same as: ros2 run tf_relay relay 'tb' 1
            output='screen',
        )
    
    turtlebot4_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('basic_turtlebot4'), 'launch', 'slam.launch.py'
        ))
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', 'src/collaborate/rviz/collaborate.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time': True}]
    )

    map_merge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('multirobot_map_merge'), 'launch', 'map_merge.launch.py'
        ))
    )

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': os.path.join(get_package_share_directory('hololens_ros2_bridge'), 'config', 'mapper_params_online_async.yaml'),
        }.items()
    )   

    human_bag = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', '/media/2TB/Collaborative_user_study_real_world/Mayooran/with_identification/rosbag2_2025_12_04-20_33_56'],
        output='screen'
    )

    return LaunchDescription([

        rviz_node,
        # hololens_bridge_launch,
        human_bag,
        slam_toolbox,
        # turtlebot4_launch,
        # map_merge_launch,
        # GroupAction([
        #     PushRosNamespace('human/'),
        #     hololens_bridge_launch
        # ]),
    ])
