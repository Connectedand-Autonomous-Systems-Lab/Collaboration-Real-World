from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'map_merge_testbed'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
        (os.path.join('share', package_name), ['README.md']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mayooran',
    maintainer_email='mayoo4234@gmail.com',
    description='Test maps and publishers for occupancy-grid map merging experiments.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'occupancy_grid_publisher = map_merge_testbed.occupancy_grid_publisher:main',
            'map_merge = map_merge_testbed.merge_map:main',
        ],
    },
)
