# Branch: unified-main
# File: trading_manager.py
"""Trading manager for SolarVille system.
Handles energy trading between prosumers and consumers with a queue-based approach.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from core.config import ConfigManager
from core.device_types import PiDevice
from core.energy_types import EnergyReading, ProsumerReading
from core.trade_types import TradeOffer, TradeRequest, TradeMatch
from network.network_manager import NetworkManager
from network.trading_integration import TradingIntegration
from simulation.trade_verification import TradeVerificationSystem

class TradingManager:
    """
    Manages energy trading between devices in the SolarVille network.
    Implements a queue-based processing system for reliable trade execution.
    """
    
    def __init__(self, config_manager: ConfigManager, network_manager: NetworkManager):
        """
        Initialize the Trading Manager.
        
        Args:
            config_manager: Configuration manager
            network_manager: Network manager for communication
        """
        self.config = config_manager
        self.network = network_manager
        self.logger = logging.getLogger(__name__)
        
        # Device info
        self.local_device = self.config.get_local_device()
        self.is_prosumer = self.local_device.is_prosumer if self.local_device else False
        
        # Trade storage
        self.active_offers = {}     # id -> TradeOffer
        self.active_requests = {}   # id -> TradeRequest
        self.trade_matches = {}     # id -> TradeMatch
        self.completed_trades = []  # List of completed TradeMatch objects
        
        # Trade processing queues
        self.offer_queue = asyncio.Queue()    # Queue of new offers
        self.request_queue = asyncio.Queue()  # Queue of new requests  
        self.match_queue = asyncio.Queue()    # Queue of matched trades to process
        
        # Integration with other components
        self.trading_integration = TradingIntegration(self.network)
        self.verification_system = TradeVerificationSystem(self)
        
        # Trade processing flags
        self.processing_active = False
        self.processing_task = None
        
        # Trading settings
        self.grid_buy_price = self.config.grid_buy_price
        self.grid_sell_price = self.config.grid_sell_price
        
        self.logger.info("Trading Manager initialized")
    
    async def start_processing(self):
        """Start the trade processing loops."""
        if self.processing_active:
            self.logger.warning("Trade processing already active")
            return
            
        self.processing_active = True
        self.processing_task = asyncio.create_task(self._process_trades())
        self.logger.info("Trade processing started")
        
    async def stop_processing(self):
        """Stop the trade processing loops."""
        if not self.processing_active:
            return
            
        self.processing_active = False
        if self.processing_task:
            await self.processing_task
            self.processing_task = None
        self.logger.info("Trade processing stopped")
        
    async def _process_trades(self):
        """Main trade processing loop."""
        try:
            while self.processing_active:
                # Process any new offers and requests
                await self._process_offers()
                await self._process_requests()
                
                # Match offers with requests
                await self._match_trades()
                
                # Process matched trades
                await self._process_matched_trades()
                
                # Short delay to avoid CPU spinning
                await asyncio.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in trade processing loop: {e}", exc_info=True)
            self.processing_active = False
    
    async def create_offer(self, amount: float, min_price: float = None):
        """
        Create a new offer to sell energy.
        
        Args:
            amount: Amount of energy to sell in kWh
            min_price: Minimum acceptable price per kWh
            
        Returns:
            Offer ID
        """
        if amount <= 0:
            raise ValueError("Offer amount must be positive")
            
        # Use default price if none specified
        if min_price is None:
            min_price = self.grid_sell_price * 1.1  # 10% above grid sell price
            
        # Create offer with expiration (e.g., 30 seconds from now)
        expiry = datetime.now() + timedelta(seconds=30)
        
        offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id=self.local_device.name,
            amount=amount,
            min_price=min_price,
            expiry=expiry
        )
        
        # Generate unique ID
        offer_id = f"offer_{offer.seller_id}_{int(offer.timestamp.timestamp())}"
        self.active_offers[offer_id] = offer
        
        # Queue for processing
        await self.offer_queue.put((offer_id, offer))
        
        self.logger.info(f"Created offer {offer_id}: {amount} kWh at £{min_price}/kWh")
        return offer_id
        
    async def create_request(self, amount: float, max_price: float = None, priority: int = 0):
        """
        Create a new request to buy energy.
        
        Args:
            amount: Amount of energy to buy in kWh
            max_price: Maximum acceptable price per kWh
            priority: Priority level (higher = more urgent)
            
        Returns:
            Request ID
        """
        if amount <= 0:
            raise ValueError("Request amount must be positive")
            
        # Use default price if none specified
        if max_price is None:
            max_price = self.grid_buy_price * 0.9  # 10% below grid buy price
            
        request = TradeRequest(
            timestamp=datetime.now(),
            buyer_id=self.local_device.name,
            amount=amount,
            max_price=max_price,
            priority=priority
        )
        
        # Generate unique ID
        request_id = f"request_{request.buyer_id}_{int(request.timestamp.timestamp())}"
        self.active_requests[request_id] = request
        
        # Queue for processing
        await self.request_queue.put((request_id, request))
        
        self.logger.info(f"Created request {request_id}: {amount} kWh at max £{max_price}/kWh")
        return request_id
        
    async def handle_peer_offer(self, offer_id: str, offer: TradeOffer):
        """
        Handle an offer received from a peer.
        
        Args:
            offer_id: Offer ID
            offer: Trade offer object
        """
        # Store the offer
        self.active_offers[offer_id] = offer
        
        # Queue for processing
        await self.offer_queue.put((offer_id, offer))
        
        self.logger.debug(f"Received peer offer {offer_id}: {offer.amount} kWh at £{offer.min_price}/kWh")
        
    async def handle_peer_request(self, request_id: str, request: TradeRequest):
        """
        Handle a request received from a peer.
        
        Args:
            request_id: Request ID
            request: Trade request object
        """
        # Store the request
        self.active_requests[request_id] = request
        
        # Queue for processing
        await self.request_queue.put((request_id, request))
        
        self.logger.debug(f"Received peer request {request_id}: {request.amount} kWh at £{request.max_price}/kWh")
    
    async def _process_offers(self):
        """Process new offers in the queue."""
        try:
            while not self.offer_queue.empty():
                offer_id, offer = await self.offer_queue.get()
                
                # Skip expired offers
                if datetime.now() > offer.expiry:
                    self.logger.debug(f"Skipping expired offer {offer_id}")
                    self.offer_queue.task_done()
                    continue
                    
                # Publish offer to network if it's our offer
                if self.local_device.name == offer.seller_id:
                    await self.trading_integration.publish_offer(offer_id, offer)
                    
                self.offer_queue.task_done()
        except Exception as e:
            self.logger.error(f"Error processing offers: {e}")
    
    async def _process_requests(self):
        """Process new requests in the queue."""
        try:
            while not self.request_queue.empty():
                request_id, request = await self.request_queue.get()
                
                # Publish request to network if it's our request
                if self.local_device.name == request.buyer_id:
                    await self.trading_integration.publish_request(request_id, request)
                    
                self.request_queue.task_done()
        except Exception as e:
            self.logger.error(f"Error processing requests: {e}")
    
    async def _match_trades(self):
        """Match offers with requests."""
        try:
            # Skip if we are not a prosumer (only prosumers match trades)
            if not self.is_prosumer:
                return
                
            # Get valid offers and requests
            valid_offers = {oid: o for oid, o in self.active_offers.items() 
                            if datetime.now() <= o.expiry}
            valid_requests = dict(self.active_requests)
            
            # Sort requests by priority (highest first)
            sorted_requests = sorted(
                valid_requests.items(),
                key=lambda x: (x[1].priority, x[1].timestamp),
                reverse=True  # Higher priority and older requests first
            )
            
            matched_trades = []
            
            # For each request, find matching offers
            for request_id, request in sorted_requests:
                remaining_amount = request.amount
                request_matches = []
                
                # Sort offers by price (lowest first)
                sorted_offers = sorted(
                    valid_offers.items(),
                    key=lambda x: (x[1].min_price, -x[1].amount)  # Lowest price, highest amount
                )
                
                for offer_id, offer in sorted_offers:
                    # Skip if price doesn't match
                    if offer.min_price > request.max_price:
                        continue
                        
                    # Skip self-trades
                    if offer.seller_id == request.buyer_id:
                        continue
                        
                    # Calculate trade amount
                    trade_amount = min(remaining_amount, offer.amount)
                    if trade_amount <= 0:
                        continue
                        
                    # Calculate price (for now, just use offer price)
                    trade_price = offer.min_price
                    
                    # Create trade match
                    trade_match = TradeMatch(
                        offer_id=offer_id,
                        request_id=request_id,
                        seller_id=offer.seller_id,
                        buyer_id=request.buyer_id,
                        amount=trade_amount,
                        price=trade_price
                    )
                    
                    # Generate unique ID
                    match_id = f"match_{trade_match.seller_id}_{trade_match.buyer_id}_{int(trade_match.created_at.timestamp())}"
                    
                    # Add to matches
                    request_matches.append((match_id, trade_match))
                    
                    # Update remaining amount
                    remaining_amount -= trade_amount
                    
                    # Update available offer amount
                    valid_offers[offer_id] = TradeOffer(
                        timestamp=offer.timestamp,
                        seller_id=offer.seller_id,
                        amount=offer.amount - trade_amount,
                        min_price=offer.min_price,
                        expiry=offer.expiry
                    )
                    
                    # If request is fully matched, break
                    if remaining_amount <= 0:
                        break
                
                # Add all matches for this request
                matched_trades.extend(request_matches)
            
            # Queue matched trades for processing
            for match_id, trade_match in matched_trades:
                self.trade_matches[match_id] = trade_match
                await self.match_queue.put((match_id, trade_match))
                
            if matched_trades:
                self.logger.info(f"Matched {len(matched_trades)} trades")
                
        except Exception as e:
            self.logger.error(f"Error matching trades: {e}")
    
    async def _process_matched_trades(self):
        """Process matched trades in the queue."""
        try:
            while not self.match_queue.empty():
                match_id, trade_match = await self.match_queue.get()
                
                # Check if we're involved in this trade
                is_seller = trade_match.seller_id == self.local_device.name
                is_buyer = trade_match.buyer_id == self.local_device.name
                
                if not (is_seller or is_buyer):
                    # We're not involved, skip
                    self.match_queue.task_done()
                    continue
                
                # Verify the trade
                is_valid = await self.verification_system.verify_trade(match_id, trade_match)
                
                if not is_valid:
                    self.logger.warning(f"Trade {match_id} failed verification")
                    trade_match.status = "failed"
                    self.trade_matches[match_id] = trade_match
                    self.match_queue.task_done()
                    continue
                
                # Execute the trade
                success = await self._execute_trade(match_id, trade_match)
                
                if success:
                    # Update trade status
                    trade_match.status = "completed"
                    trade_match.updated_at = datetime.now()
                    self.trade_matches[match_id] = trade_match
                    
                    # Move to completed trades
                    self.completed_trades.append(trade_match)
                    
                    # Log success
                    self.logger.info(
                        f"Completed trade {match_id}: {trade_match.amount} kWh "
                        f"from {trade_match.seller_id} to {trade_match.buyer_id} "
                        f"at £{trade_match.price}/kWh"
                    )
                else:
                    # Update trade status
                    trade_match.status = "failed"
                    trade_match.updated_at = datetime.now()
                    self.trade_matches[match_id] = trade_match
                    
                    # Log failure
                    self.logger.warning(f"Failed to execute trade {match_id}")
                
                self.match_queue.task_done()
                
        except Exception as e:
            self.logger.error(f"Error processing matched trades: {e}")
    
    async def _execute_trade(self, match_id: str, trade_match: TradeMatch) -> bool:
        """
        Execute a matched trade.
        
        Args:
            match_id: Match ID
            trade_match: Trade match object
            
        Returns:
            True if trade was executed successfully
        """
        try:
            is_seller = trade_match.seller_id == self.local_device.name
            is_buyer = trade_match.buyer_id == self.local_device.name
            
            # For now, just notify the other party about the trade
            if is_seller:
                await self.trading_integration.notify_trade_completion(
                    trade_match.buyer_id, match_id, trade_match
                )
            elif is_buyer:
                await self.trading_integration.notify_trade_completion(
                    trade_match.seller_id, match_id, trade_match
                )
            
            # In a real implementation, this would update energy balances,
            # handle financial transactions, etc.
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing trade {match_id}: {e}")
            return False
    
    def get_trade_status(self) -> Dict[str, Any]:
        """
        Get current trading status.
        
        Returns:
            Dictionary with trading status information
        """
        return {
            "active_offers": len(self.active_offers),
            "active_requests": len(self.active_requests),
            "pending_matches": len([m for m in self.trade_matches.values() if m.status == "pending"]),
            "completed_trades": len(self.completed_trades),
            "is_processing": self.processing_active
        }