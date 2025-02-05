# trading_manager.py
import requests
import logging
from typing import Optional, Dict, Union
from energy_types import TradeData, EnergyReading
from datetime import datetime

class TradingManager:
    def __init__(self, is_prosumer: bool, peer_url: str):
        """Initialize Trading Manager.
        
        Args:
            is_prosumer: Boolean indicating if this is a prosumer
            peer_url: URL for peer's trading endpoint
        """
        self.is_prosumer = is_prosumer
        self.peer_url = peer_url
        self.session = requests.Session()
        self.session.timeout = 5  # 5 second timeout
        
        # Dynamic pricing configuration
        self.base_grid_buy_price = 0.30  # £/kWh - Standard rate for buying from grid
        self.base_grid_sell_price = 0.17  # £/kWh - Feed-in tariff rate for selling back
        self.max_p2p_price = self.base_grid_buy_price
        self.min_p2p_price = self.base_grid_sell_price

    def calculate_grid_prices(self, time: datetime) -> tuple[float, float]:
        """Calculate dynamic grid prices based on time of day.
        
        Args:
            time: Current timestamp
        
        Returns:
            Tuple of (buy_price, sell_price)
        """
        hour = time.hour
        
        # Higher prices during peak hours (7-9am and 4-8pm)
        peak_multiplier = 1.5 if (7 <= hour <= 9) or (16 <= hour <= 20) else 1.0
        
        buy_price = self.base_grid_buy_price * peak_multiplier
        sell_price = self.base_grid_sell_price * peak_multiplier
        
        return buy_price, sell_price

    def calculate_p2p_price(self, total_demand: float, total_supply: float) -> float:
        """Calculate peer-to-peer trading price based on supply-demand ratio.
        
        Args:
            total_demand: Total energy demand
            total_supply: Total energy supply
            
        Returns:
            Calculated price per kWh
        """
        if total_supply <= 0:
            return self.max_p2p_price

        # Calculate supply-demand ratio
        ratio = total_demand / total_supply
        
        if ratio <= 0:
            return self.min_p2p_price
        elif ratio >= 1:
            return self.max_p2p_price
        else:
            # Linear interpolation between min and max price
            return self.min_p2p_price + (self.max_p2p_price - self.min_p2p_price) * ratio

    def get_peer_data(self) -> Optional[Dict]:
        """Get current peer status from server.
        
        Returns:
            Dictionary of peer data or None if request fails
        """
        try:
            response = self.session.get(f"{self.peer_url}/get_peer_data")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to get peer data: {e}")
            return None

    def process_trade(self, reading: EnergyReading) -> Optional[TradeData]:
        """Process trade based on current readings and peer status.
        
        Args:
            reading: Current energy reading
            
        Returns:
            TradeData object if trade is possible, None otherwise
        """
        try:
            # Get peer data
            peer_data = self.get_peer_data()
            if not peer_data:
                return None

            # Extract peer info
            peer_demand = peer_data.get('demand', 0)
            peer_balance = peer_data.get('balance', 0)
            
            # Calculate current grid prices
            grid_buy_price, grid_sell_price = self.calculate_grid_prices(reading.timestamp)
            
            # Calculate total supply and demand
            total_demand = abs(reading.balance) + abs(peer_balance) if reading.balance < 0 else abs(peer_balance)
            total_supply = reading.balance if reading.balance > 0 else peer_balance if peer_balance > 0 else 0
            
            # Calculate P2P price
            p2p_price = self.calculate_p2p_price(total_demand, total_supply)

            if self.is_prosumer:
                return self._process_prosumer_trade(reading, peer_balance, p2p_price, grid_buy_price, grid_sell_price)
            else:
                return self._process_consumer_trade(reading, peer_balance, p2p_price, grid_buy_price)

        except Exception as e:
            logging.error(f"Error processing trade: {e}")
            return None

    def _process_prosumer_trade(
        self, reading: EnergyReading, peer_balance: float, 
        p2p_price: float, grid_buy_price: float, grid_sell_price: float
    ) -> Optional[TradeData]:
        """Process trade from prosumer perspective."""
        if reading.balance >= 0:  # Prosumer has excess energy
            if peer_balance >= 0:  # Peer doesn't need energy
                # Sell excess to grid
                return TradeData(amount=reading.balance, price=grid_sell_price,
                               grid_buy_price=grid_buy_price, grid_sell_price=grid_sell_price)
            else:  # Peer needs energy
                # Trade the minimum of excess and peer's need
                trade_amount = min(reading.balance, abs(peer_balance))
                return TradeData(amount=trade_amount, price=p2p_price,
                               grid_buy_price=grid_buy_price, grid_sell_price=grid_sell_price)
        else:  # Prosumer needs energy
            # Buy from grid
            return TradeData(amount=-abs(reading.balance), price=grid_buy_price,
                           grid_buy_price=grid_buy_price, grid_sell_price=grid_sell_price)

    def _process_consumer_trade(
        self, reading: EnergyReading, peer_balance: float,
        p2p_price: float, grid_buy_price: float
    ) -> Optional[TradeData]:
        """Process trade from consumer perspective."""
        if peer_balance > 0 and abs(reading.balance) > 0:
            # Can trade with peer
            trade_amount = min(peer_balance, abs(reading.balance))
            return TradeData(amount=-trade_amount, price=p2p_price,
                           grid_buy_price=grid_buy_price, grid_sell_price=0)
        else:
            # Must buy from grid
            return TradeData(amount=-abs(reading.balance), price=grid_buy_price,
                           grid_buy_price=grid_buy_price, grid_sell_price=0)

    def update_peer(self, reading: EnergyReading) -> bool:
        """Send current status to peer.
        
        Args:
            reading: Current energy reading
            
        Returns:
            Boolean indicating success
        """
        try:
            data = {
                'demand': reading.demand,
                'balance': reading.balance,
            }
            response = self.session.post(
                f"{self.peer_url}/update_peer_data",
                json=data,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to update peer: {e}")
            return False

    def notify_trade_completion(self, trade: TradeData) -> bool:
        """Notify peer of completed trade.
        
        Args:
            trade: Completed trade data
            
        Returns:
            Boolean indicating success
        """
        try:
            data = {
                'trade_amount': trade.amount,
                'price': trade.price,
                'grid_buy_price': trade.grid_buy_price,
                'grid_sell_price': trade.grid_sell_price
            }
            response = self.session.post(
                f"{self.peer_url}/update_trade_data",
                json=data,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to notify trade completion: {e}")
            return False