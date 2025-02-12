# Branch: ProsumerJack
# File: main.py
from energy_types import ProsumerReading, EnergyReading
from hardware_manager import SolarMonitor, BatteryManager
from trading_manager import TradingManager
from visualisation_manager import VisualisationManager
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
        
        # Initialize prosumer-specific components
        if is_prosumer:
            self.solar_monitor = SolarMonitor()
            self.battery_manager = BatteryManager()
        
        self.start_time = None
        self.simulation_active = False

    def _create_reading(self, timestamp, current_data):
        """
        Create appropriate reading object based on role.
        
        Args:
            timestamp: Current timestamp
            current_data: Current row of data
        """
        if self.is_prosumer:
            solar_data = self.solar_monitor.get_readings()
            reading = ProsumerReading(
                timestamp=timestamp,
                demand=current_data['energy(kWh/hh)'],  # Fixed column name
                generation=solar_data['solar_energy'],
                balance=solar_data['solar_energy'] - current_data['energy(kWh/hh)'],  # Fixed column name
                battery_soc=self.battery_manager.soc,
                solar_power=solar_data['solar_power'],
                battery_voltage=solar_data['battery_voltage']
            )
        else:
            reading = EnergyReading(
                timestamp=timestamp,
                demand=current_data['energy(kWh/hh)'],  # Fixed column name
                balance=-current_data['energy(kWh/hh)']  # Fixed column name
            )
        return reading

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
            self.trading_integration.update_trade_data(trade_result)
            
            # Update battery if prosumer
            if self.is_prosumer:
                if trade_result.amount > 0:  # Selling energy
                    self.battery_manager.discharge(trade_result.amount)
                else:  # Buying energy
                    self.battery_manager.charge(-trade_result.amount)

    def _update_displays(self, reading):
        """
        Update LCD and visualization displays.
        
        Args:
            reading: Current energy reading
        """
        # Update LCD with current status
        if self.is_prosumer:
            self.lcd_manager.display_energy_status(
                reading.demand,
                reading.generation,
                reading.battery_soc * 100
            )
        else:
            self.lcd_manager.display_energy_status(reading.demand)
        
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

if __name__ == "__main__":
    args = parse_arguments()
    simulation = SimulationManager(args, is_prosumer=True)  # True for prosumer branch
    simulation.start_simulation()