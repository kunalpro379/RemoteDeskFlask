import tkinter as tk
from tkinter import ttk, messagebox, font
import win32gui
import win32ui
import win32con
import win32api
import win32com.client
from PIL import Image, ImageTk
import io
import requests
import time
import threading
from queue import Queue
import traceback
import json
import sys
import os
from datetime import datetime

from ui_componants.constants import ConnectionStatus
from ui_componants.theme import Theme

class RemoteDesktopPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Desktop Control Pro")
        self.root.geometry("800x900")
        self.root.minsize(600, 700)
        
        # Application state
        self.key = tk.StringVar(value="")
        self.host = tk.StringVar(value="http://127.0.0.1:5000")
        self.connection_status = tk.StringVar(value=ConnectionStatus.DISCONNECTED)
        self.is_running = False
        self.status_queue = Queue()
        self.stats = {
            "bytes_sent": 0,
            "frames_captured": 0,
            "events_processed": 0,
            "start_time": None
        }
        #
        # Load saved settings
        self.load_settings()
        
        # Initialize UI
        self.setup_styles()
        self.create_ui()
        self.setup_bindings()
        self.start_status_update()

    def setup_styles(self):
        """Configure ttk styles for a premium look"""
        style = ttk.Style()
        
        # General styles
        style.configure("Premium.TFrame",
                       background=Theme.BG_LIGHT)
        
        # Header styles
        style.configure("Header.TLabel",
                       background=Theme.BG_LIGHT,
                       foreground=Theme.TEXT_DARK,
                       font=("Segoe UI", 24, "bold"))
                       
        style.configure("Subheader.TLabel",
                       background=Theme.BG_LIGHT,
                       foreground=Theme.TEXT_DARK,
                       font=("Segoe UI", 14, "bold"))
        
        # Button styles
        style.configure("Primary.TButton",
                       padding=(20, 10),
                       background=Theme.PRIMARY,
                       foreground=Theme.TEXT_LIGHT,
                       font=("Segoe UI", 11, "bold"))
                       
        style.configure("Stop.TButton",
                       padding=(20, 10),
                       background=Theme.ERROR,
                       foreground=Theme.TEXT_LIGHT,
                       font=("Segoe UI", 11, "bold"))
        
        # Entry styles
        style.configure("Premium.TEntry",
                       padding=10,
                       fieldbackground=Theme.BG_MEDIUM)
                       
        # Label styles
        style.configure("Status.TLabel",
                       background=Theme.BG_LIGHT,
                       font=("Segoe UI", 11))

    def create_ui(self):
        """Create the main user interface"""
        # Main container
        self.container = ttk.Frame(self.root, style="Premium.TFrame", padding=20)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Header section
        self.create_header()
        
        # Connection section
        self.create_connection_section()
        
        # Status section
        self.create_status_section()
        
        # Statistics section
        self.create_stats_section()
        
        # Log section
        self.create_log_section()

    def create_header(self):
        """Create the application header"""
        header_frame = ttk.Frame(self.container, style="Premium.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Logo and title
        title_frame = ttk.Frame(header_frame, style="Premium.TFrame")
        title_frame.pack(fill="x")
        
        ttk.Label(title_frame,
                 text="Remote Desktop Control Pro",
                 style="Header.TLabel").pack(side="left")
                 
        ttk.Label(title_frame,
                 text="Enterprise Edition v2.1",
                 style="Status.TLabel",
                 foreground=Theme.TEXT_MUTED).pack(side="left", padx=(10, 0))

    def create_connection_section(self):
        """Create the connection settings section"""
        conn_frame = ttk.LabelFrame(self.container,
                                  text="Connection Settings",
                                  style="Premium.TFrame",
                                  padding=15)
        conn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        # Server settings
        server_frame = ttk.Frame(conn_frame, style="Premium.TFrame")
        server_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(server_frame,
                 text="Server:",
                 style="Status.TLabel").pack(side="left")
                 
        ttk.Entry(server_frame,
                 textvariable=self.host,
                 width=40,
                 style="Premium.TEntry").pack(side="left", padx=10)
        
        # Access key
        key_frame = ttk.Frame(conn_frame, style="Premium.TFrame")
        key_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(key_frame,
                 text="Access Key:",
                 style="Status.TLabel").pack(side="left")
                 
        self.key_entry = ttk.Entry(key_frame,
                                 textvariable=self.key,
                                 width=30,
                                 style="Premium.TEntry",
                                 show="●")
        self.key_entry.pack(side="left", padx=10)
        
        # Control buttons
        button_frame = ttk.Frame(conn_frame, style="Premium.TFrame")
        button_frame.pack(fill="x")
        
        self.start_button = ttk.Button(button_frame,
                                     text="▶ Start Session",
                                     style="Primary.TButton",
                                     command=self.start_session)
        self.start_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame,
                                    text="⬛ End Session",
                                    style="Stop.TButton",
                                    command=self.stop_session,
                                    state=tk.DISABLED)
        self.stop_button.pack(side="left")

    def create_status_section(self):
        """Create the status display section"""
        status_frame = ttk.LabelFrame(self.container,
                                    text="Connection Status",
                                    style="Premium.TFrame",
                                    padding=15)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        
        # Status indicator
        self.status_label = ttk.Label(status_frame,
                                    text="Not Connected",
                                    style="Status.TLabel")
        self.status_label.pack(fill="x")
        
        # Connection quality
        self.quality_frame = ttk.Frame(status_frame, style="Premium.TFrame")
        self.quality_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(self.quality_frame,
                 text="Connection Quality:",
                 style="Status.TLabel").pack(side="left")
                 
        self.quality_bar = ttk.Progressbar(self.quality_frame,
                                         length=200,
                                         mode='determinate')
        self.quality_bar.pack(side="left", padx=10)

    def create_stats_section(self):
        """Create the statistics display section"""
        stats_frame = ttk.LabelFrame(self.container,
                                   text="Session Statistics",
                                   style="Premium.TFrame",
                                   padding=15)
        stats_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        # Statistics grid
        self.stats_labels = {}
        stats_grid = ttk.Frame(stats_frame, style="Premium.TFrame")
        stats_grid.pack(fill="x")
        
        stats = [
            ("Duration", "00:00:00"),
            ("Data Transferred", "0 KB"),
            ("Frames Captured", "0"),
            ("Events Processed", "0"),
            ("Average FPS", "0.0")
        ]
        
        for i, (label, value) in enumerate(stats):
            ttk.Label(stats_grid,
                     text=f"{label}:",
                     style="Status.TLabel").grid(row=i, column=0, sticky="w", pady=2)
                     
            stat_label = ttk.Label(stats_grid,
                                 text=value,
                                 style="Status.TLabel")
            stat_label.grid(row=i, column=1, sticky="w", padx=(10, 0), pady=2)
            self.stats_labels[label] = stat_label

    def create_log_section(self):
        """Create the activity log section"""
        log_frame = ttk.LabelFrame(self.container,
                                 text="Activity Log",
                                 style="Premium.TFrame",
                                 padding=15)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 20))
        self.container.grid_rowconfigure(4, weight=1)
        
        # Log text widget with custom styling
        self.log_text = tk.Text(log_frame,
                              height=10,
                              wrap=tk.WORD,
                              font=("Consolas", 10),
                              bg=Theme.BG_DARK,
                              fg=Theme.TEXT_LIGHT,
                              padx=10,
                              pady=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame,
                                orient="vertical",
                                command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def setup_bindings(self):
        """Setup event bindings"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Control-q>", lambda e: self.on_closing())
        self.root.bind("<F5>", lambda e: self.start_session())
        self.root.bind("<F6>", lambda e: self.stop_session())

    def load_settings(self):
        """Load saved settings from file"""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    settings = json.load(f)
                    self.key.set(settings.get("key", ""))
                    self.host.set(settings.get("host", "http://3.7.254.110:5000"))
        except Exception as e:
            self.log_message(f"Failed to load settings: {str(e)}", "error")

    def save_settings(self):
        """Save current settings to file"""
        try:
            settings = {
                "key": self.key.get(),
                "host": self.host.get()
            }
            with open("settings.json", "w") as f:
                json.dump(settings, f)
        except Exception as e:
            self.log_message(f"Failed to save settings: {str(e)}", "error")

    def log_message(self, message, level="info"):
        """Add a message to the log with timestamp and color coding"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Color tags
        if not hasattr(self, "log_tags_configured"):
            self.log_text.tag_configure("error", foreground="#ef4444")
            self.log_text.tag_configure("warning", foreground="#f59e0b")
            self.log_text.tag_configure("success", foreground="#10b981")
            self.log_text.tag_configure("timestamp", foreground="#6b7280")
            self.log_tags_configured = True
        
        # Insert message with appropriate tag
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)
        
        # Update status label
        if level == "error":
            self.status_label.configure(foreground=Theme.ERROR)
        elif level == "warning":
            self.status_label.configure(foreground=Theme.WARNING)
        elif level == "success":
            self.status_label.configure(foreground=Theme.SUCCESS)
        
        status_text = message[:50] + "..." if len(message) > 50 else message
        self.status_label.configure(text=status_text)


        def update_statistics(self):
            """Update session statistics"""
            if self.stats["start_time"]:
                duration = time.time() - self.stats["start_time"]
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                
                self.stats_labels["Duration"].configure(
                    text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Update other stats
                self.stats_labels["Data Transferred"].configure(
                    text=f"{self.stats['bytes_sent'] / 1024:.1f} KB")
                self.stats_labels["Frames Captured"].configure(
                    text=str(self.stats["frames_captured"]))
                self.stats_labels["Events Processed"].configure(
                    text=str(self.stats["events_processed"]))
                
                if duration > 0:
                    fps = self.stats["frames_captured"] / duration
                    self.stats_labels["Average FPS"].configure(text=f"{fps:.1f}")
                
                # Update connection quality (0-100)
                quality = min(100, (fps * 10)) if fps > 0 else 0
                self.quality_bar["value"] = quality

    def start_status_update(self):
        """Start the status update loop"""
        try:
            while not self.status_queue.empty():
                message, level = self.status_queue.get_nowait()
                self.log_message(message, level)
                
            if self.is_running:
                self.update_statistics()
                
        except Exception as e:
            print(f"Status update error: {str(e)}")
            
        self.root.after(100, self.start_status_update)

