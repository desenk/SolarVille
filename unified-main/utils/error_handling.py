# Branch: unified-main
# File: error_handling.py

import logging
from typing import Optional

class ErrorHandler:
    @staticmethod
    def handle_error(error: Exception, context: str) -> None:
        logging.error(f"Error in {context}: {str(error)}")
