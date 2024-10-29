# server.py
from flask import Flask, render_template
from flask_socketio import SocketIO
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Serve the template
@app.route('/')
def index():
    return render_template('index.html')

# Handle incoming frames
@socketio.on('frame')
def handle_frame(frame_data):
    # Broadcast the frame to all connected clients
    socketio.emit('broadcast_frame', {'data': frame_data})

if __name__ == '__main__':
    print("Server started at http://localhost:6000")
    socketio.run(app,  port=6000)
