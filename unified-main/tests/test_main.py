# Branch: unified-main
# File: tests/test_main.py

import unittest
import os
import sys

def run_tests():
    """Run all test cases in the tests directory."""
    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return non-zero exit code if tests failed
    if not result.wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(run_tests())