# Branch: ProsumerJack
# File: server.py
from flask import Flask, request, jsonify
import logging
from threading import Event
from config import PEER_IP
from energy_types import TradeData, EnergyReading

app = Flask(__name__)

# Global state storage
peer_data = {}
current_timestamp = None
simulation_ended = Event()

@app.route('/get_peer_data', methods=['GET'])
def get_peer_data():
    """
    Endpoint for getting peer's current status
    Returns: {
        'demand': float,
        'balance': float,
        'generation': float,  # prosumer only
        'battery_soc': float  # prosumer only
    }
    """
    try:
        return jsonify(peer_data)
    except Exception as e:
        logging.error(f"Error serving peer data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_peer_data', methods=['POST'])
def update_peer_data():
    """
    Endpoint for receiving peer's current status
    Expects: {
        'demand': float,
        'balance': float,
        'generation': float,  # prosumer only
        'battery_soc': float  # prosumer only
    }
    """
    try:
        data = request.json
        peer_ip = request.remote_addr
        
        # Update stored peer data
        if peer_ip not in peer_data:
            peer_data[peer_ip] = {}
        peer_data[peer_ip].update(data)
        
        logging.info(f"Updated peer data from {peer_ip}: "
                    f"Demand: {data.get('demand', 'N/A')}kWh, "
                    f"Balance: {data.get('balance', 'N/A')}kWh")
        
        return jsonify({"status": "updated"})
    except Exception as e:
        logging.error(f"Error updating peer data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_trade_data', methods=['POST'])
def update_trade_data():
    """
    Endpoint for receiving trade information
    Expects: {
        'trade_amount': float,
        'price': float,
        'grid_buy_price': float,
        'grid_sell_price': float
    }
    """
    try:
        data = request.json
        peer_ip = request.remote_addr
        
        # Update stored trade data
        if peer_ip not in peer_data:
            peer_data[peer_ip] = {}
        peer_data[peer_ip].update(data)
        
        trade_amount = data.get('trade_amount', 'N/A')
        price = data.get('price', 'N/A')
        
        logging.info(
            f"Trade data from {peer_ip}: "
            f"Amount: {trade_amount} kWh, "
            f"Price: £{price}/kWh"
        )
        
        return jsonify({"status": "updated"})
    except Exception as e:
        logging.error(f"Error updating trade data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/simulation_status', methods=['GET'])
def get_simulation_status():
    """
    Endpoint for checking simulation status
    Returns: {
        'status': 'completed'|'starting'|'in_progress'|'not_started',
        'current_timestamp': timestamp if in_progress
    }
    """
    if simulation_ended.is_set():
        return jsonify({"status": "completed"})
    elif current_timestamp == 'START':
        return jsonify({"status": "starting"})
    elif current_timestamp:
        return jsonify({
            "status": "in_progress", 
            "current_timestamp": current_timestamp
        })
    else:
        return jsonify({"status": "not_started"})

@app.route('/sync', methods=['POST'])
def sync():
    """
    Endpoint for synchronizing timestamps between peers
    Expects: {
        'timestamp': string
    }
    """
    global current_timestamp
    data = request.json
    current_timestamp = data['timestamp']
    
    if current_timestamp == 'END':
        simulation_ended.set()
        logging.info("Received END signal. Simulation completed.")
    elif current_timestamp == 'START':
        logging.info("Received START signal. Simulation beginning.")
    else:
        logging.info(f"Synced to timestamp: {current_timestamp}")
    
    return jsonify({"status": "synced"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)