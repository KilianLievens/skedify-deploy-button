from datetime import datetime
from os import system as shell
from threading import Thread
from time import sleep

from asciimatics.effects import Julia, Print, Stars
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from pyfiglet import figlet_format

import RPi.GPIO as GPIO

#### CONSTANTS ####

SAFE_MODE = True
DRY_RUN_MODE = True

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
    && ytt -f {k8s_folder}/{environment}/cluster-configuration | kubectl apply --validate=false -f - | grep --color=always -e "^" -e "configured" \
    && {k8s_folder}/get-all-enterprise-yaml.sh {environment} | kubectl apply -f - | grep --color=always -e "^" -e "configured" \
    '''
DRY_RUN_DEPLOY_TEMPLATE = '''\
    kubectl config set-cluster {cluster_name} \
    && ytt -f {k8s_folder}/{environment}/cluster-configuration | kubectl diff -f - \
    && {k8s_folder}/get-all-enterprise-yaml.sh {environment} | kubectl diff -f - \
    '''

#### EFFECTS ####


def big_text_effect(screen, text):
    effects = [
        Print(
            screen,
            FigletText(text, font='big'),
            screen.height // 2 - 8),
        Stars(screen, (screen.width + screen.height) // 2)
    ]
    screen.play([Scene(effects, 50)], repeat=False)


def yolo_mode_effect(screen):
    effects = [
        Print(
            screen,
            FigletText('YOLOOOO', font='big'),
            screen.height // 2 - 8),
        Julia(screen)
    ]
    screen.play([Scene(effects, 50)], repeat=False)

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
        sleep(0.5)


def switch_callback(channel):
    # Give the switch some time to settle (physics yo)
    sleep(0.05)

    if not GPIO.input(channel):
        return

    if channel == PRODUCTION_SWITCH_PIN:
        # Production ENV gets warning beeps
        thread = Thread(target=beeper_daemon, args=())
        thread.daemon = True
        thread.start()

    # if all(GPIO.input(ch) for ch in SWITCHES):
    #     Screen.wrapper(yolo_mode_effect)
    #     return

    # enabled_env = SWITCHES.get(channel, "Invalid switch number").upper()
    # Screen.wrapper(big_text_effect, arguments=[enabled_env])


def deploy_button(channel):
    template = DRY_RUN_DEPLOY_TEMPLATE if DRY_RUN_MODE else DEPLOY_TEMPLATE

    if SAFE_MODE:
        sleep(0.5)
        if(not GPIO.input(channel)):
            print('Safe mode is on. Press the deploy button for at least half a second. Button cooldown is 3 seconds')
            return

    print(figlet_format('DEPLOYING'))

    commands = [GIT_LATEST] # Make sure video-k8s is up to date
    environments_to_deploy = [
        [pin, env] for pin, env in SWITCHES.items() if GPIO.input(pin)
    ]

    if not environments_to_deploy:
        shell('bash /home/pi/skedify-deploy-button/roll.sh')  # Hit em with the man
        return

    for pin, env in environments_to_deploy:
        commands.append(
            template.format(
                cluster_name=CLUSTER_NAMES[env],
                environment=env,
                k8s_folder=VIDEO_K8S_FOLDER
            )
        )
    shell('&& '.join(commands))

    print(figlet_format('DONE'))

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
        bouncetime=3000  # Avoid someone double pressing within 3 seconds
    )

    GPIO.setup(BEEPER_OUT_PIN, GPIO.OUT)

    message = input("LETS GO!\n")

finally:
    GPIO.cleanup() # Always cleanup
    print(figlet_format('Cleaned up. Goodbye.'))
