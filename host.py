'''

import win32gui
import win32ui
import win32con
import win32api
import win32com.client
from PIL import Image
import io
import requests
import time
import argparse

def main(host, key):
  r = requests.post(host+'/new_session', json={'_key': key})
  if r.status_code != 200:    
    print('Server not avaliable.')
    return

  shell = win32com.client.Dispatch('WScript.Shell')
  PREV_IMG = None
  while True:
    hdesktop = win32gui.GetDesktopWindow()

    width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

    # device context
    desktop_dc = win32gui.GetWindowDC(hdesktop)
    img_dc = win32ui.CreateDCFromHandle(desktop_dc)

    # memory context
    mem_dc = img_dc.CreateCompatibleDC()

    screenshot = win32ui.CreateBitmap()
    screenshot.CreateCompatibleBitmap(img_dc, width, height)
    mem_dc.SelectObject(screenshot)

    bmpinfo = screenshot.GetInfo()

    # copy into memory 
    mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top),win32con.SRCCOPY)

    bmpstr = screenshot.GetBitmapBits(True)

    pillow_img = Image.frombytes('RGB',
      (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
      bmpstr, 'raw', 'BGRX')

    with io.BytesIO() as image_data:
      pillow_img.save(image_data, 'PNG')
      image_data_content = image_data.getvalue()

    if image_data_content != PREV_IMG:
      files = {}
      filename = str(round(time.time()*1000))+'_'+key
      files[filename] = ('img.png', image_data_content, 'multipart/form-data')

      try:
        r = requests.post(host+'/capture_post', files=files)
      except Exception as e:
        pass

      PREV_IMG = image_data_content
    else:
      #print('no desktop change')
      pass
    
    # events
    try:
      r = requests.post(host+'/events_get', json={'_key': key})
      data = r.json()
      for e in data['events']:
        print(e)

        if e['type'] == 'click':
          win32api.SetCursorPos((e['x'], e['y']))
          time.sleep(0.1)
          win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, e['x'], e['y'], 0, 0)
          time.sleep(0.02)
          win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, e['x'], e['y'], 0, 0)

        if e['type'] == 'keydown':
          cmd = ''
          
          if e['shiftKey']:
            cmd += '+'

          if e['ctrlKey']:
            cmd += '^'

          if e['altKey']:
            cmd += '%'

          if len(e['key']) == 1:
            cmd += e['key'].lower()
          else:
            cmd += '{'+e['key'].upper()+'}'

          print(cmd)
          shell.SendKeys(cmd)
          
    except Exception as err:
      print(err)
      pass

    #screenshot.SaveBitmapFile(mem_dc, 'screen.bmp')
    # free
    mem_dc.DeleteDC()
    win32gui.DeleteObject(screenshot.GetHandle())
    time.sleep(0.2)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='pyRD')
  # parser.add_argument('addr', help='server addres', type=str)
  # parser.add_argument('key', help='acess key', type=str)
  args = parser.parse_args()
  host='http://3.7.254.110:5000'
  key = "1234"
  main(host, key)

'''
import io
import shutil
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

@app.route('/receive_passkey', methods=['POST'])
def receive_passkey():
    try:
        req = request.get_json()
        passkey = req.get('passkey')
        
        if not passkey:
            return jsonify({'error': 'Passkey not provided'}), 400

        with open('host.py', 'r') as file:
            content = file.read()
            
        import re
        new_content = re.sub(r'key\s*=\s*["\'][^"\']*["\']', f'key = "{passkey}"', content)
        
        with open('host.py', 'w') as file:
            file.write(new_content)
            
        global key
        key = passkey
        
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

@app.route('/create_dot_exe', methods=['POST'])
def create_dot_exe():
    try:
        req = request.get_json()
        filename = req.get('filename', 'host')
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dotexe_dir = os.path.join(base_dir, 'dotexe', filename)
        
        os.makedirs(dotexe_dir, exist_ok=True)
        
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

        import subprocess
        process = subprocess.Popen([
            'pyinstaller',
            '--name', filename,
            '--distpath', dotexe_dir,
            '--clean',  
            '-y',      
            'host.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"PyInstaller failed: {stderr.decode()}")
            
        exe_path = os.path.join(dotexe_dir, filename)
        if not os.path.exists(exe_path):
            exe_path = f"{exe_path}.exe"  
            
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
        filename = 'host.exe'
        base_dir = os.path.dirname(os.path.abspath(__file__))  
        exe_path = os.path.join(base_dir,  filename) 

        if not os.path.exists(exe_path):
            return jsonify({'error': 'Executable file not found'}), 404  

        return send_file(
            exe_path,
            mimetype='application/octet-stream', 
            as_attachment=True,                 
            download_name=filename                
        )

    except Exception as e:
        return jsonify({'error': f'Failed to download: {str(e)}'}), 500  
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
