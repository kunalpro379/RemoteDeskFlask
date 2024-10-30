import tkinter as tk
from tkinter import ttk, messagebox, font
import win32gui
import win32ui
import win32con
import win32api
import win32com.client
from PIL import Image, ImageTk, ImageChops
import io
import time
import traceback
import json
import sys
import os
from datetime import datetime
from host_machine import RemoteDesktopPro
from ui_componants.constants import ConnectionStatus
from ui_componants.theme import Theme
from client_logic_seperated.session_creation import SessionCreation
import socket
import struct
import time
import cv2
import numpy as np
import mss
import pyautogui

# Configuration
SERVER_HOST = "127.0.0.1"     # Replace with your server's IP address
SERVER_PORT = 8000            # Ensure this port matches your server setup
VIDEO_FPS = 60                 # Target FPS
ENCODE_QUALITY = 80            # JPEG quality (1-100), higher is better quality
MOUSE_CURSOR_SIZE = 10         # Size of mouse cursor symbol

class ScreenCapture(SessionCreation):
    def __init__(self, root):
        super().__init__(root)  # Pass root to ScreenCapture
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((SERVER_HOST, SERVER_PORT))
        print('connected to server...')

    #old fucking approach ki mkc     
    '''
    def calculate_image_delta(self, prev_image, current_image):
        """Calculate the difference between two images."""
        try:
            if prev_image is None:
                return current_image

            # Calculate the difference using ImageChops
            delta = ImageChops.difference(prev_image, current_image)
            return delta
        except Exception as e:
            self.status_queue.put((f"Image delta calculation error: {str(e)}", "error"))
            return current_image

    def capture_loop(self):
        shell = win32com.client.Dispatch("WScript.Shell")
        prev_img = None
        frame_counter = 0

        while self.is_running:
            try:
                screenshot = self.capture_screen()
                if screenshot:
                    # Process every second frame for delta calculation
                    if frame_counter % 2 == 0:
                        delta_image = self.calculate_image_delta(prev_img, screenshot)
                    else:
                        delta_image = screenshot
                    
                    image_data = self.prepare_image(delta_image)
                    
                    if image_data:
                        self.send_screenshot(image_data)
                        prev_img = screenshot  # Update the previous image only after successful send
                    
                    self.process_remote_events(shell)
                    
                frame_counter += 1
                time.sleep(0.05)  # Adjust as needed
                
            except Exception as e:
                self.handle_capture_error(e)


    def capture_screen(self):
        """Capture the screen using Windows API"""
        try:
            # Get screen dimensions
            hdesktop = win32gui.GetDesktopWindow()
            width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

            # Create device contexts
            desktop_dc = win32gui.GetWindowDC(hdesktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            # Create bitmap
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, width, height)
            mem_dc.SelectObject(screenshot)
            
            # Copy screen to bitmap
            mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)
            
            # Convert to PIL Image
            bmpinfo = screenshot.GetInfo()
            bmpstr = screenshot.GetBitmapBits(True)
            
            image = Image.frombytes(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX'
            )
            
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot.GetHandle())
            
            return image
            
        except Exception as e:
            self.status_queue.put((f"Screen capture error: {str(e)}", "error"))
            return None

    def prepare_image(self, image):
        """Compress and prepare image for sending"""
        try:
            with io.BytesIO() as image_buffer:
                # Use LANCZOS instead of ANTIALIAS for resizing
                image = image.resize(image.size, Image.LANCZOS)  
                image.save(image_buffer, 'PNG', optimize=True)
                return image_buffer.getvalue()
        except Exception as e:
            self.status_queue.put((f"Image preparation error: {str(e)}", "error"))
            return None
    print('hello')
        '''
    
    
    def screen_record_and_send(self):
        # Initialize screen capture using mss
        with mss.mss() as sct:
            print('Initializing screen capture...')

            # Get the dimensions of the primary monitor
            monitor = sct.monitors[1]  # Use monitor[1] for the primary display
            print(f'Primary monitor dimensions: {monitor}')

            # Initialize socket connection to server
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            print('Connected to server at', SERVER_HOST, SERVER_PORT)

            # Set socket options for low latency
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            try:
                while True:
                    # Capture the screen
                    img = sct.grab(monitor)
                    img_np = np.array(img)

                    # Convert BGRA to BGR
                    frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

                    # Get mouse position
                    mouse_x, mouse_y = pyautogui.position()

                    # Draw mouse cursor as a red circle
                    cv2.circle(frame, (mouse_x, mouse_y), MOUSE_CURSOR_SIZE, (0, 0, 255), -1)

                    # Encode frame as JPEG with adjustable quality
                    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), ENCODE_QUALITY]
                    _, frame_bytes = cv2.imencode(".jpg", frame, encode_params)
                    frame_data = frame_bytes.tobytes()
                    frame_size = len(frame_data)

                    # Log frame details
                    print(f'Sending frame of size: {frame_size} bytes')
                    print(f'Mouse position: ({mouse_x}, {mouse_y})')

                    # Send frame size followed by frame data
                    client_socket.sendall(struct.pack(">I", frame_size) + frame_data)

                    # Send mouse position
                    client_socket.sendall(struct.pack(">II", mouse_x, mouse_y))

                    # Log sending status
                    print('Frame and mouse position sent. Waiting for acknowledgment...')

                    # Receive acknowledgment
                    ack = client_socket.recv(1024)
                    if ack.decode() == "ACK":
                        print("Frame sent successfully, ACK received.")
                    else:
                        print("Error: ACK not received.")

                    # Control FPS
                    time.sleep(1 / VIDEO_FPS)

            except Exception as e:
                print(f"Error during streaming: {e}")
            finally:
                client_socket.close()
                print("Connection closed.")
