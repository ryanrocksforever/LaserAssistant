import time

class HR8825:
    def __init__(self, dir_pin, step_pin, enable_pin, mode_pins):
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.enable_pin = enable_pin
        self.mode_pins = mode_pins
        print(f"[INIT] Motor initialized: DIR={dir_pin}, STEP={step_pin}, ENABLE={enable_pin}, MODES={mode_pins}")

    def SetMicroStep(self, mode, step):
        print(f"[SET MICROSTEP] Mode={mode}, Step={step}")

    def TurnStep(self, Dir, steps, stepdelay=0.001):
        print(f"[MOVE] Direction={Dir}, Steps={steps}, Delay={stepdelay}")
        # Simulate delay
        time.sleep(steps * stepdelay)

    def Stop(self):
        print("[STOP] Motor stopped.")
