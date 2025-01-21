import board # type: ignore
import busio # type: ignore
import adafruit_ina219 # type: ignore

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)

# INA219 setup for prosumer demand (default address 0x40)
ina219_demand1 = adafruit_ina219.INA219(i2c, addr=0x40)

# INA219 setup for consumer demand (address 0x41)
ina219_demand2 = adafruit_ina219.INA219(i2c, addr=0x41)

# INA219 setup for battery (address 0x44)
ina219_battery = adafruit_ina219.INA219(i2c, addr=0x44)

# Adjust for higher voltage and current range
ina219_demand1.set_calibration_16V_400mA()
ina219_demand2.set_calibration_16V_400mA()
ina219_battery.set_calibration_16V_400mA()

# Increase ADC resolution for more accurate readings
ina219_demand1.bus_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_demand1.shunt_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_demand2.bus_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_demand2.shunt_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_battery.bus_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
ina219_battery.shunt_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S


def read_ina219(sensor):
    bus_voltage = sensor.bus_voltage
    shunt_voltage = sensor.shunt_voltage
    current = sensor.current / 1000  # Convert to A
    power = bus_voltage * current * 1000  # Calculate power in mW
    
    return bus_voltage, shunt_voltage, current, power


def print_readings(bus_voltage, shunt_voltage, current, power, label):
    print(f"{label} Bus Voltage:    {bus_voltage:.3f} V")
    print(f"{label} Shunt Voltage:  {shunt_voltage:.6f} V")
    print(f"{label} Total Voltage:  {bus_voltage + shunt_voltage:.3f} V")
    print(f"{label} Current:        {current*1000:.3f} mA")
    print(f"{label} Power:          {power:.3f} mW")
    print("------------------------")

def get_current_readings():
    bus_voltage_demand1, shunt_voltage_demand1, current_demand1, power_demand1 = read_ina219(ina219_demand1)
    bus_voltage_demand2, shunt_voltage_demand2, current_demand2, power_demand2 = read_ina219(ina219_demand2)
    bus_voltage_battery, shunt_voltage_battery, current_battery, power_battery = read_ina219(ina219_battery)
    
    return {
        'current_prosumer_damand': current_demand1,
        'current_consumer_damand': current_demand2,
        'power_prosumer_damand': power_demand1,
        'power_consumer_damand': power_demand2,
        'battery_voltage': bus_voltage_battery,
        'power_battery': power_battery
    }