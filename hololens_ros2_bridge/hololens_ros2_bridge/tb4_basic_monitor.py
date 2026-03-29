#!/usr/bin/env python3

import argparse
import threading
import time
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time

from sensor_msgs.msg import BatteryState
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage

# These are commonly available on TurtleBot4 / Create3 installs.
# If your message package names differ, adjust here.
from irobot_create_msgs.msg import WheelStatus

from tf2_ros import Buffer


def normalize_namespace(namespace: str) -> str:
    namespace = (namespace or '').strip()
    if not namespace or namespace == '/':
        return ''
    return f"/{namespace.strip('/')}"


def namespaced_name(namespace: str, name: str) -> str:
    namespace = normalize_namespace(namespace)
    name = name.strip()
    if not namespace:
        return name
    return f"{namespace}/{name.lstrip('/')}"


class TB4MonitorNode(Node):
    def __init__(self, robot_namespace: str = '/robot_0'):
        self.robot_namespace = normalize_namespace(robot_namespace)
        super().__init__('tb4_basic_monitor')

        self.frame_prefix = self.robot_namespace.strip('/')

        # -----------------------------
        # Internal state
        # -----------------------------
        self.latest_battery = None
        self.start_battery_pct = None
        self.latest_ip = None
        self.last_battery_time = 0.0
        self.last_ip_time = 0.0
        self.last_wheel_time = 0.0
        self.latest_wheel_msg = None

        # -----------------------------
        # TF
        # -----------------------------
        self.tf_buffer = Buffer()
        tf_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        tf_static_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.create_subscription(
            TFMessage,
            namespaced_name(self.robot_namespace, 'tf'),
            self.tf_cb,
            tf_qos,
        )
        self.create_subscription(
            TFMessage,
            namespaced_name(self.robot_namespace, 'tf_static'),
            self.tf_static_cb,
            tf_static_qos,
        )

        # -----------------------------
        # ROS subscriptions
        # -----------------------------
        self.create_subscription(
            BatteryState,
            namespaced_name(self.robot_namespace, 'battery_state'),
            self.battery_cb,
            10,
        )
        self.create_subscription(
            String,
            namespaced_name(self.robot_namespace, 'ip'),
            self.ip_cb,
            10,
        )
        self.create_subscription(
            WheelStatus,
            namespaced_name(self.robot_namespace, 'wheel_status'),
            self.wheel_cb,
            10,
        )

    def display_namespace(self):
        return self.robot_namespace or '/'

    def battery_cb(self, msg: BatteryState):
        self.latest_battery = msg
        self.last_battery_time = time.time()

        if self.start_battery_pct is None and msg.percentage >= 0.0:
            # sensor_msgs/BatteryState percentage is usually 0.0 to 1.0
            self.start_battery_pct = msg.percentage * 100.0

    def ip_cb(self, msg: String):
        self.latest_ip = msg.data.strip()
        self.last_ip_time = time.time()

    def wheel_cb(self, msg: WheelStatus):
        self.latest_wheel_msg = msg
        self.last_wheel_time = time.time()

    def tf_cb(self, msg: TFMessage):
        for transform in msg.transforms:
            self.tf_buffer.set_transform(transform, 'tb4_basic_monitor')

    def tf_static_cb(self, msg: TFMessage):
        for transform in msg.transforms:
            self.tf_buffer.set_transform_static(transform, 'tb4_basic_monitor')

    # -----------------------------
    # Helper checks
    # -----------------------------
    def battery_percent_now(self):
        if self.latest_battery is None:
            return None

        p = self.latest_battery.percentage
        if p < 0.0:
            return None
        return p * 100.0

    def battery_led_color(self):
        """Approximate TB4 BATTERY status LED color from battery percentage."""
        pct = self.battery_percent_now()
        if pct is None:
            return "UNKNOWN"

        # Approximation based on documented battery color behavior.
        if pct >= 50.0:
            return "GREEN"
        elif pct >= 20.0:
            return "YELLOW"
        else:
            return "RED"

    def comms_ok(self):
        # If battery_state is arriving recently, comms to robot are probably alive.
        return (time.time() - self.last_battery_time) < 3.0

    def wifi_ok(self):
        return bool(self.latest_ip)

    def motor_enabled(self):
        """
        Try to read a likely field name from WheelStatus.
        Message definitions can vary slightly by distro/version, so we check a few names.
        """
        if self.latest_wheel_msg is None:
            return None

        candidate_fields = [
            'wheels_enabled',
            'enabled',
            'is_enabled',
        ]

        for field in candidate_fields:
            if hasattr(self.latest_wheel_msg, field):
                return bool(getattr(self.latest_wheel_msg, field))

        return None

    def frame_candidates(self, frame: str):
        frame = frame.lstrip('/')
        return [frame, f'/{frame}']

    def tf_ok(self, parent: str, child: str):
        for parent_frame in self.frame_candidates(parent):
            for child_frame in self.frame_candidates(child):
                try:
                    if self.tf_buffer.can_transform(parent_frame, child_frame, Time()):
                        return True
                except Exception:
                    continue

        return False


class TB4MonitorGUI:
    def __init__(self, root, ros_node: TB4MonitorNode):
        self.root = root
        self.node = ros_node

        self.root.title("TurtleBot4 Basic Monitor")
        self.root.geometry("760x520")

        # Easy to extend later
        self.required_tfs = [
            ('odom', 'base_link'),
            ('base_link', 'rplidar_link'),
            ('base_link', 'oakd_link'),
        ]

        # If you use localization / SLAM later, add:
        # ('map', 'odom')

        main = ttk.Frame(root, padding=12)
        main.pack(fill='both', expand=True)

        title = ttk.Label(
            main,
            text=f"TurtleBot4 Standard - Basic Health Check ({self.node.display_namespace()})",
            font=('Arial', 16, 'bold')
        )
        title.pack(anchor='w', pady=(0, 10))

        # -----------------------------
        # Top summary
        # -----------------------------
        summary_frame = ttk.LabelFrame(main, text="Summary", padding=10)
        summary_frame.pack(fill='x', pady=6)

        self.summary_text = tk.Text(summary_frame, height=7, width=80)
        self.summary_text.pack(fill='x')

        # -----------------------------
        # TF section
        # -----------------------------
        tf_frame = ttk.LabelFrame(main, text="TF Checks", padding=10)
        tf_frame.pack(fill='x', pady=6)

        self.tf_labels = {}
        for parent, child in self.required_tfs:
            row = ttk.Frame(tf_frame)
            row.pack(fill='x', pady=2)

            name = f"{parent} -> {child}"
            ttk.Label(row, text=name, width=30).pack(side='left')

            status = ttk.Label(row, text="UNKNOWN", width=20)
            status.pack(side='left')
            self.tf_labels[(parent, child)] = status

        # -----------------------------
        # LED section
        # -----------------------------
        led_frame = ttk.LabelFrame(main, text="Expected TurtleBot4 Status LEDs", padding=10)
        led_frame.pack(fill='x', pady=6)

        self.led_labels = {}
        led_names = ["POWER", "MOTOR", "COMMS", "WIFI", "BATTERY"]
        for led_name in led_names:
            row = ttk.Frame(led_frame)
            row.pack(fill='x', pady=2)

            ttk.Label(row, text=led_name, width=15).pack(side='left')
            status = ttk.Label(row, text="UNKNOWN", width=30)
            status.pack(side='left')
            self.led_labels[led_name] = status

        # -----------------------------
        # Notes
        # -----------------------------
        notes = (
            "Note: The 5 TB4 status LEDs are inferred from ROS 2 state.\n"
            "This tells you what they should be showing, not whether each physical LED is electrically healthy.\n"
            "You can extend this GUI later by adding more topic checks, service checks, action checks, or diagnostics."
        )
        ttk.Label(main, text=notes, foreground='gray').pack(anchor='w', pady=(8, 0))

        self.update_gui()

    def set_label(self, label_widget, ok, text_ok="OK", text_bad="NOT OK", text_unknown="UNKNOWN"):
        if ok is True:
            label_widget.config(text=text_ok, foreground='green')
        elif ok is False:
            label_widget.config(text=text_bad, foreground='red')
        else:
            label_widget.config(text=text_unknown, foreground='orange')

    def update_gui(self):
        # -----------------------------
        # Summary text
        # -----------------------------
        start_pct = self.node.start_battery_pct
        current_pct = self.node.battery_percent_now()
        motor_enabled = self.node.motor_enabled()

        lines = []
        lines.append(f"Robot namespace:  {self.node.display_namespace()}")
        lines.append(f"Starting battery: {start_pct:.1f}%" if start_pct is not None else "Starting battery: waiting for data...")
        lines.append(f"Current battery:  {current_pct:.1f}%" if current_pct is not None else "Current battery: waiting for data...")
        lines.append(f"Robot IP:         {self.node.latest_ip if self.node.latest_ip else 'waiting for data...'}")
        lines.append(f"Comms alive:      {'YES' if self.node.comms_ok() else 'NO'}")

        if motor_enabled is True:
            lines.append("Motors enabled:   YES")
        elif motor_enabled is False:
            lines.append("Motors enabled:   NO")
        else:
            lines.append("Motors enabled:   UNKNOWN")

        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "\n".join(lines))

        # -----------------------------
        # TF labels
        # -----------------------------
        tf_all_ok = True
        for parent, child in self.required_tfs:
            ok = self.node.tf_ok(parent, child)
            self.set_label(self.tf_labels[(parent, child)], ok)
            tf_all_ok = tf_all_ok and ok

        # -----------------------------
        # LED expected states
        # -----------------------------
        # POWER: if this app is running on ROS and receiving data, assume power is on
        self.set_label(self.led_labels["POWER"], True, text_ok="EXPECTED ON")

        # MOTOR
        if motor_enabled is True:
            self.set_label(self.led_labels["MOTOR"], True, text_ok="EXPECTED GREEN / ON")
        elif motor_enabled is False:
            self.set_label(self.led_labels["MOTOR"], False, text_bad="EXPECTED OFF")
        else:
            self.set_label(self.led_labels["MOTOR"], None)

        # COMMS
        if self.node.comms_ok():
            self.set_label(self.led_labels["COMMS"], True, text_ok="EXPECTED GREEN / ON")
        else:
            self.set_label(self.led_labels["COMMS"], False, text_bad="EXPECTED OFF")

        # WIFI
        if self.node.wifi_ok():
            self.set_label(self.led_labels["WIFI"], True, text_ok="EXPECTED GREEN / ON")
        else:
            self.set_label(self.led_labels["WIFI"], False, text_bad="EXPECTED OFF")

        # BATTERY
        battery_color = self.node.battery_led_color()
        if battery_color == "GREEN":
            self.led_labels["BATTERY"].config(text="EXPECTED GREEN", foreground='green')
        elif battery_color == "YELLOW":
            self.led_labels["BATTERY"].config(text="EXPECTED YELLOW", foreground='orange')
        elif battery_color == "RED":
            self.led_labels["BATTERY"].config(text="EXPECTED RED", foreground='red')
        else:
            self.led_labels["BATTERY"].config(text="UNKNOWN", foreground='orange')

        self.root.after(500, self.update_gui)


def ros_spin_thread(executor):
    while rclpy.ok():
        executor.spin_once(timeout_sec=0.1)


def main():
    parser = argparse.ArgumentParser(description='Basic TurtleBot4 monitor GUI')
    parser.add_argument(
        '--robot-namespace',
        default='/robot_0',
        help='Robot ROS namespace, for example /robot_0. Use / or empty for no namespace.',
    )
    args = parser.parse_args()

    rclpy.init()

    node = TB4MonitorNode(robot_namespace=args.robot_namespace)
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    spin_thread = threading.Thread(target=ros_spin_thread, args=(executor,), daemon=True)
    spin_thread.start()

    root = tk.Tk()
    app = TB4MonitorGUI(root, node)

    try:
        root.mainloop()
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
