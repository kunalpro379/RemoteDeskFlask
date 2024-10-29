import io
import socket
import struct
import time
import cv2
from flask import Flask, Response
import numpy as np

app = Flask(__name__)

# State to hold the latest frame
latest_frame = None

@app.route('/')
def index():
    return "<h1>Video Stream</h1><p><a href='/video_feed'>View Video Feed</a></p>"

@app.route('/video_feed')
def video_feed():
    def generate():
        global latest_frame
        while True:
            if latest_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
            else:
                time.sleep(0.1)  # Small delay to prevent excessive looping

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

def start_server_socket():
    global latest_frame
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
                frame_data = client_socket.recv(frame_size)
                while len(frame_data) < frame_size:
                    frame_data += client_socket.recv(frame_size - len(frame_data))

                # Store the frame for /video_feed
                latest_frame = frame_data

                # Optionally, convert frame data to a numpy array for visualization
                frame_np = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

                # Display the frame (for debugging)
                cv2.imshow('Received Frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                # Send acknowledgment to client
                client_socket.sendall(b"ACK")
        finally:
            client_socket.close()

if __name__ == '__main__':
    import threading

    # Start the server socket for receiving frames
    threading.Thread(target=start_server_socket, daemon=True).start()
    
    # Start Flask app for video feed
    app.run(host='0.0.0.0', port=5000, debug=True)
