# Branch: unified-main
# File: logging.py

import logging
from typing import Optional

def setup_logging(log_level: Optional[str] = None) -> None:
    level = getattr(logging, log_level or 'INFO')
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
