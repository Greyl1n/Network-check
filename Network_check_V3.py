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
        """
        Initialize the application, setup data state, and build the UI.
        
        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.root = root
        self.root.title('Network Speed Logger V3')
        
        # --- Data State ---
        self.interval = 1000  # Refresh interval in milliseconds
        self.speeds = []      # Queue of (sent_mbps, recv_mbps) tuples for the graph
        self.running = False  # Toggle for the logging process
        
        # --- File I/O State ---
        self.csv_file = None
        self.csv_writer = None
        self.csv_file_path = None
        
        # --- Speed Measurement State ---
        self.last_net_io = psutil.net_io_counters() # Initial snapshot of network counters
        self.last_time = time.time()                 # Initial timestamp
        
        # Build the user interface
        self._setup_ui()
        # Initialize button states based on file selection
        self._update_csv_buttons()

    def _setup_ui(self):
        """Creates and arranges all UI components."""
        # Main container frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Graph Section
        self.fig = plt.Figure(figsize=(7, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Live Speed Labels (New in V3)
        self.speed_label_frame = tk.Frame(main_frame)
        self.speed_label_frame.pack(fill=tk.X, pady=5)
        
        self.up_val = tk.StringVar(value="Upload: 0.00 Mbps")
        self.down_val = tk.StringVar(value="Download: 0.00 Mbps")
        
        tk.Label(self.speed_label_frame, textvariable=self.up_val, font=('Consolas', 11, 'bold'), fg='#1f77b4').pack(side=tk.LEFT, expand=True)
        tk.Label(self.speed_label_frame, textvariable=self.down_val, font=('Consolas', 11, 'bold'), fg='#ff7f0e').pack(side=tk.LEFT, expand=True)

        # Controls Section
        controls_frame = tk.LabelFrame(self.root, text=" Controls ", padx=10, pady=10)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = tk.Button(controls_frame, text='▶ Start Logging', width=15, bg='#e1f5fe', command=self.start_logging)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(controls_frame, text='■ Stop', width=10, state=tk.DISABLED, command=self.stop_logging)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(controls_frame, text='📁 Choose File...', command=self.choose_save_path)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = tk.Button(controls_frame, text='🗑 Clear Data', command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # File path status label
        self.save_label = tk.Label(self.root, text='Target File: (none)', font=('Segoe UI', 8, 'italic'))
        self.save_label.pack(pady=2)

        # Data View Section
        view_frame = tk.Frame(self.root)
        view_frame.pack(pady=5)
        
        self.open_csv_btn = tk.Button(view_frame, text='External Open', command=self.open_csv_file, state=tk.DISABLED)
        self.open_csv_btn.pack(side=tk.LEFT, padx=5)
        
        self.show_table_btn = tk.Button(view_frame, text='Internal Viewer', command=self.show_csv_table, state=tk.DISABLED)
        self.show_table_btn.pack(side=tk.LEFT, padx=5)

        # Exit
        tk.Button(self.root, text='Exit Application', fg='white', bg='#c62828', command=self.exit_program).pack(pady=10)

        # Setup the animation loop (always running, but only updates data when self.running is True)
        self.ani = FuncAnimation(self.fig, self.update_tick, interval=self.interval, cache_frame_data=False)

    def calculate_speeds(self):
        """
        Calculates the current upload and download Mbps since the last call.
        
        Returns:
            tuple: (mbps_sent, mbps_recv)
        """
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        # Difference in bytes
        bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        time_delta = current_time - self.last_time
        
        # Avoid division by zero
        if time_delta <= 0:
            return 0.0, 0.0

        # Math: (bytes * 8 bits/byte) / 1,000,000 bits/Mbit / seconds = Mbps
        mbps_sent = (bytes_sent * 8) / 1_000_000 / time_delta
        mbps_recv = (bytes_recv * 8) / 1_000_000 / time_delta
        
        # Cache current values for next calculation
        self.last_net_io = current_net_io
        self.last_time = current_time
        
        return mbps_sent, mbps_recv

    def update_tick(self, frame):
        """Animation callback triggered every 1000ms."""
        # Even if not logging, we calculate to keep the 'delta' accurate for next start
        sent, recv = self.calculate_speeds()
        
        if not self.running:
            return

        # Update data buffer (keep 60 seconds of history)
        self.speeds.append((sent, recv))
        if len(self.speeds) > 60:
            self.speeds.pop(0)

        # Update UI Labels
        self.up_val.set(f"Upload: {sent:.2f} Mbps")
        self.down_val.set(f"Download: {recv:.2f} Mbps")

        # Log to file if active
        if self.csv_writer:
            try:
                self.csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f"{sent:.4f}", f"{recv:.4f}"])
            except (IOError, ValueError):
                pass # Silently ignore momentary file write issues

        # Refresh the graph
        self._refresh_plot()

    def _refresh_plot(self):
        """Redraws the matplotlib axes with current speed data."""
        self.ax.clear()
        
        up_data = [s for s, r in self.speeds]
        down_data = [r for s, r in self.speeds]
        
        self.ax.plot(up_data, label='Upload', color='#1f77b4', linewidth=2)
        self.ax.plot(down_data, label='Download', color='#ff7f0e', linewidth=2)
        
        self.ax.set_title('Live Network Activity', fontsize=10, fontweight='bold')
        self.ax.set_xlabel('Time (s ago - approx)', fontsize=9)
        self.ax.set_ylabel('Speed (Mbps)', fontsize=9)
        self.ax.legend(loc='upper left', fontsize=8)
        self.ax.grid(True, linestyle=':', alpha=0.6)
        
        # Ensure the canvas updates
        self.canvas.draw()

    def start_logging(self):
        """Initialization logic when the Start button is clicked."""
        if self.running:
            return

        # User MUST select a file before starting
        if not self.csv_file_path:
            if not self.choose_save_path():
                return
        
        try:
            # Open file in append mode
            is_new = not os.path.exists(self.csv_file_path) or os.path.getsize(self.csv_file_path) == 0
            self.csv_file = open(self.csv_file_path, 'a', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write header if new file
            if is_new:
                self.csv_writer.writerow(['Timestamp', 'Upload_Mbps', 'Download_Mbps'])
        except Exception as e:
            messagebox.showerror('File Access Error', f'Could not open {self.csv_file_path}:\n{e}')
            return

        # Start the clock fresh
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        self.running = True
        
        # Update UI state
        self.start_btn.config(state=tk.DISABLED, text='Logging...')
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)

    def stop_logging(self):
        """Stops the data collection and closes the file handle."""
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
        
        # Reset labels
        self.up_val.set("Upload: 0.00 Mbps")
        self.down_val.set("Download: 0.00 Mbps")

    def clear_data(self):
        """Resets the internal speed buffer and clears the graph."""
        if messagebox.askyesno("Confirm", "Clear the current session's graph data?"):
            self.speeds.clear()
            self._refresh_plot()

    def choose_save_path(self):
        """Opens a file dialog to define where to save CSV logs."""
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV Spreadsheet', '*.csv'), ('All files', '*.*')],
            title='Define Log Output File'
        )
        if not path:
            return False
        
        self.csv_file_path = path
        self.save_label.config(text=f'Target File: {os.path.basename(path)}')
        self._update_csv_buttons()
        return True

    def _update_csv_buttons(self):
        """Enables viewing buttons only if a valid path exists."""
        state = tk.NORMAL if self.csv_file_path else tk.DISABLED
        self.open_csv_btn.config(state=state)
        self.show_table_btn.config(state=state)

    def open_csv_file(self):
        """Opens the log file in the system's default CSV viewer (e.g., Excel)."""
        if not self.csv_file_path: return
        try:
            os.startfile(self.csv_file_path)
        except Exception as e:
            messagebox.showerror('System Error', f"Could not launch viewer: {e}")

    def show_csv_table(self):
        """Displays the logged data in a new internal window using a Treeview."""
        if not self.csv_file_path: return
        
        # Read the file data
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

        # Create child window
        top = tk.Toplevel(self.root)
        top.title(f'Log Viewer - {os.path.basename(self.csv_file_path)}')
        top.geometry("500x400")
        
        # Build Treeview
        tree = ttk.Treeview(top)
        style = ttk.Style()
        style.configure("Treeview", font=('Segoe UI', 9))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(top, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(top, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)
        
        # Define Columns
        header = rows[0]
        tree['columns'] = header
        tree['show'] = 'headings'
        
        for col in header:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor='center')
            
        # Insert Data
        for row in rows[1:]:
            tree.insert("", "end", values=row)

    def exit_program(self):
        """Stops logical processes and closes the window."""
        self.stop_logging()
        self.root.quit()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    # Set a minimum window size
    root.minsize(750, 650)
    app = NetworkSpeedLogger(root)
    root.mainloop()
