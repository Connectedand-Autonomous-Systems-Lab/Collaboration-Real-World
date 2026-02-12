#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import signal
import subprocess
import time
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import psutil


CURRENT_RE = re.compile(r'(?P<name>\S+)\s+current\(\d+\)=(?P<val>[0-9.]+)A')
VOLT_RE = re.compile(r'(?P<name>\S+)\s+volt\(\d+\)=(?P<val>[0-9.]+)V')


def run_pmic_read_adc() -> str:
    """
    Reads Raspberry Pi PMIC ADC rails via vcgencmd.
    Requires: sudo vcgencmd pmic_read_adc
    """
    # Do NOT embed sudo here; run the script with sudo instead.
    # This avoids password prompts and is more reliable.
    cp = subprocess.run(
        ["vcgencmd", "pmic_read_adc"],
        capture_output=True,
        text=True,
        check=True,
    )
    return cp.stdout


def parse_pmic_rails(text: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Returns:
      currents: { "<rail>_A": amps }
      volts:    { "<rail>_V": volts }
    """
    currents: Dict[str, float] = {}
    volts: Dict[str, float] = {}

    for line in text.splitlines():
        m = CURRENT_RE.search(line)
        if m:
            currents[m.group("name")] = float(m.group("val"))
            continue
        m = VOLT_RE.search(line)
        if m:
            volts[m.group("name")] = float(m.group("val"))
            continue

    return currents, volts


def base_rail(name: str) -> str:
    # "VDD_CORE_A" -> "VDD_CORE", "3V3_SYS_V" -> "3V3_SYS"
    if name.endswith("_A") or name.endswith("_V"):
        return name[:-2]
    return name


def compute_total_power_w(currents: Dict[str, float], volts: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """
    Computes:
      Ptotal = sum over rails that have BOTH <rail>_A and <rail>_V : V*I
    Returns:
      (Ptotal_w, per_rail_w)
    """
    per_rail_w: Dict[str, float] = {}
    total = 0.0

    for iname, amps in currents.items():
        rail = base_rail(iname)
        vname = f"{rail}_V"
        if vname not in volts:
            continue
        v = volts[vname]
        p = v * amps
        per_rail_w[rail] = p
        total += p

    return total, per_rail_w


@dataclass
class SummaryAcc:
    n: int = 0

    cpu_sum: float = 0.0
    cpu_min: float = 1e9
    cpu_max: float = -1e9

    mem_sum: float = 0.0
    mem_min: float = 1e9
    mem_max: float = -1e9

    p_sum: float = 0.0
    p_min: float = 1e9
    p_max: float = -1e9

    # energy estimate (Wh): integrate P over time using trapezoid
    energy_Wh: float = 0.0
    last_t: Optional[float] = None
    last_p: Optional[float] = None

    def add(self, t: float, cpu: float, mem: float, p: float) -> None:
        self.n += 1

        self.cpu_sum += cpu
        self.cpu_min = min(self.cpu_min, cpu)
        self.cpu_max = max(self.cpu_max, cpu)

        self.mem_sum += mem
        self.mem_min = min(self.mem_min, mem)
        self.mem_max = max(self.mem_max, mem)

        self.p_sum += p
        self.p_min = min(self.p_min, p)
        self.p_max = max(self.p_max, p)

        if self.last_t is not None and self.last_p is not None:
            dt_s = t - self.last_t
            if dt_s > 0:
                # trapezoid: average power over interval
                avg_p = 0.5 * (self.last_p + p)
                self.energy_Wh += (avg_p * dt_s) / 3600.0

        self.last_t = t
        self.last_p = p


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Log CPU, memory, and Raspberry Pi PMIC rail-sum power (Ptotal = Σ(V*I)) to CSV + summary."
    )
    ap.add_argument("--out", default="pi_system_metrics.csv", help="Output CSV file")
    ap.add_argument("--interval", type=float, default=1.0, help="Sampling interval seconds (default 1.0)")
    ap.add_argument("--duration", type=float, default=0.0, help="Duration seconds (0 = until Ctrl+C)")
    ap.add_argument("--top-rails", type=int, default=0,
                    help="If >0, also log top N rails by power each sample (adds columns). Default 0.")
    args = ap.parse_args()

    interval = max(0.1, float(args.interval))
    duration = float(args.duration)

    # graceful stop
    stop = {"flag": False}
    def _handle(sig, frame): stop["flag"] = True
    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)

    # warm-up CPU percent
    psutil.cpu_percent(interval=None)

    acc = SummaryAcc()

    # Prepare CSV header
    base_header = [
        "wall_time_s",
        "cpu_percent",
        "mem_percent",
        "mem_used_bytes",
        "mem_available_bytes",
        "Ptotal_W",              # Σ(V_rail * I_rail)
        "Pmethod",               # string marker
    ]

    # Optional: top rails columns
    topN = max(0, int(args.top_rails))
    rail_cols = []
    if topN > 0:
        for i in range(1, topN + 1):
            rail_cols += [f"rail{i}_name", f"rail{i}_W"]

    header = base_header + rail_cols

    print(f"[info] Logging to {args.out}")
    print(f"[info] Interval={interval:.3f}s  Duration={'until Ctrl+C' if duration <= 0 else f'{duration:.1f}s'}")
    print("[info] Power method: Ptotal = sum over rails with both *_V and *_A in `vcgencmd pmic_read_adc`")

    t_start = time.time()
    next_t = t_start

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        f.flush()

        while True:
            now = time.time()
            if duration > 0 and (now - t_start) >= duration:
                break
            if stop["flag"]:
                break

            if now < next_t:
                time.sleep(next_t - now)
            next_t += interval
            now = time.time()

            cpu = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            mem_percent = float(vm.percent)
            mem_used = int(vm.used)
            mem_avail = int(vm.available)

            # Power from PMIC rails
            try:
                out = run_pmic_read_adc()
                currents, volts = parse_pmic_rails(out)
                p_total, per_rail = compute_total_power_w(currents, volts)
            except subprocess.CalledProcessError as e:
                # vcgencmd failed (permissions or not supported)
                p_total = float("nan")
                per_rail = {}
            except FileNotFoundError:
                # vcgencmd not installed / not in PATH
                p_total = float("nan")
                per_rail = {}

            row = [
                f"{now:.6f}",
                f"{cpu:.2f}",
                f"{mem_percent:.2f}",
                mem_used,
                mem_avail,
                "" if p_total != p_total else f"{p_total:.3f}",  # NaN check
                "pmic_rail_sum",
            ]

            if topN > 0 and per_rail:
                # take top N rails by power
                top = sorted(per_rail.items(), key=lambda kv: kv[1], reverse=True)[:topN]
                for i in range(topN):
                    if i < len(top):
                        row += [top[i][0], f"{top[i][1]:.3f}"]
                    else:
                        row += ["", ""]
            elif topN > 0:
                row += ["", ""] * topN

            w.writerow(row)

            if p_total == p_total:  # not NaN
                acc.add(now, cpu, mem_percent, p_total)

            if (acc.n % 10) == 0:
                f.flush()

        # Summary
        f.flush()
        w.writerow([])
        w.writerow(["SUMMARY"])
        w.writerow(["samples", acc.n])
        if acc.n > 0:
            w.writerow(["cpu_avg_percent", f"{acc.cpu_sum / acc.n:.3f}"])
            w.writerow(["cpu_min_percent", f"{acc.cpu_min:.3f}"])
            w.writerow(["cpu_max_percent", f"{acc.cpu_max:.3f}"])

            w.writerow(["mem_avg_percent", f"{acc.mem_sum / acc.n:.3f}"])
            w.writerow(["mem_min_percent", f"{acc.mem_min:.3f}"])
            w.writerow(["mem_max_percent", f"{acc.mem_max:.3f}"])

            w.writerow(["Ptotal_avg_W", f"{acc.p_sum / acc.n:.3f}"])
            w.writerow(["Ptotal_min_W", f"{acc.p_min:.3f}"])
            w.writerow(["Ptotal_max_W", f"{acc.p_max:.3f}"])
            w.writerow(["energy_Wh_est", f"{acc.energy_Wh:.6f}"])
        else:
            w.writerow(["note", "No valid samples recorded (vcgencmd may have failed)."])

        f.flush()

    print("[info] Done. Summary appended to CSV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
