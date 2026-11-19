import json
import hashlib
import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_session import Session
from werkzeug.utils import secure_filename
import requests
from blockchain import Blockchain  # Ensure blockchain.py is in the same directory
import uuid

app = Flask(__name__, template_folder="templates")
CORS(app)
app.secret_key = "your_secret_key"  # Replace with a strong key
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

socketio = SocketIO(app, cors_allowed_origins="*")

blockchain = Blockchain()

# Upload folder
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Pinata API
PINATA_API_KEY = '69dd73dd4dd2a309e212'
PINATA_API_SECRET = 'f83cc87430c44ea6443adf9db13383df7e25728aa2b4b6bb5d0f0e9569a3c291'
PINATA_URL = 'https://api.pinata.cloud/pinning/pinFileToIPFS'

# Local storage files for users and posts
USER_FILE = "users.json"
POST_FILE = "posts.json"

# Store user sessions to enforce single session per user
user_sessions = {}

# Load functions for users and posts
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_posts():
    if os.path.exists(POST_FILE):
        with open(POST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

def save_posts(posts):
    with open(POST_FILE, 'w') as f:
        json.dump(posts, f)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    users = load_users()
    if username in users:
        return jsonify({"error": "Username already exists!"}), 400

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    users[username] = password_hash
    save_users(users)

    return jsonify({"message": "User registered successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    users = load_users()
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if users.get(username) != password_hash:
        return jsonify({"error": "Invalid credentials!"}), 401

    # Check if the user already has an active session
    if username in user_sessions:
        current_session_token = user_sessions[username]
        if current_session_token != session.get('session_token'):
            return jsonify({"error": "User already logged in from another device/tab!"}), 401

    # Generate a unique session token for the user
    session_token = str(uuid.uuid4())
    session['username'] = username
    session['session_token'] = session_token

    # Store the session token
    user_sessions[username] = session_token

    return jsonify({"message": "Login successful!"}), 200

@app.route('/logout', methods=['GET'])
def logout():
    username = session.get('username')
    if username:
        del user_sessions[username]  # Remove user from active sessions
    session.clear()
    return jsonify({"message": "Logged out"}), 200

@app.route('/current_user')
def get_current_user():
    if 'username' in session:
        return jsonify({"username": session['username']}), 200
    return jsonify({"error": "Not logged in"}), 401

def upload_to_pinata(file_path):
    headers = {
        'pinata_api_key': PINATA_API_KEY,
        'pinata_secret_api_key': PINATA_API_SECRET
    }
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(PINATA_URL, headers=headers, files=files)
        if response.status_code == 200:
            return response.json()['IpfsHash']
        else:
            print(response.text)
            return None

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        ipfs_cid = upload_to_pinata(file_path)
        if ipfs_cid:
            blockchain.add_post(ipfs_cid)
            previous_block = blockchain.get_previous_block()
            new_block = blockchain.create_block(previous_block['hash'])

            socketio.emit('new_post', {
                "message": "New post added!",
                "ipfs_cid": ipfs_cid,
                "block_index": new_block['index'],
                "username": session.get("username", "Anonymous")
            })

            return jsonify({"message": "File uploaded!", "cid": ipfs_cid}), 200
        else:
            return jsonify({"error": "Failed to upload to IPFS"}), 500
    return jsonify({"error": "No file uploaded"}), 400

@app.route('/add_post', methods=['POST'])
def add_post():
    """Handles the addition of a new post to the blockchain."""
    data = request.get_json()

    # Check if the post is a media post or a text post
    ipfs_cid = data.get('ipfs_cid')  # For media
    text_content = data.get('text')  # For text posts

    if not ipfs_cid and not text_content:
        return jsonify({"error": "IPFS CID or text content is required."}), 400

    # If it's a media post (IPFS CID)
    if ipfs_cid:
        blockchain.add_post(ipfs_cid)  # Add the IPFS CID to the blockchain
    # If it's a text post
    elif text_content:
        blockchain.add_post(text_content)  # Add the text content to the blockchain

    # Get the last block to create a new block
    previous_block = blockchain.get_previous_block()
    new_block = blockchain.create_block(previous_block['hash'])

    # Save to local file
    posts = load_posts()
    posts.append({
        'text': text_content if text_content else "Uploaded media",
        'ipfs_cid': ipfs_cid,
        'username': session.get("username", "Anonymous"),
        'block_index': new_block['index']
    })
    save_posts(posts)

    # Emit a 'new_post' event
    socketio.emit('new_post', {
        "message": "New post added!",
        "text": text_content if text_content else None,
        "ipfs_cid": ipfs_cid if ipfs_cid else None,
        "block_index": new_block['index'],
        "username": session.get("username", "Anonymous")
    })

    return jsonify({"message": "Post added successfully!", "block_index": new_block['index']}), 200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    posts=load_posts()
    return jsonify({
        'chain': posts,
        'length': len(posts)
    }), 200

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/index')
def home():
    posts = load_posts()  # Load all posts from the local file
    return render_template('index.html', posts=posts)  # Pass posts to the template

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True, debug=True)
