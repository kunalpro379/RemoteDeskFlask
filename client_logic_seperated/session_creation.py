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
from host_machine import RemoteDesktopPro
from ui_componants.constants import ConnectionStatus
from ui_componants.theme import Theme
from ui_componants.RemoteDeskProClass import RemoteDesktopPro


class SessionCreation(RemoteDesktopPro):

    def start_session(self):
        """Start the remote desktop session"""
        if not self.key.get():
            messagebox.showerror("Error", "Please enter an access key")
            return
            
        if not self.host.get():
            messagebox.showerror("Error", "Please enter a valid host address")
            return
            
        try:
            self.connection_status.set(ConnectionStatus.CONNECTING)
            self.log_message("Establishing connection...", "warning")
            
            # Test connection
            response = requests.post(
                f"{self.host.get()}/new_session",
                json={'_key': self.key.get()},
                timeout=5
            )
            
            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")
            
            # Start session
            self.is_running = True
            self.connection_status.set(ConnectionStatus.CONNECTED)
            self.stats["start_time"] = time.time()
            self.stats["bytes_sent"] = 0
            self.stats["frames_captured"] = 0
            self.stats["events_processed"] = 0
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.key_entry.config(state=tk.DISABLED)
            
            # Start capture thread
            self.capture_thread = threading.Thread(target=self.capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            # Save settings
            self.save_settings()
            
            self.log_message("Remote desktop session started successfully", "success")
            
        except Exception as e:
            self.connection_status.set(ConnectionStatus.ERROR)
            self.log_message(f"Failed to start session: {str(e)}", "error")
            messagebox.showerror("Connection Error", str(e))

    def stop_session(self):
        """Stop the remote desktop session"""
        try:
            self.is_running = False
            self.connection_status.set(ConnectionStatus.DISCONNECTED)
            
            # Update UI
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.key_entry.config(state=tk.NORMAL)
            
            # Reset progress bar
            self.quality_bar["value"] = 0
            
            self.log_message("Remote desktop session ended", "warning")
            
        except Exception as e:
            self.log_message(f"Error stopping session: {str(e)}", "error")