import unittest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime, timedelta
import multiprocessing
from queue import Empty
import matplotlib.pyplot as plt
from visualisation_manager import VisualisationManager
import os
import time

class TestVisualisationManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Set test environment
        os.environ['SOLARVILLE_ENV'] = 'testing'
        
        self.start_date = "2024-01-01"
        self.timescale = "d"
        self.vis_manager = VisualisationManager(self.start_date, self.timescale)
        
        # Create sample test data
        dates = pd.date_range(start=self.start_date, periods=24, freq='h')
        self.test_df = pd.DataFrame({
            'energy(kWh/hh)': [1.0] * 24,
            'generation': [0.5] * 24
        }, index=dates)

    def tearDown(self):
        """Clean up after each test"""
        try:
            self.vis_manager.stop()
        except:
            pass
        plt.close('all')

    def test_normal_initialization(self):
        """Test normal initialization sequence"""
        self.vis_manager.start(self.test_df)
        self.assertTrue(self.vis_manager.ready_event.is_set())
        self.assertTrue(self.vis_manager.error_queue.empty())

    @patch('time.sleep')  # Patch sleep to speed up test
    def test_initialization_timeout(self, mock_sleep):
        """Test handling of initialization timeout"""
        # Override ready_event with one we control
        self.vis_manager.ready_event = multiprocessing.Event()
        
        # Mock wait to always return False (timeout)
        original_wait = self.vis_manager.ready_event.wait
        self.vis_manager.ready_event.wait = lambda timeout: False
        
        try:
            with self.assertRaises(RuntimeError) as cm:
                self.vis_manager.start(self.test_df)
            self.assertEqual(str(cm.exception), "Visualization initialization timeout")
        finally:
            # Restore original wait function
            self.vis_manager.ready_event.wait = original_wait

    def test_update_with_valid_data(self):
        """Test updating plot with valid data"""
        self.vis_manager.start(self.test_df)
        
        # Create test reading
        class TestReading:
            def __init__(self):
                self.timestamp = pd.Timestamp('2024-01-01 00:00:00')
                self.demand = 1.0
                self.generation = 0.5
        
        reading = TestReading()
        self.vis_manager.update(reading)
        
        # Verify no errors occurred
        self.assertTrue(self.vis_manager.error_queue.empty())

    def test_cleanup_on_plot_process_failure(self):
        """Test cleanup when plot process fails"""
        # Create test reading before starting visualization
        class TestReading:
            def __init__(self):
                self.timestamp = pd.Timestamp('2024-01-01 00:00:00')
                self.demand = 1.0
                self.generation = 0.5

        # Start visualization
        self.vis_manager.start(self.test_df)
        
        # Ensure it started correctly
        self.assertTrue(self.vis_manager.ready_event.is_set())
        
        # Put an error in the error queue and ensure it's there
        error_msg = "Simulated plot process error"
        self.vis_manager.error_queue.put(error_msg)
        
        # Now try to update - this should raise the error
        with self.assertRaises(RuntimeError) as cm:
            self.vis_manager.update(TestReading())
            
        # Verify the error message
        self.assertEqual(str(cm.exception), f"Plot process error: {error_msg}")
        
        # Verify cleanup occurred
        self.assertTrue(self.vis_manager.error_queue.empty())

    def test_graceful_shutdown(self):
        """Test graceful shutdown sequence"""
        self.vis_manager.start(self.test_df)
        start_time = datetime.now()
        
        self.vis_manager.stop()
        
        shutdown_time = datetime.now() - start_time
        self.assertLess(shutdown_time.total_seconds(), 6)  # Should complete within timeout

    def test_queue_cleanup(self):
        """Test queue cleanup on shutdown"""
        self.vis_manager.start(self.test_df)
        
        # Add test data
        test_data = {
            'timestamp': pd.Timestamp('2024-01-01 00:00:00'),
            'demand': 1.0,
            'generation': 0.5
        }
        self.vis_manager.queue.put(test_data)
        self.vis_manager.error_queue.put("test error")
        
        self.vis_manager.stop()
        
        # Verify queues are empty
        with self.assertRaises(Empty):
            self.vis_manager.queue.get_nowait()
        with self.assertRaises(Empty):
            self.vis_manager.error_queue.get_nowait()

    def test_error_handling_during_start(self):
        """Test error handling during start process"""
        # Put an error in the queue before starting
        self.vis_manager.error_queue.put("Initialization error")
        
        with self.assertRaises(RuntimeError) as cm:
            self.vis_manager.start(self.test_df)
        self.assertTrue("Plot initialization failed" in str(cm.exception))

if __name__ == '__main__':
    unittest.main()