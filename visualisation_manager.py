# Branch: ProsumerJack
# File: visualisation_manager.py

from multiprocessing import Process, Queue, Event
from energy_types import EnergyReading
from dataAnalysis import calculate_end_date, update_plot_same
import logging
from queue import Empty

# set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VisualisationManager:
    def __init__(self, start_date, timescale):
        logging.info("Initializing visualization manager...")
        self.queue = Queue()
        self.ready_event = Event()
        self.plot_process = None
        self.start_date = start_date
        self.timescale = timescale
        self.error_queue = Queue()  # New: Queue for error propagation

    def start(self, df):
        logging.info("Starting visualization process...")
        try:
            # Start the plot process
            end_date = calculate_end_date(self.start_date, self.timescale)
            self.plot_process = Process(
                target=update_plot_same,
                args=(df, self.start_date, end_date, self.timescale, 
                      self.queue, self.ready_event, self.error_queue)  # Added error_queue
            )
            self.plot_process.start()
            
            # Wait for plot initialization with timeout
            if not self.ready_event.wait(timeout=30):  # 30 second timeout
                raise RuntimeError("Visualization initialization timeout")
            
            # Check for any errors during initialization
            try:
                error = self.error_queue.get_nowait()
                raise RuntimeError(f"Plot initialization failed: {error}")
            except Empty:
                pass  # No errors occurred
                
            logging.info("Plot initialization complete")
            
        except Exception as e:
            logging.error(f"Failed to start visualization: {e}")
            self._cleanup()
            raise

    def update(self, reading: EnergyReading):
        # Update the plot with new data
        if not self.plot_process or not self.plot_process.is_alive():
            logging.error("Plot process is not running")
            return
            
        try:
            self.queue.put({
                'timestamp': reading.timestamp,
                'generation': reading.generation if hasattr(reading, 'generation') else 0,
                'demand': reading.demand
            }, timeout=5)  # Add timeout to prevent hanging
            logging.debug(f"Updated plot with new data point at {reading.timestamp}")
            
            # Check for any errors from plot process
            try:
                error = self.error_queue.get_nowait()
                logging.error(f"Error in plot process: {error}")
                self._cleanup()
                raise RuntimeError(f"Plot process error: {error}")
            except Empty:
                pass  # No errors
                
        except Exception as e:
            logging.error(f"Error updating visualization: {e}")
            self._cleanup()
            raise

    def stop(self):
        logging.info("Stopping visualization...")
        self._cleanup()

    def _cleanup(self):
        """Clean up plot process and resources"""
        try:
            if self.plot_process:
                # Signal plot process to stop
                self.queue.put("done", timeout=5)
                
                # Wait for process to terminate with timeout
                self.plot_process.join(timeout=5)
                
                # Force terminate if still running
                if self.plot_process.is_alive():
                    logging.warning("Plot process did not terminate gracefully, forcing...")
                    self.plot_process.terminate()
                    self.plot_process.join(timeout=1)
                    
                    if self.plot_process.is_alive():
                        logging.error("Failed to terminate plot process")
                    
            logging.info("Visualization cleanup complete")
        except Exception as e:
            logging.error(f"Error during visualization cleanup: {e}")
        finally:
            # Clear queues
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
            while not self.error_queue.empty():
                try:
                    self.error_queue.get_nowait()
                except Empty:
                    break