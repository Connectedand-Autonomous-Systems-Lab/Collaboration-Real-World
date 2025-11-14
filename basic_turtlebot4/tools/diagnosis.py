import subprocess

# Simple command
subprocess.run(["ros2","daemon","stop"])
subprocess.run(["ros2","daemon","start"])