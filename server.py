from flask import Flask, request, jsonify
import logging
import time
import threading
from config import PEER_IP, LOCAL_IP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

peers = []
peer_ready = {}
simulation_started = threading.Event()
peer_data = {}

# Shared data for the example
energy_data = {
    "balance": 0,
    "currency": 100.0,
    "demand": 0,
    "generation": 0,
    "battery_charge": 0,
}

@app.route('/ready', methods=['POST'])
def ready():
    data = request.json
    peer_ip = request.remote_addr
    if peer_ip in peers:
        peer_ready[peer_ip] = True
        logging.info(f"Peer {peer_ip} is ready")
        return jsonify({"status": "ready"})
    else:
        logging.warning(f"Peer {peer_ip} not recognized")
        return jsonify({"status": "peer not recognized"}), 400

@app.route('/update_peer_data', methods=['POST'])
def update_peer_data():
    try:
        data = request.json
        peer_ip = request.remote_addr
        if peer_ip not in peer_data:
            peer_data[peer_ip] = {}
        peer_data[peer_ip].update(data)
        logging.info(f"Updated peer data for {peer_ip}: {data}")
        return jsonify({"status": "updated"})
    except Exception as e:
        logging.error(f"Error updating peer data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/start', methods=['POST'])
def start():
    global peers, peer_ready
    data = request.json
    peers = data.get('peers', peers)  # Use existing peers if not provided
    
    # Initialize peer_ready dictionary
    for peer in peers:
        if peer not in peer_ready:
            peer_ready[peer] = False

    timeout = time.time() + 60  # 60 second timeout
    while not all(peer_ready.get(peer, False) for peer in peers):
        if time.time() > timeout:
            return jsonify({"status": "Timeout waiting for peers"}), 408
        time.sleep(0.1)
    simulation_started.set()
    return jsonify({"status": "Simulation started"})

start_time = None

@app.route('/sync_start', methods=['POST'])
def sync_start():
    global start_time, peers
    data = request.json
    start_time = data.get('start_time')
    peers = data.get('peers', [])
    if start_time and peers:
        logging.info(f"Sync start received. Start time: {start_time}, Peers: {peers}")
        return jsonify({"status": "start time and peers set", "start_time": start_time, "peers": peers})
    else:
        logging.warning("Invalid start time or peers in sync_start request")
        return jsonify({"error": "Invalid start time or peers"}), 400

simulation_start_time = None

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    global simulation_start_time
    data = request.json
    simulation_start_time = data.get('start_time')
    if simulation_start_time:
        simulation_started.set()
        return jsonify({"status": "Simulation started"})
    else:
        return jsonify({"error": "Invalid start time"}), 400

@app.route('/get_data', methods=['GET'])
def get_data():
    global energy_data
    try:
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error getting data: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/get_peer_data', methods=['GET'])
def get_peer_data():
    try:
        # Return data for the peer IP
        peer_ip = request.remote_addr
        if peer_ip in peer_data:
            return jsonify(peer_data[peer_ip])
        else:
            logging.warning(f"No data available for peer {peer_ip}")
            return jsonify({"error": "No data available"}), 404
    except Exception as e:
        logging.error(f"Error getting peer data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/wait_for_start', methods=['GET'])
def wait_for_start():
    if simulation_started.wait(timeout=30):  # Wait up to 30 seconds
        return jsonify({"status": "Simulation started"})
    else:
        return jsonify({"status": "Timeout waiting for simulation to start"}), 408

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "peer_data": bool(peer_data), "peers": peers})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)