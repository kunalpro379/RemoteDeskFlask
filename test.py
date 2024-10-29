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

def screen_record_and_send():
    # Initialize screen capture using mss
    with mss.mss() as sct:
        # Get the dimensions of the primary monitor
        monitor = sct.monitors[1]  # Use monitor[1] for the primary display
        # Uncomment the next line if you want to specify a specific monitor
        # monitor = sct.monitors[2]  # Replace 2 with the desired monitor index

        # Initialize socket connection to server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, SERVER_PORT))

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

                # Send frame size followed by frame data
                client_socket.sendall(struct.pack(">I", frame_size) + frame_data)

                # Send mouse position
                client_socket.sendall(struct.pack(">II", mouse_x, mouse_y))

                # Receive acknowledgment
                ack = client_socket.recv(1024)
                if ack.decode() != "ACK":
                    print("Error sending frame")

                # Control FPS
                time.sleep(1 / VIDEO_FPS)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

if __name__ == "__main__":
    screen_record_and_send()
