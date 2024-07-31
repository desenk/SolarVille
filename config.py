# config.py
import os
import socket

PI_1_IP = '192.168.245.200'
PI_2_IP = '192.168.245.64'

def get_local_and_peer_ip():
    local_ip = PI_1_IP if PI_1_IP in socket.gethostbyname_ex(socket.gethostname())[2] else PI_2_IP
    peer_ip = PI_2_IP if local_ip == PI_1_IP else PI_1_IP
    return local_ip, peer_ip

LOCAL_IP, PEER_IP = get_local_and_peer_ip()