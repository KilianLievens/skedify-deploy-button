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

SWITCHES = {
    DEVELOPMENT_SWITCH_PIN: 'development',
    STAGING_SWITCH_PIN: 'staging',
    DEMO_SWITCH_PIN: 'demo',
    PRODUCTION_SWITCH_PIN: 'production'
}

# DEPLOY COMMANDS
CLUSTER_NAMES = {
    "development": "SkedifyVideoDevelopment",
    "staging": "SkedifyVideoStaging",
    "demo": "SkedifyVideoDemo",
    "production": "SkedifyVideoProduction"
}

VIDEO_K8S_FOLDER = '/home/pi/video-k8s'

GIT_LATEST = '''\
    git -C {k8s_folder} fetch -ap \
    && git -C {k8s_folder} checkout master \
    && git -C {k8s_folder} reset --hard origin/master \
    '''.format(k8s_folder=VIDEO_K8S_FOLDER)

DEPLOY_TEMPLATE = '''\
    kubectl config set-cluster {cluster_name} \
    && ytt -f {k8s_folder}/{environment}/cluster-configuration | kubectl apply --validate=false -f - \
    && {k8s_folder}/get-all-enterprise-yaml.sh {environment} | kubectl apply -f - \
    '''
DRY_RUN_DEPLOY_TEMPLATE = '''\
    kubectl config set-cluster {cluster_name} \
    && ytt -f {k8s_folder}/{environment}/cluster-configuration | cat - \
    && {k8s_folder}/get-all-enterprise-yaml.sh {environment} | cat - \
    '''

#### CALLBACKS ####

def beeper_daemon():
    rotator = False
    while True:
        # Check if production switch still on so we stop beeping when someone disables it
        if not GPIO.input(PRODUCTION_SWITCH_PIN):
            GPIO.output(BEEPER_OUT_PIN, False)
            break

        rotator = not rotator
        GPIO.output(BEEPER_OUT_PIN, rotator)
        time.sleep(0.5)


def switch_callback(channel):
    # Give the switch some time to settle (physics yo)
    time.sleep(0.05)

    if GPIO.input(channel):
        print(SWITCHES.get(channel, "Invalid switch number").upper())

        if channel == PRODUCTION_SWITCH_PIN:
            # Production ENV gets warning beeps
            thread = Thread(target=beeper_daemon, args=())
            thread.daemon = True
            thread.start()


def deploy_button(channel):
    print('#### DEPLOYING ####')
    commands = [GIT_LATEST]
    for pin, env in SWITCHES.items():
        # TODO rickroll if no switches
        if GPIO.input(pin):
            commands.append(
                DRY_RUN_DEPLOY_TEMPLATE.format(
                    cluster_name=CLUSTER_NAMES[env],
                    environment=env,
                    k8s_folder=VIDEO_K8S_FOLDER
                )
            )
    os.system('&& '.join(commands))
    # TODO add output highlighting

#### MAIN ####
try:
    # GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)  # Physical numbering

    for pin in SWITCHES:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(
            pin,
            GPIO.RISING,
            callback=switch_callback,
            bouncetime=300
        )

    GPIO.setup(DEPLOY_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(
        DEPLOY_BUTTON_PIN,
        GPIO.RISING,
        callback=deploy_button,
        bouncetime=5000  # Avoid someone double pressing within 5 seconds
    )

    GPIO.setup(BEEPER_OUT_PIN, GPIO.OUT)

    message = input("LETS GO!\n")

finally:
    # Always cleanup
    GPIO.cleanup()
    print('cleaned up')
