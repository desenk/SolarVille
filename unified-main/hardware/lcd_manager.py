import logging
from typing import Optional

class LCDManager:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._initialize_display()
