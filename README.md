# Network Speed Logger

A real-time network monitoring desktop application built with Python, Tkinter, Matplotlib, and Psutil. It measures upload and download speeds, displays a live graph, and logs results to CSV.

## Features

- Live network speed graph (upload & download in Mbps)
- Rolling 60-second history with 1-second update interval
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
python Network_check_V3.py
```

1. Click **Choose File** to select a CSV output location
2. Click **Start Logging** to begin monitoring
3. View live upload/download speeds on the graph and labels
4. Click **Stop** to end the session and close the CSV file
5. View logged data via **External Open** or **Internal Viewer**

## How It Works

The app uses `psutil.net_io_counters()` to measure cumulative bytes sent and received. Every second it computes the delta in bytes and elapsed time, then converts to Mbps:

```
(bytes * 8 bits/byte) / 1,000,000 bits/Mbit / seconds = Mbps
```

Data is buffered for 60 seconds and plotted in real-time. When logging is active, each reading is appended to the CSV file as `Timestamp, Upload_Mbps, Download_Mbps`.

## Project Structure

```
Network_Checker/
├── Network_check_V3.py    # Main application
├── Network_check_V3.exe   # Standalone executable
├── archive/
│   ├── Network_check.py   # V1
│   └── Network_check_V2.py# V2
└── README.md
```
