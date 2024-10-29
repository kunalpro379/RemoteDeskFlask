import io
import socket
import struct
import time
import cv2
from flask import Flask, Response
import numpy as np
import threading

app = Flask(__name__)

# State to hold the latest frame and cursor position
latest_frame = None
mouse_position = (0, 0)
lock = threading.Lock()  # To manage access to shared variables

@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>Video Stream</title>
        </head>
        <body>
            <h1>Live Video Stream</h1>
            <img src="/video_feed" width="1000" height="500" />
        </body>
    </html>
    """

def get_frame():
    """Generator function for the video stream"""
    global latest_frame, mouse_position
    while True:
        if latest_frame is not None:
            with lock:  # Acquire lock for thread-safe access
                frame_copy = latest_frame.copy()
                # Draw the mouse cursor on the frame
                cv2.circle(frame_copy, mouse_position, 10, (0, 0, 255), -1)

            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame_copy)
            frame_bytes = buffer.tobytes()

            # Yield the frame in the correct format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(
        get_frame(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

def start_server_socket():
    global latest_frame, mouse_position
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(1)
    print("Server is listening for incoming frames...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connected to {addr}")

        try:
            while True:
                # Receive the size of the frame data
                packed_size = client_socket.recv(4)
                if not packed_size:
                    break
                frame_size = struct.unpack(">I", packed_size)[0]

                # Receive the actual frame data
                frame_data = b''
                remaining = frame_size
                while remaining > 0:
                    chunk = client_socket.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    frame_data += chunk
                    remaining -= len(chunk)

                # Convert frame data to numpy array
                frame_np = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

                if frame is not None:
                    with lock:  # Acquire lock for thread-safe access
                        latest_frame = frame

                # Receive mouse position
                mouse_data = client_socket.recv(8)  # 4 bytes for x, 4 bytes for y
                if mouse_data:
                    mouse_x, mouse_y = struct.unpack(">II", mouse_data)
                    with lock:  # Acquire lock for thread-safe access
                        mouse_position = (mouse_x, mouse_y)

                # Send acknowledgment to client
                client_socket.sendall(b"ACK")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

if __name__ == '__main__':
    # Start the server socket for receiving frames in a separate thread
    socket_thread = threading.Thread(target=start_server_socket, daemon=True)
    socket_thread.start()

    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
