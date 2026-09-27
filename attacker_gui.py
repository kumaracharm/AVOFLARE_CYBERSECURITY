import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import time

# Configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 8888

class AttackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("UAV Threat Injector (Spoofing & Hacking)")
        self.root.geometry("400x380")
        self.root.configure(bg="#2d2d2d")
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.heartbeat_active = True
        
        # Start background heartbeat to keep the RTOS watchdog happy
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#444", foreground="white", font=('Helvetica', 10, 'bold'))
        style.map("TButton", background=[('active', '#666')])
        
        lbl = tk.Label(root, text="Adversary Command Injection", font=("Helvetica", 14, "bold"), bg="#2d2d2d", fg="#ff4444")
        lbl.pack(pady=10)

        # 1. Valid Command
        btn_valid = ttk.Button(root, text="1. Send Valid Waypoint", command=self.send_valid)
        btn_valid.pack(fill='x', padx=20, pady=5)

        # 2. Spoof Actuator
        btn_actuator = ttk.Button(root, text="2. Spoof RAW Actuator Override", command=self.send_actuator)
        btn_actuator.pack(fill='x', padx=20, pady=5)

        # 3. Schema Violation
        btn_schema = ttk.Button(root, text="3. Inject Unrecoverable Altitude (85,000m)", command=self.send_schema)
        btn_schema.pack(fill='x', padx=20, pady=5)

        # 4. DoS Flood
        btn_dos = ttk.Button(root, text="4. Execute DoS Flood (20 packets)", command=self.send_dos)
        btn_dos.pack(fill='x', padx=20, pady=5)
        
        # 5. Crash RTOS / Stop Heartbeat
        self.btn_crash = ttk.Button(root, text="5. CRASH AI SYSTEM (Stop Heartbeat)", command=self.toggle_crash)
        self.btn_crash.pack(fill='x', padx=20, pady=5)
        
        status_lbl = tk.Label(root, text="Watch the Terminal for CDSG Firewall Drops!", font=("Helvetica", 9, "italic"), bg="#2d2d2d", fg="#aaaaaa")
        status_lbl.pack(pady=20)

    def send_cmd(self, cmd_str):
        self.sock.sendto(cmd_str.encode(), (UDP_IP, UDP_PORT))

    def send_valid(self):
        self.send_cmd("SET_WAYPOINT 1500 50")

    def send_actuator(self):
        self.send_cmd("RAW_ACTUATOR_OVERRIDE 0 0")

    def send_schema(self):
        self.send_cmd("SET_WAYPOINT 85000 25")

    def send_dos(self):
        for _ in range(20):
            self.send_cmd("UPDATE_TARGET 0 0")
            time.sleep(0.01) # Rapid fire

    def toggle_crash(self):
        if self.heartbeat_active:
            self.heartbeat_active = False
            self.send_cmd("CRASH 0 0")
            self.btn_crash.config(text="RECOVER AI SYSTEM (Resume Heartbeat)")
        else:
            self.heartbeat_active = True
            self.btn_crash.config(text="5. CRASH AI SYSTEM (Stop Heartbeat)")

    def heartbeat_loop(self):
        while True:
            if self.heartbeat_active:
                self.send_cmd("HEARTBEAT 0 0")
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = AttackerGUI(root)
    root.mainloop()
