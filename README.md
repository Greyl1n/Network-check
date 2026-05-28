📡 Network Speed Logger V3
Real‑time network monitoring with Tkinter + Matplotlib + Psutil

A desktop application that measures upload/download speeds, displays a live graph, and logs results to CSV.
Built with Python, Tkinter, Matplotlib, and Psutil.

🚀 Features
📈 Live network speed graph (upload & download Mbps)

🧮 Accurate speed calculation using psutil.net_io_counters()

💾 CSV logging with timestamps

🪟 Internal CSV table viewer (Tkinter Treeview)

📂 External CSV opening (Excel, LibreOffice, etc.)

🧹 Clear graph data without restarting

🖥 Clean, responsive Tkinter UI

🔄 1‑second update interval with rolling 60‑second history

🛠 Requirements
Python 3.x

psutil

matplotlib

tkinter (bundled with most Python installations)

Install missing dependencies:

bash
pip install psutil matplotlib
🧭 Application Overview
The application is implemented as a single class:

python
class NetworkSpeedLogger:
It manages:

UI creation

Network speed measurement

CSV file handling

Graph animation

Internal CSV viewer

Application lifecycle

🖼 User Interface Layout
1. Live Graph
A Matplotlib plot embedded inside Tkinter using FigureCanvasTkAgg.

2. Real‑Time Speed Labels
Displays current upload/download speeds:

Upload: X.XX Mbps

Download: X.XX Mbps

3. Control Panel
▶ Start Logging

■ Stop

📁 Choose File

🗑 Clear Data

4. File Status
Shows the selected CSV file name.

5. Data View Options
External Open — opens CSV in system default viewer

Internal Viewer — opens a Tkinter table window

6. Exit Button
Gracefully closes the application.

📡 How Speed Is Calculated
The app uses psutil’s cumulative byte counters:

“(bytes * 8 bits/byte) / 1,000,000 bits/Mbit / seconds = Mbps”

Steps:

Read current counters

Compute byte deltas

Compute time delta

Convert to Mbps

Cache values for next tick

Returns:

python
(upload_mbps, download_mbps)
🔄 Update Loop (FuncAnimation)
Runs every 1000 ms:

Calculates speeds

Updates labels

Appends to rolling 60‑second buffer

Writes to CSV (if logging)

Redraws the graph

💾 CSV Logging
When logging starts:

Ensures a file is selected

Opens file in append mode

Writes header if file is new

Writes rows in format:

Code
Timestamp, Upload_Mbps, Download_Mbps
When logging stops:

File is flushed and closed

Buttons reset

Labels reset

📂 CSV Viewing
External Viewer
Uses:

python
os.startfile(self.csv_file_path)
Internal Viewer
A Tkinter Toplevel window with:

Treeview table

Scrollbars

Auto‑sized columns

All CSV rows displayed

🗑 Clearing Data
Clears the in‑memory graph buffer and refreshes the plot.

🏁 Running the Application
bash
python Network_check_V3.py
The main entry point:

python
if __name__ == '__main__':
    root = tk.Tk()
    root.minsize(750, 650)
    app = NetworkSpeedLogger(root)
    root.mainloop()
📘 Summary
Network Speed Logger V3 is a compact, GUI‑based monitoring tool that provides:

Real‑time visualization

Accurate speed measurement

Persistent CSV logging

Built‑in data inspection

It’s ideal for diagnostics, monitoring unstable connections, or logging network performance over time.
