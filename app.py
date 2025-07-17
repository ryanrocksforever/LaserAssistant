from flask import Flask, render_template, request, jsonify
from HR8825 import HR8825
from dotenv import load_dotenv
import openai
import json
import os
import atexit
import threading
import time

# Load env vars
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# ─── Inactivity Timer ───
STEPPER_TIMEOUT = 60
last_activity_time = time.time()

def inactivity_monitor():
    while True:
        time.sleep(5)
        if time.time() - last_activity_time > STEPPER_TIMEOUT:
            galvo.disable_motors()

threading.Thread(target=inactivity_monitor, daemon=True).start()

# ─── Galvo Setup ───
class GalvoController:
    def __init__(self):
        self.MIN_X, self.MAX_X = 0, 75
        self.MIN_Y, self.MAX_Y = 0, 200
        self.current_position = {'x': 0, 'y': 0}
        self.home_position = {'x': 0, 'y': 0}

        self.Motor1 = HR8825(13, 19, 12, (16, 17, 20))
        self.Motor2 = HR8825(24, 18, 4, (21, 22, 27))
        self.Motor1.SetMicroStep('softward', '1/8step')
        self.Motor2.SetMicroStep('softward', '1/8step')
        self.home()

    def _update_activity(self):
        global last_activity_time
        last_activity_time = time.time()

    def home(self):
        self.move_to(self.home_position['x'], self.home_position['y'])

    def reset_home(self):
        self.home_position = self.current_position.copy()

    def move_to(self, x, y, delay=0.001):
        self._update_activity()
        dx = max(self.MIN_X, min(self.MAX_X, x)) - self.current_position['x']
        dy = max(self.MIN_Y, min(self.MAX_Y, y)) - self.current_position['y']
        self.move_relative(dx, dy, delay)

    def move_relative(self, dx, dy, delay=0.001):
        self._update_activity()
        x_target = max(self.MIN_X, min(self.MAX_X, self.current_position['x'] + dx))
        y_target = max(self.MIN_Y, min(self.MAX_Y, self.current_position['y'] + dy))

        if dx != 0:
            self.Motor1.TurnStep('forward' if dx > 0 else 'backward', abs(dx), delay)
        if dy != 0:
            self.Motor2.TurnStep('forward' if dy > 0 else 'backward', abs(dy), delay)

        self.current_position = {'x': x_target, 'y': y_target}

    def disable_motors(self):
        self.Motor1.Stop()
        self.Motor2.Stop()

    def shutdown(self):
        self.disable_motors()
        self.home()

galvo = GalvoController()
atexit.register(galvo.shutdown)

# ─── Location Load/Save ───
LOCATION_FILE = 'locations.json'

def load_locations():
    if not os.path.exists(LOCATION_FILE):
        return {}
    with open(LOCATION_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_locations(locs):
    with open(LOCATION_FILE, 'w') as f:
        json.dump(locs, f, indent=2)

# ─── Routes ───
@app.route('/')
def index():
    return render_template('index.html', locations=load_locations())

@app.route('/get_position')
def get_position():
    return jsonify(galvo.current_position)

@app.route('/move_manual', methods=['POST'])
def move_manual():
    data = request.get_json()
    direction = data.get('direction')
    step = int(data.get('step_size', 5))
    if direction == 'up': galvo.move_relative(0, step)
    elif direction == 'down': galvo.move_relative(0, -step)
    elif direction == 'left': galvo.move_relative(-step, 0)
    elif direction == 'right': galvo.move_relative(step, 0)
    return '', 204

@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.get_json()
    name = data.get('name')
    if name:
        locs = load_locations()
        locs[name] = galvo.current_position.copy()
        save_locations(locs)
    return '', 204

@app.route('/goto/<name>', methods=['POST'])
def goto_location(name):
    locations = load_locations()
    def find_location(name, node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == name and isinstance(v, dict) and 'x' in v and 'y' in v:
                    return v
                result = find_location(name, v)
                if result:
                    return result
        elif isinstance(node, list):
            for item in node:
                result = find_location(name, item)
                if result:
                    return result
        return None

    pos = find_location(name, locations)
    if pos:
        galvo.move_to(pos['x'], pos['y'])
        return '', 204
    return 'Location not found', 404

@app.route('/voice_command', methods=['POST'])
def voice_command():
    text = request.get_json().get('text', '').strip().lower()
    if not text:
        return jsonify({'status': 'error', 'message': 'No input received'}), 400

    locations = load_locations()
    flat_names = []

    def collect_names(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict) and 'x' in v and 'y' in v:
                    flat_names.append(k)
                collect_names(v)
        elif isinstance(d, list):
            for item in d:
                collect_names(item)

    collect_names(locations)
    location_names = ', '.join(flat_names)
    prompt = f"Known locations: {location_names}. Which location best matches: \"{text}\"? Respond with only the name or 'none'."

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        match = response.choices[0].message.content.strip()
        if match in flat_names:
            return goto_location(match)
        return jsonify({'status': 'not found', 'message': match})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/reset_home', methods=['POST'])
def reset_home():
    galvo.reset_home()
    return jsonify({'status': 'success', 'new_home': galvo.home_position})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
