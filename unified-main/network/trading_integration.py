# Branch: unified-main
# File: trading_integration.py
"""Trading integration for SolarVille system.
Handles network communication for trade offers, requests, and notifications.
"""

import logging
from typing import Dict, Any, Optional

from core.trade_types import TradeOffer, TradeRequest, TradeMatch
from network.network_manager import NetworkManager

class TradingIntegration:
    """
    Handles network communication for trade offers, requests, and notifications.
    """
    
    def __init__(self, network_manager: NetworkManager):
        """
        Initialize Trading Integration.
        
        Args:
            network_manager: Network Manager instance
        """
        self.network = network_manager
        self.logger = logging.getLogger(__name__)
        
    async def publish_offer(self, offer_id: str, offer: TradeOffer) -> bool:
        """
        Publish an offer to peers.
        
        Args:
            offer_id: Offer ID
            offer: Trade offer object
            
        Returns:
            True if published successfully
        """
        try:
            # Prepare data for network
            data = {
                "type": "offer",
                "id": offer_id,
                "offer": offer.to_dict()
            }
            
            # Broadcast to all peers
            responses = self.network.broadcast(
                endpoint="/trade/offer",
                data=data
            )
            
            success_count = sum(1 for resp in responses.values() if "error" not in resp)
            self.logger.debug(f"Published offer {offer_id} to {success_count} peers")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Error publishing offer: {e}")
            return False
    
    async def publish_request(self, request_id: str, request: TradeRequest) -> bool:
        """
        Publish a request to peers.
        
        Args:
            request_id: Request ID
            request: Trade request object
            
        Returns:
            True if published successfully
        """
        try:
            # Prepare data for network
            data = {
                "type": "request",
                "id": request_id,
                "request": request.to_dict()
            }
            
            # Broadcast to all peers
            responses = self.network.broadcast(
                endpoint="/trade/request",
                data=data
            )
            
            success_count = sum(1 for resp in responses.values() if "error" not in resp)
            self.logger.debug(f"Published request {request_id} to {success_count} peers")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Error publishing request: {e}")
            return False
    
    async def notify_trade_completion(self, peer_id: str, match_id: str, trade_match: TradeMatch) -> bool:
        """
        Notify a peer about a completed trade.
        
        Args:
            peer_id: ID of the peer to notify
            match_id: Match ID
            trade_match: Trade match object
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Prepare data
            data = {
                "type": "trade_completion",
                "id": match_id,
                "trade": trade_match.to_dict()
            }
            
            # Get peer device
            peer = self.network.get_device_by_name(peer_id)
            if not peer:
                self.logger.warning(f"Peer {peer_id} not found")
                return False
                
            # Send notification
            response = self.network.send_request(
                peer=peer,
                endpoint="/trade/completion",
                method="POST",
                data=data
            )
            
            return "error" not in response
            
        except Exception as e:
            self.logger.error(f"Error notifying trade completion: {e}")
            return False