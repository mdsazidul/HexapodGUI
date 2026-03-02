import RPi.GPIO as GPIO
import time


class Buzzer:
    def __init__(self, buzzer_pin=18):
        """
        Initialize the Buzzer with the specified GPIO pin.
        :param buzzer_pin: GPIO pin connected to the buzzer
        """
        self.BUZZER_PIN = buzzer_pin

        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT)

    def run(self, state):
        """
        Control the buzzer state.
        :param state: '1' to turn ON, '0' to turn OFF
        """
        if state == '1':
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        else:
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def beep(self, duration=1):
        """
        Make a short beep sound.
        :param duration: Time in seconds for the beep
        """
        self.run('1')
        time.sleep(duration)
        self.run('0')

    def cleanup(self):
        """
        Clean up GPIO settings.
        """
        GPIO.cleanup()


# Test script to run this file directly
if __name__ == "__main__":
    try:
        buzzer = Buzzer()
        print("Press Ctrl+C to exit.")
        while True:
            buzzer.beep(1)  # Beep for 1 second
            time.sleep(2)  # Wait for 2 seconds before the next beep
    except KeyboardInterrupt:
        print("\nExiting...")
        buzzer.cleanup()
