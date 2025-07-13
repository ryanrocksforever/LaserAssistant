from flask import Flask, render_template, request, redirect, jsonify
import json
import os
import atexit

# Optional hardware support
try:
    from HR8825 import HR8825
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    print("⚠️ Hardware not available — simulation mode enabled.")

app = Flask(__name__)

class GalvoController:
    def __init__(self):
        self.X_MIN = -75
        self.X_MAX = 75
        self.Y_MIN = 0
        self.Y_MAX = 200
        self.REVERSED = {'x': True, 'y': True}
        self.current_position = {'x': 0, 'y': 0}

        if MOTOR_AVAILABLE:
            self.Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
            self.Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))
            self.Motor1.SetMicroStep('softward', '1/8step')
            self.Motor2.SetMicroStep('softward', '1/8step')

            # Move to known bottom Y limit
            self.move_to(self.current_position['x'], self.Y_MIN)
            self.current_position['y'] = self.Y_MIN

            self.startup_test()
        else:
            self.Motor1 = self.Motor2 = None

    def enforce_limits(self, x, y):
        x = max(self.X_MIN, min(self.X_MAX, x))
        y = max(self.Y_MIN, min(self.Y_MAX, y))
        return x, y

    def move_axis(self, motor, axis, steps, delay=0.001):
        if not motor or steps == 0:
            return
        if self.REVERSED.get(axis, False):
            steps = -steps
        direction = 'forward' if steps > 0 else 'backward'
        getattr(motor, 'TurnStep')(Dir=direction, steps=abs(steps), stepdelay=delay)
        self.current_position[axis] += steps

    def move_to(self, x, y):
        x, y = self.enforce_limits(x, y)
        dx = x - self.current_position['x']
        dy = y - self.current_position['y']
        self.move_axis(self.Motor1, 'x', dx)
        self.move_axis(self.Motor2, 'y', dy)

    def move_manual(self, direction, step_size):
        x, y = self.current_position['x'], self.current_position['y']
        if direction == 'up':
            y += step_size
        elif direction == 'down':
            y -= step_size
        elif direction == 'left':
            x -= step_size
        elif direction == 'right':
            x += step_size
        self.move_to(x, y)

    def startup_test(self):
        print("🔁 Running startup motor test...")
        self.move_manual('right', 10)
        self.move_manual('left', 10)
        self.move_manual('up', 10)
        self.move_manual('down', 10)
        print("✅ Startup complete.")

    def stop(self):
        print("🛑 Stopping: moving to bottom Y...")
        self.move_to(self.current_position['x'], self.Y_MIN)
        if self.Motor1:
            self.Motor1.Stop()
        if self.Motor2:
            self.Motor2.Stop()
        print("✅ Motors stopped cleanly.")

galvo = GalvoController()
atexit.register(galvo.stop)

LOCATIONS_FILE = 'locations.json'

def load_locations():
    try:
        with open(LOCATIONS_FILE, 'r') as f:
            text = f.read().strip()
            return json.loads(text) if text else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_locations(locations):
    with open(LOCATIONS_FILE, 'w') as f:
        json.dump(locations, f, indent=2)

# ────── ROUTES ─────────────────────────────

@app.route('/')
def index():
    return render_template('index.html',
                           locations=load_locations(),
                           current=galvo.current_position
                           )

@app.route('/move', methods=['POST'])
def move():
    direction = request.form.get('direction')
    step_size = int(request.form.get('step_size', 10))
    galvo.move_manual(direction, step_size)
    return redirect('/')

@app.route('/move_manual', methods=['POST'])
def move_manual_api():
    data = request.get_json()
    direction = data.get('direction')
    step = int(data.get('step_size', 10))
    galvo.move_manual(direction, step)
    return jsonify(galvo.current_position)

@app.route('/get_position')
def get_position():
    return jsonify(galvo.current_position)

@app.route('/goto/<name>', methods=['POST'])
def goto(name):
    locations = load_locations()
    if name in locations:
        x, y = locations[name]
        galvo.move_to(x, y)
    return redirect('/')

@app.route('/save_location', methods=['POST'])
def save_location():
    name = request.form.get('location_name')
    if name:
        locations = load_locations()
        locations[name] = [
            galvo.current_position['x'],
            galvo.current_position['y']
        ]
        save_locations(locations)
    return redirect('/')

# ───────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
