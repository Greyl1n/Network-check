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
    def __init__(self, root):
        self.root = root
        self.root.title('Network Speed Logger')
        
        # Data state
        self.interval = 1000  # Animation interval in ms
        self.speeds = [] # List of (sent, recv) tuples
        self.running = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_file_path = None
        
        # Speed measurement state
        self.last_net_io = None
        self.last_time = None

        # Setup UI
        self._setup_ui()
        self._update_csv_buttons()

    def _setup_ui(self):
        # Main Frame
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Matplotlib Figure
        self.fig = plt.Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Controls Frame
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=10)

        self.start_btn = tk.Button(controls_frame, text='Start', command=self.start_logging)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(controls_frame, text='Stop', command=self.stop_logging, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(controls_frame, text='Save As...', command=self.choose_save_path)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.console_save_btn = tk.Button(controls_frame, text='Console Save...', command=self.console_choose_path)
        self.console_save_btn.pack(side=tk.LEFT, padx=5)

        # File Label
        self.save_label = tk.Label(self.root, text='Save file: (not set)')
        self.save_label.pack(pady=5)

        # CSV Actions Frame
        csv_frame = tk.Frame(self.root)
        csv_frame.pack(pady=5)
        
        self.open_csv_btn = tk.Button(csv_frame, text='Open CSV', command=self.open_csv_file, state=tk.DISABLED)
        self.open_csv_btn.pack(side=tk.LEFT, padx=5)
        
        self.show_table_btn = tk.Button(csv_frame, text='Show Table', command=self.show_csv_table, state=tk.DISABLED)
        self.show_table_btn.pack(side=tk.LEFT, padx=5)

        # Exit
        exit_btn = tk.Button(self.root, text='Exit', fg='red', command=self.exit_program)
        exit_btn.pack(pady=10)

        # Animation reference
        self.ani = FuncAnimation(self.fig, self.update_plot, interval=self.interval, cache_frame_data=False)

    def get_speed_non_blocking(self):
        """Calculates speed based on time delta since last check."""
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        if self.last_net_io is None or self.last_time is None:
            self.last_net_io = current_net_io
            self.last_time = current_time
            return 0.0, 0.0

        # Calculate deltas
        bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        time_delta = current_time - self.last_time
        
        if time_delta <= 0:
            return 0.0, 0.0

        # Convert to Mbps
        mbps_sent = (bytes_sent * 8) / 1_000_000 / time_delta
        mbps_recv = (bytes_recv * 8) / 1_000_000 / time_delta
        
        # Update state
        self.last_net_io = current_net_io
        self.last_time = current_time
        
        return mbps_sent, mbps_recv

    def update_plot(self, frame):
        if not self.running:
            return

        sent, recv = self.get_speed_non_blocking()
        self.speeds.append((sent, recv))
        
        # Keep last 60 points
        if len(self.speeds) > 60:
            self.speeds.pop(0)

        # Log to CSV if active
        if self.csv_writer:
            try:
                self.csv_writer.writerow([datetime.now().isoformat(), sent, recv])
            except ValueError:
                pass # Handle potential I/O issues silently during update loop

        # Update Graph
        self.ax.clear()
        self.ax.plot([s for s, r in self.speeds], label='Upload (Mbps)')
        self.ax.plot([r for s, r in self.speeds], label='Download (Mbps)')
        self.ax.legend(loc='upper left')
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Speed (Mbps)')
        self.ax.set_title('Network Speed Logger (Mbps)')
        self.ax.grid(True, linestyle='--', alpha=0.5)

    def start_logging(self):
        if self.running:
            return

        # Ensure path if needed
        if not self.csv_file_path:
            if not self.choose_save_path():
                return
        
        # Prepare CSV
        try:
            file_exists = os.path.exists(self.csv_file_path) and os.path.getsize(self.csv_file_path) > 0
            self.csv_file = open(self.csv_file_path, 'a', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            if not file_exists:
                self.csv_writer.writerow(['Timestamp', 'Upload_Mbps', 'Download_Mbps'])
        except Exception as e:
            messagebox.showerror('File Error', f'Unable to open file for writing:\n{e}')
            return

        # Reset State
        self.speeds.clear()
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        self.running = True
        
        # Update Buttons
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

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
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def choose_save_path(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            title='Save network log as...'
        )
        if not path:
            return False
        
        self.csv_file_path = path
        self.save_label.config(text=f'Save file: {os.path.basename(path)}')
        self._update_csv_buttons()
        return True

    def console_choose_path(self):
        try:
            print('\nEnter path to save CSV (or leave blank to cancel):')
            path = input().strip()
        except Exception:
             messagebox.showwarning('Console Unavailable', 'Console input is not available.')
             return False

        if not path:
            return False
        
        if not path.lower().endswith('.csv'):
            path += '.csv'
            
        # Validate creation
        try:
            dirpath = os.path.dirname(path) or '.'
            os.makedirs(dirpath, exist_ok=True)
            with open(path, 'a', newline=''):
                pass
        except Exception as e:
            messagebox.showerror('File Error', f'Unable to use path:\n{e}')
            return False

        self.csv_file_path = path
        self.save_label.config(text=f'Save file: {os.path.basename(path)}')
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
            messagebox.showerror('Error', str(e))

    def show_csv_table(self):
        if not self.csv_file_path: return
        
        try:
            with open(self.csv_file_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            messagebox.showerror('Error', str(e))
            return
            
        if not rows:
            messagebox.showinfo('Info', 'File is empty')
            return

        top = tk.Toplevel(self.root)
        top.title(f'Viewer - {os.path.basename(self.csv_file_path)}')
        
        tree = ttk.Treeview(top)
        
        # Scrollbars
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
            tree.column(col, width=100)
            
        for row in rows[1:]:
            tree.insert("", "end", values=row)

    def exit_program(self):
        self.stop_logging()
        self.root.quit()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = NetworkSpeedLogger(root)
    root.mainloop()
