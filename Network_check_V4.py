import psutil
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import csv
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class NetworkSpeedLogger:
    """
    A GUI application that monitors and logs network upload and download speeds.
    Displays a real-time graph and allows saving data to a CSV file.
    """
    def __init__(self, root):
        self.root = root
        self.root.title('Network Speed Logger V4')
        
        # Apply a basic ttk theme
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        # --- Data State ---
        self.interval_ms = 1000  # Refresh interval in milliseconds
        self.speeds = []         # Queue of (sent_mbps, recv_mbps) tuples
        self.running = False     # Toggle for the logging process
        
        # --- File I/O State ---
        self.csv_file = None
        self.csv_writer = None
        self.csv_file_path = None
        
        # --- Speed Measurement State ---
        self.selected_interface = tk.StringVar(value="All Interfaces")
        self.last_net_io = self._get_net_io()
        self.last_time = time.time()
        
        self._setup_ui()
        self._update_csv_buttons()

    def _get_net_io(self):
        interface = self.selected_interface.get()
        if interface == "All Interfaces" or interface == "":
            return psutil.net_io_counters()
        else:
            counters = psutil.net_io_counters(pernic=True)
            return counters.get(interface, psutil.net_io_counters())

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Graph Section
        self.fig = plt.Figure(figsize=(7, 4), dpi=100)
        self.fig.patch.set_facecolor('#f0f0f0')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#ffffff')
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Live Speed Labels
        self.speed_label_frame = ttk.Frame(main_frame)
        self.speed_label_frame.pack(fill=tk.X, pady=5)
        
        self.up_val = tk.StringVar(value="Upload: 0.00 Mbps")
        self.down_val = tk.StringVar(value="Download: 0.00 Mbps")
        
        ttk.Label(self.speed_label_frame, textvariable=self.up_val, font=('Consolas', 12, 'bold'), foreground='#1f77b4').pack(side=tk.LEFT, expand=True)
        ttk.Label(self.speed_label_frame, textvariable=self.down_val, font=('Consolas', 12, 'bold'), foreground='#ff7f0e').pack(side=tk.LEFT, expand=True)

        # Configuration Section
        config_frame = ttk.LabelFrame(main_frame, text=" Configuration ", padding="10")
        config_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(config_frame, text="Interface:").pack(side=tk.LEFT, padx=5)
        interfaces = ["All Interfaces"] + list(psutil.net_io_counters(pernic=True).keys())
        self.iface_cb = ttk.Combobox(config_frame, textvariable=self.selected_interface, values=interfaces, state="readonly", width=25)
        self.iface_cb.pack(side=tk.LEFT, padx=5)
        self.iface_cb.bind("<<ComboboxSelected>>", self._on_interface_change)

        ttk.Label(config_frame, text="Interval:").pack(side=tk.LEFT, padx=(15, 5))
        self.interval_var = tk.StringVar(value="1 Second")
        intervals = ["1 Second", "2 Seconds", "5 Seconds", "10 Seconds"]
        self.interval_cb = ttk.Combobox(config_frame, textvariable=self.interval_var, values=intervals, state="readonly", width=12)
        self.interval_cb.pack(side=tk.LEFT, padx=5)
        self.interval_cb.bind("<<ComboboxSelected>>", self._on_interval_change)

        # Controls Section
        controls_frame = ttk.LabelFrame(main_frame, text=" Controls ", padding="10")
        controls_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(controls_frame, text='▶ Start Logging', command=self.start_logging, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(controls_frame, text='■ Stop', command=self.stop_logging, state=tk.DISABLED, width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(controls_frame, text='📁 Choose File...', command=self.choose_save_path)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(controls_frame, text='🗑 Clear Data', command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        self.save_label = ttk.Label(controls_frame, text='Target File: (none)', font=('Segoe UI', 8, 'italic'))
        self.save_label.pack(side=tk.LEFT, padx=15)

        # Data View Section
        view_frame = ttk.Frame(main_frame)
        view_frame.pack(pady=5)
        
        self.open_csv_btn = ttk.Button(view_frame, text='External Open', command=self.open_csv_file, state=tk.DISABLED)
        self.open_csv_btn.pack(side=tk.LEFT, padx=5)
        
        self.show_table_btn = ttk.Button(view_frame, text='Internal Viewer', command=self.show_csv_table, state=tk.DISABLED)
        self.show_table_btn.pack(side=tk.LEFT, padx=5)

        # Exit
        ttk.Button(main_frame, text='Exit Application', command=self.exit_program).pack(pady=10)

        self.ani = FuncAnimation(self.fig, self.update_tick, interval=self.interval_ms, cache_frame_data=False)

    def _on_interface_change(self, event):
        self.last_net_io = self._get_net_io()
        self.last_time = time.time()
        self.speeds.clear()
        self._refresh_plot()

    def _on_interval_change(self, event):
        val = self.interval_var.get()
        if val == "1 Second": self.interval_ms = 1000
        elif val == "2 Seconds": self.interval_ms = 2000
        elif val == "5 Seconds": self.interval_ms = 5000
        elif val == "10 Seconds": self.interval_ms = 10000
        
        # Update animation interval
        if self.ani and self.ani.event_source:
            self.ani.event_source.interval = self.interval_ms

    def calculate_speeds(self):
        current_net_io = self._get_net_io()
        current_time = time.time()
        
        bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        time_delta = current_time - self.last_time
        
        if time_delta <= 0:
            return 0.0, 0.0

        mbps_sent = (bytes_sent * 8) / 1_000_000 / time_delta
        mbps_recv = (bytes_recv * 8) / 1_000_000 / time_delta
        
        self.last_net_io = current_net_io
        self.last_time = current_time
        
        return mbps_sent, mbps_recv

    def update_tick(self, frame):
        sent, recv = self.calculate_speeds()
        
        if not self.running:
            return

        self.speeds.append((sent, recv))
        if len(self.speeds) > 60:
            self.speeds.pop(0)

        self.up_val.set(f"Upload: {sent:.2f} Mbps")
        self.down_val.set(f"Download: {recv:.2f} Mbps")

        if self.csv_writer:
            try:
                self.csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f"{sent:.4f}", f"{recv:.4f}"])
            except (IOError, ValueError):
                pass

        self._refresh_plot()

    def _refresh_plot(self):
        self.ax.clear()
        
        up_data = [s for s, r in self.speeds]
        down_data = [r for s, r in self.speeds]
        
        self.ax.plot(up_data, label='Upload', color='#1f77b4', linewidth=2)
        self.ax.plot(down_data, label='Download', color='#ff7f0e', linewidth=2)
        
        self.ax.set_title(f'Live Network Activity ({self.selected_interface.get()})', fontsize=10, fontweight='bold')
        self.ax.set_xlabel('Updates (last 60)', fontsize=9)
        self.ax.set_ylabel('Speed (Mbps)', fontsize=9)
        self.ax.legend(loc='upper left', fontsize=8)
        self.ax.grid(True, linestyle=':', alpha=0.6)
        
        self.canvas.draw()

    def start_logging(self):
        if self.running: return

        if not self.csv_file_path:
            if not self.choose_save_path():
                return
        
        try:
            is_new = not os.path.exists(self.csv_file_path) or os.path.getsize(self.csv_file_path) == 0
            self.csv_file = open(self.csv_file_path, 'a', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            if is_new:
                self.csv_writer.writerow(['Timestamp', 'Upload_Mbps', 'Download_Mbps'])
        except Exception as e:
            messagebox.showerror('File Access Error', f'Could not open {self.csv_file_path}:\n{e}')
            return

        self.last_net_io = self._get_net_io()
        self.last_time = time.time()
        self.running = True
        
        self.start_btn.config(state=tk.DISABLED, text='Logging...')
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)
        self.iface_cb.config(state=tk.DISABLED)
        self.interval_cb.config(state=tk.DISABLED)

    def stop_logging(self):
        self.running = False
        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
            self.csv_writer = None
        
        self.start_btn.config(state=tk.NORMAL, text='▶ Start Logging')
        self.stop_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)
        self.iface_cb.config(state="readonly")
        self.interval_cb.config(state="readonly")
        
        self.up_val.set("Upload: 0.00 Mbps")
        self.down_val.set("Download: 0.00 Mbps")

    def clear_data(self):
        if messagebox.askyesno("Confirm", "Clear the current session's graph data?"):
            self.speeds.clear()
            self._refresh_plot()

    def choose_save_path(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV Spreadsheet', '*.csv'), ('All files', '*.*')],
            title='Define Log Output File'
        )
        if not path: return False
        
        self.csv_file_path = path
        self.save_label.config(text=f'Target File: {os.path.basename(path)}')
        self._update_csv_buttons()
        return True

    def _update_csv_buttons(self):
        state = tk.NORMAL if self.csv_file_path else tk.DISABLED
        self.open_csv_btn.config(state=state)
        self.show_table_btn.config(state=state)

    def open_csv_file(self):
        if not self.csv_file_path: return
        try:
            os.startfile(self.csv_file_path)
        except Exception as e:
            messagebox.showerror('System Error', f"Could not launch viewer: {e}")

    def show_csv_table(self):
        if not self.csv_file_path: return
        try:
            with open(self.csv_file_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            messagebox.showerror('Read Error', f"Failed to read file: {e}")
            return
            
        if not rows:
            messagebox.showinfo('Info', 'Log file is currently empty.')
            return

        top = tk.Toplevel(self.root)
        top.title(f'Log Viewer - {os.path.basename(self.csv_file_path)}')
        top.geometry("500x400")
        
        tree = ttk.Treeview(top)
        style = ttk.Style()
        style.configure("Treeview", font=('Segoe UI', 9))
        
        vsb = ttk.Scrollbar(top, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(top, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)
        
        header = rows[0]
        tree['columns'] = header
        tree['show'] = 'headings'
        
        for col in header:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor='center')
            
        for row in rows[1:]:
            tree.insert("", "end", values=row)

    def exit_program(self):
        self.stop_logging()
        # Ensure matplotlib animation is stopped to prevent background thread issues
        if hasattr(self, 'ani') and self.ani and self.ani.event_source:
            self.ani.event_source.stop()
        self.root.quit()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.minsize(800, 700)
    # Handle the window close button (X) properly
    app = NetworkSpeedLogger(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_program)
    root.mainloop()
