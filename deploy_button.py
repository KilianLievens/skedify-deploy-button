import RPi.GPIO as GPIO
import os
import time
from datetime import datetime
from threading import Thread

#### CONSTANTS ####

# BUTTONS
DEPLOY_BUTTON_PIN = 29

# OUTPUTS
BEEPER_OUT_PIN = 40

# SWITCHES
DEVELOPMENT_SWITCH_PIN = 37
STAGING_SWITCH_PIN = 35
DEMO_SWITCH_PIN = 33
PRODUCTION_SWITCH_PIN = 31

SWITCH_MESSAGES = {
    DEVELOPMENT_SWITCH_PIN: 'DEVELOPMENT ENABLED',
    STAGING_SWITCH_PIN: 'STAGING ENABLED',
    DEMO_SWITCH_PIN: 'DEMO ENABLED',
    PRODUCTION_SWITCH_PIN: 'PRODUCTION ENABLED'
}

#### CALLBACKS ####
def beeper_daemon():
    rotator = False
    while True:
        # Check if production switch still on so we stop beeping when someone disables it
        if not GPIO.input(PRODUCTION_SWITCH_PIN):
            GPIO.output(BEEPER_OUT_PIN, False)
            break

        rotator != rotator
        GPIO.output(BEEPER_OUT_PIN, rotator)
        time.sleep(0.5)

def switch_callback(channel):
    # Give time for the switch to settle (physics yo)
    time.sleep(0.05)

    if GPIO.input(channel):
        print(SWITCH_MESSAGES.get(channel, "UH OH. You found a bug :'("))

        if channel == PRODUCTION_SWITCH_PIN:
            thread = Thread(target=beeper_daemon, args=())
            thread.daemon = True
            thread.start()


def deploy_button(channel):

    # TODO 

    print('DEPLOYING!')


#### MAIN ####
try:
    # GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)  # physical numbering

    for pin in SWITCH_MESSAGES.keys():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(
            pin,
            GPIO.RISING,
            callback=switch_callback,
            bouncetime=300
            )

    GPIO.setup(BEEPER_OUT_PIN, GPIO.OUT)
    GPIO.add_event_detect(
        DEPLOY_BUTTON_PIN,
        GPIO.RISING,
        callback=deploy_button,
        bouncetime=5000 # Avoid someone double pressing within 5 seconds
        )

    GPIO.setup(DEPLOY_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    message = input("LETS GO!\n")

finally:
    GPIO.cleanup()
    print('cleaned up')
