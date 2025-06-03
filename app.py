import serial
import threading
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from datetime import datetime
import socket

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200

motor_state = "Wachten op data..."
confidence = "-"

users = {
    'admin': 'password123',
    'user1': 'pass1',
    'user2': 'pass2',
    'user3': 'pass3',
    'user4': 'pass4'
}

def check_authentication(username, password):
    return users.get(username) == password

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        ip_address = request.remote_addr

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if check_authentication(username, password):
            session['username'] = username
            log_line = f"[{timestamp}] Inlogpoging (GESLAAGD) - Gebruiker: {username} - IP: {ip_address}\n"
            with open('login_log.txt', 'a') as log_file:
                log_file.write(log_line)
            return redirect(url_for('dashboard'))
        else:
            log_line = f"[{timestamp}] Inlogpoging (MISLUKT) - Gebruiker: {username} - IP: {ip_address}\n"
            with open('login_log.txt', 'a') as log_file:
                log_file.write(log_line)
            flash('Ongeldige gebruikersnaam of wachtwoord.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ip_address = request.remote_addr 
    log_line = f"[{timestamp}] Logout: {session['username']} - IP: {ip_address}\n"
    with open('login_log.txt', 'a') as log_file:
        log_file.write(log_line)
        
    session.pop('username', None)
    return redirect(url_for('login'))

def read_from_serial():
    global motor_state, confidence
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[INFO] Verbonden met {SERIAL_PORT}")

        while True:
            line = ser.readline().decode('utf-8').strip()
            print("[SERIAL]", line)

            if line.startswith("Predictions"):
                results = {'normaal': 0, 'abnormaal': 0, 'uit': 0}
                for _ in range(3):
                    result_line = ser.readline().decode('utf-8').strip()
                    print("[SERIAL DATA]", result_line)
                    try:
                        label, value = result_line.split(':')
                        results[label.strip()] = float(value.strip())
                    except:
                        continue
                
                motor_state = max(results, key=results.get)
                confidence = f"{results[motor_state]*100:.2f}%"
                socketio.emit('update', {'state': motor_state, 'confidence': confidence})

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_line = f"[{timestamp}] State: {motor_state}, Confidence: {confidence}\n"
                with open('motor_log.txt', 'a') as log_file:
                    log_file.write(log_line)
                
    except serial.SerialException:
        print(f"[ERROR] Kan seriële poort {SERIAL_PORT} niet openen")

@socketio.on('connect')
def handle_connect():
    emit('update', {'state': motor_state, 'confidence': confidence})

if __name__ == '__main__':
    thread = threading.Thread(target=read_from_serial)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
