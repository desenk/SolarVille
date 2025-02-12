# Branch: ProsumerJack
# File: run.py
import logging
from config import parse_arguments
from main import SimulationManager

logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'  # Added module name to format
)

def main():
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Create and start simulation
        simulation = SimulationManager(args, is_prosumer=True)
        
        logging.info("Starting prosumer simulation...")
        logging.info(f"Using data file: {args.file_path}")
        logging.info(f"Household ID: {args.household}")
        logging.info(f"Start date: {args.start_date}")
        
        # Run simulation
        simulation.start_simulation()
        
    except KeyboardInterrupt:
        logging.info("Prosumer simulation stopped by user")
    except Exception as e:
        logging.error(f"Error in prosumer simulation: {e}", exc_info=True)
    finally:
        logging.info("Prosumer simulation ended")

if __name__ == "__main__":
    main()