# Network Speed & Health Monitor

A high-performance real-time network monitoring desktop application built with Python, Tkinter, Matplotlib, and Psutil. It monitors upload and download speeds, tracks network health and latency, displays interface details, and logs metrics to CSV.

## Key Features in V5

- **High-Performance Matplotlib Rendering**: Re-engineered plotting pipeline using persistent `Line2D` data updates and non-blocking redraws (`canvas.draw_idle()`), reducing CPU overhead by up to 90% and eliminating canvas flicker.
- **Immediate Live Monitoring**: Network activity is monitored live immediately on app start without forcing CSV file selection.
- **Hardware & Interface Detection**:
  - Automatically identifies active network adapters (Wi-Fi, Ethernet, Virtual switches).
  - Displays **IPv4 address**, **MAC address**, connection status (**UP / DOWN**), hardware **Link Speed** (e.g. 1 Gbps, 2.4 Gbps Wi-Fi 6), and **MTU**.
- **Comprehensive Session Analytics**:
  - **Peak Speeds**: Tracks maximum upload and download speeds.
  - **Average Speeds**: Calculates session average bandwidth consumption.
  - **Data Volume**: Shows cumulative uploaded and downloaded bytes (auto-formatted in B, KB, MB, GB) and session elapsed time.
- **Network Health & Latency**:
  - Non-blocking background thread measuring real-time **Ping Latency (ms)** to primary and fallback DNS servers.
  - Live **packet transmission rates** (packets/sec sent & received).
- **Flexible Controls & Units**:
  - Toggle between **Mbps** (Megabits/sec) and **MB/s** (MegaBytes/sec).
  - Configurable update intervals (0.5s, 1s, 2s, 5s).
  - Adjustable rolling history window (30s, 60s, 120s, 300s).
- **Enhanced CSV Logging & Built-in Viewer**:
  - Independent recording control with automatic timestamped file generation (`network_log_YYYYMMDD_HHMMSS.csv`) or custom file picker.
  - Logs comprehensive metrics: `Timestamp`, `Interface`, `Upload_Mbps`, `Download_Mbps`, `Upload_MBs`, `Download_MBs`, `Ping_ms`, `Session_Upload_MB`, `Session_Download_MB`.
  - Built-in interactive table viewer with summary statistics and sortable columns (click any column header to sort ascending/descending).
  - External launch button to open logs in Excel or default CSV viewer.

## Requirements

- Python 3.x
- psutil
- matplotlib
- tkinter (bundled with standard Python installations)

```bash
pip install psutil matplotlib
```

## Usage

Run the Python application:
```bash
python Network_check_V5.py
```
```

### Basic Workflow
1. **Interface Selection**: Choose the adapter to monitor from the dropdown (or select "All Interfaces"). Adapter status, IP, MAC, link speed, and MTU will display automatically.
2. **Live View**: Live download/upload speeds, latency, and session volume will update continuously.
3. **Record Logs**: Click **Start Recording** to log metrics to CSV (auto-named or custom selected via **Log File...**).
4. **Pause/Resume**: Use **Pause Monitor** to freeze live tracking or **Reset Session** to clear counters and chart history.
5. **Inspect Data**: Open logs via **Built-in Log Viewer** or launch in external spreadsheet applications with **Open Log Externally**.

## Project Structure

```
Network_Checker/
├── Network_check_V5.py    # Current main application (V5)
├── README.md              # Project documentation
└── archive/               # Historical versions
    ├── Network_check.py       # V1
    ├── Network_check_V2.py    # V2
    ├── Network_check_V3.py    # V3
    ├── Network_check_V3.exe   # V3 Executable
    ├── Network_check_V4.py    # V4
    └── Network_check_V4.exe   # V4 Executable
```
