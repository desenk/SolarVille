import netifaces # type: ignore

PI_1_IP = '10.126.46.162'  # IP of Pi 1
PI_2_IP = '10.126.50.50'  # IP of Pi 2

def get_network_ip():
    # Get the non-loopback IP address of the machine.
    try:
        # Get all network interfaces
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            # Skip loopback interface
            if interface == 'lo':
                continue
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                ip = addrs[netifaces.AF_INET][0]['addr']
                if ip != '127.0.0.1':
                    print(f"Network IP: {ip}")
                    return ip
    except Exception as e:
        print(f"Error getting network IP: {e}")
    return None

def get_local_and_peer_ip():
    local_ip = get_network_ip()
    if local_ip:
        if local_ip == PI_1_IP:
            return PI_1_IP, PI_2_IP
        elif local_ip == PI_2_IP:
            return PI_2_IP, PI_1_IP

LOCAL_IP, PEER_IP = get_local_and_peer_ip()

print(f"Local IP: {LOCAL_IP}")
print(f"Peer IP: {PEER_IP}")

SOLAR_SCALE_FACTOR = 1000  # Adjust this value as needed