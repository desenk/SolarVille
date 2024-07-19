from flask import Flask, request, jsonify
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


app = Flask(__name__)

# Shared data for the example
energy_data = {
    "balance": 0,
    "currency": 100.0,
    "demand": 0,
    "generation": 0
}

@app.route('/update_balance', methods=['POST'])
def update_balance():
    global energy_data
    try:
        data = request.json
        energy_data['balance'] += data.get('amount', 0)
        logging.info(f"Balance updated: {energy_data['balance']}")
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error updating balance: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/update_demand', methods=['POST'])
def update_demand():
    global energy_data
    try:
        data = request.json
        energy_data['demand'] = data.get('demand', 0)
        logging.info(f"Demand updated: {energy_data['demand']}")
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error updating demand: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/update_generation', methods=['POST'])
def update_generation():
    global energy_data
    try:
        data = request.json
        energy_data['generation'] = data.get('generation', 0)
        logging.info(f"Generation updated: {energy_data['generation']}")
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error updating generation: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/get_data', methods=['GET'])
def get_data():
    global energy_data
    try:
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error getting data: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    peers = request.json.get('peers', [])
    for peer in peers:
        response = requests.post(f'http://{peer}:5000/start_simulation')
        if response.status_code != 200:
            logging.error(f"Failed to start simulation on peer {peer}")
    return jsonify({"status": "Simulation started on all peers"})

@app.route('/sync', methods=['POST'])
def sync():
    global energy_data
    try:
        data = request.json
        energy_data.update(data)
        logging.info(f"Synced data: {energy_data}")
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error syncing data: {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)