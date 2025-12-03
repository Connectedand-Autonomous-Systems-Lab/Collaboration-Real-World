from launch import LaunchDescription
from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    tf_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='tf_publisher',
        name='tf_publisher',
        output='screen'
    )

    si_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='si_publisher',
        name='si_publisher',
        output='screen'
    )

    sm_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='sm_publisher',
        name='sm_publisher',
        output='screen'
    )

    pointcloud_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='pointcloud_publisher',
        name='pointcloud_publisher',
        output='screen'
    )

    depth_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='depth_publisher',
        name='depth_publisher',
        output='screen'
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
            'output_frame': 'odom',
        }],
        )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', 'src/hololens_ros2_bridge/rviz/hololens.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time': True}]
    )

    # human_bag = ExecuteProcess(
    #     cmd=['ros2', 'bag', 'play', '/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge/rosbag/run2', '--topics', '/hololens/si/head_orientation', '/hololens/si/head_position', '/hololens/sm/pcd', '/point_cloud2', '/scan', '/tf', '/tf_static'],
    #     output='screen'
    # )

    human_bag = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', '/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge/rosbag/oakd_on_hl/full_round_gitc4/rosbag2_2025_11_30-16_59_25'],
        output='screen'
    )
    
    pointcloud_to_laserscan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[
            ('cloud_in', 'point_cloud2'),
            ('scan', 'scan'),
        ],
        parameters=[{
            'max_height': 2.0,
            'min_height': -0.5
        }],
        output='screen',
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


    return LaunchDescription([
        # tf_publisher_node,
        # si_publisher_node,
        # sm_publisher_node,
        # pointcloud_publisher_node,
        # depth_publisher_node,
        # depth_image_to_laserscan_node,
        rviz_node,
        # pointcloud_to_laserscan_node,
        slam_toolbox,
        human_bag
    ])
