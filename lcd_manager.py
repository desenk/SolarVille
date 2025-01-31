# Branch: ProsumerJack
# File: lcd_manager.py

import logging
from typing import Optional
import time

try:
    import board # type: ignore
    import digitalio # type: ignore
    import adafruit_character_lcd.character_lcd as characterlcd # type: ignore
    MOCK_LCD = False
except (ImportError, NotImplementedError):
    MOCK_LCD = True
    logging.warning("Running with mock LCD display")

class LCDManager:
    def __init__(self):
        """Initialize LCD display or mock if hardware not available"""
        if not MOCK_LCD:
            # LCD configuration
            lcd_columns = 16
            lcd_rows = 2

            # Define GPIO pins
            lcd_rs = digitalio.DigitalInOut(board.D25)
            lcd_en = digitalio.DigitalInOut(board.D24)
            lcd_d4 = digitalio.DigitalInOut(board.D23)
            lcd_d5 = digitalio.DigitalInOut(board.D17)
            lcd_d6 = digitalio.DigitalInOut(board.D18)
            lcd_d7 = digitalio.DigitalInOut(board.D22)

            # Initialize the LCD
            self.lcd = characterlcd.Character_LCD_Mono(
                lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, 
                lcd_columns, lcd_rows
            )
        else:
            self.lcd = None

    def display_message(self, message: str, duration: Optional[float] = 5.0):
        """Display message on LCD or log if in mock mode"""
        try:
            if self.lcd is not None:
                self.lcd.clear()
                
                # Format message for 16x2 display
                if len(message) > 16:
                    # Split into two lines if message is too long
                    message = message[:16] + '\n' + message[16:32]
                
                self.lcd.message = message
                
                if duration:
                    time.sleep(duration)
                    self.lcd.clear()
            else:
                logging.info(f"Mock LCD Display: {message}")
        except Exception as e:
            logging.error(f"LCD Display error: {e}")

    def display_trade_info(self, amount: float, price: float):
        """Display trade information"""
        message = f"Trade:{amount:.2f}kWh\nPrice:£{price:.2f}"
        self.display_message(message)

    def display_energy_status(self, demand: float, generation: float = 0, battery_soc: float = None):
        """Display energy status"""
        if battery_soc is not None:
            message = f"D:{demand:.2f} G:{generation:.2f}\nBat:{battery_soc:.0f}%"
        else:
            message = f"Demand:{demand:.2f}kWh"
        self.display_message(message)

    def clear(self):
        """Clear the LCD display"""
        if self.lcd is not None:
            self.lcd.clear()