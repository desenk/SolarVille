import socket

PI_1_IP = '10.126.55.70' # IP of Pi 1
PI_2_IP = '10.126.97.214' #IP of Pi 2

def get_local_and_peer_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    if local_ip == PI_1_IP:
        return PI_1_IP, PI_2_IP
    else:
        return PI_2_IP, PI_1_IP

LOCAL_IP, PEER_IP = get_local_and_peer_ip()
