from flask import Flask, request, jsonify, render_template
import json
import time
import atexit

# Attempt to import motor driver
try:
    from HR8825 import HR8825
    MOTOR_AVAILABLE = True
except Exception as e:
    print(f"⚠️ HR8825 library could not be imported: {e}")
    MOTOR_AVAILABLE = False

# ─── Flask App ─────────────────────────────────────────────
app = Flask(__name__)

# ─── Galvo Controller Class ────────────────────────────────
class GalvoController:
    def __init__(self):
        self.MICROSTEP_MODE = '1/8step'
        self.REVERSED = {'x': True, 'y': True}
        self.M1_HOME_OFFSET = -150
        self.current_position = {'x': 0, 'y': 0}

        if not MOTOR_AVAILABLE:
            print("🚫 Motor not available. Skipping motor init.")
            self.Motor1 = None
            self.Motor2 = None
            return

        try:
            self.Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
            self.Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))
            self.Motor1.SetMicroStep('softward', self.MICROSTEP_MODE)
            self.Motor2.SetMicroStep('softward', self.MICROSTEP_MODE)
            print("✨ GalvoController initialized.")
            self.startup_sequence()
        except Exception as e:
            print(f"❌ Failed to initialize motors: {e}")
            self.Motor1 = None
            self.Motor2 = None

    def move_axis(self, motor, axis, steps, delay=0.001):
        if not motor or steps == 0:
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

    def stop(self):
        if self.Motor1:
            self.Motor1.Stop()
        if self.Motor2:
            self.Motor2.Stop()
        print("🛑 Motors stopped and cleaned up.")

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

# ─── Shared Galvo Controller ───────────────────────────────
galvo = None

# ─── Flask Routes ──────────────────────────────────────────
@app.route('/')
def index():
    locations = load_locations()
    return render_template('index.html', locations=locations)

@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.json
    locations = load_locations()
    locations[data['item']] = {'x': data['x'], 'y': data['y']}
    save_locations(locations)
    return jsonify({'status': 'success'})

@app.route('/get_location/<item>')
def get_location(item):
    if not galvo:
        return jsonify({'status': 'error', 'message': 'Motors not initialized'})
    locations = load_locations()
    if item in locations:
        coords = locations[item]
        galvo.move_to(coords['x'], coords['y'])
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Item not found'})

@app.route('/move_manual', methods=['POST'])
def move_manual():
    if not galvo:
        return jsonify({'status': 'error', 'message': 'Motors not initialized'})
    data = request.json
    galvo.move_manual(data['direction'])
    return jsonify({'status': 'success', 'position': galvo.current_position})

# ─── Cleanup on Exit ───────────────────────────────────────
@atexit.register
def shutdown():
    if galvo:
        galvo.stop()

# ─── Safe Entry Point ──────────────────────────────────────
if __name__ == '__main__':
    import os
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # This is the actual Flask run (not the reloader)
        galvo = GalvoController()
    else:
        print("🚫 Skipping motor init due to Flask reloader phase.")

    print("🚀 Starting Flask server...")
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)
