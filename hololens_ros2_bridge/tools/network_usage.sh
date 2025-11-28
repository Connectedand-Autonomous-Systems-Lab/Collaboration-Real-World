#!/usr/bin/env bash

IFACE="wls4"                 # <-- change if needed
OUT="wls4_traffic.csv"

# CSV header
echo "date_time,interface,rx_kbps,tx_kbps" > "$OUT"

sar -n DEV 1 | awk -v iface="$IFACE" -v out="$OUT" '
BEGIN {
    OFS = ",";
    iface_col = rx_col = tx_col = 0;
}

# Detect header line with IFACE / rxkB/s / txkB/s and record column indexes
$0 ~ /IFACE/ && $0 ~ /rxkB\/s/ {
    for (i = 1; i <= NF; i++) {
        if ($i == "IFACE")   iface_col = i;
        if ($i == "rxkB/s")  rx_col    = i;
        if ($i == "txkB/s")  tx_col    = i;
    }
    next;
}

# Once we know the column indices, process lines for our interface
iface_col > 0 && $iface_col == iface {
    # Build time (handles both "HH:MM:SS AM" and "HH:MM:SS" formats)
    t = $1;
    if ($2 == "AM" || $2 == "PM") {
        t = t " " $2;
    }

    # Get today date
    cmd = "date +%F";
    cmd | getline today;
    close(cmd);

    rx_kbps = $(rx_col) * 8;   # kB/s -> kbps
    tx_kbps = $(tx_col) * 8;

    print today "_" t, $iface_col, rx_kbps, tx_kbps >> out;
    fflush(out);
}
'
