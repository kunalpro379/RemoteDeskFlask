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
import socket
import struct
import cv2
import numpy as np
import mss
import pyautogui
from datetime import datetime
from queue import Queue


SERVER_HOST = "127.0.0.1"     
SERVER_PORT = 8000        
VIDEO_FPS = 60
ENCODE_QUALITY = 80           
MOUSE_CURSOR_SIZE = 10        
class RemoteDesktopHandler:
    def __init__(self, root):
        self.root = root
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((SERVER_HOST, SERVER_PORT))
        print("Connected to server...")

        self.shell = win32com.client.Dispatch("WScript.Shell")
        self.status_queue = Queue()
        self.is_running = True


        self.stats = {"bytes_sent": 0, "frames_captured": 0, "events_processed": 0}
        
        threading.Thread(target=self.screen_record_and_send, daemon=True).start()
        threading.Thread(target=self.event_handler_loop, daemon=True).start()

    def screen_record_and_send(self):
        """Capture the screen and send to the server."""
        with mss.mss() as sct:
            print("Initializing screen capture...")

            monitor = sct.monitors[1]
            print(f"Primary monitor dimensions: {monitor}")

            self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

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
        """Continuously poll for events and handle them."""
        while self.is_running:
            self.process_remote_events()

    def process_remote_events(self):
        """Process remote control events from server."""
        try:
            response = requests.post(
                f"{SERVER_HOST}/events_get",
                json={'_key': "unique_key"},  # Example key; replace with actual key as needed
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
        """Handle remote mouse click events."""
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
        """Handle remote keyboard events."""
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
