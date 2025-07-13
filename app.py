from flask import Flask, render_template, request, redirect, jsonify
import json
import os
from HR8825 import HR8825

app = Flask(__name__)

# ─── Motor Setup ───────────────────────────────────────────────
Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))

Motor1.SetMicroStep('softward', '1/8step')
Motor2.SetMicroStep('softward', '1/8step')

current_position = {'x': 0, 'y': 0}

# ─── Movement Logic ─────────────────────────────────────────────
def move_axis(motor, axis, steps, delay=0.001):
    global current_position
    if steps == 0:
        return
    direction = 'forward' if steps > 0 else 'backward'
    getattr(motor, 'TurnStep')(Dir=direction, steps=abs(steps), stepdelay=delay)
    current_position[axis] += steps

def move_relative(dx, dy):
    move_axis(Motor1, 'x', dx)
    move_axis(Motor2, 'y', dy)

def move_to_position(target_x, target_y):
    dx = target_x - current_position['x']
    dy = target_y - current_position['y']
    move_relative(dx, dy)

# ─── Storage ────────────────────────────────────────────────────
LOCATION_FILE = "locations.json"

def save_locations(locations):
    with open(LOCATION_FILE, "w") as f:
        json.dump(locations, f)

def load_locations():
    if not os.path.exists(LOCATION_FILE):
        return {}
    with open(LOCATION_FILE, "r") as f:
        return json.load(f)

# ─── Routes ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    locations = load_locations()
    return render_template("index.html", locations=locations, current=current_position)

@app.route("/move", methods=["POST"])
def move():
    step_size = int(request.form.get("step_size", 10))
    direction = request.form.get("direction")

    dx, dy = 0, 0
    if direction == "up":
        dy = step_size
    elif direction == "down":
        dy = -step_size
    elif direction == "left":
        dx = -step_size
    elif direction == "right":
        dx = step_size

    move_relative(dx, dy)
    return redirect("/")

@app.route("/save_location", methods=["POST"])
def save_location():
    name = request.form.get("location_name")
    if name:
        locations = load_locations()
        locations[name] = current_position.copy()
        save_locations(locations)
    return redirect("/")

@app.route("/goto/<name>", methods=["POST"])
def goto(name):
    locations = load_locations()
    if name in locations:
        pos = locations[name]
        move_to_position(pos['x'], pos['y'])
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
