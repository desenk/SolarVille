# Branch: ProsumerJack
# File: trading_manager.py

import requests
import logging
from energy_types import TradeData, EnergyReading, ProsumerReading
from config import PEER_IP, LOCAL_IP

class TradingManager:
    def __init__(self, is_prosumer: bool):
        self.is_prosumer = is_prosumer
        self.current_trade = None
        self.peer_ip = PEER_IP
        # Constants for pricing
        self.grid_buy_price = 0.25  # £/kWh
        self.grid_sell_price = 0.05  # £/kWh

    def calculate_trade_price(self, total_demand: float, total_supply: float) -> float:
        """Calculate P2P trading price based on supply-demand ratio"""
        if total_supply <= 0:
            return self.grid_buy_price

        sdr = total_demand / total_supply
        if sdr <= 0:
            return self.grid_sell_price
        elif sdr >= 1:
            return self.grid_buy_price
        else:
            return self.grid_sell_price * (1 - sdr) + self.grid_buy_price * sdr

    def _process_prosumer_trade(self, reading: ProsumerReading) -> TradeData:
        """Handle trading logic for prosumer"""
        try:
            # Get peer (consumer) data
            peer_response = requests.get(f'http://{self.peer_ip}:5000/get_peer_data')
            if peer_response.status_code != 200:
                logging.error("Failed to get peer data")
                return None

            peer_data = peer_response.json()
            peer_demand = peer_data.get('demand', 0)
            peer_balance = peer_data.get('balance', 0)

            total_demand = reading.demand + peer_demand
            total_supply = reading.generation

            # Calculate price based on supply and demand
            price = self.calculate_trade_price(total_demand, total_supply)

            if reading.balance >= 0:  # Prosumer has excess energy
                if peer_balance >= 0:  # Peer doesn't need energy
                    # No trade needed, all excess goes to grid
                    return TradeData(amount=0, price=self.grid_sell_price)
                else:  # Peer needs energy
                    trade_amount = min(reading.balance, abs(peer_balance))
                    return TradeData(amount=trade_amount, price=price)
            else:  # Prosumer needs energy
                # Buy from grid, no peer trading
                return TradeData(amount=-abs(reading.balance), price=self.grid_buy_price)

        except Exception as e:
            logging.error(f"Error in prosumer trade processing: {e}")
            return None

    def _process_consumer_trade(self, reading: EnergyReading) -> TradeData:
        """Handle trading logic for consumer"""
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
                return TradeData(amount=-trade_amount, price=peer_price)
            else:
                # Must buy from grid
                return TradeData(amount=-abs(reading.balance), price=self.grid_buy_price)

        except Exception as e:
            logging.error(f"Error in consumer trade processing: {e}")
            return None

    def process_trade(self, reading: EnergyReading) -> TradeData:
        """Main trade processing method"""
        # Update peer with current status
        self._update_peer_data(reading)

        # Process trade based on role
        if self.is_prosumer:
            trade_result = self._process_prosumer_trade(reading)
        else:
            trade_result = self._process_consumer_trade(reading)

        # Log trade result
        if trade_result:
            self._log_trade(trade_result)
            self._update_trade_data(trade_result)

        return trade_result

    def _update_peer_data(self, reading: EnergyReading):
        """Send current status to peer"""
        data = {
            'demand': reading.demand,
            'balance': reading.balance,
        }
        if isinstance(reading, ProsumerReading):
            data.update({
                'generation': reading.generation,
                'battery_soc': reading.battery_soc
            })

        try:
            requests.post(
                f'http://{self.peer_ip}:5000/update_peer_data',
                json=data,
                timeout=5
            )
        except Exception as e:
            logging.error(f"Failed to update peer data: {e}")

    def _update_trade_data(self, trade: TradeData):
        """Send trade data to peer"""
        try:
            requests.post(
                f'http://{self.peer_ip}:5000/update_trade_data',
                json={
                    'trade_amount': trade.amount,
                    'price': trade.price,
                    'grid_buy_price': self.grid_buy_price,
                    'grid_sell_price': self.grid_sell_price
                },
                timeout=5
            )
        except Exception as e:
            logging.error(f"Failed to update trade data: {e}")

    def _log_trade(self, trade: TradeData):
        """Log trade details"""
        direction = "Selling" if trade.amount > 0 else "Buying"
        amount = abs(trade.amount)
        total_cost = amount * trade.price
        logging.info(
            f"{direction} {amount:.3f} kWh at £{trade.price:.3f}/kWh "
            f"(Total: £{total_cost:.3f})"
        )