import time
import board
import busio
import adafruit_ina219
import adafruit_character_lcd.character_lcd as characterlcd
import digitalio

# INA219 setup
i2c = busio.I2C(board.SCL, board.SDA)
ina219 = adafruit_ina219.INA219(i2c)

# Adjust for very low power measurements
ina219.set_calibration_16V_400mA()

# LCD setup
lcd_columns = 16
lcd_rows = 2

lcd_rs = digitalio.DigitalInOut(board.D25)
lcd_en = digitalio.DigitalInOut(board.D24)
lcd_d4 = digitalio.DigitalInOut(board.D23)
lcd_d5 = digitalio.DigitalInOut(board.D17)
lcd_d6 = digitalio.DigitalInOut(board.D18)
lcd_d7 = digitalio.DigitalInOut(board.D22)

lcd = characterlcd.Character_LCD_Mono(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows
)

def read_solar_panel():
    bus_voltage = ina219.bus_voltage  # voltage on V- (load side)
    shunt_voltage = ina219.shunt_voltage  # voltage between V+ and V- across the shunt
    current = ina219.current  # current in mA
    
    # Calculate power manually
    power = bus_voltage * (current / 1000)  # V * A = W
    power_mw = power * 1000  # Convert W to mW
    
    return bus_voltage, shunt_voltage, current, power_mw

def display_readings(bus_voltage, current, power_mw):
    lcd.clear()
    # First row: Voltage and Current
    lcd.message = f"V:{bus_voltage:.2f}V I:{current:.2f}mA\n"
    # Second row: Power in mW
    lcd.message += f"P:{power_mw:.3f}mW"

def print_readings(bus_voltage, shunt_voltage, current, power_mw):
    print(f"Bus Voltage:    {bus_voltage:.3f} V")
    print(f"Shunt Voltage:  {shunt_voltage:.6f} V")
    print(f"Load Voltage:   {bus_voltage + shunt_voltage:.3f} V")
    print(f"Current:        {current:.3f} mA")
    print(f"Power:          {power_mw:.3f} mW")
    print("------------------------")

try:
    print("Press CTRL+C to exit")
    while True:
        bus_voltage, shunt_voltage, current, power_mw = read_solar_panel()
        display_readings(bus_voltage, current, power_mw)
        print_readings(bus_voltage, shunt_voltage, current, power_mw)
        time.sleep(2)

except KeyboardInterrupt:
    print("\nMeasurement stopped by user")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    lcd.clear()
    lcd.message = "Monitoring\nstopped"
    time.sleep(2)
    lcd.clear()
