from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'basic_turtlebot4'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
            # Install launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        # Optionally install RViz config or other files
        (os.path.join('share', package_name, 'rviz2'), glob('rviz2/*.rviz')),
        ('share/' + package_name, ['package.xml']),
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
            'rotate_map = basic_turtlebot4.rotate_map_node:main',
            'tf_rewrite = basic_turtlebot4.tf_rewrite:main',
        ],
    },
)
