from launch import LaunchDescription
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction
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

    return LaunchDescription([

        rviz_node,
        tf_relay,
        # hololens_bridge_launch,
        # turtlebot4_launch,

        GroupAction([
            PushRosNamespace('tb_0/'),
            # SetRemap(src='/tf', dst='/tb/tf'),
            # SetRemap(src='/tf_static', dst='/tb/tf_static'),
            turtlebot4_launch
        ]),
        # GroupAction([
        #     PushRosNamespace('human/'),
        #     hololens_bridge_launch
        # ]),
    ])
