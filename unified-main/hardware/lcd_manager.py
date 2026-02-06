# Branch: unified-main
# File: lcd_manager.py

"""LCD display manager for SolarVille system."""

import logging
from typing import Optional

class LCDManager:
    """Manages 16x2 LCD display for showing energy status."""

    def __init__(self, mock_mode: bool = True):
        """
        Initialize LCD manager.

        Args:
            mock_mode: If True, simulate LCD without hardware
        """
        self.mock_mode = mock_mode
        self.logger = logging.getLogger(__name__)
        self._initialize_display()

    def _initialize_display(self):
        """Initialize LCD hardware or mock."""
        if self.mock_mode:
            self.logger.info("LCD initialized in mock mode")
            self.lcd = None
        else:
            # TODO: Initialize real LCD hardware
            # from RPLCD.gpio import CharLCD
            # self.lcd = CharLCD(...)
            self.logger.info("LCD hardware initialization not implemented")
            self.lcd = None

    def display(self, line1: str, line2: str = ""):
        """
        Display text on LCD.

        Args:
            line1: Text for first line (max 16 chars)
            line2: Text for second line (max 16 chars)
        """
        if self.mock_mode:
            self.logger.debug(f"LCD: [{line1[:16]:16}] [{line2[:16]:16}]")
        else:
            if self.lcd:
                self.lcd.clear()
                self.lcd.write_string(line1[:16] + "\n\r" + line2[:16])

    def clear(self):
        """Clear the LCD display."""
        if not self.mock_mode and self.lcd:
            self.lcd.clear()

    def cleanup(self):
        """Cleanup LCD resources."""
        if not self.mock_mode and self.lcd:
            self.lcd.clear()
            self.lcd.close()