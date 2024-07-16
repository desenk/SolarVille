from flask import Flask, request, jsonify
import requests

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
    data = request.json
    energy_data['balance'] += data.get('amount', 0)
    return jsonify(energy_data)

@app.route('/update_demand', methods=['POST'])
def update_demand():
    global energy_data
    data = request.json
    energy_data['demand'] = data.get('demand', 0)
    return jsonify(energy_data)

@app.route('/update_generation', methods=['POST'])
def update_generation():
    global energy_data
    data = request.json
    energy_data['generation'] = data.get('generation', 0)
    return jsonify(energy_data)

@app.route('/get_data', methods=['GET'])
def get_data():
    global energy_data
    return jsonify(energy_data)

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    peers = request.json.get('peers', [])
    for peer in peers:
        response = requests.post(f'http://{peer}:5000/start')
        if response.status_code != 200:
            logging.error(f"Failed to start simulation on peer {peer}")
    return jsonify({"status": "Simulation started on all peers"})

@app.route('/sync', methods=['POST'])
def sync():
    global energy_data
    data = request.json
    energy_data.update(data)
    return jsonify(energy_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)