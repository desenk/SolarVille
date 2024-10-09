import time
import board # type: ignore
import digitalio # type: ignore
import adafruit_character_lcd.character_lcd as characterlcd # type: ignore

# Define LCD dimensions
lcd_columns = 16
lcd_rows = 2

# Define GPIO pins
lcd_rs = digitalio.DigitalInOut(board.D25)
lcd_en = digitalio.DigitalInOut(board.D24)
lcd_d4 = digitalio.DigitalInOut(board.D23)
lcd_d5 = digitalio.DigitalInOut(board.D17)
lcd_d6 = digitalio.DigitalInOut(board.D18)
lcd_d7 = digitalio.DigitalInOut(board.D22)

# Initialise the LCD class
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows)

def display_message(message):
    lcd.clear() # Clear the display
    # Insert a newline if the message is longer than 16 characters
    if len(message) > lcd_columns:
        message = message[:lcd_columns] + '\n' + message[lcd_columns:]
    lcd.message = message # Display the message
    time.sleep(5) # Display the message for 5 seconds
    lcd.clear() # Clear the display after 5 seconds
