import socket

#IP for hot spot
#PI_1_IP = '192.168.137.85' # IP of Pi 1
#PI_2_IP = '192.168.137.142' #IP of Pi 2

# IP for eduroam remote control
PI_1_IP = '10.126.46.162' # IP of Pi 1
PI_2_IP = '10.126.50.50' # IP of Pi 2

def get_local_and_peer_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    if local_ip == PI_1_IP:
        return PI_1_IP, PI_2_IP
    else:
        return PI_2_IP, PI_1_IP

LOCAL_IP, PEER_IP = get_local_and_peer_ip()
