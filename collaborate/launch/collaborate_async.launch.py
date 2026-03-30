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

def find_rosbag(parent_dir):
    folders = os.listdir(parent_dir)
    for folder in folders:
        if folder.startswith("rosbag2"):
            return parent_dir + "/" + folder

def generate_launch_description():
    
    human = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('collaborate'), 'launch', 'human_only_replay.launch.py')
        ),
    )

    # turtlebot = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(get_package_share_directory('basic_turtlebot4'), 'launch', 'discovery_server.launch.py')
    #     ),
    # )

    turtlebot = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', find_rosbag('src/hololens_ros2_bridge/rosbag/tb_simple_teleop')],
        output='screen'
    )

    merge_map = Node(
        package='map_merge_testbed',
        executable='map_merge',
        name='map_merge',
        output='screen',
        parameters=[
            {
                'map1_topic': '/robot_0/map',
                'map2_topic': '/map',
                'merged_map_topic': '/merged_map',
                'merged_map_frame': 'merged_map',
                'publish_period': 1.0,
                'map1_x_offset': 0.0,
                'map1_y_offset': 0.0,
                'map1_rotate_180': True,
                'map2_x_offset': 0.0,
                'map2_y_offset': 0.0,
            }
        ],
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', 'src/hololens_ros2_bridge/rviz/collaborate.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time':True}]
    )

    return LaunchDescription([
        human,
        turtlebot,
        rviz2,
        merge_map,
    ])
