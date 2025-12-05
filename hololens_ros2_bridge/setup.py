from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'hololens_ros2_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('params', '*.yaml')))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mayooran',
    maintainer_email='mayoo4234@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tf_publisher = hololens_ros2_bridge.tf_publisher:main',
            'pointcloud_publisher = hololens_ros2_bridge.pointcloud_publisher:main',
            'si_publisher = hololens_ros2_bridge.si_publisher:main',
            'sm_publisher = hololens_ros2_bridge.sm_publisher:main',
            'pcd_logger = hololens_ros2_bridge.pointcloud_logger:main',
            'depth_publisher = hololens_ros2_bridge.depth_publisher:main',
            'pv_publisher = hololens_ros2_bridge.pv_publisher:main',
            'thread_publisher = hololens_ros2_bridge.thread_publisher:main',
            'image_publisher = hololens_ros2_bridge.image_publisher:main',
            'si_publisher_new = hololens_ros2_bridge.si_publisher_new:main',
            'keyboard_publisher = hololens_ros2_bridge.keyboard_publisher:main',
        ],
    },
)
