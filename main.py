# Branch: consumerJack
# File: main.py

from energy_types import EnergyReading
from visualisation_manager import VisualisationManager
from trading_manager import TradingManager
from trading_integration import TradingIntegration
from lcd_manager import LCDManager
from dataAnalysis import load_data, calculate_sleep_time
from config import parse_arguments
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SimulationManager:
    def __init__(self, args, is_prosumer=False):
        """
        Initialize simulation manager.
        
        Args:
            args: Command line arguments
            is_prosumer: Boolean indicating if this is a prosumer (True) or consumer (False)
        """
        self.is_prosumer = is_prosumer
        self.args = args
        
        # Initialize simulation components
        self.vis_manager = VisualisationManager(args.start_date, args.timescale)
        self.trading_manager = TradingManager(is_prosumer)
        self.lcd_manager = LCDManager()
        self.trading_integration = TradingIntegration()
        
        self.start_time = None
        self.simulation_active = False

    def _create_reading(self, timestamp, current_data):
        """
        Create appropriate reading object based on role.
        
        Args:
            timestamp: Current timestamp
            current_data: Current row of data
        """
        try:
            # Ensure energy value is numeric
            energy = float(current_data['energy(kWh/hh)'])
            
            # For consumer, we only need basic energy reading
            reading = EnergyReading(
                timestamp=timestamp,
                demand=energy,
                balance=-energy  # Negative as consumer only uses energy
            )
            return reading
            
        except (ValueError, TypeError) as e:
            logging.error(f"Error converting energy value: {current_data['energy(kWh/hh)']} - {str(e)}")
            # Return a reading with zero values if conversion fails
            return EnergyReading(
                timestamp=timestamp,
                demand=0.0,
                balance=0.0
            )

    def _handle_trade(self, reading, trade_result):
        """
        Handle trade result and update relevant components.
        
        Args:
            reading: Current energy reading
            trade_result: Result of trade processing
        """
        if trade_result:
            # Log trade details
            logging.info(
                f"Trade completed at {reading.timestamp} - "
                f"Amount: {trade_result.amount:.3f} kWh, "
                f"Price: £{trade_result.price:.3f}/kWh"
            )
            
            # Update LCD with trade info
            self.lcd_manager.display_trade_info(
                trade_result.amount, 
                trade_result.price
            )
            
            # Send trade data to peer
            try:
                self.trading_integration.update_trade_data(trade_result)
            except Exception as e:
                logging.debug(f"Failed to update trade data (normal if running standalone): {e}")

    def _update_displays(self, reading):
        """
        Update LCD and visualization displays.
        
        Args:
            reading: Current energy reading
        """
        # Get the current generation value from visualization manager
        generation = self.vis_manager.df.loc[reading.timestamp, 'generation'] if self.vis_manager.df is not None else 0
        
        # Update LCD with current status including generation
        self.lcd_manager.display_energy_status(reading.demand, generation)
        
        # Update visualization
        self.vis_manager.update(reading)

    def start_simulation(self):
        """Main simulation loop"""
        logging.info("Starting simulation...")
        
        try:
            # Load data
            logging.info("Loading data from file...")
            df = load_data(
                self.args.file_path,
                self.args.household,
                self.args.start_date,
                self.args.timescale
            )
            
            if df.empty:
                logging.error("No data loaded. Exiting simulation.")
                return
            
            logging.info(f"Successfully loaded {len(df)} rows of data")
            
            # Start visualization
            logging.info("Starting visualization...")
            self.vis_manager.start(df)
            
            # Record start time
            self.start_time = time.time()
            self.simulation_active = True
            
            # Signal simulation start - don't stop if this fails
            try:
                self.trading_integration.sync_timestamp('START')
            except Exception as e:
                logging.debug(f"Failed to signal start (normal if running standalone): {e}")
            
            try:
                logging.info("Beginning main simulation loop...")
                for timestamp in df.index:
                    if not self.simulation_active:
                        break
                    
                    try:
                        logging.debug(f"Processing timestamp: {timestamp}")
                        current_data = df.loc[timestamp]
                        
                        # Create reading object
                        reading = self._create_reading(timestamp, current_data)
                        
                        # Update peer with current status - continue if this fails
                        try:
                            self.trading_integration.update_peer_data(reading)
                        except Exception as e:
                            logging.debug(f"Failed to update peer (normal if running standalone): {e}")
                        
                        # Process trade
                        try:
                            trade_result = self.trading_manager.process_trade(reading)
                            if trade_result:
                                self._handle_trade(reading, trade_result)
                        except Exception as e:
                            logging.debug(f"Failed to process trade (normal if running standalone): {e}")
                        
                        # Update displays
                        self._update_displays(reading)
                        
                        # Sync timestamp - continue if this fails
                        try:
                            self.trading_integration.sync_timestamp(str(timestamp))
                        except Exception as e:
                            logging.debug(f"Failed to sync timestamp (normal if running standalone): {e}")
                        
                        # Calculate and apply sleep time
                        sleep_time = calculate_sleep_time(timestamp, self.start_time)
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                    
                    except Exception as e:
                        logging.error(f"Error processing timestamp {timestamp}: {e}")
                        continue  # Continue with next timestamp even if this one fails
                
                logging.info("Main simulation loop completed")
                # Signal simulation end - don't stop if this fails
                try:
                    self.trading_integration.sync_timestamp('END')
                except Exception as e:
                    logging.debug(f"Failed to signal end (normal if running standalone): {e}")
                
            except KeyboardInterrupt:
                logging.info("Simulation interrupted by user")
                self.simulation_active = False
                
        except Exception as e:
            logging.error(f"Error in simulation: {e}", exc_info=True)
            self.simulation_active = False
        
        finally:
            # Clean up
            self.lcd_manager.clear()
            self.vis_manager.stop()
            logging.info("Simulation ended")