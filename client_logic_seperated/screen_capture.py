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
from client_logic_seperated.session_creation import SessionCreation

class ScreenCapture(SessionCreation):
    def capture_loop(self):
        """Main screen capture and event processing loop"""
        shell = win32com.client.Dispatch("WScript.Shell")
        prev_img = None
        consecutive_errors = 0
        
        while self.is_running:
            try:
                # Capture screen
                screenshot = self.capture_screen()
                if screenshot:
                    # Compress and prepare image
                    image_data = self.prepare_image(screenshot)
                    
                    # Send if changed
                    if image_data != prev_img:
                        self.send_screenshot(image_data)
                        prev_img = image_data
                        
                    # Process remote events
                    self.process_remote_events(shell)
                    
                    # Reset error counter on success
                    consecutive_errors = 0
                    
                time.sleep(0.1)  # Prevent excessive CPU usage
                
            except Exception as e:
                consecutive_errors += 1
                self.status_queue.put((f"Capture error: {str(e)}", "error"))
                
                # Stop session if too many consecutive errors
                if consecutive_errors > 5:
                    self.is_running = False
                    self.status_queue.put(("Too many consecutive errors, stopping session", "error"))
                    self.root.after(0, self.stop_session)
                    break
                    
                time.sleep(1)  # Wait before retrying

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
            
            # Cleanup
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
                image.save(image_buffer, 'PNG', optimize=True)
                return image_buffer.getvalue()
        except Exception as e:
            self.status_queue.put((f"Image preparation error: {str(e)}", "error"))
            return None
