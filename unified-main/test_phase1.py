#!/usr/bin/env python3
"""
Quick test script for Phase 1 simulation.
Tests data loading and basic simulation without hardware.
"""

import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_data_loading():
    """Test that data can be loaded from the dataset."""
    from simulation.data_analysis import load_data, calculate_end_date

    print("\n=== Testing Data Loading ===")

    # Test parameters
    file_path = "dataset/block_0.csv"
    household = "MAC000002"
    start_date = "2012-10-24"
    timescale = "d"

    # Calculate end date
    end_date = calculate_end_date(start_date, timescale)
    print(f"Date range: {start_date} to {end_date}")

    # Load data
    df = load_data(
        file_path=file_path,
        household=household,
        start_date=start_date,
        end_date=end_date.strftime("%Y-%m-%d")
    )

    if df is None or df.empty:
        print("❌ Failed to load data")
        return False

    print(f"✓ Loaded {len(df)} rows")
    print(f"✓ Date range: {df.index[0]} to {df.index[-1]}")
    print(f"✓ Columns: {df.columns.tolist()}")

    # Show sample data
    print("\nFirst 5 rows:")
    print(df.head())

    return True


def test_config_loading():
    """Test that configuration loads correctly."""
    from core.config import ConfigManager

    print("\n=== Testing Configuration ===")

    config = ConfigManager(config_dir="config")
    config.load_config()

    print(f"✓ Simulation config loaded")
    print(f"  - File path: {config.sim_config.file_path}")
    print(f"  - Household: {config.sim_config.household}")
    print(f"  - Start date: {config.sim_config.start_date}")
    print(f"  - Timescale: {config.sim_config.timescale}")
    print(f"  - Speed: {config.sim_config.simulation_speed}x")
    print(f"  - Interval: {config.sim_config.interval_seconds}s")
    print(f"  - Mock mode: {config.sim_config.mock_mode}")

    print(f"\n✓ Network topology loaded")
    print(f"  - Devices: {list(config.devices.keys())}")

    local_device = config.get_local_device()
    if local_device:
        print(f"  - Local device: {local_device.name} ({local_device.hostname})")
    else:
        print(f"  - Local device: None (hostname not in config)")

    return True


def main():
    """Run Phase 1 tests."""
    print("=" * 60)
    print("Phase 1 Simulation Test")
    print("=" * 60)

    try:
        # Test 1: Data loading
        if not test_data_loading():
            print("\n❌ Data loading test failed")
            return 1

        # Test 2: Configuration
        if not test_config_loading():
            print("\n❌ Configuration test failed")
            return 1

        print("\n" + "=" * 60)
        print("✓ All Phase 1 tests passed!")
        print("=" * 60)
        print("\nTo run the full simulation:")
        print("  cd unified-main")
        print("  PYTHONPATH=$(pwd) python3 core/main.py --config config/ --mock")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
