##########################################
# Servo control example python script for AVDASI 2 AVIONICS
# Controls flap and aileron servos
# Author: Ethan Sheehan & Lucas Dick
##########################################

from pymavlink import mavutil

# Define pins for each servo
FLAP_PIN = 8
AILERON_PIN = 9

# Angle to PWM converter functions
def flap_angle_to_pwm(angle):
    return -19 * angle + 1550  # Equation for flap servo

def aileron_angle_to_pwm(angle):
    return -19 * angle + 1550  # Equation for aileron servo - adjust coefficients as needed

def mav_bytes(string):
    return bytes(string, 'utf-8')

class Servo:
    def __init__(self, pin, angle_converter, min_pwm=950, max_pwm=2150, trim=1550, reversed=False):
        self.pin = pin
        self.min = min_pwm
        self.max = max_pwm
        self.trim = trim
        self.reversed = reversed
        self.angle_converter = angle_converter

    def angle_to_pwm(self, angle):
        return self.angle_converter(angle)

class ServoController:
    def __init__(self, mav):
        self.mav = mav
        self.flap = Servo(pin=FLAP_PIN, angle_converter=flap_angle_to_pwm)
        self.aileron = Servo(pin=AILERON_PIN, angle_converter=aileron_angle_to_pwm)

    def write_servo_params(self, servo):
        print(f"Setting servo {servo.pin} params...")
        for key, val in {
            "MAX": servo.max,
            "MIN": servo.min,
            "TRIM": servo.trim,
            "REVERSED": int(servo.reversed)
        }.items():
            self.mav.mav.param_set_send(
                self.mav.target_system,
                self.mav.target_component,
                mav_bytes(f"SERVO{servo.pin}_{key}"),
                val,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
        print("Done.")

    def write_all_servo_params(self):
        self.write_servo_params(self.flap)
        self.write_servo_params(self.aileron)

    def move_servo(self, servo, angle):
        pwm = servo.angle_to_pwm(angle)
        print(f"Servo {servo.pin}: Angle {angle}° → PWM {pwm}")
        self.mav.mav.command_long_send(
            self.mav.target_system,
            self.mav.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0, servo.pin, pwm, 0, 0, 0, 0, 0
        )

    def move_flap(self, angle):
        self.move_servo(self.flap, angle)

    def move_aileron(self, angle):
        self.move_servo(self.aileron, angle)

if __name__ == "__main__":
    mav = mavutil.mavlink_connection('udp:0.0.0.0:14550')
    mav.wait_heartbeat()
    print("Heartbeat received from system (system %u component %u)" % 
          (mav.target_system, mav.target_component))

    controller = ServoController(mav)
    controller.write_all_servo_params()

    # Example: Move both servos
    controller.move_flap(30)
    controller.move_aileron(15)
