# Ez a modul egy DS18B20 beolvasasat valositja meg. A beolvasott adatokat Celsiusban kiirja a program.
# A DS18B20 egy digitális hőmérséklet érzékelő, amely egy vezetékes OneWire protokollt használ.

import machine
import onewire
import ds18x20 
import time

import network

FAN_DUTY_CYCLE_MAX = 65535 # Maximum duty cycle for fan
TEMPERATURE_RANGE = 5 # Temperature range for fan control
FAN_PWM_FREQ = 25000 # Fan PWM frequency
PWM_STEP = FAN_DUTY_CYCLE_MAX / TEMPERATURE_RANGE # Step for PWM duty cycle adjustment
SET_TEMPERATURE = 22.0 # Set temperature threshold in Celsius

ds_pin = machine.Pin(22) # GPIO pin for DS18B20
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin)) # Create DS18B20 object

# Fan PWM output pin, pull-up resistor
fan_pwm = machine.Pin(0, machine.Pin.OUT) # GPIO pin for fan control
# Set up PWM for fan control
fan_pwm = machine.PWM(fan_pwm) # Create PWM object
fan_pwm.freq(FAN_PWM_FREQ) # Set frequency to 1kHz
fan_pwm.duty_u16(FAN_DUTY_CYCLE_MAX) # Set duty cycle to 10% (6553.5/65535 = 0.1)  

# Control LED
led = machine.Pin("LED", machine.Pin.OUT) # GPIO pin for LED
led.on() # Turn on LED

# Connect to wired network
'''
print("Connecting to wired network...")
lan = network.WIZNET5K() # Create WIZNET5K object for wired network
if lan.active():
    print("Wired network is already active.")
print("Aquiring DHCP address...")
lan.active(True) # Activate the network interface
if lan.ifconfig()[0] != "0.0.0.0":
    print("Wired network connected with IP:", lan.ifconfig()[0]) # Print IP address
'''

roms = ds_sensor.scan() # Scan for DS18B20 devices
print('Found DS18B20 devices:', roms) # Print found devices

# Delay for 2 seconds to allow devices to stabilize
time.sleep(2)

while True:
    try:
        ds_sensor.convert_temp() # Start temperature conversion
        time.sleep(1) # Wait for conversion to complete
        led.toggle() # Toggle LED state
        for rom in roms:
            tempC = ds_sensor.read_temp(rom) # Read temperature
            # Print temperature, only one decimal place
            print('Temperature: {:.1f}\'C '.format(tempC))

            # Control fan speed based on temperature
            if tempC > SET_TEMPERATURE:
                # Increase fan speed
                fan_pwm.duty_u16(int(PWM_STEP * (tempC - SET_TEMPERATURE)))
                print("Fan speed increased to: ", int(PWM_STEP * (tempC - SET_TEMPERATURE)))
            else:
                # Decrease fan speed
                fan_pwm.duty_u16(0)
                print("Fan speed decreased to: 0")

        #time.sleep(2) # Wait before next reading
    except KeyboardInterrupt:
        break

