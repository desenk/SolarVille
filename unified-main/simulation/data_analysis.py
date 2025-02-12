import pandas as pd
import logging
from typing import Optional

def load_data(file_path: str, household: str) -> Optional[pd.DataFrame]:
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        return None
