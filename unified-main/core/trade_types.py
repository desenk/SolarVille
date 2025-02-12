"""Trade-related data structures for the SolarVille system."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class TradeData:
    """Represents an energy trade between devices"""
    timestamp: datetime
    seller_id: str
    buyer_id: str
    amount: float             # kWh - amount of energy to trade
    price: float             # £/kWh - price per unit
    status: str = "pending"   # pending, completed, failed
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "seller_id": self.seller_id,
            "buyer_id": self.buyer_id,
            "amount": self.amount,
            "price": self.price,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeData':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            seller_id=data["seller_id"],
            buyer_id=data["buyer_id"],
            amount=data["amount"],
            price=data["price"],
            status=data.get("status", "pending")
        )