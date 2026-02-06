# Branch: unified-main
# File: data_analysis.py

"""Clean, efficient data loading and analysis for SolarVille simulation."""

import pandas as pd
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def load_data(file_path: str, household: str = None, start_date = None,
              end_date = None, chunk_size: int = 50000) -> Optional[pd.DataFrame]:
    """
    Efficiently load energy data from large CSV file.

    Args:
        file_path: Path to CSV file
        household: Household ID to filter (e.g., 'MAC000002'). If None, loads all.
        start_date: Start date in 'YYYY-MM-DD' format. If None, loads from beginning.
        end_date: End date in 'YYYY-MM-DD' format. If None, loads to end.
        chunk_size: Rows per chunk for filtering (larger = faster but more memory)

    Returns:
        DataFrame with datetime index and 'energy(kWh/hh)' column, or None on error
    """
    try:
        logger.info(f"Loading data from {file_path}")
        if household:
            logger.info(f"Filtering for household: {household}")

        # Convert date strings/objects to datetime if provided
        if start_date:
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            elif isinstance(start_date, datetime):
                start_dt = start_date
            else:
                start_dt = datetime.combine(start_date, datetime.min.time())
        else:
            start_dt = None

        if end_date:
            if isinstance(end_date, str):
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            elif isinstance(end_date, datetime):
                end_dt = end_date
            else:
                end_dt = datetime.combine(end_date, datetime.min.time())
        else:
            end_dt = None

        if start_dt and end_dt:
            logger.info(f"Date range: {start_date} to {end_date}")

        # If filtering is needed, use chunked reading (for 60MB file)
        if household or start_dt or end_dt:
            filtered_chunks = []
            total_rows = 0

            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                # Filter by household
                if household and 'LCLid' in chunk.columns:
                    chunk = chunk[chunk['LCLid'] == household]

                if chunk.empty:
                    continue

                # Convert timestamp
                if 'tstp' in chunk.columns:
                    chunk['datetime'] = pd.to_datetime(chunk['tstp'])
                elif 'DateTime' in chunk.columns:
                    chunk['datetime'] = pd.to_datetime(chunk['DateTime'])
                else:
                    logger.error("No timestamp column found (expected 'tstp' or 'DateTime')")
                    return None

                # Filter by date range
                if start_dt:
                    chunk = chunk[chunk['datetime'] >= start_dt]
                if end_dt:
                    chunk = chunk[chunk['datetime'] < end_dt]

                if not chunk.empty:
                    filtered_chunks.append(chunk)
                    total_rows += len(chunk)

            if not filtered_chunks:
                logger.warning("No data found matching criteria")
                return pd.DataFrame()

            df = pd.concat(filtered_chunks, ignore_index=True)
            logger.info(f"Loaded {total_rows} rows after filtering")

        else:
            # No filtering needed, load entire file
            df = pd.read_csv(file_path)

            # Convert timestamp
            if 'tstp' in df.columns:
                df['datetime'] = pd.to_datetime(df['tstp'])
            elif 'DateTime' in df.columns:
                df['datetime'] = pd.to_datetime(df['DateTime'])
            else:
                logger.error("No timestamp column found")
                return None

            logger.info(f"Loaded {len(df)} rows")

        # Set datetime as index
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)

        # Keep only necessary columns
        energy_col = None
        for col in ['energy(kWh/hh)', 'KWH/hh', 'energy']:
            if col in df.columns:
                energy_col = col
                break

        if energy_col is None:
            logger.error(f"No energy column found. Available columns: {df.columns.tolist()}")
            return None

        # Rename to standard name
        if energy_col != 'energy':
            df['energy'] = df[energy_col]

        logger.info(f"Data loaded successfully: {len(df)} rows from {df.index[0]} to {df.index[-1]}")
        return df

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading data: {e}", exc_info=True)
        return None


def calculate_end_date(start_date, timescale: str) -> datetime:
    """
    Calculate end date based on start date and timescale.

    Args:
        start_date: Start date as string 'YYYY-MM-DD', datetime, or date object
        timescale: 'd' (day), 'w' (week), 'm' (month), 'y' (year)

    Returns:
        End date as datetime object
    """
    # Handle various input types
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    elif isinstance(start_date, datetime):
        start_dt = start_date
    else:
        # Assume it's a date object from YAML
        start_dt = datetime.combine(start_date, datetime.min.time())

    timescale_deltas = {
        'd': timedelta(days=1),
        'w': timedelta(weeks=1),
        'm': timedelta(days=30),
        'y': timedelta(days=365)
    }

    if timescale not in timescale_deltas:
        raise ValueError(f"Invalid timescale '{timescale}'. Use 'd', 'w', 'm', or 'y'.")

    return start_dt + timescale_deltas[timescale]


def calculate_sleep_time(simulation_speed: int, interval_seconds: int) -> float:
    """
    Calculate sleep time between simulation steps.

    Args:
        simulation_speed: Speedup factor (e.g., 300 = 5 minutes real time = 1 day simulated)
        interval_seconds: Time interval between readings in simulation (e.g., 1800 = 30 min)

    Returns:
        Sleep time in seconds
    """
    # Real time = simulated time / speedup
    # If interval is 1800 seconds (30 min) and speedup is 300x
    # Then sleep = 1800 / 300 = 6 seconds
    return interval_seconds / simulation_speed
