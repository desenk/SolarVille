import requests
from config import LOCAL_IP, PEER_IP

def send_data_to_peer(data):
    try:
        response = requests.post(f'http://{PEER_IP}:5000/update_peer_data', json=data)
        if response.status_code == 200:
            print("Data sent successfully!")
        else:
            print(f"Failed to send data. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data: {e}")

def fetch_data_from_peer():
    try:
        response = requests.get(f'http://{LOCAL_IP}:5000/get_peer_data')
        if response.status_code == 200:
            peer_data = response.json()
            print("Received data from peer:", peer_data)
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    # 测试数据上传to prosumer
    test_data = {
        'demand': 10,
        'generation': 5,
        'balance': -5,
        'battery SoC': 0.5,
        'enable': 1
    }
    send_data_to_peer(test_data)

    #Test data fetch from own server
    from server import app
    server_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    server_thread.start()
    fetch_data_from_peer()
