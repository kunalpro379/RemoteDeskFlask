import io
from flask import Flask, Response, request, jsonify, render_template

try:
    from werkzeug.wsgi import FileWrapper
except Exception as e:
    from werkzeug import FileWrapper
from flask import send_file
import os
import time
from flask_cors import CORS

global STATE
STATE = {}

app = Flask(__name__)
CORS(app)
''' Client '''

@app.route('/')
def root():
    return render_template('/index.html')

@app.route('/rd', methods=['POST'])
def rd():
    req = request.get_json()
    key = req['_key']

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

    STATE[key]['events'].append(request.get_json())
    return jsonify({'ok': True})

''' Remote '''

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
    STATE[key]['events'] = []
    return jsonify({'events': events_to_execute})

# First endpoint to receive and assign passkey
@app.route('/receive_passkey', methods=['POST'])
def receive_passkey():
    try:
        # Get passkey from POST request
        req = request.get_json()
        passkey = req.get('passkey')
        
        if not passkey:
            return jsonify({'error': 'Passkey not provided'}), 400

        # Read host.py content
        with open('host.py', 'r') as file:
            content = file.read()
            
        # Find and replace the key in host.py
        import re
        new_content = re.sub(r'key\s*=\s*["\'][^"\']*["\']', f'key = "{passkey}"', content)
        
        # Write back to host.py
        with open('host.py', 'w') as file:
            file.write(new_content)
            
        # Also update the current global key
        global key
        key = passkey
        
        # Initialize state if needed
        if key not in STATE:
            STATE[key] = {
                'im': b'',
                'filename': 'none.png',
                'events': []
            }
            
        return jsonify({
            'message': 'Passkey received and assigned successfully',
            'key': key
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to assign passkey: {str(e)}'
        }), 500

# Second endpoint to create executable with custom name
@app.route('/create_dot_exe', methods=['POST'])
def create_dot_exe():
    try:
        # Get filename from request
        req = request.get_json()
        filename = req.get('filename', 'host')  # default to 'host' if not provided
        
        # Create dotexe directory if it doesn't exist
        if not os.path.exists('dotexe'):
            os.makedirs('dotexe')
        
        # Run pyinstaller command with custom name and directory
        import subprocess
        process = subprocess.Popen([
            'pyinstaller',
            '--name', f'{filename}',  # Set custom name
            '--distpath', './dotexe',  # Set output directory
            'host.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"PyInstaller failed: {stderr.decode()}")
            
        # Wait for exe to be available (max 30 seconds)
        exe_path = os.path.join('dotexe', filename, f'{filename}.exe')
        max_wait = 30
        while max_wait > 0 and not os.path.exists(exe_path):
            time.sleep(1)
            max_wait -= 1
            
        if not os.path.exists(exe_path):
            raise Exception("Executable file not generated in time")
            
        return jsonify({
            'message': f'Executable {filename}.exe created successfully',
            'exe_path': exe_path
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to create executable: {str(e)}'
        }), 500

# Updated download endpoint to handle custom named executables
@app.route('/download_exe', methods=['GET'])
def download_exe():
    try:
        filename = request.args.get('filename', 'host')  # Get filename from query params
        exe_path = os.path.join('dotexe', filename, f'{filename}.exe')
        
        if not os.path.exists(exe_path):
            return jsonify({'error': 'Executable file not found'}), 404
            
        return send_file(
            exe_path,
            as_attachment=True,
            download_name=f'{filename}.exe'
        )
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to download: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

