import socket
import struct
import time
import cv2
import numpy as np
import mss

# Configuration
SERVER_HOST = "127.0.0.1"  # Replace with your server's IP address
SERVER_PORT = 8000          # Ensure this port matches your server setup
VIDEO_RESOLUTION = (1920, 1080)  # Screen resolution
VIDEO_FPS = 30

def screen_record_and_send():
    # Initialize screen capture using mss
    with mss.mss() as sct:
        # Define the bounding box for the screen capture
        monitor = sct.monitors[1]  # Change index to select the right monitor if needed

        # Initialize socket connection to server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, SERVER_PORT))

        try:
            while True:
                # Capture the screen
                img = sct.grab(monitor)
                img_np = np.array(img)

                # Convert BGRA to BGR
                frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

                # Encode frame as JPEG
                _, frame_bytes = cv2.imencode(".jpg", frame)
                frame_data = frame_bytes.tobytes()
                frame_size = len(frame_data)

                # Send frame size followed by frame data
                client_socket.sendall(struct.pack(">I", frame_size) + frame_data)

                # Receive acknowledgment
                ack = client_socket.recv(1024)
                if ack.decode() == "ACK":
                    print("Frame sent successfully")
                else:
                    print("Error sending frame")

                # Control FPS
                time.sleep(1 / VIDEO_FPS)

        finally:
            client_socket.close()

if __name__ == "__main__":
    screen_record_and_send()
