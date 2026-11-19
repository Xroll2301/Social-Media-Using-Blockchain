import socketio
import time

# Connect to the Socket.IO server
sio = socketio.Client()

# Event that runs when connected to the server
@sio.event
def connect():
    print("Connected to the server!")
    time.sleep(1)
    # Send a message after connecting
    send_message("user1", "Hello, this is user1!")

# Event that receives the new message broadcast
@sio.event
def new_message(data):
    print(f"New message from {data['username']}: {data['message']}")

# Send a message to the server
def send_message(username, message):
    sio.emit('send_message', {'username': username, 'message': message})

# Connect to the server
sio.connect('http://127.0.0.1:5001')

# Run the client to keep listening for incoming messages
while True:
    time.sleep(10)
