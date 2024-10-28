from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import numpy as np
import cv2
import zlib
import io
from threading import Lock
import threading
import queue
from waitress import serve

app = Flask(__name__)
CORS(app)

class StreamState:
    def __init__(self):
        self.current_frame = None
        self.frame_lock = Lock()
        self.events = []
        self.event_lock = Lock()
        self.frame_queue = queue.Queue(maxsize=3)

class StreamManager:
    def __init__(self):
        self.states = {}
        self.state_lock = Lock()
    
    def get_or_create_state(self, key):
        with self.state_lock:
            if key not in self.states:
                self.states[key] = StreamState()
            return self.states[key]

stream_manager = StreamManager()

@app.route('/capture_post', methods=['POST'])
def capture_post():
    try:
        filename = list(request.files.keys())[0]
        key = filename.split('_')[1]
        
        # Get stream state
        state = stream_manager.get_or_create_state(key)
        
        # Get compressed data
        compressed_data = request.files[filename].read()
        
        # Decompress
        frame_data = zlib.decompress(compressed_data)
        
        # Convert to numpy array
        frame_array = np.frombuffer(frame_data, dtype=np.uint8)
        
        # Decode JPEG
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        
        # Update frame in state
        with state.frame_lock:
            if state.current_frame is not None:
                # Apply delta
                state.current_frame = cv2.add(state.current_frame, frame)
            else:
                state.current_frame = frame
            
            # Add to frame queue for client retrieval
            try:
                state.frame_queue.put_nowait(state.current_frame.copy())
            except queue.Full:
                # Remove oldest frame if queue is full
                try:
                    state.frame_queue.get_nowait()
                    state.frame_queue.put_nowait(state.current_frame.copy())
                except:
                    pass

        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/rd', methods=['POST'])
def rd():
    try:
        req = request.get_json()
        key = req['_key']
        
        # Get stream state
        state = stream_manager.get_or_create_state(key)
        
        # Get latest frame
        frame = None
        try:
            frame = state.frame_queue.get_nowait()
        except queue.Empty:
            # If no new frame, use current frame
            with state.frame_lock:
                if state.current_frame is not None:
                    frame = state.current_frame.copy()
        
        if frame is not None:
            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Create response
            return Response(buffer.tobytes(), mimetype='image/jpeg')
        else:
            return Response(status=204)  # No content
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/event_post', methods=['POST'])
def event_post():
    req = request.get_json()
    key = req['_key']
    
    # Get stream state
    state = stream_manager.get_or_create_state(key)
    
    # Add event
    with state.event_lock:
        state.events.append(req)
    
    return jsonify({'ok': True})

@app.route('/events_get', methods=['POST'])
def events_get():
    req = request.get_json()
    key = req['_key']
    
    # Get stream state
    state = stream_manager.get_or_create_state(key)
    
    # Get and clear events
    with state.event_lock:
        events = state.events.copy()
        state.events = []
    
    return jsonify({'events': events})

if __name__ == '__main__':
    # Run with multiple worker threads
    serve(app, host='0.0.0.0', port=5000, threads=4)



# old #not requried code  snippet
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