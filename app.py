from flask import Flask, request, jsonify, render_template
import json
import time
from HR8825 import HR8825

# ─── Flask App ─────────────────────────────────────────────
app = Flask(__name__)

# ─── Galvo Controller Class ────────────────────────────────
class GalvoController:
    def __init__(self):
        self.MICROSTEP_MODE = '1/8step'
        self.REVERSED = {'x': True, 'y': True}
        self.M1_HOME_OFFSET = -150

        # Setup motors
        self.Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
        self.Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))

        self.Motor1.SetMicroStep('softward', self.MICROSTEP_MODE)
        self.Motor2.SetMicroStep('softward', self.MICROSTEP_MODE)

        self.current_position = {'x': 0, 'y': 0}

        print("✨ GalvoController initialized.")
        self.startup_sequence()

    def move_axis(self, motor, axis, steps, delay=0.001):
        if steps == 0:
            return
        if self.REVERSED.get(axis, False):
            steps = -steps
        direction = 'forward' if steps > 0 else 'backward'
        print(f"🔁 Moving {axis.upper()} axis {steps} steps {direction}")
        getattr(motor, 'TurnStep')(Dir=direction, steps=abs(steps), stepdelay=delay)
        self.current_position[axis] += steps

    def move_to(self, target_x, target_y):
        dx = target_x - self.current_position['x']
        dy = target_y - self.current_position['y']
        self.move_axis(self.Motor1, 'x', dx)
        self.move_axis(self.Motor2, 'y', dy)

    def move_manual(self, direction, step_size=10):
        if direction == 'up':
            self.move_axis(self.Motor2, 'y', step_size)
        elif direction == 'down':
            self.move_axis(self.Motor2, 'y', -step_size)
        elif direction == 'left':
            self.move_axis(self.Motor1, 'x', -step_size)
        elif direction == 'right':
            self.move_axis(self.Motor1, 'x', step_size)

    def startup_sequence(self):
        print("🔧 Running startup sequence...")
        self.move_axis(self.Motor1, 'x', 100)
        self.move_axis(self.Motor1, 'x', -100)
        self.move_axis(self.Motor2, 'y', 100)
        self.move_axis(self.Motor2, 'y', -100)
        print("✅ Startup sequence complete.")

# ─── Location Storage ──────────────────────────────────────
def load_locations():
    try:
        with open('locations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_locations(data):
    with open('locations.json', 'w') as f:
        json.dump(data, f, indent=4)

# ─── Create Shared Controller Instance ─────────────────────
galvo = GalvoController()

# ─── Routes ────────────────────────────────────────────────
@app.route('/')
def index():
    locations = load_locations()
    return render_template('index.html', locations=locations)

@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.json
    locations = load_locations()
    item = data['item']
    x = data['x']
    y = data['y']
    locations[item] = {'x': x, 'y': y}
    save_locations(locations)
    print(f"💾 Saved location for '{item}' → X: {x}, Y: {y}")
    return jsonify({'status': 'success'})

@app.route('/get_location/<item>')
def get_location(item):
    locations = load_locations()
    if item in locations:
        coords = locations[item]
        galvo.move_to(coords['x'], coords['y'])
        print(f"🎯 Pointing to '{item}' at X: {coords['x']}, Y: {coords['y']}")
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Item not found'})

@app.route('/move_manual', methods=['POST'])
def move_manual():
    data = request.json
    direction = data['direction']
    galvo.move_manual(direction)
    return jsonify({'status': 'success', 'position': galvo.current_position})

# ─── Run Server ─────────────────────────────────────────────
if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
