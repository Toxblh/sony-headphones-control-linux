#!/bin/python

# Thanks https://github.com/impankratov/sony-headphones-control-py
import enum
import sys
import os
import dbus
import bluetooth
import json
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import QStringListModel

CONFIG_FOLDER = str(Path.home()) + '/.config/sony-headphones-control'
CONFIG_PATH = CONFIG_FOLDER + '/config.json'

class Mode(enum.Enum):
    NoiseCancelling = 'noise-cancelling'
    WindCancelling = 'wind-cancelling'
    AmbientSound = 'ambient-sound'
    Disabled = 'disable'

# enabled - any NC/WC/AS modes
# noiseCancelling - 0, 1, 2 modes of NC
# volume - That is volume of ambient sound in ambient mode
# voice - focus on human voices in Ambient mode
def getPacket(enabled: bool, noiseCancelling: int, volume: int, voice: bool):
    packetPrefix = [12, 0, 0, 0, 0, 8, 104, 2]
    enabledValue = 16 if enabled else 0

    data = [enabledValue, 2, noiseCancelling, 1, voice, volume]
    packet = packetPrefix + data

    controlSum = 0

    for b in packet:
        controlSum += b

    readyPacket = [62] + packet + [controlSum] + [60]

    return bytes(readyPacket)


def setMode(mode):

    config = openConfig()

    print('config', config['device'])

    addr = config['device']
    print("Set mode", mode)
    print("Searching for {}...".format(addr))

    uuid = "96cc203e-5068-46ad-b32d-e316f5e069ba"

    service_matches = bluetooth.find_service(uuid=uuid, address=addr)

    print('service_matches', service_matches)

    if len(service_matches) == 0:
        print("Couldn't find the device service.")
        sys.exit(0)

    first_match = service_matches[0]
    print('first_match', first_match)
    port = first_match["port"]
    host = first_match["host"]

    ambientSoundBytes = None

    if mode == Mode.NoiseCancelling:
        # Noise cancelling
        ambientSoundBytes = getPacket(True, 2, 0, False)

    elif mode == Mode.WindCancelling:
        # Wind cancelling
        ambientSoundBytes = getPacket(True, 1, 0, False)

    elif mode == Mode.AmbientSound:
        # Ambient sound
        ambientSoundBytes = getPacket(True, 0, 19, False)

    elif mode == Mode.Disabled:
        # Disabled ambient sound
        ambientSoundBytes = getPacket(False, 0, 0, False)

    else:
        print('Unknown mode, exiting')
        sys.exit(0)

    # print('ambientSoundBytes', ambientSoundBytes)

    print("Connecting to {} to enable {}".format(host, mode))

    # Create the client socket
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    print('host', host)
    print('port', port)
    sock.connect((host, port))
    sock.send(ambientSoundBytes)
    sock.close()

def openConfig():
    config = {'device': '', 'name': ''}
    Path(CONFIG_FOLDER).mkdir(parents=True, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    else:
        print(config)
        with open(CONFIG_PATH, 'w+') as f:
            json.dump(config, f)

    return config

def getBlueDevices():
    bus = dbus.SystemBus()
    obj = bus.get_object('org.bluez', "/")
    manager = dbus.Interface(obj, "org.freedesktop.DBus.ObjectManager")
    objects = manager.GetManagedObjects()
    devices = []
    for path in objects.keys():
        interfaces = objects[path]
        for interface in interfaces.keys():
            if interface == "org.bluez.Device1":
                devices.append(path)

    bt_devices = []
    for device in devices:
        obj = bus.get_object('org.bluez', device)
        info = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
        bt_devices.append({
            "name": str(info.Get("org.bluez.Device1", "Name")),
            "addr": str(info.Get("org.bluez.Device1", "Address"))
        })

    return bt_devices


def showSettings():
    print("Connecting to")


def saveDevice(index):
    device = view.model().itemData(index)
    print(device[0])
    for x in devices:
        if x['name'] == device[0]:
            devAddr = x['addr']

    devLabel.setText(device[0] + ": " + devAddr)
    config = {'device': devAddr, 'name': device[0]}

    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)


app = QApplication([])
app.setQuitOnLastWindowClosed(False)

config = openConfig()

# Tray
icon = QIcon("icon.png")

tray = QSystemTrayIcon()
tray.setIcon(icon)
tray.setVisible(True)

act_NC = QAction('Noise cancelling')
act_NC.triggered.connect(lambda: setMode(Mode.NoiseCancelling))

act_WC = QAction('Wind cancelling')
act_WC.triggered.connect(lambda: setMode(Mode.WindCancelling))

act_AS = QAction('Ambient sound')
act_AS.triggered.connect(lambda: setMode(Mode.AmbientSound))

act_Dis = QAction('Disabled ambient sound')
act_Dis.triggered.connect(lambda: setMode(Mode.Disabled))

settings = QAction("Settings")
settings.triggered.connect(showSettings)

quit = QAction('Quit')
quit.triggered.connect(app.quit)

menu = QMenu()
name = QAction(config['name'])

menu.addAction(name)
menu.addSeparator()
menu.addAction(act_NC)
menu.addAction(act_WC)
menu.addAction(act_AS)
menu.addAction(act_Dis)
menu.addSeparator()
menu.addAction(settings)
menu.addAction(quit)

tray.setContextMenu(menu)

# Window
window = QWidget()
window.setWindowTitle('Sony control')
window.setGeometry(1500, 700, 400, 200)

layout = QVBoxLayout()

devices = getBlueDevices()
options = []
for device in devices:
    options.append(device['name'])

model = QStringListModel(options)
view = QListView()
view.setModel(model)
view.clicked.connect(saveDevice)

devLabel = QLabel("Current device: " +
                  config['name'] + ": " + config['device'])

layout.addWidget(devLabel)
layout.addWidget(view)
window.setLayout(layout)
window.show()

app_icon = QIcon('icon.png')
app.setWindowIcon(app_icon)

app.exec_()
