# Branch: unified-main
# File: trade_types.py
"""Trade-related data structures for the SolarVille system."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

@dataclass
class TradeOffer:
    """Energy a device wants to sell"""
    timestamp: datetime
    seller_id: str
    amount: float         # kWh available to sell
    min_price: float      # Minimum acceptable price per kWh
    expiry: datetime      # When this offer expires
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "seller_id": self.seller_id,
            "amount": self.amount,
            "min_price": self.min_price,
            "expiry": self.expiry.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeOffer':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            seller_id=data["seller_id"],
            amount=data["amount"],
            min_price=data["min_price"],
            expiry=datetime.fromisoformat(data["expiry"])
        )
    
@dataclass
class TradeRequest:
    """Energy a device wants to buy"""
    timestamp: datetime
    buyer_id: str
    amount: float         # kWh wanted to buy
    max_price: float      # Maximum acceptable price per kWh
    priority: int = 0     # Priority level (higher = more urgent)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "buyer_id": self.buyer_id,
            "amount": self.amount,
            "max_price": self.max_price,
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeRequest':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            buyer_id=data["buyer_id"],
            amount=data["amount"],
            max_price=data["max_price"],
            priority=data.get("priority", 0)
        )

@dataclass
class TradeMatch:
    """A matched trade between seller and buyer"""
    offer_id: str
    request_id: str
    seller_id: str
    buyer_id: str
    amount: float         # kWh to be traded
    price: float          # Price per kWh
    status: str = "pending"  # pending/confirmed/completed/failed
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "offer_id": self.offer_id,
            "request_id": self.request_id,
            "seller_id": self.seller_id,
            "buyer_id": self.buyer_id,
            "amount": self.amount,
            "price": self.price,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeMatch':
        return cls(
            offer_id=data["offer_id"],
            request_id=data["request_id"],
            seller_id=data["seller_id"],
            buyer_id=data["buyer_id"],
            amount=data["amount"],
            price=data["price"],
            status=data.get("status", "pending"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )