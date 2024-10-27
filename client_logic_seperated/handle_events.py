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
from client_logic_seperated.screen_capture import ScreenCapture


class HandleEvents(ScreenCapture):

    def send_screenshot(self, image_data):
        """Send screenshot to server"""
        try:
            if not image_data:
                return
                
            filename = f"{round(time.time()*1000)}_{self.key.get()}"
            files = {filename: ('screenshot.png', image_data, 'multipart/form-data')}
            
            response = requests.post(
                f"{self.host.get()}/capture_post",
                files=files,
                timeout=5
            )
            
            if response.status_code == 200:
                self.stats["bytes_sent"] += len(image_data)
                self.stats["frames_captured"] += 1
                self.status_queue.put(("Screenshot sent successfully", "success"))
            else:
                raise Exception(f"Server returned status code: {response.status_code}")
                
        except Exception as e:
            self.status_queue.put((f"Failed to send screenshot: {str(e)}", "error"))

    def process_remote_events(self, shell):
        """Process remote control events"""
        try:
            response = requests.post(
                f"{self.host.get()}/events_get",
                json={'_key': self.key.get()},
                timeout=5
            )
            
            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")
                
            data = response.json()
            
            for event in data.get('events', []):
                if event['type'] == 'click':
                    self.handle_click_event(event)
                elif event['type'] == 'keydown':
                    self.handle_key_event(event, shell)
                    
                self.stats["events_processed"] += 1
                
        except Exception as e:
            self.status_queue.put((f"Failed to process events: {str(e)}", "error"))

    def handle_click_event(self, event):
        """Handle remote mouse click events"""
        try:
            x, y = event['x'], event['y']
            
            # Move cursor
            win32api.SetCursorPos((x, y))
            time.sleep(0.1)
            
            # Simulate click
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            
            self.status_queue.put((f"Mouse click at ({x}, {y})", "success"))
            
        except Exception as e:
            self.status_queue.put((f"Failed to process click event: {str(e)}", "error"))

    def handle_key_event(self, event, shell):
        """Handle remote keyboard events"""
        try:
            # Build key command
            cmd = ''
            if event['shiftKey']: cmd += '+'
            if event['ctrlKey']: cmd += '^'
            if event['altKey']: cmd += '%'
            
            # Add key
            if len(event['key']) == 1:
                cmd += event['key'].lower()
            else:
                cmd += '{' + event['key'].upper() + '}'
                
            # Send keystroke
            shell.SendKeys(cmd)
            self.status_queue.put((f"Key press: {cmd}", "success"))
            
        except Exception as e:
            self.status_queue.put((f"Failed to process key event: {str(e)}", "error"))

