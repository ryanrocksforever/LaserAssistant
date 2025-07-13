from flask import Flask, render_template, request, jsonify
from HR8825 import HR8825
from dotenv import load_dotenv
import openai
import json
import os
import atexit

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# ─────── Galvo Controller ───────
class GalvoController:
    def __init__(self):
        self.MIN_X, self.MAX_X = 0, 75
        self.MIN_Y, self.MAX_Y = 0, 200
        self.current_position = {'x': 0, 'y': 0}

        self.Motor1 = HR8825(13, 19, 12, (16, 17, 20))
        self.Motor2 = HR8825(24, 18, 4, (21, 22, 27))
        self.Motor1.SetMicroStep('softward', '1/8step')
        self.Motor2.SetMicroStep('softward', '1/8step')

        self.home()

    def home(self):
        self.move_to(0, 0)

    def move_to(self, x, y, delay=0.001):
        dx = max(self.MIN_X, min(self.MAX_X, x)) - self.current_position['x']
        dy = max(self.MIN_Y, min(self.MAX_Y, y)) - self.current_position['y']
        self.move_relative(dx, dy, delay)

    def move_relative(self, dx, dy, delay=0.001):
        x_target = max(self.MIN_X, min(self.MAX_X, self.current_position['x'] + dx))
        y_target = max(self.MIN_Y, min(self.MAX_Y, self.current_position['y'] + dy))

        if dx != 0:
            self.Motor1.TurnStep('forward' if dx > 0 else 'backward', abs(dx), delay)
        if dy != 0:
            self.Motor2.TurnStep('forward' if dy > 0 else 'backward', abs(dy), delay)

        self.current_position = {'x': x_target, 'y': y_target}

    def shutdown(self):
        self.move_to(0, 0)
        self.Motor1.Stop()
        self.Motor2.Stop()

galvo = GalvoController()
atexit.register(galvo.shutdown)

# ─────── Location Storage ───────
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

# ─────── Routes ───────
@app.route('/')
def index():
    return render_template('index.html', locations=load_locations().keys())

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

@app.route('/goto/<loc>', methods=['POST'])
def goto_location(loc):
    locations = load_locations()
    pos = locations.get(loc)
    if pos:
        galvo.move_to(pos['x'], pos['y'])
        return '', 204
    return 'Location not found', 404

@app.route('/voice_command', methods=['POST'])
def voice_command():
    text = request.get_json().get('text', '').strip().lower()
    if not text:
        return 'Missing input', 400

    locations = load_locations()
    location_names = ', '.join(locations.keys())
    prompt = (
        f"These are the known locations: {location_names}.\n"
        f"Given the voice command: \"{text}\", which location should the laser point to?\n"
        f"Respond with exactly one of the names, or say \"none\" if nothing matches."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        location = response['choices'][0]['message']['content'].strip()
        if location in locations:
            galvo.move_to(locations[location]['x'], locations[location]['y'])
            return jsonify({'status': 'success', 'location': location})
        return jsonify({'status': 'not found', 'message': location})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
