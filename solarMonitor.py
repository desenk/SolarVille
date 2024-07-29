import time
import board # type: ignore
import busio # type: ignore
import adafruit_ina219 # type: ignore
import adafruit_character_lcd.character_lcd as characterlcd # type: ignore
import digitalio # type: ignore

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)

# INA219 setup for solar panel (default address 0x40)
ina219_solar = adafruit_ina219.INA219(i2c)

# INA219 setup for battery (address 0x41)
ina219_battery = adafruit_ina219.INA219(i2c, addr=0x41)

# Adjust for higher voltage and current range
ina219_solar.set_calibration_16V_400mA()
ina219_battery.set_calibration_16V_400mA()

# Increase ADC resolution for more accurate readings
ina219_solar.bus_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_solar.shunt_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_battery.bus_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_battery.shunt_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S

# LCD setup (unchanged)
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

def read_ina219(sensor):
    bus_voltage = sensor.bus_voltage
    shunt_voltage = sensor.shunt_voltage
    current = sensor.current / 1000  # Convert to A
    power = bus_voltage * current * 1000  # Calculate power in mW
    
    return bus_voltage, shunt_voltage, current, power

def display_readings(bus_voltage_solar, current_solar, power_solar, bus_voltage_battery, current_battery, power_battery):
    lcd.clear()
    lcd.message = f"S:V:{bus_voltage_solar:.2f}V I:{current_solar:.2f}A\n"
    lcd.message += f"P:{power_solar:.3f}mW\n"
    lcd.message += f"B:V:{bus_voltage_battery:.2f}V I:{current_battery:.2f}A\n"
    lcd.message += f"P:{power_battery:.3f}mW"

def print_readings(bus_voltage, shunt_voltage, current, power, label):
    print(f"{label} Bus Voltage:    {bus_voltage:.3f} V")
    print(f"{label} Shunt Voltage:  {shunt_voltage:.6f} V")
    print(f"{label} Total Voltage:  {bus_voltage + shunt_voltage:.3f} V")
    print(f"{label} Current:        {current*1000:.3f} mA")
    print(f"{label} Power:          {power:.3f} mW")
    print("------------------------")

try:
    print("Press CTRL+C to exit")
    while True:
        bus_voltage_solar, shunt_voltage_solar, current_solar, power_solar = read_ina219(ina219_solar)
        bus_voltage_battery, shunt_voltage_battery, current_battery, power_battery = read_ina219(ina219_battery)
        
        display_readings(bus_voltage_solar, current_solar, power_solar, bus_voltage_battery, current_battery, power_battery)
        
        print_readings(bus_voltage_solar, shunt_voltage_solar, current_solar, power_solar, "Solar")
        print_readings(bus_voltage_battery, shunt_voltage_battery, current_battery, power_battery, "Battery")
        
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