# Network Speed Logger

A real-time network monitoring desktop application built with Python, Tkinter, Matplotlib, and Psutil. It measures upload and download speeds, displays a live graph, and logs results to CSV.

## Features

- Live network speed graph (upload & download in Mbps)
- **New in V4**: Specific network interface selection (e.g., Wi-Fi, Ethernet, or All)
- **New in V4**: Adjustable logging intervals (1s, 2s, 5s, 10s)
- **New in V4**: Modernized UI using Tkinter `ttk`
- Rolling 60-second history buffer
- Real-time speed labels
- CSV logging with timestamps
- Built-in CSV table viewer (Tkinter Treeview)
- Open CSV externally in system default viewer
- Clear graph data without restarting

## Requirements

- Python 3.x
- psutil
- matplotlib
- tkinter (bundled with most Python installations)

```bash
pip install psutil matplotlib
```

## Usage

```bash
python Network_check_V4.py
```

1. Select the **Interface** you want to monitor (e.g., All Interfaces, Wi-Fi).
2. Select the **Interval** for logging/updating.
3. Click **Choose File** to select a CSV output location.
4. Click **Start Logging** to begin monitoring.
5. View live upload/download speeds on the graph and labels.
6. Click **Stop** to end the session and close the CSV file.
7. View logged data via **External Open** or **Internal Viewer**.

## How It Works

The app uses `psutil.net_io_counters(pernic=True)` to measure cumulative bytes sent and received for specific or all interfaces. It computes the delta in bytes and elapsed time, then converts to Mbps:

```
(bytes * 8 bits/byte) / 1,000,000 bits/Mbit / seconds = Mbps
```

Data is buffered for 60 data points and plotted in real-time. When logging is active, each reading is appended to the CSV file as `Timestamp, Upload_Mbps, Download_Mbps`.

## Project Structure

```
Network_Checker/
├── Network_check_V4.py    # Main application
├── Network_check_V4.exe   # Standalone executable
├── archive/
│   ├── Network_check.py       # V1
│   ├── Network_check_V2.py    # V2
│   ├── Network_check_V3.py    # V3
│   └── Network_check_V3.exe   # V3 Executable
└── README.md
```
