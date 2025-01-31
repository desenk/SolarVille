#!/bin/bash
# run_tests.sh

# Script to run tests with proper environment setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment...${NC}"

# Activate virtual environment if it exists
if [ -d "venv-mac" ]; then
    echo "Activating venv-mac..."
    source venv-mac/bin/activate
else
    echo -e "${RED}Warning: venv-mac not found${NC}"
fi

# Set environment variable for testing
export SOLARVILLE_ENV=testing

# Run the tests
echo -e "${YELLOW}Running tests...${NC}"
python3 -m unittest test_visualisation_manager.py -v

# Store the test result
TEST_RESULT=$?

# Cleanup
echo -e "${YELLOW}Cleaning up...${NC}"
unset SOLARVILLE_ENV

# Check if tests passed
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed${NC}"
fi

exit $TEST_RESULT