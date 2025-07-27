##########################################
# UI example python script for AVDASI 2 AVIONICS
# Creates a barebones UI for your GS
# Shows connections status
# Arming button
# Safety switch toggle button
# Set servo angles for flap and aileron
# Author: Ethan Sheehan & Lucas Dick (Updated by Gemini)
#
# This file should be able to run independently.
#
# Changes from previous version:
# - Added separate controls for Flap and Aileron servos.
# - UI now has two input fields and two "Send" buttons.
# - Updated send_angle methods to call move_flap and move_aileron.
# - Integrated mavlink connection logic into the main block for standalone testing.
#
# Potential upgrades:
# - Make it actually look good
# - Mode switching
# - Flap position display
# - Flap angle graph
# - Live data graphing
# - Use another module/code to make it look better (tkinter has its limits)
# - Make it run faster/smoother/better response time
##########################################

import tkinter as tk
from tkinter import ttk, messagebox
from pymavlink import mavutil

# Assume the other example codes are in files named accordingly
# and are in the same directory.
import Servo_example  # This should be the new servo code provided
import GS_example
import Arm_example

# Class for Servo UI functions
class ServoUI:
    # How the UI looks function
    def __init__(self, root, servo_controller=None):
        # Initialize the main window and store the servo controller
        self.root = root
        self.root.title("Flap and Aileron Control")
        self.servo_controller = servo_controller

        # --- Main Frame ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Connection Status ---
        status_frame = ttk.LabelFrame(main_frame, text="System Status")
        status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.status_var = tk.StringVar(value=GS_example.connection_status.capitalize())
        ttk.Label(status_frame, text="Connection:").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.status_var, foreground="red").pack(side=tk.LEFT, padx=5, pady=5)

        # --- Servo Controls ---
        servo_frame = ttk.LabelFrame(main_frame, text="Servo Controls")
        servo_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Flap Controls
        ttk.Label(servo_frame, text="Flap Angle (°):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.flap_angle_entry = ttk.Entry(servo_frame, width=10)
        self.flap_angle_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(servo_frame, text="Send Flap", command=self.send_flap_angle).grid(row=0, column=2, padx=5, pady=2)

        # Aileron Controls
        ttk.Label(servo_frame, text="Aileron Angle (°):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.aileron_angle_entry = ttk.Entry(servo_frame, width=10)
        self.aileron_angle_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(servo_frame, text="Send Aileron", command=self.send_aileron_angle).grid(row=1, column=2, padx=5, pady=2)

        # --- Arming and Safety Controls ---
        arming_frame = ttk.LabelFrame(main_frame, text="Vehicle State")
        arming_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Safety switch button
        self.safety_enabled = True
        self.safety_button = ttk.Button(
            arming_frame,
            text="Safety Enabled (Click to toggle)",
            command=self.toggle_safety
        )
        self.safety_button.pack(fill=tk.X, padx=5, pady=5)

        # Arming button
        self.armed = False
        self.arming_button = ttk.Button(
            arming_frame,
            text="Arming Disabled (Click to toggle)",
            command=self.toggle_arming
        )
        self.arming_button.pack(fill=tk.X, padx=5, pady=5)

        # Arming status label
        self.arming_status_label = ttk.Label(
            arming_frame,
            text="DISARMED - NO LOGGING",
            background="red",
            foreground="white",
            anchor="center",
            padding=5
        )
        self.arming_status_label.pack(fill=tk.X, padx=5, pady=5)

        # Start status updater loop
        self.update_status()

    # Safety switch action function
    def toggle_safety(self):
        # Toggles the safety switch state on the flight controller
        if not self.servo_controller:
            messagebox.showwarning("Not Connected", "Vehicle is not connected.")
            return
        mav = self.servo_controller.mav
        # Toggle the state
        new_state = not self.safety_enabled
        success = Arm_example.toggle_safety_switch(mav, new_state) # calls arming example code
        # Update button text based on new state
        if success:
            self.safety_enabled = new_state
            self.safety_button.config(text=f"Safety {'Enabled' if self.safety_enabled else 'Disabled'} (Click to toggle)")
        else:
            messagebox.showerror("Safety Switch Error", "Failed to toggle safety switch.")

    # Arming action function
    def toggle_arming(self):
        # Toggles the arming state of the vehicle
        if not self.servo_controller:
            messagebox.showwarning("Not Connected", "Vehicle is not connected.")
            return
        mav = self.servo_controller.mav
        self.armed = not self.armed
        success = Arm_example.toggle_arming_switch(mav, self.armed) # calls arming example code
        if success:
            if self.armed:
                self.arming_button.config(text="Arming Enabled (Click to toggle)")
                self.arming_status_label.config(text="ARMED AND LOGGING", background="green")
            else:
                self.arming_button.config(text="Arming Disabled (Click to toggle)")
                self.arming_status_label.config(text="DISARMED - NO LOGGING", background="red")
        else:
            # If arming failed, revert the state
            self.armed = not self.armed
            messagebox.showerror("Arming Error", "Failed to toggle arming state.")


    # Connection status action function
    def update_status(self):
        # Updates the connection status label every 1000 milliseconds
        self.status_var.set(GS_example.connection_status.capitalize()) # call GS example code
        self.root.after(1000, self.update_status)

    # Servo controller configuration function
    def set_servo_controller(self, servo_controller):
        self.servo_controller = servo_controller # writes servo configuration

    # Flap angle action function
    def send_flap_angle(self):
        # Sends angle value entered by the user to the flap servo
        if not self.servo_controller: # check if connected
            messagebox.showwarning("Not Connected", "Vehicle is not connected.")
            return
        try:
            angle = float(self.flap_angle_entry.get()) # Get angle from input
            self.servo_controller.move_flap(angle) # Send angle via MAVLink
            print(f"Sent flap angle: {angle}°")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the angle.")
        except Exception as e: # other error handling
            messagebox.showerror("Send Error", str(e))

    # Aileron angle action function
    def send_aileron_angle(self):
        # Sends angle value entered by the user to the aileron servo
        if not self.servo_controller: # check if connected
            messagebox.showwarning("Not Connected", "Vehicle is not connected.")
            return
        try:
            angle = float(self.aileron_angle_entry.get()) # Get angle from input
            self.servo_controller.move_aileron(angle) # Send angle via MAVLink
            print(f"Sent aileron angle: {angle}°")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the angle.")
        except Exception as e: # other error handling
            messagebox.showerror("Send Error", str(e))

# Independence call
if __name__ == "__main__": # Allows this script to be run independently
    # This block is useful for testing the UI before integrating into a wider system
    
    root = tk.Tk() # Creates the main application window for the UI using Tkinter
    servo_controller = None
    
    try:
        # Attempt to connect to the vehicle
        print("Connecting to vehicle on: udp:0.0.0.0:14550")
        mav_connection = mavutil.mavlink_connection('udp:0.0.0.0:14550')
        #mav_connection.wait_heartbeat()
        print("Heartbeat received from system (system %u component %u)" % 
              (mav_connection.target_system, mav_connection.target_component))
        
        # Instantiate the servo controller with the connection
        servo_controller = Servo_example.ServoController(mav_connection)
        
        # It's good practice to set the servo params on startup
        print("Setting servo parameters...")
        servo_controller.write_all_servo_params()
        print("Servo parameters set.")

    except Exception as e: # error handling
        messagebox.showwarning("Connection Error", f"Could not connect to vehicle: {e}\n\nRunning in offline mode.")
        servo_controller = None

    # Launch the Servo UI
    servo_ui = ServoUI(root, servo_controller)
    root.mainloop()

