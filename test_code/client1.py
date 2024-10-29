# client.py
import socketio
import numpy as np
import cv2
from PIL import ImageGrab
import base64

sio = socketio.Client()

# Connect to the server
@sio.event
def connect():
    print("Connected to the server.")

# Capture and send frames
def capture_screen():
    while True:
        # Capture the screen
        screen = ImageGrab.grab()
        screen_np = np.array(screen)
        _, buffer = cv2.imencode('.jpg', screen_np)
        frame_data = base64.b64encode(buffer).decode('utf-8')
        sio.emit('frame', frame_data)

# Connect and start capturing
if __name__ == '__main__':
    sio.connect('http://localhost:6000')
    capture_screen()
