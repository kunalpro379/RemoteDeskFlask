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
from client_logic_seperated.handleEventsAndScreens import RemoteDesktopHandler
import socket
import struct
import cv2
import numpy as np
import mss
import pyautogui

SERVER_HOST = "127.0.0.1"     
SERVER_PORT = 8000        
VIDEO_FPS = 60
ENCODE_QUALITY = 80           
MOUSE_CURSOR_SIZE = 10     

class SessionCreation(RemoteDesktopPro):
    def __init__(self, root):
        super().__init__(root)
        self.root = root

        self.shell = win32com.client.Dispatch("WScript.Shell")
        self.status_queue = Queue()
        self.is_running = True

        self.stats = {"bytes_sent": 0, "frames_captured": 0, "events_processed": 0}

    def start_session(self):
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
            self.capture_thread = threading.Thread(target=self.screen_record_and_send)
            self.capture_thread.daemon = True
            self.capture_thread.start()

            # Start event handler loop
            self.event_handler_loop_thread = threading.Thread(target=self.event_handler_loop)
            self.event_handler_loop_thread.daemon = True
            self.event_handler_loop_thread.start()

            # Save settings
            self.save_settings()

            self.log_message("Remote desktop session started successfully", "success")

            

        except Exception as e:
            self.connection_status.set(ConnectionStatus.ERROR)
            self.log_message(f"Failed to start session: {str(e)}", "error")
            messagebox.showerror("Connection Error", str(e))

    def stop_session(self):
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



    def screen_record_and_send(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]

            try:
                while self.is_running:
                    img = sct.grab(monitor)
                    img_np = np.array(img)
                    frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

                    mouse_x, mouse_y = pyautogui.position()
                    cv2.circle(frame, (mouse_x, mouse_y), MOUSE_CURSOR_SIZE, (0, 0, 255), -1)

                    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), ENCODE_QUALITY]
                    _, frame_bytes = cv2.imencode(".jpg", frame, encode_params)
                    frame_data = frame_bytes.tobytes()
                    frame_size = len(frame_data)

                    self.client_socket.sendall(struct.pack(">I", frame_size) + frame_data)
                    self.client_socket.sendall(struct.pack(">II", mouse_x, mouse_y))

                    ack = self.client_socket.recv(1024)
                    if ack.decode() == "ACK":
                        print("Frame sent successfully, ACK received.")
                    else:
                        print("Error: ACK not received.")

                    time.sleep(1 / VIDEO_FPS)

            except Exception as e:
                print(f"Error during streaming: {e}")
            finally:
                self.client_socket.close()
                print("Connection closed.")

    def event_handler_loop(self):
        while self.is_running:
            self.process_remote_events()



    '''
    def process_remote_events(self):
        try:
            response = requests.post(
                f"{SERVER_HOST}/events_get",
                json={'_key': "unique_key"},
                timeout=5
            )

            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")

            data = response.json()

            for event in data.get('events', []):
                if event['type'] == 'click':
                    self.handle_click_event(event)
                elif event['type'] == 'keydown':
                    self.handle_key_event(event)

                self.stats["events_processed"] += 1

        except Exception as e:
            self.status_queue.put((f"Failed to process events: {str(e)}", "error"))
'''


    def process_remote_events(self):
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
                    self.handle_key_event(event)

                self.stats["events_processed"] += 1

        except Exception as e:
            self.status_queue.put((f"Failed to process events: {str(e)}", "error"))

    def handle_click_event(self, event):
        try:
            x, y = event['x'], event['y']
            win32api.SetCursorPos((x, y))
            time.sleep(0.1)

            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            self.status_queue.put((f"Mouse click at ({x}, {y})", "success"))

        except Exception as e:
            self.status_queue.put((f"Failed to process click event: {str(e)}", "error"))
    def handle_key_event(self, event):
        try:
            cmd = ''
            if event['shiftKey']: cmd += '+'
            if event['ctrlKey']: cmd += '^'
            if event['altKey']: cmd += '%'

            if len(event['key']) == 1:
                cmd += event['key'].lower()
            else:
                cmd += '{' + event['key'].upper() + '}'

            self.shell.SendKeys(cmd)
            self.status_queue.put((f"Key press: {cmd}", "success"))

        except Exception as e:
            self.status_queue.put((f"Failed to process key event: {str(e)}", "error"))