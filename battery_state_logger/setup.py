from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'battery_state_logger'

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
    description='Logs battery state and power to CSV with summary.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'battery_state_logger = battery_state_logger.battery_state_logger:main',
        ],
    },
)
