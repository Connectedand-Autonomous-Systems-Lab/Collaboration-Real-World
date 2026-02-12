#!/usr/bin/env python3
import argparse
import csv
import os
import signal
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

import psutil


# -------------------------
# Power readers
# -------------------------

def _read_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def find_rapl_energy_paths() -> List[str]:
    """
    Find Intel RAPL energy_uj files (microjoules) under /sys/class/powercap/intel-rapl:*
    Summing packages/domains gives approximate whole-CPU energy.
    """
    base = "/sys/class/powercap"
    paths: List[str] = []
    if not os.path.isdir(base):
        return paths

    try:
        for name in os.listdir(base):
            if not name.startswith("intel-rapl"):
                continue
            p = os.path.join(base, name, "energy_uj")
            if os.path.isfile(p):
                paths.append(p)

            # include subdomains (intel-rapl:X:Y/energy_uj)
            subdir = os.path.join(base, name)
            try:
                for sub in os.listdir(subdir):
                    if sub.startswith("intel-rapl"):
                        sp = os.path.join(subdir, sub, "energy_uj")
                        if os.path.isfile(sp):
                            paths.append(sp)
            except Exception:
                pass
    except Exception:
        pass

    # de-dup
    return sorted(list(set(paths)))


def rapl_total_energy_uj(energy_paths: List[str]) -> Optional[int]:
    if not energy_paths:
        return None
    vals = []
    for p in energy_paths:
        v = _read_int(p)
        if v is None:
            return None
        vals.append(v)
    return sum(vals)


def find_battery_power_now_paths() -> List[str]:
    """
    Find laptop battery power_now (uW) files. Sum across batteries if multiple.
    Typical path: /sys/class/power_supply/BAT0/power_now
    """
    base = "/sys/class/power_supply"
    paths: List[str] = []
    if not os.path.isdir(base):
        return paths
    try:
        for name in os.listdir(base):
            if not name.startswith("BAT"):
                continue
            p = os.path.join(base, name, "power_now")
            if os.path.isfile(p):
                paths.append(p)
    except Exception:
        pass
    return sorted(paths)


def battery_total_power_w(power_paths: List[str]) -> Optional[float]:
    if not power_paths:
        return None
    vals = []
    for p in power_paths:
        v = _read_int(p)  # typically uW
        if v is None:
            return None
        vals.append(v)
    # uW -> W
    return sum(vals) / 1e6


@dataclass
class SummaryAcc:
    n: int = 0

    cpu_sum: float = 0.0
    cpu_min: float = 1e9
    cpu_max: float = -1e9

    mem_sum: float = 0.0
    mem_min: float = 1e9
    mem_max: float = -1e9

    power_sum: float = 0.0
    power_min: float = 1e9
    power_max: float = -1e9
    power_n: int = 0  # count only samples where power is available

    def add(self, cpu: float, mem: float, power: Optional[float]) -> None:
        self.n += 1

        self.cpu_sum += cpu
        self.cpu_min = min(self.cpu_min, cpu)
        self.cpu_max = max(self.cpu_max, cpu)

        self.mem_sum += mem
        self.mem_min = min(self.mem_min, mem)
        self.mem_max = max(self.mem_max, mem)

        if power is not None:
            self.power_n += 1
            self.power_sum += power
            self.power_min = min(self.power_min, power)
            self.power_max = max(self.power_max, power)


def main() -> int:
    ap = argparse.ArgumentParser(description="Log CPU, memory, and power usage to CSV with final summary.")
    ap.add_argument("--out", default="system_metrics.csv", help="Output CSV file (default: system_metrics.csv)")
    ap.add_argument("--interval", type=float, default=1.0, help="Sampling interval seconds (default: 1.0)")
    ap.add_argument("--duration", type=float, default=0.0, help="Optional duration seconds (0 = until Ctrl+C)")
    args = ap.parse_args()

    interval = max(0.1, float(args.interval))
    duration = float(args.duration)

    # Power sources
    rapl_paths = find_rapl_energy_paths()
    bat_power_paths = find_battery_power_now_paths()

    power_mode = "none"
    if rapl_paths:
        power_mode = "intel_rapl_energy"
    elif bat_power_paths:
        power_mode = "battery_power_now"

    print(f"[info] Logging to: {args.out}")
    print(f"[info] Interval: {interval:.3f}s, Duration: {'until Ctrl+C' if duration <= 0 else f'{duration:.1f}s'}")
    print(f"[info] Power source: {power_mode}")

    # Setup graceful shutdown
    stop = {"flag": False}

    def _handle_sig(sig, frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    # Warm-up for psutil cpu_percent (first call can be 0.0)
    psutil.cpu_percent(interval=None)

    # For RAPL power computation:
    prev_energy_uj = rapl_total_energy_uj(rapl_paths) if rapl_paths else None
    prev_energy_time = time.time()

    acc = SummaryAcc()

    # CSV
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "wall_time_s",
            "cpu_percent",
            "mem_percent",
            "mem_used_bytes",
            "mem_available_bytes",
            "power_w",
            "power_source",
        ])
        f.flush()

        t_start = time.time()
        next_t = t_start

        while True:
            now = time.time()
            if duration > 0 and (now - t_start) >= duration:
                break
            if stop["flag"]:
                break

            # sleep to schedule
            if now < next_t:
                time.sleep(next_t - now)
            next_t += interval
            now = time.time()

            cpu = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            mem_percent = float(vm.percent)
            mem_used = int(vm.used)
            mem_avail = int(vm.available)

            power_w: Optional[float] = None

            if rapl_paths:
                cur_energy_uj = rapl_total_energy_uj(rapl_paths)
                cur_t = now
                if cur_energy_uj is not None and prev_energy_uj is not None:
                    dt = cur_t - prev_energy_time
                    if dt > 0:
                        dE_uj = cur_energy_uj - prev_energy_uj
                        # Handle wrap-around (rare but possible). If negative, skip this sample.
                        if dE_uj >= 0:
                            # microjoules / seconds => microwatts => watts
                            power_w = (dE_uj / dt) / 1e6
                prev_energy_uj = cur_energy_uj
                prev_energy_time = cur_t

            elif bat_power_paths:
                power_w = battery_total_power_w(bat_power_paths)

            # log row
            w.writerow([
                f"{now:.6f}",
                f"{cpu:.2f}",
                f"{mem_percent:.2f}",
                mem_used,
                mem_avail,
                "" if power_w is None else f"{power_w:.3f}",
                power_mode,
            ])

            # accumulate summary
            acc.add(cpu=cpu, mem=mem_percent, power=power_w)

            # flush occasionally
            if (acc.n % 10) == 0:
                f.flush()

        # Summary section appended at end
        f.flush()
        w.writerow([])
        w.writerow(["SUMMARY"])
        w.writerow(["samples", acc.n])
        w.writerow(["cpu_avg_percent", f"{(acc.cpu_sum / acc.n) if acc.n else 0.0:.3f}"])
        w.writerow(["cpu_min_percent", f"{acc.cpu_min if acc.n else 0.0:.3f}"])
        w.writerow(["cpu_max_percent", f"{acc.cpu_max if acc.n else 0.0:.3f}"])
        w.writerow(["mem_avg_percent", f"{(acc.mem_sum / acc.n) if acc.n else 0.0:.3f}"])
        w.writerow(["mem_min_percent", f"{acc.mem_min if acc.n else 0.0:.3f}"])
        w.writerow(["mem_max_percent", f"{acc.mem_max if acc.n else 0.0:.3f}"])

        if acc.power_n > 0:
            w.writerow(["power_source", power_mode])
            w.writerow(["power_avg_w", f"{acc.power_sum / acc.power_n:.3f}"])
            w.writerow(["power_min_w", f"{acc.power_min:.3f}"])
            w.writerow(["power_max_w", f"{acc.power_max:.3f}"])
        else:
            w.writerow(["power_source", power_mode])
            w.writerow(["power_note", "power not available (no RAPL and no battery power_now)"])

        f.flush()

    print("[info] Done. Summary appended to CSV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
