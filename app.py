import serial
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Setup Flask app
app = Flask(__name__)
socketio = SocketIO(app)

# Serial port settings
SERIAL_PORT = 'COM3'  # Update if needed
BAUD_RATE = 115200

motor_state = "Wachten op data..."  # Update to Dutch
confidence = "-"

@app.route('/')
def index():
    return render_template('dashboard.html')

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

@socketio.on('connect')
def handle_connect():
    emit('update', {'state': motor_state, 'confidence': confidence})

if __name__ == '__main__':
    thread = threading.Thread(target=read_from_serial)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
