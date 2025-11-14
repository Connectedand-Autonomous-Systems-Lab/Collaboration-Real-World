from launch import LaunchDescription
from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', 'src/basic_turtlebot4/rviz2/oakd.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time': True}]
    )


    oakd_publisher_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('depthai_ros_driver'), 'launch', 'rgbd_pcl.launch.py')
        )
    )   
    
    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': os.path.join(get_package_share_directory('basic_turtlebot4'), 'config', 'oakd.yaml'),
        }.items()
    )   

    depth_image_to_laserscan_node = Node(
        package='depthimage_to_laserscan',
        executable='depthimage_to_laserscan_node',
        name='depth_image_to_laserscan',
        remappings=[
            ('depth', 'oak/stereo/image_raw'),
            ('depth_camera_info', 'oak/stereo/camera_info'),
            ('/scan', 'oakd/scan'),
        ],  
        parameters=[{
            'output_frame': 'oak-d-base-frame',
        }],
        )


    return LaunchDescription([
        rviz_node,
        # oakd_publisher_node,
        depth_image_to_laserscan_node,
        slam_toolbox,
    ])
