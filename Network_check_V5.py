import psutil
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import csv
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import socket
from collections import deque


def format_bytes(bytes_count):
    """Convert bytes into human-readable B, KB, MB, GB format."""
    if bytes_count < 1024:
        return f"{bytes_count:.0f} B"
    elif bytes_count < 1024 ** 2:
        return f"{bytes_count / 1024:.2f} KB"
    elif bytes_count < 1024 ** 3:
        return f"{bytes_count / (1024 ** 2):.2f} MB"
    else:
        return f"{bytes_count / (1024 ** 3):.2f} GB"


def format_duration(seconds):
    """Format elapsed seconds into HH:MM:SS."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class NetworkSpeedLoggerV5:
    """
    Network Speed & Health Monitor V5
    - Real-time network upload/download bandwidth monitoring
    - Hardware interface detection (IP, MAC, Link speed, MTU, Status)
    - Session metrics: Peak, Average, Total transferred data (MB/GB)
    - Network health: Background ping latency (ms), packet rates, error counters
    - Highly optimized Matplotlib rendering using persistent line updates
    - Independent live monitoring and CSV recording with auto-generated filenames
    """
    def __init__(self, root):
        self.root = root
        self.root.title('Network Speed & Health Monitor V5')
        self.root.geometry('960x780')
        self.root.minsize(860, 680)

        # Apply a clean ttk theme
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        self._configure_custom_styles(style)

        # --- State Variables ---
        self.is_monitoring = True      # Live monitoring active
        self.is_logging = False         # CSV recording active
        self.interval_ms = 1000         # Update interval in ms
        self.max_history_points = 60    # Points to retain on the graph
        self.display_unit = tk.StringVar(value="Mbps")  # "Mbps" or "MB/s"
        self.window_size_var = tk.StringVar(value="60s")
        self.selected_interface = tk.StringVar(value="All Interfaces")
        self.interval_var = tk.StringVar(value="1 Second")

        # Rolling graph history: stores (time_idx, sent_val, recv_val)
        self.speeds_up = deque(maxlen=self.max_history_points)
        self.speeds_down = deque(maxlen=self.max_history_points)

        # --- Session Analytics ---
        self.session_start_time = time.time()
        self.session_bytes_sent = 0
        self.session_bytes_recv = 0
        self.peak_up_mbps = 0.0
        self.peak_down_mbps = 0.0
        self.total_packets_sent = 0
        self.total_packets_recv = 0
        self.last_net_io = self._get_net_io()
        self.last_time = time.time()

        # --- Network Health / Ping ---
        self.current_ping_ms = None
        self.ping_target = "8.8.8.8"
        self.stop_threads = threading.Event()
        self.ping_thread = threading.Thread(target=self._ping_worker, daemon=True)
        self.ping_thread.start()

        # --- File I/O State ---
        self.csv_file = None
        self.csv_writer = None
        self.csv_file_path = None
        self.logged_rows_count = 0

        # --- Build UI ---
        self._setup_ui()
        self._update_interface_info()
        self._update_csv_buttons()

        # Start main update loop using Tkinter after() for seamless responsiveness
        self.timer_id = self.root.after(self.interval_ms, self._on_tick)

    def _configure_custom_styles(self, style):
        """Define custom UI aesthetics."""
        style.configure('Card.TFrame', background='#ffffff', relief='ridge', borderwidth=1)
        style.configure('CardTitle.TLabel', font=('Segoe UI', 8, 'bold'), foreground='#666666', background='#ffffff')
        style.configure('CardValue.TLabel', font=('Segoe UI', 15, 'bold'), background='#ffffff')
        style.configure('CardSub.TLabel', font=('Segoe UI', 8), foreground='#555555', background='#ffffff')
        style.configure('Badge.TLabel', font=('Segoe UI', 8, 'bold'), padding=(6, 2))
        style.configure('Header.TLabel', font=('Segoe UI', 10, 'bold'))

    # =========================================================================
    # Hardware & Network Counters
    # =========================================================================

    def _get_net_io(self):
        """Fetch network I/O counters for the selected interface or all."""
        interface = self.selected_interface.get()
        if interface == "All Interfaces" or not interface:
            return psutil.net_io_counters()
        else:
            counters = psutil.net_io_counters(pernic=True)
            return counters.get(interface, psutil.net_io_counters())

    def _get_available_interfaces(self):
        """Fetch list of valid network interfaces."""
        try:
            interfaces = ["All Interfaces"] + list(psutil.net_io_counters(pernic=True).keys())
            return interfaces
        except Exception:
            return ["All Interfaces"]

    def _update_interface_info(self):
        """Extract IP, MAC, Link Speed, MTU, and Status for the selected interface."""
        iface = self.selected_interface.get()
        if iface == "All Interfaces":
            active_count = 0
            stats_dict = psutil.net_if_stats()
            for name, stat in stats_dict.items():
                if stat.isup:
                    active_count += 1
            self.lbl_iface_status.config(text=f"● Active ({active_count} Up)", foreground='#0f7b0f')
            self.lbl_iface_ip.config(text="IP: Multiple")
            self.lbl_iface_mac.config(text="MAC: N/A")
            self.lbl_iface_speed.config(text="Link: Combined")
            self.lbl_iface_mtu.config(text="MTU: Various")
            return

        # Interface specific stats
        stats = psutil.net_if_stats().get(iface)
        addrs = psutil.net_if_addrs().get(iface, [])

        # Status
        if stats and stats.isup:
            self.lbl_iface_status.config(text="● CONNECTED", foreground='#0f7b0f')
        else:
            self.lbl_iface_status.config(text="○ DISCONNECTED", foreground='#b22222')

        # IP Address
        ipv4_list = [a.address for a in addrs if a.family.name == 'AF_INET']
        ip_str = ipv4_list[0] if ipv4_list else "None"
        self.lbl_iface_ip.config(text=f"IPv4: {ip_str}")

        # MAC Address
        mac_list = [a.address for a in addrs if (hasattr(psutil, 'AF_LINK') and a.family == psutil.AF_LINK) or a.family.name == 'AF_LINK']
        mac_str = mac_list[0] if mac_list else "N/A"
        self.lbl_iface_mac.config(text=f"MAC: {mac_str}")

        # Link Speed
        if stats and stats.speed > 0:
            self.lbl_iface_speed.config(text=f"Link: {stats.speed} Mbps")
        else:
            self.lbl_iface_speed.config(text="Link: N/A")

        # MTU
        mtu_val = stats.mtu if stats else "N/A"
        self.lbl_iface_mtu.config(text=f"MTU: {mtu_val}")

    def _ping_worker(self):
        """Background thread testing network latency to DNS without blocking GUI."""
        while not self.stop_threads.is_set():
            t0 = time.perf_counter()
            try:
                # Fast TCP handshake to port 53 (DNS) on Google or Cloudflare
                sock = socket.create_connection((self.ping_target, 53), timeout=1.0)
                sock.close()
                latency = (time.perf_counter() - t0) * 1000
                self.current_ping_ms = latency
            except Exception:
                # Fallback to secondary target
                try:
                    t1 = time.perf_counter()
                    sock = socket.create_connection(("1.1.1.1", 53), timeout=1.0)
                    sock.close()
                    self.current_ping_ms = (time.perf_counter() - t1) * 1000
                except Exception:
                    self.current_ping_ms = None
            
            # Wait 2 seconds between ping samples
            self.stop_threads.wait(2.0)

    # =========================================================================
    # UI Layout Construction
    # =========================================================================

    def _setup_ui(self):
        main_container = ttk.Frame(self.root, padding="8")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Top Section: Interface & Hardware Info
        top_frame = ttk.LabelFrame(main_container, text=" Network Adapter & Interface Status ", padding="8")
        top_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(top_frame, text="Adapter:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 4))
        self.iface_cb = ttk.Combobox(
            top_frame,
            textvariable=self.selected_interface,
            values=self._get_available_interfaces(),
            state="readonly",
            width=24
        )
        self.iface_cb.pack(side=tk.LEFT, padx=(0, 10))
        self.iface_cb.bind("<<ComboboxSelected>>", self._on_interface_change)

        # Hardware badges / info chips
        self.lbl_iface_status = ttk.Label(top_frame, text="● Detecting...", font=('Segoe UI', 9, 'bold'))
        self.lbl_iface_status.pack(side=tk.LEFT, padx=8)

        self.lbl_iface_ip = ttk.Label(top_frame, text="IPv4: ...", font=('Segoe UI', 9))
        self.lbl_iface_ip.pack(side=tk.LEFT, padx=8)

        self.lbl_iface_mac = ttk.Label(top_frame, text="MAC: ...", font=('Segoe UI', 9))
        self.lbl_iface_mac.pack(side=tk.LEFT, padx=8)

        self.lbl_iface_speed = ttk.Label(top_frame, text="Link: ...", font=('Segoe UI', 9))
        self.lbl_iface_speed.pack(side=tk.LEFT, padx=8)

        self.lbl_iface_mtu = ttk.Label(top_frame, text="MTU: ...", font=('Segoe UI', 9))
        self.lbl_iface_mtu.pack(side=tk.LEFT, padx=8)

        # 2. Metric Dashboard Cards
        cards_frame = ttk.Frame(main_container)
        cards_frame.pack(fill=tk.X, pady=(0, 6))
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        # Card 1: Download
        c1 = ttk.Frame(cards_frame, style='Card.TFrame', padding="8")
        c1.grid(row=0, column=0, padx=4, sticky="nsew")
        ttk.Label(c1, text="▼ DOWNLOAD SPEED", style='CardTitle.TLabel', foreground='#0078d4').pack(anchor='w')
        self.lbl_down_val = ttk.Label(c1, text="0.00 Mbps", style='CardValue.TLabel', foreground='#0078d4')
        self.lbl_down_val.pack(anchor='w', pady=(2, 2))
        self.lbl_down_stats = ttk.Label(c1, text="Peak: 0.00 | Avg: 0.00", style='CardSub.TLabel')
        self.lbl_down_stats.pack(anchor='w')

        # Card 2: Upload
        c2 = ttk.Frame(cards_frame, style='Card.TFrame', padding="8")
        c2.grid(row=0, column=1, padx=4, sticky="nsew")
        ttk.Label(c2, text="▲ UPLOAD SPEED", style='CardTitle.TLabel', foreground='#e67e22').pack(anchor='w')
        self.lbl_up_val = ttk.Label(c2, text="0.00 Mbps", style='CardValue.TLabel', foreground='#e67e22')
        self.lbl_up_val.pack(anchor='w', pady=(2, 2))
        self.lbl_up_stats = ttk.Label(c2, text="Peak: 0.00 | Avg: 0.00", style='CardSub.TLabel')
        self.lbl_up_stats.pack(anchor='w')

        # Card 3: Data Volume
        c3 = ttk.Frame(cards_frame, style='Card.TFrame', padding="8")
        c3.grid(row=0, column=2, padx=4, sticky="nsew")
        ttk.Label(c3, text="📊 SESSION VOLUME", style='CardTitle.TLabel', foreground='#27ae60').pack(anchor='w')
        self.lbl_total_data = ttk.Label(c3, text="↓ 0 B  ↑ 0 B", style='CardValue.TLabel', foreground='#27ae60')
        self.lbl_total_data.pack(anchor='w', pady=(2, 2))
        self.lbl_elapsed = ttk.Label(c3, text="Duration: 00:00:00", style='CardSub.TLabel')
        self.lbl_elapsed.pack(anchor='w')

        # Card 4: Health & Latency
        c4 = ttk.Frame(cards_frame, style='Card.TFrame', padding="8")
        c4.grid(row=0, column=3, padx=4, sticky="nsew")
        ttk.Label(c4, text="📶 LATENCY & PACKETS", style='CardTitle.TLabel', foreground='#8e44ad').pack(anchor='w')
        self.lbl_ping = ttk.Label(c4, text="Ping: -- ms", style='CardValue.TLabel', foreground='#8e44ad')
        self.lbl_ping.pack(anchor='w', pady=(2, 2))
        self.lbl_packets = ttk.Label(c4, text="Pkts: ↓ 0/s  ↑ 0/s", style='CardSub.TLabel')
        self.lbl_packets.pack(anchor='w')

        # 3. Optimized Matplotlib Graph
        graph_frame = ttk.Frame(main_container)
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.fig = plt.Figure(figsize=(8, 3.8), dpi=100)
        self.fig.patch.set_facecolor('#f7f7f9')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#ffffff')

        # Persistent Line objects for super-fast redraws without ax.clear()
        self.line_down, = self.ax.plot([], [], label='Download', color='#0078d4', linewidth=2.0, antialiased=True)
        self.line_up, = self.ax.plot([], [], label='Upload', color='#e67e22', linewidth=2.0, antialiased=True)

        self.ax.set_title(f'Real-Time Network Activity ({self.selected_interface.get()})', fontsize=10, fontweight='bold', pad=8)
        self.ax.set_xlabel('Time Window (Seconds)', fontsize=9)
        self.ax.set_ylabel(f'Speed ({self.display_unit.get()})', fontsize=9)
        self.ax.legend(loc='upper left', frameon=True, facecolor='#ffffff', edgecolor='#dddddd', fontsize=8)
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.set_xlim(0, self.max_history_points - 1)
        self.ax.set_ylim(0, 10.0)

        self.fig.tight_layout(pad=1.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 4. Control Toolbar
        controls_frame = ttk.LabelFrame(main_container, text=" Controls & Configuration ", padding="8")
        controls_frame.pack(fill=tk.X, pady=(0, 4))

        # Left controls: Monitoring & Reset
        self.pause_btn = ttk.Button(controls_frame, text='⏸ Pause Monitor', command=self.toggle_monitoring, width=15)
        self.pause_btn.pack(side=tk.LEFT, padx=3)

        self.reset_btn = ttk.Button(controls_frame, text='🗑 Reset Session', command=self.reset_session, width=14)
        self.reset_btn.pack(side=tk.LEFT, padx=3)

        # Separator
        ttk.Separator(controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Middle controls: Recording to CSV
        self.record_btn = ttk.Button(controls_frame, text='⏺ Start Recording', command=self.toggle_recording, width=16)
        self.record_btn.pack(side=tk.LEFT, padx=3)

        self.choose_file_btn = ttk.Button(controls_frame, text='📁 Log File...', command=self.choose_save_path)
        self.choose_file_btn.pack(side=tk.LEFT, padx=3)

        self.lbl_record_status = ttk.Label(controls_frame, text='Log: Inactive', font=('Segoe UI', 8, 'italic'), foreground='#777777')
        self.lbl_record_status.pack(side=tk.LEFT, padx=8)

        # Separator
        ttk.Separator(controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Right controls: Interval, Unit, Window
        ttk.Label(controls_frame, text="Interval:").pack(side=tk.LEFT, padx=(4, 2))
        intervals = ["0.5 Seconds", "1 Second", "2 Seconds", "5 Seconds"]
        self.interval_cb = ttk.Combobox(controls_frame, textvariable=self.interval_var, values=intervals, state="readonly", width=11)
        self.interval_cb.pack(side=tk.LEFT, padx=2)
        self.interval_cb.bind("<<ComboboxSelected>>", self._on_interval_change)

        ttk.Label(controls_frame, text="Unit:").pack(side=tk.LEFT, padx=(6, 2))
        units = ["Mbps", "MB/s"]
        self.unit_cb = ttk.Combobox(controls_frame, textvariable=self.display_unit, values=units, state="readonly", width=6)
        self.unit_cb.pack(side=tk.LEFT, padx=2)
        self.unit_cb.bind("<<ComboboxSelected>>", self._on_unit_change)

        ttk.Label(controls_frame, text="Window:").pack(side=tk.LEFT, padx=(6, 2))
        windows = ["30s", "60s", "120s", "300s"]
        self.window_cb = ttk.Combobox(controls_frame, textvariable=self.window_size_var, values=windows, state="readonly", width=6)
        self.window_cb.pack(side=tk.LEFT, padx=2)
        self.window_cb.bind("<<ComboboxSelected>>", self._on_window_change)

        # 5. Bottom Action Bar
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X, pady=(4, 0))

        self.open_csv_btn = ttk.Button(bottom_frame, text='📂 Open Log Externally', command=self.open_csv_file, state=tk.DISABLED)
        self.open_csv_btn.pack(side=tk.LEFT, padx=3)

        self.show_table_btn = ttk.Button(bottom_frame, text='📋 Built-in Log Viewer', command=self.show_csv_table, state=tk.DISABLED)
        self.show_table_btn.pack(side=tk.LEFT, padx=3)

        ttk.Button(bottom_frame, text='✕ Exit Monitor', command=self.exit_program).pack(side=tk.RIGHT, padx=3)

    # =========================================================================
    # Calculation & Update Loop (Optimized Matplotlib)
    # =========================================================================

    def _calculate_metrics(self):
        """Compute deltas, throughput, session statistics, and packet rates."""
        current_net_io = self._get_net_io()
        current_time = time.time()

        delta_time = current_time - self.last_time
        if delta_time <= 0:
            return 0.0, 0.0, 0.0, 0.0, 0, 0

        bytes_sent = max(0, current_net_io.bytes_sent - self.last_net_io.bytes_sent)
        bytes_recv = max(0, current_net_io.bytes_recv - self.last_net_io.bytes_recv)

        pkts_sent = max(0, current_net_io.packets_sent - self.last_net_io.packets_sent)
        pkts_recv = max(0, current_net_io.packets_recv - self.last_net_io.packets_recv)

        self.session_bytes_sent += bytes_sent
        self.session_bytes_recv += bytes_recv

        # Speeds in Mbps (Megabits/sec)
        mbps_sent = (bytes_sent * 8) / 1_000_000 / delta_time
        mbps_recv = (bytes_recv * 8) / 1_000_000 / delta_time

        # Speeds in MB/s (MegaBytes/sec)
        mbs_sent = bytes_sent / (1024 * 1024) / delta_time
        mbs_recv = bytes_recv / (1024 * 1024) / delta_time

        # Packets per second
        rate_pkts_sent = pkts_sent / delta_time
        rate_pkts_recv = pkts_recv / delta_time

        # Update peaks
        if mbps_sent > self.peak_up_mbps:
            self.peak_up_mbps = mbps_sent
        if mbps_recv > self.peak_down_mbps:
            self.peak_down_mbps = mbps_recv

        self.last_net_io = current_net_io
        self.last_time = current_time

        return mbps_sent, mbps_recv, mbs_sent, mbs_recv, rate_pkts_sent, rate_pkts_recv

    def _on_tick(self):
        """Main update tick called by Tkinter root.after() loop."""
        if self.is_monitoring:
            mbps_sent, mbps_recv, mbs_sent, mbs_recv, pkts_sent_s, pkts_recv_s = self._calculate_metrics()

            unit = self.display_unit.get()
            is_mbps = (unit == "Mbps")
            val_down = mbps_recv if is_mbps else mbs_recv
            val_up = mbps_sent if is_mbps else mbs_sent
            peak_down = self.peak_down_mbps if is_mbps else (self.peak_down_mbps / 8)
            peak_up = self.peak_up_mbps if is_mbps else (self.peak_up_mbps / 8)

            elapsed = max(1.0, time.time() - self.session_start_time)
            avg_down_mbps = (self.session_bytes_recv * 8) / 1_000_000 / elapsed
            avg_up_mbps = (self.session_bytes_sent * 8) / 1_000_000 / elapsed
            avg_down = avg_down_mbps if is_mbps else (avg_down_mbps / 8)
            avg_up = avg_up_mbps if is_mbps else (avg_up_mbps / 8)

            # Update Card 1: Download
            self.lbl_down_val.config(text=f"{val_down:.2f} {unit}")
            self.lbl_down_stats.config(text=f"Peak: {peak_down:.2f} | Avg: {avg_down:.2f} {unit}")

            # Update Card 2: Upload
            self.lbl_up_val.config(text=f"{val_up:.2f} {unit}")
            self.lbl_up_stats.config(text=f"Peak: {peak_up:.2f} | Avg: {avg_up:.2f} {unit}")

            # Update Card 3: Session Data
            str_down = format_bytes(self.session_bytes_recv)
            str_up = format_bytes(self.session_bytes_sent)
            self.lbl_total_data.config(text=f"↓ {str_down}  ↑ {str_up}")
            self.lbl_elapsed.config(text=f"Duration: {format_duration(elapsed)}")

            # Update Card 4: Latency & Packets
            if self.current_ping_ms is not None:
                color = '#27ae60' if self.current_ping_ms < 60 else ('#e67e22' if self.current_ping_ms < 120 else '#e74c3c')
                self.lbl_ping.config(text=f"Ping: {self.current_ping_ms:.0f} ms", foreground=color)
            else:
                self.lbl_ping.config(text="Ping: Timeout", foreground='#e74c3c')
            self.lbl_packets.config(text=f"Pkts: ↓ {pkts_recv_s:.0f}/s  ↑ {pkts_sent_s:.0f}/s")

            # Store in rolling buffers
            self.speeds_down.append(val_down)
            self.speeds_up.append(val_up)

            # Log to CSV if active
            if self.is_logging and self.csv_writer:
                try:
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ping_str = f"{self.current_ping_ms:.1f}" if self.current_ping_ms else "N/A"
                    self.csv_writer.writerow([
                        now_str,
                        self.selected_interface.get(),
                        f"{mbps_sent:.4f}",
                        f"{mbps_recv:.4f}",
                        f"{mbs_sent:.4f}",
                        f"{mbs_recv:.4f}",
                        ping_str,
                        f"{(self.session_bytes_sent / (1024**2)):.2f}",
                        f"{(self.session_bytes_recv / (1024**2)):.2f}"
                    ])
                    self.logged_rows_count += 1
                    # Periodic flush to avoid data loss
                    if self.logged_rows_count % 5 == 0 and self.csv_file:
                        self.csv_file.flush()
                    self.lbl_record_status.config(
                        text=f"🔴 Recording: {os.path.basename(self.csv_file_path)} ({self.logged_rows_count} rows)",
                        foreground='#b22222'
                    )
                except Exception:
                    pass

            # Fast persistent redraw
            self._update_graph_fast()

        # Reschedule next tick
        self.timer_id = self.root.after(self.interval_ms, self._on_tick)

    def _update_graph_fast(self):
        """Ultra-fast Matplotlib update modifying existing Line2D data without ax.clear()."""
        down_list = list(self.speeds_down)
        up_list = list(self.speeds_up)
        n = len(down_list)
        if n == 0:
            return

        x = list(range(n))
        self.line_down.set_data(x, down_list)
        self.line_up.set_data(x, up_list)

        # Adjust axes view limits dynamically
        max_val = max(max(down_list, default=1.0), max(up_list, default=1.0))
        upper_limit = max(5.0, max_val * 1.2)

        self.ax.set_xlim(0, max(self.max_history_points - 1, n - 1))
        self.ax.set_ylim(0, upper_limit)

        # Idle redraw does not block the Tkinter GUI thread
        self.canvas.draw_idle()

    # =========================================================================
    # User Interactions & Event Handlers
    # =========================================================================

    def _on_interface_change(self, event=None):
        """Handle network adapter change."""
        self.last_net_io = self._get_net_io()
        self.last_time = time.time()
        self.speeds_down.clear()
        self.speeds_up.clear()
        self._update_interface_info()
        self.ax.set_title(f'Real-Time Network Activity ({self.selected_interface.get()})', fontsize=10, fontweight='bold', pad=8)
        self._update_graph_fast()

    def _on_interval_change(self, event=None):
        """Change refresh rate."""
        val = self.interval_var.get()
        if "0.5" in val:
            self.interval_ms = 500
        elif "1 " in val:
            self.interval_ms = 1000
        elif "2 " in val:
            self.interval_ms = 2000
        elif "5 " in val:
            self.interval_ms = 5000
        else:
            self.interval_ms = 1000

    def _on_unit_change(self, event=None):
        """Toggle between Mbps and MB/s."""
        unit = self.display_unit.get()
        self.ax.set_ylabel(f'Speed ({unit})', fontsize=9)
        self.speeds_down.clear()
        self.speeds_up.clear()
        self._update_graph_fast()

    def _on_window_change(self, event=None):
        """Change rolling history window."""
        win_str = self.window_size_var.get().replace('s', '')
        try:
            sec = int(win_str)
            # Calculate points based on interval
            pts = max(10, int(sec / (self.interval_ms / 1000)))
            self.max_history_points = pts
            self.speeds_down = deque(list(self.speeds_down)[-pts:], maxlen=pts)
            self.speeds_up = deque(list(self.speeds_up)[-pts:], maxlen=pts)
            self.ax.set_xlim(0, self.max_history_points - 1)
            self._update_graph_fast()
        except ValueError:
            pass

    def toggle_monitoring(self):
        """Pause or resume live throughput monitoring."""
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.pause_btn.config(text='⏸ Pause Monitor')
            self.last_net_io = self._get_net_io()
            self.last_time = time.time()
        else:
            self.pause_btn.config(text='▶ Resume Monitor')

    def reset_session(self):
        """Reset session statistics and clear chart history."""
        if messagebox.askyesno("Confirm Reset", "Reset all session statistics, total volume, and graph history?"):
            self.session_start_time = time.time()
            self.session_bytes_sent = 0
            self.session_bytes_recv = 0
            self.peak_up_mbps = 0.0
            self.peak_down_mbps = 0.0
            self.speeds_down.clear()
            self.speeds_up.clear()
            self.last_net_io = self._get_net_io()
            self.last_time = time.time()
            self.lbl_down_val.config(text=f"0.00 {self.display_unit.get()}")
            self.lbl_up_val.config(text=f"0.00 {self.display_unit.get()}")
            self.lbl_down_stats.config(text="Peak: 0.00 | Avg: 0.00")
            self.lbl_up_stats.config(text="Peak: 0.00 | Avg: 0.00")
            self.lbl_total_data.config(text="↓ 0 B  ↑ 0 B")
            self.lbl_elapsed.config(text="Duration: 00:00:00")
            self._update_graph_fast()

    # =========================================================================
    # Logging & File Operations
    # =========================================================================

    def toggle_recording(self):
        """Start or stop recording network metrics to CSV."""
        if self.is_logging:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Initiate CSV recording with auto-generated default filename if none selected."""
        if not self.csv_file_path:
            # Auto-generate a default timestamped filename in current working directory
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.csv_file_path = os.path.abspath(f"network_log_{ts}.csv")

        try:
            is_new = not os.path.exists(self.csv_file_path) or os.path.getsize(self.csv_file_path) == 0
            self.csv_file = open(self.csv_file_path, 'a', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)

            if is_new:
                self.csv_writer.writerow([
                    'Timestamp',
                    'Interface',
                    'Upload_Mbps',
                    'Download_Mbps',
                    'Upload_MBs',
                    'Download_MBs',
                    'Ping_ms',
                    'Session_Upload_MB',
                    'Session_Download_MB'
                ])
                self.csv_file.flush()
        except Exception as e:
            messagebox.showerror('File Access Error', f'Could not open log file:\n{self.csv_file_path}\nError: {e}')
            return

        self.is_logging = True
        self.record_btn.config(text='⏹ Stop Recording')
        self.choose_file_btn.config(state=tk.DISABLED)
        self.lbl_record_status.config(
            text=f"🔴 Recording: {os.path.basename(self.csv_file_path)}",
            foreground='#b22222'
        )
        self._update_csv_buttons()

    def _stop_recording(self):
        """Stop CSV recording and flush buffers to disk."""
        self.is_logging = False
        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
            self.csv_writer = None

        self.record_btn.config(text='⏺ Start Recording')
        self.choose_file_btn.config(state=tk.NORMAL)
        self.lbl_record_status.config(
            text=f"Log: Saved ({self.logged_rows_count} rows in {os.path.basename(self.csv_file_path)})",
            foreground='#0f7b0f'
        )
        self._update_csv_buttons()

    def choose_save_path(self):
        """Prompt user for a custom CSV save path."""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            initialfile=f"network_log_{ts}.csv",
            filetypes=[('CSV Spreadsheet', '*.csv'), ('All files', '*.*')],
            title='Specify Network Log File'
        )
        if not path:
            return False

        self.csv_file_path = path
        self.lbl_record_status.config(text=f'Target: {os.path.basename(path)}')
        self._update_csv_buttons()
        return True

    def _update_csv_buttons(self):
        """Enable or disable viewer buttons depending on file availability."""
        has_file = self.csv_file_path and os.path.exists(self.csv_file_path)
        state = tk.NORMAL if has_file else tk.DISABLED
        self.open_csv_btn.config(state=state)
        self.show_table_btn.config(state=state)

    def open_csv_file(self):
        """Open the active CSV log in the system's default spreadsheet viewer."""
        if not self.csv_file_path or not os.path.exists(self.csv_file_path):
            messagebox.showinfo("No Log File", "No log file has been recorded yet.")
            return
        try:
            os.startfile(self.csv_file_path)
        except Exception as e:
            messagebox.showerror('System Error', f"Could not launch external viewer: {e}")

    def show_csv_table(self):
        """Display an interactive, optimized built-in table viewer with summary metrics."""
        if not self.csv_file_path or not os.path.exists(self.csv_file_path):
            messagebox.showinfo("No Log File", "No log file has been recorded yet.")
            return

        try:
            with open(self.csv_file_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            messagebox.showerror('Read Error', f"Failed to read file: {e}")
            return

        if not rows or len(rows) < 2:
            messagebox.showinfo('Info', 'Log file is currently empty or has no records.')
            return

        header = rows[0]
        data_rows = rows[1:]
        total_records = len(data_rows)

        top = tk.Toplevel(self.root)
        top.title(f'Log Viewer - {os.path.basename(self.csv_file_path)}')
        top.geometry("820x460")
        top.minsize(600, 350)

        # Summary Bar
        summary_frame = ttk.Frame(top, padding="6")
        summary_frame.pack(fill=tk.X)
        summary_text = f"Total Records: {total_records} | Start: {data_rows[0][0]} | End: {data_rows[-1][0]}"
        ttk.Label(summary_frame, text=summary_text, font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)

        # Treeview Table
        table_frame = ttk.Frame(top)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        tree = ttk.Treeview(table_frame, columns=header, show='headings')
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)

        for col in header:
            tree.heading(col, text=col, command=lambda _c=col: self._sort_treeview_column(tree, _c, False))
            tree.column(col, width=110, anchor='center')

        # Insert rows (show up to 2000 most recent records to maintain maximum performance)
        display_rows = data_rows[-2000:] if len(data_rows) > 2000 else data_rows
        for row in display_rows:
            tree.insert("", "end", values=row)

        if len(data_rows) > 2000:
            ttk.Label(top, text=f"Displaying newest 2,000 of {total_records} rows for performance.", font=('Segoe UI', 8, 'italic')).pack(pady=2)

    def _sort_treeview_column(self, tree, col, reverse):
        """Sort treeview content when a column header is clicked."""
        try:
            items = [(tree.set(k, col), k) for k in tree.get_children('')]
            # Try sorting numerically if possible
            try:
                items.sort(key=lambda t: float(t[0].replace('N/A', '-999')), reverse=reverse)
            except ValueError:
                items.sort(reverse=reverse)
            for index, (val, k) in enumerate(items):
                tree.move(k, '', index)
            tree.heading(col, command=lambda: self._sort_treeview_column(tree, col, not reverse))
        except Exception:
            pass

    def exit_program(self):
        """Cleanly terminate monitoring, background threads, and file handles."""
        self.stop_threads.set()
        if self.is_logging:
            self._stop_recording()
        if hasattr(self, 'timer_id') and self.timer_id:
            self.root.after_cancel(self.timer_id)
        try:
            plt.close(self.fig)
        except Exception:
            pass
        self.root.quit()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = NetworkSpeedLoggerV5(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_program)
    root.mainloop()
