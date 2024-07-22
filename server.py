from flask import Flask, request, jsonify
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Shared data for the example
energy_data = {
    "balance": 0,
    "currency": 100.0,
    "demand": 0,
    "generation": 0
}

simulation_start_time = None

@app.route('/sync_start', methods=['POST'])
def sync_start():
    global simulation_start_time
    data = request.json
    if 'start_time' in data:
        simulation_start_time = data['start_time']
        return jsonify({"status": "success", "start_time": simulation_start_time})
    else:
        return jsonify({"status": "error", "message": "No start time provided"}), 400

@app.route('/get_start_time', methods=['GET'])
def get_start_time():
    global simulation_start_time
    if simulation_start_time:
        return jsonify({"start_time": simulation_start_time})
    else:
        return jsonify({"status": "error", "message": "Start time not set"}), 404

@app.route('/start', methods=['POST'])
def start():
    return jsonify({"status": "Simulation already running"})

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    return jsonify({"status": "Simulation already running"})

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)