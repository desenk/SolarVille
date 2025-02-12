# visualisation_manager.py
# ProsumerJack
from multiprocessing import Process, Queue, Event
from energy_types import EnergyReading
from dataAnalysis import calculate_end_date, update_plot_same
import logging
from queue import Empty

class VisualisationManager:
    def __init__(self, start_date, timescale):
        """Initialize visualization manager with queues and events."""
        self.queue = Queue()
        self.ready_event = Event()
        self.error_queue = Queue()
        self.plot_process = None
        self.start_date = start_date
        self.timescale = timescale

    def start(self, df):
        """Start the visualization process."""
        try:
            # Initialize and start plot process
            end_date = calculate_end_date(self.start_date, self.timescale)
            self.plot_process = Process(
                target=update_plot_same,
                args=(df, self.start_date, end_date, self.timescale, 
                      self.queue, self.ready_event, self.error_queue)
            )
            self.plot_process.start()
            
            # Wait for initialization with timeout
            if not self.ready_event.wait(timeout=30):
                logging.error("Visualization failed to initialize within timeout")
                self._cleanup()
                return False
            
            # Check for initialization errors
            if not self.error_queue.empty():
                error = self.error_queue.get_nowait()
                logging.error(f"Plot initialization error: {error}")
                self._cleanup()
                return False
                
            logging.info("Visualization started successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start visualization: {e}")
            self._cleanup()
            return False

    def update(self, reading):
        """Update visualization with new data."""
        if not self.plot_process or not self.plot_process.is_alive():
            logging.error("Plot process is not running")
            return False
            
        try:
            # Check for any errors from plot process
            if not self.error_queue.empty():
                error = self.error_queue.get_nowait()
                logging.error(f"Plot process error: {error}")
                self._cleanup()
                return False
                
            # Send update to plot process
            data = {
                'timestamp': reading.timestamp,
                'demand': reading.demand,
                'generation': getattr(reading, 'generation', 0)
            }
            self.queue.put(data, timeout=5)
            return True
                
        except Exception as e:
            logging.error(f"Error updating visualization: {e}")
            self._cleanup()
            return False

    def stop(self):
        """Stop visualization and clean up resources."""
        logging.info("Stopping visualization...")
        self._cleanup()

    def _cleanup(self):
        """Clean up processes and resources."""
        try:
            if self.plot_process:
                # Signal plot process to stop
                try:
                    self.queue.put("done", timeout=5)
                except:
                    pass
                    
                # Wait for process to terminate
                self.plot_process.join(timeout=5)
                
                # Force terminate if still running
                if self.plot_process.is_alive():
                    self.plot_process.terminate()
                    self.plot_process.join(timeout=1)
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            
        finally:
            # Clear queues
            for q in [self.queue, self.error_queue]:
                while not q.empty():
                    try:
                        q.get_nowait()
                    except Empty:
                        break