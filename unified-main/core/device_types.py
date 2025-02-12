"""Device-related data structures for the SolarVille system."""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class PiDevice:
    """Represents a Raspberry Pi device in the network"""
    name: str
    ip_address: str
    is_prosumer: bool
    hostname: str
    location: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "ip_address": self.ip_address,
            "is_prosumer": self.is_prosumer,
            "hostname": self.hostname,
            "location": self.location
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PiDevice':
        return cls(
            name=data["name"],
            ip_address=data["ip_address"],
            is_prosumer=data["is_prosumer"],
            hostname=data["hostname"],
            location=data.get("location")
        )