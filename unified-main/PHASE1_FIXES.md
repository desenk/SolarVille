# Phase 1 Fixes - MacBook Development Support

## Problem
The simulation failed on MacBook with: `Could not determine local device`

This happened because the hostname matching logic expected Raspberry Pi hostnames (e.g., "prosumer-pi-1", "consumer-pi-1"), but on MacBook the hostname is different.

## Solution

### 1. Mock Mode Fallback (`core/config.py`)
- In mock mode, if hostname doesn't match any device, use the first device as default
- This allows development on MacBook without modifying config files

### 2. Device Selection Option (`core/main.py`)
Added `--device` command line argument to explicitly choose which device to simulate:

```bash
# Simulate as prosumer
python3 core/main.py --mock --device pi1

# Simulate as consumer
python3 core/main.py --mock --device pi2
```

### 3. Better Error Messages
- Logs which device is being used
- Shows available devices if invalid device specified
- Warns when using fallback device in mock mode

## Usage on MacBook

### Quick Start (Auto-select)
```bash
cd unified-main
PYTHONPATH=$(pwd) python3 test_phase1.py
```
Will automatically use first device (pi1) in mock mode.

### Run Specific Device
```bash
# Run as prosumer with solar/battery
PYTHONPATH=$(pwd) python3 core/main.py --mock --device pi1

# Run as consumer (no solar/battery)
PYTHONPATH=$(pwd) python3 core/main.py --mock --device pi2
```

### Configuration Priority
1. If `--device` specified → use that device
2. Else if hostname matches config → use matched device
3. Else if mock mode → use first device (pi1)
4. Else → error

## Testing Both Device Types

You can now test both consumer and prosumer behavior on MacBook:

**Prosumer (pi1):**
- Has solar generation (mocked)
- Has battery storage (mocked)
- Creates trade offers when surplus energy

**Consumer (pi2):**
- Only consumes energy
- Creates trade requests when deficit

## Next: Run Phase 1 Test

```bash
cd unified-main
source venv/bin/activate  # If using venv
PYTHONPATH=$(pwd) python3 test_phase1.py
```

Should now show:
```
✓ All Phase 1 tests passed!
```
