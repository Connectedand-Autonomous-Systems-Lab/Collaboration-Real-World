# map_merge_testbed

Small ROS 2 test package for publishing two occupancy-grid maps at the same time.

## What it gives you

- `robot1/map` and `robot2/map` published simultaneously
- Two different sample maps in `maps/`
- Static transforms from `world` to each map frame for RViz visualization

## Build

```bash
colcon build --packages-select map_merge_testbed
source install/setup.bash
```

## Run

```bash
ros2 launch map_merge_testbed publish_test_maps.launch.py
```

This launch file publishes:

- `/robot1/map` with frame `robot1_map`
- `/robot2/map` with frame `robot2_map`

If your merger expects known initial poses, the launch file places the second map at:

- `x = 1.6`
- `y = 0.8`
- `yaw = 0.0`
