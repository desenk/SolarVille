import time
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

# Define LCD dimensions
lcd_columns = 16
lcd_rows = 2

# Define GPIO pins
lcd_rs = digitalio.DigitalInOut(board.D25)
lcd_en = digitalio.DigitalInOut(board.D24)
lcd_d4 = digitalio.DigitalInOut(board.D23)
lcd_d5 = digitalio.DigitalInOut(board.D17)
lcd_d6 = digitalio.DigitalInOut(board.D27)
lcd_d7 = digitalio.DigitalInOut(board.D22)

# Initialise the LCD class
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows)

# Clear any previous text
lcd.clear()

# Display text
lcd.message = "Hello, World!"

# Wait for 5 seconds
time.sleep(5)

# Clear the display
lcd.clear()
