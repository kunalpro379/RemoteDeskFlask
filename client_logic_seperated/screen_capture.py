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

class ScreenCapture(SessionCreation):

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


