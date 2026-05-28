



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



interval = 1  # seconds
speeds = []
running = False
ani = None
csv_file = None
csv_writer = None
csv_file_path = None  # path selected by user for CSV output

def get_speed():
    net1 = psutil.net_io_counters()
    time.sleep(interval)
    net2 = psutil.net_io_counters()
    bytes_sent = net2.bytes_sent - net1.bytes_sent
    bytes_recv = net2.bytes_recv - net1.bytes_recv
    mbps_sent = (bytes_sent * 8) / 1_000_000 / interval
    mbps_recv = (bytes_recv * 8) / 1_000_000 / interval
    return mbps_sent, mbps_recv

def update(frame):
    if not running:
        return
    sent, recv = get_speed()
    speeds.append((sent, recv))
    if len(speeds) > 60:
        speeds.pop(0)
    if csv_writer:
        csv_writer.writerow([datetime.now().isoformat(), sent, recv])
    ax.clear()
    ax.plot([s for s, r in speeds], label='Upload (Mbps)')
    ax.plot([r for s, r in speeds], label='Download (Mbps)')
    ax.legend()
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Speed (Mbps)')
    ax.set_title('Network Speed Logger (Mbps)')
    canvas.draw()



def start_logging():
    global running, ani, csv_file, csv_writer
    if running:
        return
    running = True
    speeds.clear()
    # Ensure we have a target path. If not, prompt the user.
    global csv_file_path
    if not csv_file_path:
        if not choose_save_path():
            # user cancelled; don't start logging
            running = False
            return

    # Open the CSV file for append and write header if file is empty/new
    try:
        file_exists = os.path.exists(csv_file_path) and os.path.getsize(csv_file_path) > 0
        csv_file = open(csv_file_path, 'a', newline='')
        csv_writer = csv.writer(csv_file)
        if not file_exists:
            csv_writer.writerow(['Timestamp', 'Upload_Mbps', 'Download_Mbps'])
    except Exception as e:
        messagebox.showerror('File Error', f'Unable to open file for writing:\n{e}')
        running = False
        return
    ani = FuncAnimation(fig, update, interval=interval*1000)
    canvas.draw()

def stop_logging():
    global running, csv_file, csv_writer
    running = False
    if csv_file:
        try:
            csv_file.flush()
            csv_file.close()
        except Exception:
            pass
        csv_file = None
        csv_writer = None


def choose_save_path():
    """Prompt the user to select (or create) a CSV file path to save logs.

    Returns True if a path was selected, False if cancelled.
    """
    global csv_file_path
    # Use asksaveasfilename to let user pick folder and filename
    path = filedialog.asksaveasfilename(
        defaultextension='.csv',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
        title='Save network log as...'
    )
    if not path:
        return False
    csv_file_path = path
    # update label in UI if present
    try:
        save_label.config(text=f'Save file: {os.path.basename(csv_file_path)}')
    except Exception:
        pass
    try:
        update_csv_buttons()
    except Exception:
        pass
    return True


# Minimal tkinter UI with embedded plot
root = tk.Tk()
root.title('Network Speed Logger')

frame = tk.Frame(root)
frame.pack()

fig = plt.Figure(figsize=(6, 4))
ax = fig.add_subplot(111)
canvas = FigureCanvasTkAgg(fig, master=frame)
canvas.get_tk_widget().pack()

start_btn = tk.Button(root, text='Start', command=start_logging)
start_btn.pack(padx=10, pady=5)
stop_btn = tk.Button(root, text='Stop', command=stop_logging)
stop_btn.pack(padx=10, pady=5)
save_btn = tk.Button(root, text='Save As...', command=choose_save_path)
save_btn.pack(padx=10, pady=5)

# Label to show current save file (filename only)
save_label = tk.Label(root, text='Save file: (not set)')
save_label.pack(padx=10, pady=5)

# Console fallback button for non-GUI/headless use
def console_choose_path():
    """Prompt the user in the console for a CSV path. Returns True if set."""
    global csv_file_path
    try:
        print('\nEnter path to save CSV (or leave blank to cancel):')
        path = input().strip()
    except Exception:
        # If input fails (no console), show messagebox and return False
        try:
            messagebox.showwarning('Console Unavailable', 'Console input is not available on this platform.')
        except Exception:
            pass
        return False

    if not path:
        return False
    # Ensure extension
    if not path.lower().endswith('.csv'):
        path = path + '.csv'
    # Try to create/validate
    try:
        # ensure directory exists
        dirpath = os.path.dirname(path) or '.'
        if not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        # test open
        with open(path, 'a', newline=''):
            pass
    except Exception as e:
        try:
            messagebox.showerror('File Error', f'Unable to create/open file:\n{e}')
        except Exception:
            print(f'ERROR: Unable to create/open file: {e}')
        return False

    csv_file_path = path
    try:
        save_label.config(text=f'Save file: {os.path.basename(csv_file_path)}')
    except Exception:
        pass
    try:
        update_csv_buttons()
    except Exception:
        pass
    return True

# Add a button to trigger console fallback prompt
console_save_btn = tk.Button(root, text='Console Save...', command=console_choose_path)
console_save_btn.pack(padx=10, pady=5)

# Exit button to close program cleanly
def exit_program():
    # Ensure logging is stopped and files are closed
    stop_logging()
    try:
        root.quit()
        root.destroy()
    except Exception:
        pass

exit_btn = tk.Button(root, text='Exit', fg='red', command=exit_program)
exit_btn.pack(padx=10, pady=5)


# Buttons to open and view the CSV file
def update_csv_buttons():
    """Enable/disable CSV-related buttons based on whether csv_file_path is set."""
    state = 'normal' if csv_file_path else 'disabled'
    try:
        open_csv_btn.config(state=state)
        show_table_btn.config(state=state)
    except Exception:
        pass


def open_csv_file():
    """Open the CSV file with the system default application (Windows: Explorer/Excel).

    Uses os.startfile which is Windows-specific but safe here since the app appears to run on Windows.
    """
    if not csv_file_path:
        messagebox.showinfo('No file', 'No CSV file selected. Use Save As... or Console Save...')
        return
    try:
        os.startfile(csv_file_path)
    except Exception as e:
        messagebox.showerror('Open Failed', f'Could not open file:\n{e}')


def show_csv_table():
    """Display the CSV contents in a new Tkinter Toplevel using a Treeview table.

    This avoids external apps and gives a quick in-app preview.
    """
    if not csv_file_path:
        messagebox.showinfo('No file', 'No CSV file selected. Use Save As... or Console Save...')
        return
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception as e:
        messagebox.showerror('Read Failed', f'Could not read CSV file:\n{e}')
        return

    if not rows:
        messagebox.showinfo('Empty', 'CSV file is empty')
        return

    header = rows[0]
    data = rows[1:]

    top = tk.Toplevel(root)
    top.title(f'CSV Viewer — {os.path.basename(csv_file_path)}')
    top.geometry('800x400')

    tbl_frame = tk.Frame(top)
    tbl_frame.pack(fill='both', expand=True)

    cols = [f'col{i}' for i in range(len(header))]
    tree = ttk.Treeview(tbl_frame, columns=cols, show='headings')
    for i, h in enumerate(header):
        tree.heading(cols[i], text=h)
        tree.column(cols[i], width=120, anchor='w')

    # Insert rows
    for row in data:
        # Ensure row has the same length as header (pad or truncate)
        row = list(row) + [''] * (len(header) - len(row))
        tree.insert('', 'end', values=row[:len(header)])

    vsb = ttk.Scrollbar(tbl_frame, orient='vertical', command=tree.yview)
    hsb = ttk.Scrollbar(tbl_frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side='right', fill='y')
    hsb.pack(side='bottom', fill='x')
    tree.pack(fill='both', expand=True)


# Create Open/Show buttons (start disabled until a file is chosen)
open_csv_btn = tk.Button(root, text='Open CSV', command=open_csv_file, state='disabled')
open_csv_btn.pack(padx=10, pady=5)

show_table_btn = tk.Button(root, text='Show Table', command=show_csv_table, state='disabled')
show_table_btn.pack(padx=10, pady=5)

# Ensure buttons reflect initial state
update_csv_buttons()

root.mainloop()
