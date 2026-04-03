import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction, DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node, PushRosNamespace
from launch.substitutions import LaunchConfiguration

def find_rosbag(parent_dir):
    folders = os.listdir(parent_dir)
    for folder in folders:
        if folder.startswith("rosbag2"):
            return parent_dir + "/" + folder

def generate_launch_description():
    package_name = 'human_robot_pkg'
    hololens_ros2_bridge_dir = '/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge'
    
    human_bag = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', find_rosbag('/media/2TB/Collaborative_user_study_real_world/Raj/run1'), '--remap', '/tf:=/human/tf', '/scan:=/human/scan'],
        output='screen'
    )

    tf_rewrite = Node(
        package='basic_turtlebot4',
        executable='tf_rewrite',
        name='tf_rewrite',
        output='screen',
    )
    
    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            # '--remap': '__node:=/human/slam_toolbox',
            # 'use_sim_time': 'true',
            'slam_params_file': os.path.join(get_package_share_directory('hololens_ros2_bridge'), 'config', 'hololens.yaml'),
        }.items()
    )

    print(os.path.join(get_package_share_directory('hololens_ros2_bridge'), 'config', 'hololens.yaml'))

    # slam_toolbox = Node(
    #     package='slam_toolbox',
    #     executable='async_slam_toolbox_node',
    #     name='human_slam_toolbox',
    #     output='screen',
    #     parameters=[
    #         os.path.join(hololens_ros2_bridge_dir, 'config', 'hololens.yaml')
    #     ],
    # )
    

    # slam_toolbox_human = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'online_async_launch.py')
    #     ),
    #     launch_arguments={
    #         'use_sim_time': 'true',
    #         # 'namespace':''
    #     }.items()
    # )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', 'src/hololens_ros2_bridge/rviz/human_only.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time':True}]
    )

    wavefront_frontier_publisher = Node(
        package='human_robot_pkg',
        executable='wavefront_frontier_publisher',
        output='screen',
        parameters=[{'use_sim_time':True},
                    {'map_topic': '/human/map'},
                    {'odom_topic': '/human/odom'},
                    {'frame_id': 'human/map'}]
    )

    odom_publisher = Node(
        package="hololens_ros2_bridge",
        executable="odom_publisher"
    )

    return LaunchDescription({
        GroupAction([
            PushRosNamespace('human'),
            slam_toolbox,
        ]),
        human_bag,
        tf_rewrite,
        # rviz2,
        # wavefront_frontier_publisher,
        # slam_toolbox,
        # odom_publisher,
    
    })
