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

###############################################################################

# So far, this works well on the following setting:
# - Orbi wifi
# - Simple discovery
# - No namespace

################################################################################

def generate_launch_description():
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': "/home/mayooran/Documents/hololens_ros2_bridge/src/basic_turtlebot4/config/robot_odom.yaml",
        }.items()
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
        arguments=['robot', '1'],  # same as: ros2 run tf_relay relay 'tb' 1
        output='screen',
    )

    human_bag = ExecuteProcess(
            cmd=['ros2', 'bag', 'play', '/media/2TB/Collaborative_user_study_real_world/Mohammed/run5/rosbag2_2025_12_04-19_56_22', ],
            output='screen'
        )

    wavefront_frontier_publisher = Node(
        package='human_robot_pkg',
        executable='wavefront_frontier_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'map_topic': '/robot_0/map',  # <- your map topic here
            # optional:
            'odom_topic': '/robot_0/odom',
            # 'frontiers_topic': '/frontiers',
            # 'markers_topic': '/frontier_markers',
            # 'publish_rate_hz': 1.0,
            'frame_id': 'map',
        }]
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

    rviz2 = ExecuteProcess(
        cmd=['rviz2', '-d','/home/mayooran/Documents/hololens_ros2_bridge/src/basic_turtlebot4/rviz2/discovery_server.rviz'],
        output='screen'
    )

    return LaunchDescription([
        GroupAction([
            SetRemap(src='/map', dst='/robot_0/map'),
            PushRosNamespace('robot_0/'),
            slam_launch,
            # nav2
        ]),

        # slam_launch,
        # nav2,
        rviz2,
        tf_relay,
        # depth_image_to_laserscan_node
        # wavefront_frontier_publisher,
        # human_bag,
    ])
