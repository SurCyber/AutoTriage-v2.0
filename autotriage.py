# android_forensic_tool_gui.py

import subprocess
import sys
import sys
import os
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
from tkinter import filedialog

REPORTS_DIR = os.path.join(BASE_DIR, "reports")  # default fallback


def browse_output_folder():
    path = filedialog.askdirectory(title="Select Output Folder")
    if path:
        output_dir_var.set(path)
        global REPORTS_DIR
        REPORTS_DIR = path
        os.makedirs(REPORTS_DIR, exist_ok=True)

selected_device = None

# -------------------- ADB Utilities --------------------
ADB_PATH = os.path.join(BASE_DIR, "Tools", "adb.exe")

def run_adb_command(cmd_list):
    full_cmd = [ADB_PATH] + cmd_list[1:] if "adb" in cmd_list[0] else cmd_list
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        return result.stdout.strip()
    except FileNotFoundError:
        return "ADB not found. Ensure adb.exe is bundled correctly."


def list_connected_devices():
    output = run_adb_command(["adb", "devices", "-l"])
    lines = output.splitlines()
    devices = []
    for line in lines[1:]:
        if "device" in line and not "offline" in line:
            parts = line.split()
            device_id = parts[0]
            info = " ".join(parts[1:])
            devices.append((device_id, f"{device_id} - {info}"))
    return devices

def get_installed_apps():
    output = run_adb_command(["adb", "-s", selected_device, "shell", "pm", "list", "packages"])
    return "\n".join([line.split(":")[1] for line in output.splitlines()])

def get_uninstalled_apps():
    output = run_adb_command(["adb", "-s", selected_device, "shell", "pm", "list", "packages", "-u"])
    return "\n".join([line.split(":")[1] for line in output.splitlines()])

def get_current_foreground_app():
    output = run_adb_command(["adb", "-s", selected_device, "shell", "dumpsys", "window"])
    return "\n".join([line for line in output.splitlines() if "mCurrentFocus" in line])

def get_resumed_activities():
    output = run_adb_command(["adb", "-s", selected_device, "shell", "dumpsys", "activity", "activities"])
    return "\n".join([line for line in output.splitlines() if "ResumedActivity" in line])

def get_current_user():
    return run_adb_command(["adb", "-s", selected_device, "shell", "am", "get-current-user"])

def get_user_profiles():
    return run_adb_command(["adb", "-s", selected_device, "shell", "pm", "list", "users"])

def capture_logcat():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"logcat_{selected_device}_{timestamp}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        subprocess.run(["adb", "-s", selected_device, "logcat", "-d"], stdout=f, text=True)
    return f"Logcat saved to {filename}"

import csv

import threading

# -------------------- HTML Report Generator --------------------
def generate_html_report():
    from datetime import datetime, timezone
    import glob
    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_path = os.path.join(REPORTS_DIR, f"forensic_report_{selected_device}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

    device_info_raw = run_adb_command(["adb", "-s", selected_device, "devices", "-l"])
    device_line = next((line for line in device_info_raw.splitlines() if selected_device in line), "Not available")
    device_info = device_line if device_line else "Not available"

    logo_path = logo_path_var.get()
    logo_tag = f'<img src="{logo_path}" alt="Logo" width="100" height="100">' if logo_path else ""

    rows_html = ""
    import glob
    csv_files = sorted(glob.glob(os.path.join(REPORTS_DIR, f"*_{selected_device}_*.csv")))
    for file in csv_files:
        try:
            with open(file, encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                if len(lines) > 1:
                    status = "✅ Found"
                elif len(lines) == 1:
                    status = "❌ No Data"
                else:
                    status = "Not Analyzed"
                data_type = os.path.basename(file).split('_')[0].replace('_', ' ').title()
                link = os.path.basename(file)
                rows_html += f"<tr><td>{device_info}</td><td><a href='{link}'>{link}</a></td><td>{data_type}</td><td>{status}</td></tr>"
        except:
            data_type = os.path.basename(file).split('_')[0].replace('_', ' ').title()
            link = os.path.basename(file)
            rows_html += f"<tr><td>{device_info}</td><td><a href='{link}'>{link}</a></td><td>{data_type}</td><td>❌ Error</td></tr>"


    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"""
        <html>
        <head><title>Android Forensic Report</title>
        <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; color: #007BFF; font-weight: bold; }}
</style>
        </head>
        <body>
            <h1>Android Forensic Report</h1>
            <p><strong>Date:</strong> {utc_now}</p>
            <p><strong>Investigator:</strong> {investigator_entry.get()}</p>
            <p><strong>Organization:</strong> {organization_entry.get()}</p>
            {logo_tag}
            <h2>Device: {device_info}</h2>
            <table>
<tr><th>Source (Device)</th><th>Destination (CSV Report)</th><th>Data Type</th><th>Status</th></tr>
                {rows_html}
            </table>
            <footer style='margin-top: 50px; font-size: 0.9em; color: gray; text-align: center;'>
            <p>Generated by AutoTriage v2.0</p>
            <p>Made by Soukarya Sur. Follow me on LinkedIn https://www.linkedin.com/in/soukarya-sur-096589256/</p>
        </footer>
        </body>
        </html>
        """)

    messagebox.showinfo("Report Generated", f"HTML report saved to: {report_path}")

# -------------------- GUI Functions --------------------
def display_output(title, content):
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, f"=== {title} ===\n{content}")

def refresh_device_list():
    devices = list_connected_devices()
    device_combo['values'] = [info for (_, info) in devices]
    if devices:
        device_combo.current(0)
        on_device_select(None)
    else:
        messagebox.showerror("No Devices", "No connected device found.\nPlease connect a device and enable USB debugging.")

def on_device_select(event):
    global selected_device
    index = device_combo.current()
    devices = list_connected_devices()
    if 0 <= index < len(devices):
        selected_device = devices[index][0]

def show_installed_apps():
    threading.Thread(target=_show_installed_apps).start()

def _show_installed_apps():
    output = get_installed_apps()
    display_output("Installed Apps", output)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"installed_apps_{selected_device}_{timestamp}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Package Name"])
        for line in output.splitlines():
            writer.writerow([line])

def show_uninstalled_apps():
    threading.Thread(target=_show_uninstalled_apps).start()

def _show_uninstalled_apps():
    all_packages = get_uninstalled_apps().splitlines()
    installed = get_installed_apps().splitlines()
    uninstalled_only = sorted(set(all_packages) - set(installed))

    output = output = "\n".join(uninstalled_only)
  
    display_output("Uninstalled (Retained) Apps", output)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"uninstalled_apps_{selected_device}_{timestamp}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Uninstalled Package Name"])
        for line in uninstalled_only:
            writer.writerow([line])

def show_foreground_app():
    threading.Thread(target=_show_foreground_app).start()

def _show_foreground_app():
    output = get_current_foreground_app()
    display_output("Current Foreground App", output)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"foreground_app_{selected_device}_{timestamp}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Foreground App Info"])
        for line in output.splitlines():
            writer.writerow([line])

def show_resumed_activities():
    threading.Thread(target=_show_resumed_activities).start()

def _show_resumed_activities():
    output = get_resumed_activities()
    display_output("Resumed Activities", output)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"resumed_activities_{selected_device}_{timestamp}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Resumed Activity Info"])
        for line in output.splitlines():
            writer.writerow([line])

def show_current_user():
    threading.Thread(target=_show_current_user).start()

def _show_current_user():
    output = get_current_user()
    display_output("Current User ID", output)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"current_user_{selected_device}_{timestamp}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Current User ID"])
        writer.writerow([output])

def show_user_profiles():
    threading.Thread(target=_show_user_profiles).start()

def _show_user_profiles():
    output = get_user_profiles()
    display_output("User Profiles", output)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORTS_DIR, f"user_profiles_{selected_device}_{timestamp}.csv")
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User Info"])
        for line in output.splitlines():
            writer.writerow([line])

def save_logcat():
    threading.Thread(target=_save_logcat).start()

def _save_logcat():
    result = capture_logcat()
    messagebox.showinfo("Logcat Saved", result)

import webbrowser

from tkinter import filedialog, simpledialog
from PIL import Image, ImageTk

# -------------------- GUI Setup --------------------
root = tk.Tk()
output_dir_var = tk.StringVar()
root.title("Android Forensic Automation Tool")
root.geometry("850x620")

# Investigator & organization input UI
info_frame = tk.Frame(root)
info_frame.pack(pady=5)

tk.Label(info_frame, text="Investigator:").grid(row=0, column=0, padx=5, sticky='e')
investigator_entry = tk.Entry(info_frame, width=30)
investigator_entry.grid(row=0, column=1, padx=5)


tk.Label(info_frame, text="Organization:").grid(row=0, column=2, padx=5, sticky='e')
organization_entry = tk.Entry(info_frame, width=30)
organization_entry.grid(row=0, column=3, padx=5)

logo_path_var = tk.StringVar()
tk.Label(info_frame, text="Logo:").grid(row=1, column=0, padx=5, sticky='e')
logo_entry = tk.Entry(info_frame, textvariable=logo_path_var, width=30)
logo_entry.grid(row=1, column=1, padx=5)
tk.Button(info_frame, text="Browse", command=lambda: logo_path_var.set(filedialog.askopenfilename(title="Select Logo", filetypes=[("Image Files", "*.png *.jpg *.jpeg")]))).grid(row=1, column=2, padx=5)

tk.Label(info_frame, text="Output Folder:").grid(row=1, column=3, padx=5, sticky='e')
output_entry = tk.Entry(info_frame, textvariable=output_dir_var, width=30)
output_entry.grid(row=1, column=4, padx=5)
tk.Button(info_frame, text="Browse", command=browse_output_folder).grid(row=1, column=5, padx=5)

organization_logo = None
if logo_path_var.get():
    try:
        logo_img = Image.open(logo_path_var.get())
        logo_img = logo_img.resize((100, 100))
        organization_logo = ImageTk.PhotoImage(logo_img)
    except Exception as e:
        messagebox.showerror("Logo Error", f"Could not load logo: {e}")

def open_report_folder():
    threading.Thread(target=lambda: webbrowser.open(REPORTS_DIR)).start()

# Action buttons
frame = tk.Frame(root)
frame.pack(pady=10)
# Top control buttons
control_frame = tk.Frame(root)
control_frame.pack(pady=5)

tk.Button(control_frame, text="Generate HTML Report", command=lambda: threading.Thread(target=generate_html_report).start(), width=25, bg="orange", fg="white").pack(side=tk.LEFT, padx=10)
tk.Button(control_frame, text="Open Report Folder", command=open_report_folder, width=25, bg="#007BFF", fg="white").pack(side=tk.LEFT, padx=10)

# Device selection frame
device_frame = tk.Frame(root)
device_frame.pack(pady=10)
tk.Label(device_frame, text="Select Device:").pack(side=tk.LEFT, padx=5)
device_combo = ttk.Combobox(device_frame, state="readonly", width=80)
device_combo.pack(side=tk.LEFT, padx=5)
device_combo.bind("<<ComboboxSelected>>", on_device_select)
tk.Button(device_frame, text="Refresh Devices", command=refresh_device_list).pack(side=tk.LEFT, padx=5)


# Action buttons
frame = tk.Frame(root)
frame.pack(pady=10)

def list_features():
    features = [
        "Show Current User",
        "List Installed Apps",
        "List Uninstalled Apps",
        "Show Foreground App",
        "Show Resumed Activities",
        "Show User Profiles",
        "Capture Logcat",
        "Open Report Folder"
    ]
    display_output("Available Features", "\n".join(features))


buttons = [
    ("List Features", list_features),
    ("Show Current User", show_current_user),
    ("List Installed Apps", show_installed_apps),
    ("List Uninstalled Apps", show_uninstalled_apps),
    ("Show Foreground App", show_foreground_app),
    ("Show Resumed Activities", show_resumed_activities),
    ("Show User Profiles", show_user_profiles),
    ("Capture Logcat", save_logcat),
]

for i, (label, command) in enumerate(buttons):
    tk.Button(frame, text=label, command=command, width=30).grid(row=i // 2, column=i % 2, padx=10, pady=5)

# Output box
output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=20)
output_text.pack(padx=10, pady=10)

# Load initial devices
refresh_device_list()

root.mainloop()
