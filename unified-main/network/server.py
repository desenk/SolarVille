# Branch: unified-main
# File: network/server.py

"""
Enhanced Flask server for SolarVille system.
Supports multi-peer architecture with routes for energy data, trading, and network management.
"""

import logging
import threading
import time
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, Response
from typing import Dict, Any, Optional, List

from core.config import ConfigManager
from core.device_types import PiDevice
from core.energy_types import EnergyReading, ProsumerReading
from core.trade_types import TradeOffer, TradeRequest, TradeMatch

class ServerError(Exception):
    """Base exception for server-related errors"""
    pass

class Server:
    """
    Flask server for SolarVille network communications.
    Handles API endpoints for energy data, trading, and network management.
    """
    
    def __init__(self, config_manager: ConfigManager, trading_manager=None):
        """
        Initialize the server.
        
        Args:
            config_manager: Configuration manager
            trading_manager: Trading Manager instance (optional)
        """
        self.config = config_manager
        self.trading_manager = trading_manager
        self.logger = logging.getLogger(__name__)
        self.app = Flask(__name__)
        
        # Data storage
        self.peer_data: Dict[str, Dict[str, Any]] = {}
        self.trade_data: Dict[str, List[Dict[str, Any]]] = {}
        self.simulation_data = {
            "status": "not_started",
            "current_timestamp": None,
            "start_time": None,
            "end_time": None
        }
        
        # Server status
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Setup routes
        self._setup_routes()
        
        self.logger.info("Server initialized")
    
    def register_trading_manager(self, trading_manager):
        """
        Register a trading manager with the server.
        
        Args:
            trading_manager: Trading Manager instance
        """
        self.trading_manager = trading_manager
        self.logger.info("Trading Manager registered with server")
    
    def _setup_routes(self) -> None:
        """Setup Flask routes for the server."""
        # Health check endpoint
        @self.app.route('/health', methods=['GET'])
        def health_check() -> Response:
            """Health check endpoint."""
            local_device = self.config.get_local_device()
            if not local_device:
                return jsonify({
                    "status": "error",
                    "message": "Local device not configured"
                })
                
            return jsonify({
                "status": "healthy",
                "device_name": local_device.name,
                "is_prosumer": local_device.is_prosumer,
                "simulation_status": self.simulation_data["status"]
            })
        
        # Peer information endpoint
        @self.app.route('/peer_info', methods=['GET'])
        def peer_info() -> Response:
            """Return information about this peer."""
            local_device = self.config.get_local_device()
            if not local_device:
                return jsonify({
                    "status": "error",
                    "message": "Local device not configured"
                })
                
            return jsonify({
                "status": "success",
                "name": local_device.name,
                "is_prosumer": local_device.is_prosumer,
                "hostname": local_device.hostname,
                "location": getattr(local_device, "location", "unknown")
            })
        
        # Energy data endpoint
        @self.app.route('/energy_data', methods=['GET', 'POST'])
        def energy_data() -> Response:
            """Handle energy data requests and updates."""
            if request.method == 'GET':
                # Return current energy data
                return jsonify({
                    "status": "success",
                    "data": self.peer_data
                })
                
            elif request.method == 'POST':
                try:
                    data = request.json
                    peer_ip = request.remote_addr
                    
                    # Validate data
                    required_fields = ['timestamp', 'demand', 'balance']
                    for field in required_fields:
                        if field not in data:
                            return jsonify({
                                "status": "error",
                                "message": f"Missing required field: {field}"
                            }), 400
                    
                    # Store data
                    if peer_ip not in self.peer_data:
                        self.peer_data[peer_ip] = {}
                    self.peer_data[peer_ip].update(data)
                    
                    self.logger.debug(f"Updated energy data from {peer_ip}")
                    
                    return jsonify({"status": "success"})
                    
                except Exception as e:
                    self.logger.error(f"Error processing energy data: {str(e)}")
                    return jsonify({
                        "status": "error",
                        "message": str(e)
                    }), 500
        
        # Trade endpoint
        @self.app.route('/trade', methods=['GET', 'POST'])
        def trade() -> Response:
            """Handle trade requests and updates."""
            if request.method == 'GET':
                # Return trade history
                return jsonify({
                    "status": "success",
                    "trades": self.trade_data
                })
                
            elif request.method == 'POST':
                try:
                    data = request.json
                    peer_ip = request.remote_addr
                    
                    # Validate trade data
                    required_fields = ['timestamp', 'amount', 'price']
                    for field in required_fields:
                        if field not in data:
                            return jsonify({
                                "status": "error",
                                "message": f"Missing required field: {field}"
                            }), 400
                    
                    # Store trade data
                    if peer_ip not in self.trade_data:
                        self.trade_data[peer_ip] = []
                    
                    # Add current trade
                    trade_record = {
                        "timestamp": data["timestamp"],
                        "amount": data["amount"],
                        "price": data["price"],
                        "recorded_at": datetime.now().isoformat()
                    }
                    self.trade_data[peer_ip].append(trade_record)
                    
                    self.logger.info(
                        f"Recorded trade from {peer_ip}: "
                        f"Amount: {data['amount']} kWh, "
                        f"Price: £{data['price']}/kWh"
                    )
                    
                    return jsonify({"status": "success"})
                    
                except Exception as e:
                    self.logger.error(f"Error processing trade: {str(e)}")
                    return jsonify({
                        "status": "error",
                        "message": str(e)
                    }), 500
        
        # Simulation status endpoint
        @self.app.route('/simulation', methods=['GET', 'POST'])
        def simulation() -> Response:
            """Handle simulation status updates and queries."""
            if request.method == 'GET':
                # Return current simulation status
                return jsonify({
                    "status": "success",
                    "simulation": self.simulation_data
                })
                
            elif request.method == 'POST':
                try:
                    data = request.json
                    
                    # Update simulation status
                    if 'status' in data:
                        self.simulation_data["status"] = data["status"]
                    
                    if 'timestamp' in data:
                        self.simulation_data["current_timestamp"] = data["timestamp"]
                        
                        # Update start and end times as appropriate
                        if data["timestamp"] == "START":
                            self.simulation_data["start_time"] = datetime.now().isoformat()
                            self.simulation_data["status"] = "starting"
                        elif data["timestamp"] == "END":
                            self.simulation_data["end_time"] = datetime.now().isoformat()
                            self.simulation_data["status"] = "completed"
                        else:
                            self.simulation_data["status"] = "in_progress"
                    
                    self.logger.debug(f"Updated simulation status: {self.simulation_data['status']}")
                    return jsonify({"status": "success"})
                    
                except Exception as e:
                    self.logger.error(f"Error updating simulation status: {str(e)}")
                    return jsonify({
                        "status": "error",
                        "message": str(e)
                    }), 500
        
        # Synchronization endpoint
        @self.app.route('/sync', methods=['POST'])
        def sync() -> Response:
            """Synchronize timestamps between peers."""
            try:
                data = request.json
                
                if 'timestamp' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Missing timestamp"
                    }), 400
                
                # Update timestamp
                self.simulation_data["current_timestamp"] = data["timestamp"]
                
                # Update simulation status based on timestamp
                if data["timestamp"] == "START":
                    self.simulation_data["status"] = "starting"
                    self.simulation_data["start_time"] = datetime.now().isoformat()
                    self.logger.info("Received START signal")
                elif data["timestamp"] == "END":
                    self.simulation_data["status"] = "completed"
                    self.simulation_data["end_time"] = datetime.now().isoformat()
                    self.logger.info("Received END signal")
                else:
                    if self.simulation_data["status"] != "in_progress":
                        self.simulation_data["status"] = "in_progress"
                    self.logger.debug(f"Synced to timestamp: {data['timestamp']}")
                
                return jsonify({"status": "synced"})
                
            except Exception as e:
                self.logger.error(f"Error syncing timestamp: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
                
        # ============= New Trading System Endpoints =============
        
        # Trade offer endpoint
        @self.app.route('/trade/offer', methods=['POST'])
        def trade_offer() -> Response:
            """Handle a new trade offer from a peer."""
            try:
                if not self.trading_manager:
                    return jsonify({
                        "status": "error",
                        "message": "Trading Manager not registered"
                    }), 500
                    
                data = request.json
                peer_ip = request.remote_addr
                
                # Validate required fields
                if 'id' not in data or 'offer' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Missing required fields"
                    }), 400
                
                # Get offer data
                offer_id = data['id']
                offer_data = data['offer']
                
                # Create offer object
                try:
                    offer = TradeOffer.from_dict(offer_data)
                except Exception as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid offer data: {str(e)}"
                    }), 400
                
                # Add to trading manager
                # Note: We're using create_task instead of awaiting directly
                # since Flask doesn't support async views without additional libraries
                asyncio.run(self.trading_manager.handle_peer_offer(offer_id, offer))
                
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"Error processing trade offer: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500

        # Trade request endpoint
        @self.app.route('/trade/request', methods=['POST'])
        def trade_request() -> Response:
            """Handle a new trade request from a peer."""
            try:
                if not self.trading_manager:
                    return jsonify({
                        "status": "error",
                        "message": "Trading Manager not registered"
                    }), 500
                    
                data = request.json
                peer_ip = request.remote_addr
                
                # Validate required fields
                if 'id' not in data or 'request' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Missing required fields"
                    }), 400
                
                # Get request data
                request_id = data['id']
                request_data = data['request']
                
                # Create request object
                try:
                    trade_request = TradeRequest.from_dict(request_data)
                except Exception as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid request data: {str(e)}"
                    }), 400
                
                # Add to trading manager
                asyncio.run(self.trading_manager.handle_peer_request(request_id, trade_request))
                
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"Error processing trade request: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500

        # Trade completion endpoint
        @self.app.route('/trade/completion', methods=['POST'])
        def trade_completion() -> Response:
            """Handle a trade completion notification."""
            try:
                if not self.trading_manager:
                    return jsonify({
                        "status": "error",
                        "message": "Trading Manager not registered"
                    }), 500
                    
                data = request.json
                peer_ip = request.remote_addr
                
                # Validate required fields
                if 'id' not in data or 'trade' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Missing required fields"
                    }), 400
                
                # Get trade data
                match_id = data['id']
                trade_data = data['trade']
                
                # Create trade match object
                try:
                    trade_match = TradeMatch.from_dict(trade_data)
                except Exception as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid trade data: {str(e)}"
                    }), 400
                
                # Update trade status in trading manager
                # For now just log it - in a full implementation we would update the status
                self.logger.info(f"Received trade completion notification for {match_id}")
                
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"Error processing trade completion: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500

        # Trade status endpoint
        @self.app.route('/trade/status', methods=['GET'])
        def trade_status() -> Response:
            """Get current trading status."""
            try:
                if not self.trading_manager:
                    return jsonify({
                        "status": "error",
                        "message": "Trading Manager not registered"
                    }), 500
                    
                status = self.trading_manager.get_trade_status()
                return jsonify({
                    "status": "success",
                    "trading_status": status
                })
                
            except Exception as e:
                self.logger.error(f"Error retrieving trade status: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
    
    def start(self, host: str = '0.0.0.0', port: Optional[int] = None) -> None:
        """
        Start the server in a background thread.
        
        Args:
            host: Host to listen on
            port: Port to listen on (uses config value if None)
        """
        if self.is_running:
            self.logger.warning("Server already running")
            return
            
        # Use configured port if none specified
        if port is None:
            port = self.config.server_port
            
        # Start in a background thread
        self.is_running = True
        self.server_thread = threading.Thread(
            target=self._run_server,
            args=(host, port),
            daemon=True
        )
        self.server_thread.start()
        
        # Wait a moment for the server to start
        time.sleep(0.5)
        
        # Check if server started successfully
        if not self.is_running:
            raise ServerError("Failed to start server")
            
        self.logger.info(f"Server started on {host}:{port}")
    
    def _run_server(self, host: str, port: int) -> None:
        """
        Run the Flask server.
        
        Args:
            host: Host to listen on
            port: Port to listen on
        """
        try:
            self.app.run(host=host, port=port, debug=False, use_reloader=False)
        except Exception as e:
            self.logger.error(f"Server error: {str(e)}")
            self.is_running = False
    
    def stop(self) -> None:
        """Stop the server."""
        if not self.is_running:
            self.logger.warning("Server not running")
            return
            
        self.is_running = False
        
        # Server shutdown logic here
        # This is a simplified version - in a real implementation
        # we would need to use Flask's shutdown mechanism
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)
            if self.server_thread.is_alive():
                self.logger.warning("Server thread did not terminate cleanly")
                
        self.logger.info("Server stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current server status.
        
        Returns:
            Dictionary with server status information
        """
        return {
            "running": self.is_running,
            "peer_count": len(self.peer_data),
            "trade_count": sum(len(trades) for trades in self.trade_data.values()),
            "simulation_status": self.simulation_data["status"]
        }

# This is the Flask application instance that will be imported by other modules
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def default_health_check():
    """Default health check endpoint."""
    return jsonify({"status": "healthy"})