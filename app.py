from flask import Flask, render_template, request, jsonify
from HR8825 import HR8825
import json
import os
import atexit

app = Flask(__name__)

# ────── Galvo Control ──────
class GalvoController:
    def __init__(self):
        self.MIN_X = 0
        self.MAX_X = 75
        self.MIN_Y = 0
        self.MAX_Y = 200

        self.current_position = {'x': 0, 'y': 0}

        self.Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
        self.Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))
        self.Motor1.SetMicroStep('softward', '1/8step')
        self.Motor2.SetMicroStep('softward', '1/8step')

        self.home()

    def home(self):
        # Go to known zero
        self.move_to(0, 0)

    def move_to(self, x, y, delay=0.001):
        dx = x - self.current_position['x']
        dy = y - self.current_position['y']
        self.move_relative(dx, dy, delay)

    def move_relative(self, dx, dy, delay=0.001):
        target_x = max(self.MIN_X, min(self.MAX_X, self.current_position['x'] + dx))
        target_y = max(self.MIN_Y, min(self.MAX_Y, self.current_position['y'] + dy))
        dx = target_x - self.current_position['x']
        dy = target_y - self.current_position['y']

        if dx != 0:
            dir_x = 'forward' if dx > 0 else 'backward'
            self.Motor1.TurnStep(Dir=dir_x, steps=abs(dx), stepdelay=delay)
        if dy != 0:
            dir_y = 'forward' if dy > 0 else 'backward'
            self.Motor2.TurnStep(Dir=dir_y, steps=abs(dy), stepdelay=delay)

        self.current_position['x'] = target_x
        self.current_position['y'] = target_y

    def shutdown(self):
        self.move_to(0, 0)
        self.Motor1.Stop()
        self.Motor2.Stop()

galvo = GalvoController()
atexit.register(galvo.shutdown)

# ────── Location Persistence ──────
LOCATION_FILE = 'locations.json'

def load_locations():
    if not os.path.exists(LOCATION_FILE):
        return {}
    with open(LOCATION_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_locations(locations):
    with open(LOCATION_FILE, 'w') as f:
        json.dump(locations, f, indent=2)

# ────── Flask Routes ──────
@app.route('/')
def index():
    locations = load_locations()
    return render_template('index.html', locations=locations.keys())

@app.route('/move_manual', methods=['POST'])
def move_manual():
    data = request.get_json()
    direction = data.get('direction')
    step_size = int(data.get('step_size', 5))

    if direction == 'up':
        galvo.move_relative(0, step_size)
    elif direction == 'down':
        galvo.move_relative(0, -step_size)
    elif direction == 'left':
        galvo.move_relative(-step_size, 0)
    elif direction == 'right':
        galvo.move_relative(step_size, 0)

    return '', 204

@app.route('/get_position')
def get_position():
    return jsonify(galvo.current_position)

@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return 'Missing name', 400

    locations = load_locations()
    locations[name] = galvo.current_position.copy()
    save_locations(locations)
    return '', 204

@app.route('/goto/<location>', methods=['POST'])
def goto_location(location):
    locations = load_locations()
    pos = locations.get(location)
    if pos:
        galvo.move_to(pos['x'], pos['y'])
        return '', 204
    return 'Location not found', 404

# ────── Run ──────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
