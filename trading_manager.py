# Branch: consumerJack
# File: trading_manager.py

import requests
import logging
from energy_types import TradeData, EnergyReading
from config import PEER_IP, LOCAL_IP

class TradingManager:
    def __init__(self, is_prosumer: bool):
        # We ignore is_prosumer since this is the consumer branch
        self.peer_ip = PEER_IP
        # Constants for pricing
        self.grid_buy_price = 0.25  # £/kWh
        self.grid_sell_price = 0.05  # £/kWh

    def process_trade(self, reading: EnergyReading) -> TradeData:
        """Process trade for consumer"""
        try:
            # Get peer (prosumer) data
            peer_response = requests.get(f'http://{self.peer_ip}:5000/get_peer_data')
            if peer_response.status_code != 200:
                logging.error("Failed to get peer data")
                return None

            peer_data = peer_response.json()
            peer_available = peer_data.get('balance', 0)
            peer_price = peer_data.get('peer_price', self.grid_buy_price)

            if peer_available > 0 and abs(reading.balance) > 0:
                # Can trade with peer
                trade_amount = min(peer_available, abs(reading.balance))
                return TradeData(
                    amount=-trade_amount,  # Negative as consumer is buying
                    price=peer_price
                )
            else:
                # Must buy from grid
                return TradeData(
                    amount=-abs(reading.balance),  # Negative as consumer is buying
                    price=self.grid_buy_price
                )

        except Exception as e:
            logging.error(f"Error in trade processing: {e}")
            return None

    def _update_peer_data(self, reading: EnergyReading):
        """Send current status to peer"""
        try:
            data = {
                'demand': reading.demand,
                'balance': reading.balance
            }
            
            requests.post(
                f'http://{self.peer_ip}:5000/update_peer_data',
                json=data,
                timeout=5
            )
        except Exception as e:
            logging.error(f"Failed to update peer data: {e}")

    def _log_trade(self, trade: TradeData):
        """Log trade details"""
        amount = abs(trade.amount)
        total_cost = amount * trade.price
        logging.info(
            f"Buying {amount:.3f} kWh at £{trade.price:.3f}/kWh "
            f"(Total: £{total_cost:.3f})"
        )