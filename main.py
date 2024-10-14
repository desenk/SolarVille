import requests
from config import LOCAL_IP, PEER_IP

def fetch_data_from_peer():
    try:
        response = requests.get(f'http://{PEER_IP}:5000/get_peer_data')
        if response.status_code == 200:
            peer_data = response.json()
            print("Received data from peer:", peer_data)
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
   
    fetch_data_from_peer()