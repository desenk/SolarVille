import unittest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime, timedelta
import multiprocessing
from queue import Empty
import matplotlib.pyplot as plt
from visualisation_manager import VisualisationManager

class TestVisualisationManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.start_date = "2024-01-01"
        self.timescale = "d"
        self.vis_manager = VisualisationManager(self.start_date, self.timescale)
        
        # Create sample test data
        dates = pd.date_range(start=self.start_date, periods=24, freq='H')
        self.test_df = pd.DataFrame({
            'energy(kWh/hh)': [1.0] * 24,
            'generation': [0.5] * 24
        }, index=dates)

    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'vis_manager'):
            self.vis_manager.stop()
        plt.close('all')

    def test_normal_initialization(self):
        """Test normal initialization sequence"""
        try:
            self.vis_manager.start(self.test_df)
            self.assertTrue(self.vis_manager.plot_process.is_alive())
            self.assertTrue(self.vis_manager.ready_event.is_set())
        finally:
            self.vis_manager.stop()

    def test_initialization_timeout(self):
        """Test handling of initialization timeout"""
        # Mock ready_event.wait to simulate timeout
        with patch('multiprocessing.Event.wait', return_value=False):
            with self.assertRaises(RuntimeError):
                self.vis_manager.start(self.test_df)

    def test_update_with_valid_data(self):
        """Test updating plot with valid data"""
        self.vis_manager.start(self.test_df)
        try:
            # Create mock reading
            mock_reading = Mock()
            mock_reading.timestamp = datetime.now()
            mock_reading.demand = 1.0
            mock_reading.generation = 0.5

            # Should not raise any exceptions
            self.vis_manager.update(mock_reading)
            
            # Verify data was put in queue
            data = self.vis_manager.queue.get(timeout=1)
            self.assertEqual(data['demand'], 1.0)
            self.assertEqual(data['generation'], 0.5)
        finally:
            self.vis_manager.stop()

    def test_cleanup_on_plot_process_failure(self):
        """Test cleanup when plot process fails"""
        self.vis_manager.start(self.test_df)
        
        # Simulate plot process failure
        self.vis_manager.error_queue.put("Test error")
        
        # Update should detect the error and cleanup
        mock_reading = Mock()
        mock_reading.timestamp = datetime.now()
        mock_reading.demand = 1.0
        
        with self.assertRaises(RuntimeError):
            self.vis_manager.update(mock_reading)
            
        # Verify cleanup occurred
        self.assertFalse(self.vis_manager.plot_process.is_alive())

    def test_graceful_shutdown(self):
        """Test graceful shutdown sequence"""
        self.vis_manager.start(self.test_df)
        
        # Stop should complete within timeout
        start_time = datetime.now()
        self.vis_manager.stop()
        shutdown_time = datetime.now() - start_time
        
        # Should take less than 6 seconds (5s timeout + 1s buffer)
        self.assertLess(shutdown_time.total_seconds(), 6)
        self.assertFalse(self.vis_manager.plot_process.is_alive())

    def test_queue_cleanup(self):
        """Test queue cleanup on shutdown"""
        self.vis_manager.start(self.test_df)
        
        # Add some items to queues
        self.vis_manager.queue.put("test")
        self.vis_manager.error_queue.put("test error")
        
        self.vis_manager.stop()
        
        # Queues should be empty after cleanup
        with self.assertRaises(Empty):
            self.vis_manager.queue.get_nowait()
        with self.assertRaises(Empty):
            self.vis_manager.error_queue.get_nowait()

if __name__ == '__main__':
    unittest.main()