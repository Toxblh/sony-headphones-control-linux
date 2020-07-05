# Thanks https://github.com/impankratov/sony-headphones-control-py
import sys
import bluetooth

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

addr = None
mode = None

if len(sys.argv) < 3:
    print("Invalid arguments, please specify BT address and desired mode\n\nChoose one of mode:\n  noise-cancelling\n  wind-cancelling\n  ambient-sound\n  disable")
    sys.exit(0)
else:
    addr = sys.argv[1]
    mode = sys.argv[2]
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

if mode == 'noise-cancelling':
    # Noise cancelling
    ambientSoundBytes = getPacket(True, 2, 0, False)

elif mode == 'wind-cancelling':
    # Wind cancelling
    ambientSoundBytes = getPacket(True, 1, 0, False)

elif mode == 'ambient-sound':
    # Ambient sound
    ambientSoundBytes = getPacket(True, 0, 19, False)

elif mode == 'disable':
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
