# Network Speed & Health Monitor

A high-performance real-time network monitoring desktop application built with Python, Tkinter, Matplotlib, and Psutil. It monitors upload and download speeds, tracks network health and latency, displays interface details, and logs metrics to CSV.

## Key Features

- **High-Performance Matplotlib Rendering**: Built with an optimized plotting pipeline using persistent `Line2D` updates and non-blocking redraws (`canvas.draw_idle()`), maintaining minimal CPU usage and smooth rendering.
- **Immediate Live Monitoring**: Network activity is monitored live immediately on start without requiring CSV configuration.
- **Hardware & Interface Detection**:
  - Automatically identifies active network adapters (Wi-Fi, Ethernet, Virtual switches).
  - Displays **IPv4 address**, **MAC address**, connection status (**UP / DOWN**), hardware **Link Speed** (e.g., 1 Gbps, 2.4 Gbps Wi-Fi 6), and **MTU**.
- **Comprehensive Session Analytics**:
  - **Peak Speeds**: Tracks maximum upload and download speeds during the session.
  - **Average Speeds**: Computes mean bandwidth consumption over time.
  - **Data Volume**: Displays cumulative uploaded and downloaded bytes (auto-formatted in B, KB, MB, GB) and session duration.
- **Network Health & Latency**:
  - Non-blocking background thread measuring real-time **Ping Latency (ms)** to primary and fallback DNS servers.
  - Real-time **packet transmission rates** (packets/sec sent & received).
- **Flexible Controls & Units**:
  - Toggle units between **Mbps** (Megabits/sec) and **MB/s** (MegaBytes/sec).
  - Configurable update intervals (0.5s, 1s, 2s, 5s).
  - Adjustable rolling history window (30s, 60s, 120s, 300s).
- **CSV Logging & Built-in Viewer**:
  - Independent recording control with automatic timestamped file generation (`network_log_YYYYMMDD_HHMMSS.csv`) or custom file picker.
  - Records detailed metrics: `Timestamp`, `Interface`, `Upload_Mbps`, `Download_Mbps`, `Upload_MBs`, `Download_MBs`, `Ping_ms`, `Session_Upload_MB`, `Session_Download_MB`.
  - Built-in interactive table viewer with summary statistics and sortable columns (click column headers to sort).
  - Quick button to open logs in the system's default spreadsheet viewer.

## Requirements

- Python 3.8+
- psutil
- matplotlib
- tkinter (bundled with standard Python installations)

Install dependencies via pip:

```bash
pip install psutil matplotlib
```

## Usage

Run the application:

```bash
python Network_check_V5.py
```

### Basic Workflow

1. **Select Interface**: Choose the network adapter to monitor from the dropdown (or select "All Interfaces"). Adapter status, IP, MAC, link speed, and MTU will display automatically.
2. **Monitor Live Speeds**: Live upload/download throughput, ping latency, and session data volume update in real time.
3. **Record Logs**: Click **Start Recording** to log metrics to a CSV file (auto-named or customized via **Log File...**).
4. **Pause or Reset**: Use **Pause Monitor** to freeze live tracking, or **Reset Session** to clear counters and chart history.
5. **Inspect Data**: View records in the **Built-in Log Viewer** or open directly in external tools using **Open Log Externally**.

## How It Works

The application samples network counters using `psutil.net_io_counters()`:
- Speed is calculated by computing the delta of transferred bytes and dividing by elapsed time between samples.
- The unit converter scales speeds to **Mbps** `(bytes * 8 / 1,000,000 / dt)` or **MB/s** `(bytes / (1024 * 1024) / dt)`.
- Network latency is measured asynchronously in a background daemon thread via lightweight TCP handshakes to public DNS resolvers (port 53), ensuring the GUI remains responsive.

## Project Structure

```
Network_Checker/
├── Network_check_V5.py    # Current application
├── README.md              # Documentation
└── archive/               # Historical script versions
    ├── Network_check.py       # V1
    ├── Network_check_V2.py    # V2
    ├── Network_check_V3.py    # V3
    └── Network_check_V4.py    # V4
```
