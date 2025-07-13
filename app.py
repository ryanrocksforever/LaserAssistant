from flask import Flask, render_template, request, jsonify
import json, os
from HR8825 import HR8825

app = Flask(__name__)

# ─── CONFIG ────────────────────────────────
X_RANGE = 75
Y_RANGE = 200
POSITION_FILE = "locations.json"
current_position = {'x': 0, 'y': 0}

# ─── Motor Setup ───────────────────────────
Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))
Motor1.SetMicroStep('softward', '1/8step')
Motor2.SetMicroStep('softward', '1/8step')

# ─── Movement Functions ────────────────────
def move_axis(motor, axis, steps, delay=0.001):
    if steps == 0:
        return

    target = current_position[axis] + steps
    limit = X_RANGE if axis == 'x' else Y_RANGE
    if target < 0 or target > limit:
        print(f"Blocked movement: {axis} target {target} outside 0-{limit}")
        return

    direction = 'forward' if steps > 0 else 'backward'
    getattr(motor, 'TurnStep')(Dir=direction, steps=abs(steps), stepdelay=delay)
    current_position[axis] = target

def move_to(x, y):
    dx = x - current_position['x']
    dy = y - current_position['y']
    move_axis(Motor1, 'x', dx)
    move_axis(Motor2, 'y', dy)

# ─── Storage ───────────────────────────────
def save_locations(locations):
    with open(POSITION_FILE, 'w') as f:
        json.dump(locations, f)

def load_locations():
    if not os.path.exists(POSITION_FILE):
        return {}
    with open(POSITION_FILE, 'r') as f:
        return json.load(f)

# ─── Routes ────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", locations=load_locations(), current=current_position)

@app.route("/move_manual", methods=["POST"])
def move_manual():
    data = request.get_json()
    direction = data.get("direction")
    step = int(data.get("step_size", 10))

    dx, dy = 0, 0
    if direction == "left": dx = -step
    elif direction == "right": dx = step
    elif direction == "up": dy = step
    elif direction == "down": dy = -step

    move_axis(Motor1, 'x', dx)
    move_axis(Motor2, 'y', dy)
    return jsonify(success=True)

@app.route("/get_position")
def get_position():
    return jsonify(current_position)

@app.route("/save_location", methods=["POST"])
def save_location():
    name = request.form.get("location_name")
    if name:
        locations = load_locations()
        locations[name] = current_position.copy()
        save_locations(locations)
    return ("", 204)

@app.route("/goto/<name>", methods=["POST"])
def goto(name):
    locations = load_locations()
    if name in locations:
        move_to(locations[name]['x'], locations[name]['y'])
    return ("", 204)

if __name__ == "__main__":
    # Reset to origin before start
    move_axis(Motor1, 'x', -X_RANGE)
    move_axis(Motor2, 'y', -Y_RANGE)
    current_position['x'] = 0
    current_position['y'] = 0

    app.run(host="0.0.0.0", port=5000)
