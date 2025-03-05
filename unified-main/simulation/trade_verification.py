# Branch: unified-main
# File: trade_verification.py

"""Trade verification system for SolarVille.
Verifies trade validity and ensures trades meet all requirements.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from core.trade_types import TradeOffer, TradeRequest, TradeMatch

class TradeVerificationSystem:
    """
    Verifies trade validity and ensures trades meet all requirements.
    """
    
    def __init__(self, trading_manager):
        """
        Initialize the Trade Verification System.
        
        Args:
            trading_manager: Trading Manager instance
        """
        self.trading_manager = trading_manager
        self.logger = logging.getLogger(__name__)
        
    async def verify_trade(self, match_id: str, trade_match: TradeMatch) -> bool:
        """
        Verify if a trade is valid.
        
        Args:
            match_id: Match ID
            trade_match: Trade match object
            
        Returns:
            True if trade is valid
        """
        try:
            # Get the original offer and request
            offer_id = trade_match.offer_id
            request_id = trade_match.request_id
            
            offer = self.trading_manager.active_offers.get(offer_id)
            request = self.trading_manager.active_requests.get(request_id)
            
            # Check if offer and request exist
            if not offer or not request:
                self.logger.warning(f"Offer or request not found for trade {match_id}")
                return False
                
            # Check if offer has expired
            if datetime.now() > offer.expiry:
                self.logger.warning(f"Offer {offer_id} has expired for trade {match_id}")
                return False
                
            # Check if offer has enough energy
            if offer.amount < trade_match.amount:
                self.logger.warning(f"Offer {offer_id} has insufficient energy for trade {match_id}")
                return False
                
            # Check if price is acceptable
            if trade_match.price < offer.min_price or trade_match.price > request.max_price:
                self.logger.warning(f"Price {trade_match.price} is not acceptable for trade {match_id}")
                return False
                
            # Check if buyer and seller are correct
            if offer.seller_id != trade_match.seller_id or request.buyer_id != trade_match.buyer_id:
                self.logger.warning(f"Buyer or seller mismatch for trade {match_id}")
                return False
                
            # All checks passed
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying trade {match_id}: {e}")
            return False