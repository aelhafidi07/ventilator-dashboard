import serial
import threading
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit

# Setup Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key
socketio = SocketIO(app)

# Serial port settings
SERIAL_PORT = 'COM3'  # Update if needed
BAUD_RATE = 115200

motor_state = "Wachten op data..."  # Update to Dutch
confidence = "-"

# Hardcoded users (for demo purposes)
USERS = {"admin": "password123"}

# Authentication function
def check_authentication(username, password):
    return USERS.get(username) == password

# Route for the index (Login page)
@app.route('/')
def index():
    # Check if the user is logged in (i.e., check session for 'username')
    if 'username' in session:
        # Redirect to dashboard if logged in
        return redirect(url_for('dashboard'))
    # Otherwise, show login page
    return render_template('login.html')

# Route to handle login form submission
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if check_authentication(username, password):
        # Store the username in session and redirect to dashboard
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        # Redirect to the login page if credentials are incorrect
        return redirect(url_for('index'))

# Route for the dashboard
@app.route('/dashboard')
def dashboard():
    # If the user is not logged in, redirect them to the login page
    if 'username' not in session:
        return redirect(url_for('index'))  # Redirect to login page
    return render_template('dashboard.html')  # Otherwise, render the dashboard

# Route to log the user out
@app.route('/logout')
def logout():
    # Remove user from session and redirect to login page
    session.pop('username', None)
    return redirect(url_for('index'))  # Redirect to login page

# Serial reading function
def read_from_serial():
    global motor_state, confidence

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[INFO] Connected to {SERIAL_PORT}")

        while True:
            line = ser.readline().decode('utf-8').strip()
            print("[SERIAL]", line)

            if line.startswith("Predictions"):
                results = {'normaal': 0, 'abnormaal': 0, 'uit': 0}
                for _ in range(3):  # Read next 3 lines
                    result_line = ser.readline().decode('utf-8').strip()
                    print("[SERIAL DATA]", result_line)
                    try:
                        label, value = result_line.split(':')
                        results[label.strip()] = float(value.strip())
                    except:
                        continue
                motor_state = max(results, key=results.get)
                confidence = f"{results[motor_state]*100:.2f}%"  # Percentage for confidence
                socketio.emit('update', {'state': motor_state, 'confidence': confidence})
    except serial.SerialException:
        print(f"[ERROR] Could not open serial port {SERIAL_PORT}")

# Handle socket connection
@socketio.on('connect')
def handle_connect():
    emit('update', {'state': motor_state, 'confidence': confidence})

# Run the app with socketio
if __name__ == '__main__':
    thread = threading.Thread(target=read_from_serial)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
