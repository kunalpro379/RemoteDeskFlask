import io
import os
from flask import Flask, Response, request, jsonify, render_template

try:
    from werkzeug.wsgi import FileWrapper
except Exception as e:
    from werkzeug import FileWrapper

global STATE
STATE = {}

application = Flask(__name__)

@application.route('/')
def root():
    return render_template('index.html')

@application.route('/rd', methods=['POST'])
def rd():
    req = request.get_json()
    key = req['_key']

    if key not in STATE:
        return jsonify({'error': 'Invalid key'}), 400

    if req['filename'] == STATE[key]['filename']:
        attachment = io.BytesIO(b'')
    else:
        attachment = io.BytesIO(STATE[key]['im'])

    w = FileWrapper(attachment)
    resp = Response(w, mimetype='text/plain', direct_passthrough=True)
    resp.headers['filename'] = STATE[key]['filename']
    
    return resp

@application.route('/event_post', methods=['POST'])
def event_post():
    global STATE

    req = request.get_json()
    key = req['_key']

    if key not in STATE:
        return jsonify({'error': 'Invalid key'}), 400

    STATE[key]['events'].append(req)
    return jsonify({'ok': True})

@application.route('/new_session', methods=['POST'])
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

@application.route('/capture_post', methods=['POST'])
def capture_post():
    global STATE
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    filename = list(request.files.keys())[0]
    key = filename.split('_')[1]

    if key not in STATE:
        return jsonify({'error': 'Invalid key'}), 400

    with io.BytesIO() as image_data:
        request.files[filename].save(image_data)
        STATE[key]['im'] = image_data.getvalue()
        STATE[key]['filename'] = filename

    return jsonify({'ok': True})

@application.route('/events_get', methods=['POST'])
def events_get():
    req = request.get_json()
    key = req['_key']
    
    if key not in STATE:
        return jsonify({'error': 'Invalid key'}), 400

    events_to_execute = STATE[key]['events'].copy()
    STATE[key]['events'] = []
    return jsonify({'events': events_to_execute})

if __name__ == '__main__':
    #port = int(os.environ.get("PORT", 5000))
    #application.run(host='0.0.0.0', port=port, debug=True)
    application.run(debug=True)
