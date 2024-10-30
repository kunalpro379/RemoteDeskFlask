import io
import socket
import struct
import cv2
from flask import Flask, Response, request, jsonify, render_template
import numpy as np
from werkzeug.wsgi import FileWrapper
from flask_cors import CORS
import threading
import time
import re

app = Flask(__name__)
CORS(app)

latest_frame = None
mouse_position = (0, 0)
lock = threading.Lock()  # To manage access to shared variables
STATE = {}

@app.route('/')
def root():
    return render_template('index.html')

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

@app.route('/rd', methods=['POST'])
def rd():
    req = request.get_json()
    key = req['_key']

    if key not in STATE:
        # Initialize state for new key
        STATE[key] = {
            'im': b'',
            'filename': 'none.png',
            'events': []
        }

    if req['filename'] == STATE[key]['filename']:
        attachment = io.BytesIO(b'')
    else:
        attachment = io.BytesIO(STATE[key]['im'])

    w = FileWrapper(attachment)
    resp = Response(w, mimetype='text/plain', direct_passthrough=True)
    resp.headers['filename'] = STATE[key]['filename']

    return resp

@app.route('/event_post', methods=['POST'])
def event_post():
    global STATE

    req = request.get_json()
    key = req['_key']

    if key not in STATE:
        # Initialize the state for the new key
        # STATE[key] = {
        #     'im': b'',
        #     'filename': 'none.png',
        #     'events': []
        # }
        STATE[key] = {'im': b'', 'filename': 'none.png', 'events': []}


    STATE[key]['events'].append(req)
    return jsonify({'ok': True})

@app.route('/new_session', methods=['POST'])
def new_session():
    global STATE

    req = request.get_json()
    key = req['_key']
    STATE[key] = {
        'im': b'',
        'filename': 'none.png',
        'events': []
    }

    return jsonify({'ok': True})

@app.route('/capture_post', methods=['POST'])
def capture_post():
    global STATE

    with io.BytesIO() as image_data:
        filename = list(request.files.keys())[0]
        key = filename.split('_')[1]
        request.files[filename].save(image_data)
        STATE[key]['im'] = image_data.getvalue()
        STATE[key]['filename'] = filename

    return jsonify({'ok': True})

@app.route('/events_get', methods=['POST'])
def events_get():
    req = request.get_json()
    key = req['_key']
    events_to_execute = STATE[key]['events'].copy()
    STATE[key]['events'] = []  # Clear after copying
    return jsonify({'events': events_to_execute})

@app.route('/receive_passkey', methods=['POST'])
def receive_passkey():
    try:
        req = request.get_json()
        passkey = req.get('passkey')

        if not passkey:
            return jsonify({'error': 'Passkey not provided'}), 400

        with open('host.py', 'r') as file:
            content = file.read()

        new_content = re.sub(r'key\s*=\s*["\']([^"\']+)["\']', f'key = "{passkey}"', content)

        with open('host.py', 'w') as file:
            file.write(new_content)

        global STATE
        if passkey not in STATE:
            STATE[passkey] = {
                'im': b'',
                'filename': 'none.png',
                'events': []
            }

        return jsonify({'message': 'Passkey received and assigned successfully', 'key': passkey}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to assign passkey: {str(e)}'}), 500

# Start the server socket in a separate thread
socket_thread = threading.Thread(target=start_server_socket, daemon=True)
socket_thread.start()



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)




'''
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
'''





#old code functions  snippet
# #not requried code  snippet
''' 
@app.route('/create_dot_exe', methods=['POST'])
def create_dot_exe():
    try:
        # Get filename from request
        req = request.get_json()
        filename = req.get('filename', 'host')
        
        # Create absolute path for dotexe directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dotexe_dir = os.path.join(base_dir, 'dotexe', filename)
        
        # Create dotexe directory if it doesn't exist
        os.makedirs(dotexe_dir, exist_ok=True)
        
        # Clean up existing files
        if os.path.exists(dotexe_dir):
            for file in os.listdir(dotexe_dir):
                file_path = os.path.join(dotexe_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Error: {e}")

        # Run pyinstaller command with forced overwrite
        import subprocess
        process = subprocess.Popen([
            'pyinstaller',
            '--name', filename,
            '--distpath', dotexe_dir,
            '--clean',  # Clean PyInstaller cache
            '-y',      # Overwrite output directory without asking
            'host.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"PyInstaller failed: {stderr.decode()}")
            
        # Check for the executable (note: on Linux it won't have .exe extension)
        exe_path = os.path.join(dotexe_dir, filename)
        if not os.path.exists(exe_path):
            exe_path = f"{exe_path}.exe"  # Try with .exe extension
            
        max_wait = 30
        while max_wait > 0 and not os.path.exists(exe_path):
            time.sleep(1)
            max_wait -= 1
            
        if not os.path.exists(exe_path):
            raise Exception("Executable file not generated in time")
            
        return jsonify({
            'message': f'Executable {filename} created successfully',
            'exe_path': exe_path
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
@app.route('/download_exe', methods=['GET'])
def download_exe():
    try:
        # Specify the fixed path to the executable file
        filename = 'host.exe'
        base_dir = os.path.dirname(os.path.abspath(__file__))  # Get the base directory of the current file
        exe_path = os.path.join(base_dir,  filename)  # Construct the path

        # Check if the executable file exists
        if not os.path.exists(exe_path):
            return jsonify({'error': 'Executable file not found'}), 404  # Return 404 if not found

        # Send the executable file as a downloadable attachment
        return send_file(
            exe_path,
            mimetype='application/octet-stream',  # Set the MIME type for an executable
            as_attachment=True,                   # Indicate that this should be a download
            download_name=filename                # Name of the file when downloaded
        )

    except Exception as e:
        return jsonify({'error': f'Failed to download: {str(e)}'}), 500  # Return 500 on error
# @app.route('/download_exe', methods=['GET'])
# def download_exe():
#     try:
#         filename = request.args.get('filename', 'host')
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         exe_dir = os.path.join(base_dir, 'dotexe', filename)
        
#         # Try both with and without .exe extension
#         exe_path = os.path.join(exe_dir, filename)
#         if not os.path.exists(exe_path):
#             exe_path = f"{exe_path}.exe"
            
#         if not os.path.exists(exe_path):
#             return jsonify({'error': 'Executable file not found'}), 404
            
#         return send_file(
#             exe_path,
#             mimetype='application/octet-stream',
#             as_attachment=True,
#             download_name=f'{filename}.exe' if filename.endswith('.exe') else filename
#         )
        
#     except Exception as e:
#         return jsonify({
#             'error': f'Failed to download: {str(e)}'}), 500


 '''