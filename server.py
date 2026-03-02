# # RUNS On RRaspberry Pi Process commands & move servos control Hexapod servos	✅ use TCP/CP
import socket
import json
import time
import os
import numpy as np
from picamera2 import Picamera2
from adafruit_servokit import ServoKit
import RPi.GPIO as GPIO
from Ultrasonic import Ultrasonic
from Buzzer import Buzzer
from ADCDevice import ADS7830

import datetime

import signal
import sys

# Inilize to check battery level

adc = ADS7830()

# Initialize Servo Control
kit = ServoKit(channels=16)

# Initialize Ultrasonic Sensor and Buzzer
ultrasonic = Ultrasonic()
buzzer = Buzzer()

# Initialize Camera
try:
    picam2 = Picamera2()
    picam2.start()
    time.sleep(2)  # Give some time for the camera to initialize
except RuntimeError as e:
    print("Camera initialization failed:", e)
    picam2 = None  # Prevent further errors


# Function to get ultrasonic distance


def get_distance():
    """
    Get the distance from the ultrasonic sensor.
    :return: Distance in centimeters (cm)
    """
    try:
        distance = ultrasonic.getDistance()
        print(f" Measured Distance: {distance} CM")  # Debugging print
        return distance
    except Exception as e:
        print(f"Error getting distance: {e}")
        return -1  # Return -1 if an error occurs


# Function to activate the buzzer


def test_Buzzer():
    try:
        buzzer.run('1')
        time.sleep(1)
        print("1S")
        time.sleep(1)
        print("2S")
        time.sleep(1)
        print("3S")
        buzzer.run('0')
        print("\nEnd of program")
    except KeyboardInterrupt:
        buzzer.run('0')
        print("\nEnd of program")


# NEUTRAL_POSITION = [90, 90, 90]  # Hip, Thigh, Calf
# LEG_COUNT = 6  # Hexapod has 6 legs
#
# # ✅ Define **Gait Sequences** for Smooth Movement
# Gait_Sequences = {
#     "forward": [
#         [[70, 110, 90], [70, 110, 90], [80, 100, 90], [80, 100, 90], [90, 120, 90], [90, 120, 90]],
#         [[110, 70, 90], [110, 70, 90], [100, 80, 90], [100, 80, 90], [120, 90, 90], [120, 90, 90]],
#     ],
#     "backward": [
#         [[110, 70, 90], [110, 70, 90], [100, 80, 90], [100, 80, 90], [120, 90, 90], [120, 90, 90]],
#         [[70, 110, 90], [70, 110, 90], [80, 100, 90], [80, 100, 90], [90, 120, 90], [90, 120, 90]],
#     ],
#     "left": [
#         [[90, 70, 110], [90, 110, 70], [90, 80, 100], [90, 100, 80], [90, 70, 110], [90, 110, 70]],
#         [[90, 110, 70], [90, 70, 110], [90, 100, 80], [90, 80, 100], [90, 110, 70], [90, 70, 110]],
#     ],
#     "right": [
#         [[90, 110, 70], [90, 70, 110], [90, 100, 80], [90, 80, 100], [90, 110, 70], [90, 70, 110]],
#         [[90, 70, 110], [90, 110, 70], [90, 80, 100], [90, 100, 80], [90, 70, 110], [90, 110, 70]],
#     ],
# }
#
#
# # ✅ Function to Move Servos Based on Gait Sequences
# def move_servos(action):
#     if action in Gait_Sequences:
#         for step in Gait_Sequences[action]:  # Iterate through movement phases
#             for i in range(LEG_COUNT):  # Loop through 6 legs
#                 kit.servo[i * 3].angle = step[i][0]  # Hip
#                 kit.servo[i * 3 + 1].angle = step[i][1]  # Thigh
#                 kit.servo[i * 3 + 2].angle = step[i][2]  # Calf
#                 time.sleep(0.2)  # Smooth transition delay
#         reset_servos()
#         print(f"✅ {action.capitalize()} movement executed!")
#
#
# # ✅ Function to Reset Servos to Neutral Position
# def reset_servos():
#     for i in range(LEG_COUNT):
#         kit.servo[i * 3].angle = NEUTRAL_POSITION[0]
#         kit.servo[i * 3 + 1].angle = NEUTRAL_POSITION[1]
#         kit.servo[i * 3 + 2].angle = NEUTRAL_POSITION[2]
#     print("✅ Servos returned to neutral position.")


# Function to capture a photo
# ------------------------------------------------------ old -



def capture_photo():
    """Capture an image using Picamera2 with a unique filename."""
    image_dir = "/home/sakhtar/captured_images"
    os.makedirs(image_dir, exist_ok=True)

    # Generate a unique filename using the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(image_dir, f"image_{timestamp}.jpg")

    try:
        if picam2 is None:
            print("❌ Camera not initialized!")
            return None

        picam2.start()
        time.sleep(2)  # Allow camera to stabilize
        picam2.capture_file(image_path)
        picam2.stop()

        print(f"Image saved at: {image_path}")
        return image_path
    except Exception as e:
        print(f"❌ Error capturing image: {e}")
        return None


def get_battery_level():
    try:
        channel = 0  # Ensure this is the correct ADC channel
        raw_value = adc.analogRead(channel)  # Read raw ADC value
        print(f"Raw ADC Value: {raw_value}")  # Debugging print

        power = float(raw_value) * (5.0 / 255.0)  # Convert to voltage
        print(f"Battery Voltage: {power:.2f}V")  # Debugging print

        return power  # Ensuring it returns a float
    except Exception as e:
        print(f"Error getting battery level: {e}")
        return None  # None in case of an error


def handle_exit(signum, frame):
    print("Server shutting down...")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)  # Handle Ctrl+C


# Start TCP Server
def start_server():
    global client_socket

    def find_raspberry_pi_ip():
        try:
            hostname = "raspberrypi.local"  # Change to actual hostname if needed
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        except socket.gaierror:
            return None  # Return None if the Pi is not found

    RPI_HOST = find_raspberry_pi_ip()  # Raspberry Pi's IP
    PORT = 5002

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reusing

    try:
        server_socket.bind((RPI_HOST, PORT))
        server_socket.listen(5)

        print(f"Running server on {RPI_HOST}:{PORT}...")

        while True:
            try:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")

                data = client_socket.recv(1024).decode()
                if not data:
                    continue  # Instead of breaking the loop, just ignore empty data

                print(f"Received data: {data}")

                try:
                    command = json.loads(data).get("command")
                except json.JSONDecodeError:
                    print("Invalid JSON received")
                    client_socket.sendall(json.dumps({"status": "error", "message": "Invalid JSON"}).encode())
                    continue

                print(f"Received command: {command}")

                response = {"status": "success"}

                if command == "distance":
                    response = {"status": "success", "distance": get_distance()}

                elif command in ["forward", "backward", "left", "right"]:
                    move_servos(command)

                elif command == "buzzer":
                    print("🔊 Buzzer Command Received!")  # ✅ Debugging print
                    test_Buzzer()
                    response = {"buzzer": "activated"}

                elif command == "capture":
                    response['image'] = capture_photo()

                elif command == "battery_level":
                    print("Battery Level Command Received!")  # Debugging print
                    battery_voltage = get_battery_level()

                    if isinstance(battery_voltage, (int, float)):  # ✅ Ensure it's a number
                        response["battery_level"] = "{:.2f}V".format(battery_voltage)
                    else:
                        response["battery_level"] = "Error reading battery"
                # Face Recognition chunk
                elif command == "start_face_recognition":
                    try:
                        import subprocess
                        script_path = "/home/sakhtar/HexapodGUI/face_recognition/face_recognition_stream.py"
                        subprocess.Popen(["python3", script_path])
                        response = {"status": "face_rec_started"}
                        print("🎥 Face recognition script started.")
                    except Exception as e:
                        print(f"Error starting face recognition: {e}")
                        response = {"status": "error", "message": str(e)}

                client_socket.sendall(json.dumps(response).encode())

            except Exception as e:
                print(f"Error handling client request: {e}")
            finally:
                client_socket.close()

    except OSError as e:
        print("Error:", e)

    finally:
        server_socket.close()
        print("Server socket closed.")


if __name__ == "__main__":
    start_server()
