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


def send(sock, message):
    """
    This function sends a message through a bluetooth socket
    """
    sock.send(b"\r\n" + message + b"\r\n")

# Thanks https://github.com/TheWeirdDev/Bluetooth_Headset_Battery_Level
def get_at_command(sock, line, device, battery):
    """
    Will try to get and print the battery level of supported devices
    """
    blevel = -1

    if b"BRSF" in line:
        send(sock, b"+BRSF: 1024")
        send(sock, b"OK")
    elif b"CIND=" in line:
        send(sock, b"+CIND: (\"battchg\",(0-5))")
        send(sock, b"OK")
    elif b"CIND?" in line:
        send(sock, b"+CIND: 5")
        send(sock, b"OK")
    elif b"BIND=?" in line:
        # Announce that we support the battery level HF indicator
        # https://www.bluetooth.com/specifications/assigned-numbers/hands-free-profile/
        send(sock, b"+BIND: (2)")
        send(sock, b"OK")
    elif b"BIND?" in line:
        # Enable battery level HF indicator
        send(sock, b"+BIND: 2,1")
        send(sock, b"OK")
    elif b"XAPL=" in line:
        send(sock, b"+XAPL: iPhone,7")
        send(sock, b"OK")
    elif b"IPHONEACCEV" in line:
        parts = line.strip().split(b',')[1:]
        if len(parts) > 1 and (len(parts) % 2) == 0:
            parts = iter(parts)
            params = dict(zip(parts, parts))
            if b'1' in params:
                blevel = (int(params[b'1']) + 1) * 10
    elif b"BIEV=" in line:
        params = line.strip().split(b"=")[1].split(b",")
        if params[0] == b"2":
            blevel = int(params[1])
    elif b"XEVENT=BATTERY" in line:
        params = line.strip().split(b"=")[1].split(b",")
        blevel = int(params[1]) / int(params[2]) * 100
    else:
        send(sock, b"OK")

    if blevel != -1:
        print(f"Battery level for {device} is {blevel}%")
        battery.setText(f"Battery: {blevel}%")
        return False

    return True

def find_rfcomm_port(device):
    """
    Find the RFCOMM port number for a given bluetooth device
    """
    uuid = "0000111e-0000-1000-8000-00805f9b34fb"
    
    proto = bluetooth.find_service(address=device, uuid=uuid)
    if len(proto) == 0:
        print("Couldn't find the RFCOMM port number")
        return 4

    for pr in proto:
        if 'protocol' in pr and pr['protocol'] == 'RFCOMM':
            port = pr['port']
            return port
    return 4

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

def getBatteryLevel(battery):
    battery.setText("Battery: ...%")
    config = openConfig()
    print('config', config['device'])

    addr = config['device']
    print("Searching for {}...".format(addr))

    try:
        port = find_rfcomm_port(addr)
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((addr, port))
        while get_at_command(sock, sock.recv(128), addr, battery):
            pass
        sock.close()
    except OSError as err:
        print(f"{addr} is offline", err)

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


def showSettings(window):
    window.show()


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


config = openConfig()

# App
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
app_icon = QIcon('icon.png')
app.setWindowIcon(app_icon)

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
settings.triggered.connect(lambda: showSettings(window))

battery = QAction("Battery")
battery.triggered.connect(lambda: getBatteryLevel(battery))
# getBatteryLevel(battery)

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
menu.addAction(battery)
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

# Start app
app.exec_()
