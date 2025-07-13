from flask import Flask, render_template, request, jsonify
import json
from HR8825Test import HR8825

# Motor setup from your provided code
MICROSTEP_MODE = '1/8step'
REVERSED = {'x': True, 'y': True}
M1_HOME_OFFSET = -150

Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
Motor2 = HR8825(dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))

Motor1.SetMicroStep('softward', MICROSTEP_MODE)
Motor2.SetMicroStep('softward', MICROSTEP_MODE)

current_position = {'x': 0, 'y': 0}

def move_axis(motor, axis, steps, delay=0.001):
    global current_position
    if steps == 0:
        return
    if REVERSED.get(axis, False):
        steps = -steps
    direction = 'forward' if steps > 0 else 'backward'
    getattr(motor, 'TurnStep')(Dir=direction, steps=abs(steps), stepdelay=delay)
    current_position[axis] += steps

def move_to(x, y):
    global current_position
    dx = x - current_position['x']
    dy = y - current_position['y']
    move_axis(Motor1, 'x', dx)
    move_axis(Motor2, 'y', dy)

app = Flask(__name__)

def load_locations():
    try:
        with open('locations.json', 'r') as file:
            return json.load(file)
    except:
        return {}

def save_locations(data):
    with open('locations.json', 'w') as file:
        json.dump(data, file, indent=4)

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
    locations = load_locations()
    if item in locations:
        loc = locations[item]
        move_to(loc['x'], loc['y'])
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Item not found'})

@app.route('/move_manual', methods=['POST'])
def move_manual():
    data = request.json
    direction = data['direction']
    step_size = 10  # fine adjustment steps

    if direction == 'up':
        move_axis(Motor2, 'y', step_size)
    elif direction == 'down':
        move_axis(Motor2, 'y', -step_size)
    elif direction == 'left':
        move_axis(Motor1, 'x', -step_size)
    elif direction == 'right':
        move_axis(Motor1, 'x', step_size)

    return jsonify({'status': 'success', 'position': current_position})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
