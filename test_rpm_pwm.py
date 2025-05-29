# Ez a modul egy DS18B20 beolvasasat valositja meg. A beolvasott adatokat Celsiusban kiirja a program.
# A DS18B20 egy digitális hőmérséklet érzékelő, amely egy vezetékes OneWire protokollt használ.

import machine
import onewire
import ds18x20 
import time

import network
import socket

#import os
#import ujson as json

# HTML code for the web page
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>TemperTemperature measurement</title>
        <style>
            .centerText {
                text-align: center;
            }
            .border {
                margin: auto;
                width: 300px;
                height: 50px;
                border: 1px solid #000000;
            }
        </style>
    </head>
    <body>
        <div class="centerText">
            <h1>Temperature</h1>
        </div>
        <div class="border">
            <canvas id="myCanvas">
                Your browser does not support the HTML5 canvas tag.
            </canvas>
        </div>
        <div class="centerText">
            <p id="intText"></p>
        </div>
            <script>
                const canvas = document.getElementById('myCanvas');
                const ctx = canvas.getContext('2d');

                let i;
                let count = 0;
                const CANV_WIDTH = 300;
                const CANV_HEIGHT = 50;
                
                document.getElementById('intText').innerHTML = i;
                setInterval(getVal, 1000);

                async function getVal() {
                    console.log('Fetching data...' + count);
                    count++;
                    let response = await fetch('/datas');
                    let value = await response.json();
                    i = value.inbound_temp; // Get inbound temperature from JSON response
                    console.log(i);
                    printValue();

                    i = mapValue(i, 0, 20000, 0, CANV_WIDTH);

                    ctx.fillStyle = 'black';
                    ctx.fillRect(0, 0, i, CANV_HEIGHT);

                    ctx.fillStyle = 'white';
                    ctx.fillRect(i + 1, 0, CANV_WIDTH, CANV_HEIGHT);
                }
                
                function printValue() {
                    if(i > 20000) {
                        i = 20000;
                    }
                    let iInt = parseInt(i);
                    document.getElementById('intText').innerHTML = iInt + ' / 20000';
                }

                function mapValue(val, min, max, omin, omax) {
                    return ((val - min) / (max - min) * (omax - omin));
                }
            </script>
    </body>
</html>
"""


TIMER_ID = -1 # Timer ID for periodic tasks
FAN_DUTY_CYCLE_DEFAULT_MAX = 65535 # Maximum duty cycle for fan
FAN_DUTY_CYCLE_DEFAULT_MIN = 0 # Minimum duty cycle for fan
FAN_DUTY_CYCLE_MIN = 25000 # Minimum duty cycle for fan
FAN_DUTY_CYCLE_MAX = 55000 # Maximum duty cycle for fan
FAN_PWM_FREQ = 25000 #25000 # Fan PWM frequency
FAN_IN_PWM_PIN = 0 # GPIO pin for inbound fan PWM control
FAN_OUT_PWM_PIN = 4 # GPIO pin for outbound fan PWM control
SET_TEMPERATURE = 28.0 # Set temperature threshold in Celsius
DELTA_TEMPERATURE = 5.0 # Delta temperature for fan speed adjustment
RPM_IN_PIN = 1 # GPIO pin for inbound RPM sensor
RPM_OUT_PIN = 3 # GPIO pin for outbound RPM sensor
#DS_IN_ROM_ADDRESS = (0x28, 0x33, 0x5e, 0xba, 0x10, 0x00, 0x00, 0x5d) # ROM address for DS18B20 sensor inbound air
#DS_OUT_ROM_ADDRESS = (0x28, 0x0c, 0xba, 0xde, 0x0d, 0x00, 0x00, 0x95) # ROM address for DS18B20 sensor outbound air
#ROMS = (DS_IN_ROM_ADDRESS, DS_OUT_ROM_ADDRESS) # Tuple of ROM addresses for DS18B20 sensors
#DS18B20_ROM_ADDRESS_FILE = "ds18b20_roms.json" # File to store DS18B20 ROM addresses
DS_IN_SENSOR_PIN = 22 # GPIO pin for DS18B20 sensor inbound air
DS_OUT_SENSOR_PIN = 2 # GPIO pin for DS18B20 sensor outbound air

# Network constants
_IP_ADDRESS = "172.23.7.87" # Static IP address for the device
_NETMASK = "255.255.255.0" # Subnet mask for the network
_GATEWAY = "172.23.7.254" # Gateway address for the network
_DNS_SERVER = "172.23.10.1" # DNS server address for the network

# Initialize network interface
nic = network.WIZNET5K() # type: ignore # Create a WIZNET5K network interface object
print("Network interface created:", nic) # Debug print
if not nic.isconnected(): # Check if network interface is not connected
    nic.active(True) # Activate the network interface
    try:
        nic.ifconfig((_IP_ADDRESS, _NETMASK, _GATEWAY, _DNS_SERVER)) # Set static IP configuration
        #nic.ifconfig(('dhcp')) # Request IP address from DHCP server
    except Exception as e:
        print("Error setting static IP configuration:", e) # Debug print
        machine.reset() # Reset the machine if there is an error
   
print("Waiting for network connection...", end='') # Debug print
while not nic.isconnected(): # Wait until network interface is connected
    time.sleep(.5) # Sleep for 1 second
    print('.', end='') # Debug print
print() # New line after waiting for network connection
print("IP configuartion: ", nic.ipconfig('addr4')) # Get current network configuration
time.sleep(1) # Wait for network to stabilize


tempC_IN = 0.0 # Initialize temperature variable for inbound air
tempC_OUT = 0.0 # Initialize outbound air temperature variable

ledToggle_time = time.ticks_ms() # Initialize LED toggle time
ledToggle_time_tick = 1000 # Time interval for LED toggle in milliseconds

#rpm_time = time.ticks_ms() # Initialize time for RPM calculation
rpm_time_tick = 3000 # Time interval for RPM calculation in milliseconds
rpm_IN_counter = 0 # Initialize inbound fan RPM counter
rpm_OUT_counter = 0 # Initialize outbound fan RPM counter
rpm_IN = 0 # Initialize inbound RPM variable
rpm_OUT = 0 # Initialize outbound RPM variable
# GPIO pin for RPM sensor, pull-up resistor
rpm_IN_pin = machine.Pin(RPM_IN_PIN, machine.Pin.IN, machine.Pin.PULL_UP) # Set pin for RPM sensor inbound air
rpm_OUT_pin = machine.Pin(RPM_OUT_PIN, machine.Pin.IN, machine.Pin.PULL_UP) # Set pin for RPM sensor outbound air

#control_time = time.ticks_ms() # Initialize control time
control_time_tick = 1000 # Time interval for control in milliseconds

#dsSensor_read_time = time.ticks_ms() # Initialize time for DS18B20 reading
dsSensor_read_time_tick = 1000 # Time interval for DS18B20 reading in milliseconds
ds_IN_pin = machine.Pin(DS_IN_SENSOR_PIN) # GPIO pin for DS18B20 incoming air
ds_OUT_pin = machine.Pin(DS_OUT_SENSOR_PIN) # GPIO pin for DS18B20 outgoing air
ds_IN_sensor = ds18x20.DS18X20(onewire.OneWire(ds_IN_pin)) # Create DS18B20 object
ds_OUT_sensor = ds18x20.DS18X20(onewire.OneWire(ds_OUT_pin)) # Create DS18B20 object for outbound air
ds_sensors_convert_state = True # Initialize DS18B20 conversion state

# Fan PWM output pin, pull-up resistor
fan_IN_pwm_pin = machine.Pin(FAN_IN_PWM_PIN, machine.Pin.OUT) # GPIO pin for fan control
fan_OUT_pwm_pin = machine.Pin(FAN_OUT_PWM_PIN, machine.Pin.OUT) # GPIO pin for outbound fan control
# Set up PWM for fan control
fan_IN_pwm = machine.PWM(fan_IN_pwm_pin) # Create PWM object for inbound fan
fan_OUT_pwm = machine.PWM(fan_OUT_pwm_pin) # Create PWM object for outbound fan
fan_IN_pwm.freq(FAN_PWM_FREQ) # Set frequency to 25kHz for inbound fan
fan_OUT_pwm.freq(FAN_PWM_FREQ) # Set frequency to 25kHz for outbound fan
fan_IN_pwm.duty_u16(FAN_DUTY_CYCLE_MAX) # Set duty cycle to max initially for inbound fan
fan_OUT_pwm.duty_u16(FAN_DUTY_CYCLE_MAX) # Set duty cycle to max initially for outbound fan
fan_IN_pwm_value_percent = 0 # Initialize fan PWM value in percent
fan_OUT_pwm_value_percent = 0 # Initialize outbound fan PWM value in percent

# Control LED
led = machine.Pin("LED", machine.Pin.OUT) # GPIO pin for LED
led.on() # Turn on LED

roms = [] # Initialize list for DS18B20 ROM addresses



def handle_interrupt_rpm_IN(pin):
    global rpm_IN_counter
    rpm_IN_counter += 1 # Increment RPM counter on interrupt


def handle_interrupt_rpm_OUT(pin):
    global rpm_OUT_counter
    rpm_OUT_counter += 1 # Increment RPM counter on interrupt for outbound air


def map(value, in_min, in_max, out_min, out_max):
    # Map a value from one range to another
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def fan_pwm_percent_to_duty_cycle(percent):
    # Convert percentage to PWM duty cycle value
    return int(map(percent, 0, 100, FAN_DUTY_CYCLE_MIN, FAN_DUTY_CYCLE_MAX))


def set_fan_speed(percent, fan_pwm):
    # Set fan speed based on percentage
    if percent < 0:
        percent = 0
    elif percent > 100:
        percent = 100
    duty_cycle = fan_pwm_percent_to_duty_cycle(percent)
    if percent == 0:
        fan_pwm.duty_u16(FAN_DUTY_CYCLE_DEFAULT_MIN) # type: ignore
    elif percent == 100:
        fan_pwm.duty_u16(FAN_DUTY_CYCLE_DEFAULT_MAX)
    else:
        fan_pwm.duty_u16(duty_cycle) # Set PWM duty cycle
    print("Fan name: {}  -> ".format(fan_pwm), end='') # Debug print
    print("Fan speed set to: {}% (Duty cycle: {})".format(percent, duty_cycle))


def rpm_calculation():
    global rpm_IN, rpm_OUT, rpm_IN_counter, rpm_OUT_counter, rpm_time_tick
    rpm_IN = 0 # Initialize RPM variable
    rpm_OUT = 0 # Initialize outbound RPM variable

    # Calculate RPM based on counter
    print("RPM IN counter: ", rpm_IN_counter) # Debug print
    if rpm_IN_counter > 0:
        rpm_IN = int(rpm_IN_counter / 2 / (rpm_time_tick / 1000) * 60) # Calculate RPM
    else:
        rpm_IN = 0 # Reset RPM counter if no pulses detected
    print("RPM: ", rpm_IN)
    rpm_IN_counter = 0 # Reset RPM counter for next calculation

    print("RPM OUT counter: ", rpm_OUT_counter) # Debug print
    if rpm_OUT_counter > 0:
        rpm_OUT = int(rpm_OUT_counter / 2 / (rpm_time_tick / 1000) * 60) # Calculate outbound RPM
    else:
        rpm_OUT = 0 # Reset outbound RPM counter if no pulses detected
    print("RPM OUT: ", rpm_OUT)
    rpm_OUT_counter = 0 # Reset outbound RPM counter for next calculation
    

def DS18B20_reading():
    global dsSensor_read_time, dsSensor_read_time_tick, tempC_IN, tempC_OUT, ds_sensors_convert_state, roms
    # Read temperature from DS18B20 sensor
    if ds_sensors_convert_state:
        ds_IN_sensor.convert_temp() # Start temperature conversion for inbound air
        ds_OUT_sensor.convert_temp() # Start temperature conversion for outbound air
        ds_sensors_convert_state = False # Set conversion state to false
        return
    if roms:
        tempC_IN = ds_IN_sensor.read_temp(roms[0]) # Read temperature from inbound air sensor
        tempC_OUT = ds_OUT_sensor.read_temp(roms[1]) # Read temperature from outbound air sensor
        print('Temperature inbound air: {:.1f}\'C '.format(tempC_IN)) # Print temperature inbound air
        print('Temperature outbound air: {:.1f}\'C '.format(tempC_OUT)) # Print temperature outbound air
    else:
        print("No DS18B20 ROM addresses available for reading.")
    ds_sensors_convert_state = True # Set conversion state to true for next reading


def control_fan_speed():
    global tempC_IN, tempC_OUT, fan_IN_pwm_value_percent, fan_OUT_pwm_value_percent, fan_IN_pwm, fan_OUT_pwm
    # Control fan speed based on temperature
    if tempC_OUT > tempC_IN:
        # Print tempC_IN and tempC_OUT for debugging
        print("Inbound air temperature: {:.1f}°C".format(tempC_IN)) # Debug print
        print("Outbound air temperature: {:.1f}°C".format(tempC_OUT)) # Debug print
        # Print temperature difference
        print("Temperature difference: {:.1f}°C".format(tempC_OUT - tempC_IN)) # Debug print

        # Increase fan speed
        fan_IN_pwm_value_percent = map(tempC_OUT, tempC_IN, tempC_IN + DELTA_TEMPERATURE, 0, 100)
        fan_OUT_pwm_value_percent = map(tempC_OUT, tempC_IN, tempC_IN + DELTA_TEMPERATURE, 0, 100)
        set_fan_speed(fan_IN_pwm_value_percent, fan_IN_pwm)
        set_fan_speed(fan_OUT_pwm_value_percent, fan_OUT_pwm)
    else:
        # Decrease fan speed
        set_fan_speed(0, fan_IN_pwm)
        set_fan_speed(0, fan_OUT_pwm)
        fan_IN_pwm_value_percent = 0 # Reset inbound fan speed
        fan_OUT_pwm_value_percent = 0 # Reset outbound fan speed
    

def toggle_led():
    global ledToggle_time, ledToggle_time_tick
    # Toggle LED state
    led.toggle() # Toggle LED state
    if rpm_IN > 0:
        ledToggle_time_tick = int(700 / rpm_IN * 1000)
    else:
        ledToggle_time_tick = 3000 # Default toggle time if RPM is 0
    if ledToggle_time_tick < 100: # Minimum toggle time
        ledToggle_time_tick = 100
    ledToggle_time = time.ticks_ms() # Reset LED toggle time


def initWebServer():
    # Initialize web server
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1] # Get address info for web server
    server = socket.socket() # Create a socket object
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Set socket options to reuse address
        server.bind(addr) # Bind the socket to the address
    except Exception as e:
        print("Error binding socket:", e)
        print("Continuing...") # Debug print
        
    server.listen(5) # Listen for incoming connections
    print("Web server started on " + str(addr)) # Debug print
    return server # Return the server object


def web_page(server):
    global tempC_IN, tempC_OUT, rpm_IN, rpm_OUT, fan_IN_pwm_value_percent, fan_OUT_pwm_value_percent
    # Handle web page requests
    cl, addr = server.accept() # Accept incoming connection
    print("Client connected from " + str(addr)) # Debug print
    request = cl.recv(1024).decode('utf-8') # Receive request from client
    if "GET / " in request:
        cl.send("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
        cl.send(html) # Send HTML response
        #cl.close() # Close client connection
    elif "GET /datas " in request:
        cl.send("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n") # Send HTTP response header
        # Send JSON response
        cl.send('{"inbound_temp" : ' + str(tempC_IN) + ', \
                "outbound_temp" : ' + str(tempC_OUT) + ', \
                "inbound_rpm" : ' + str(rpm_IN) + ', \
                "outbound_rpm" : ' + str(rpm_OUT) + ', \
                "inbound_fan_speed" : ' + str(fan_IN_pwm_value_percent) + ', \
                "outbound_fan_speed" : ' + str(fan_OUT_pwm_value_percent) + '}') # Send JSON response with temperature and RPM data
        cl.close() # Close client connection
        
        print("rpm_IN: ", rpm_IN) # Debug print
        print("rpm_OUT: ", rpm_OUT) # Debug print
    else:
        cl.close() # Close client connection if no valid request


#roms.append(ds_IN_sensor.scan()) # Append inbound air sensor ROM address
roms.append(ds_IN_sensor.scan()[0]) # Append inbound air sensor ROM address
roms.append(ds_OUT_sensor.scan()[0]) # Append outbound air sensor ROM address
print('Found DS18B20 devices:', roms) # Print found devices


# Print ROM addresses of found DS18B20 devices
if roms:
    for rom in roms:
        for byte_in_rom in rom:
            # Print each byte in ROM address in hexadecimal format
            print('{:02x}'.format(byte_in_rom), end=' ')
        print() # New line after printing ROM addresses
else:
    print("No DS18B20 ROM addresses available to print.")


# Attach interrupt to RPM pin, falling edge trigger
rpm_IN_pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=handle_interrupt_rpm_IN) # Set up interrupt handler for inbound air
# Attach interrupt to RPM pin, rising edge trigger
rpm_OUT_pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=handle_interrupt_rpm_OUT) # Set up interrupt handler for outbound air

# Timers
timer_rpm_calculation = machine.Timer(TIMER_ID) # Timer for RPM calculation
timer_rpm_calculation.init(period=rpm_time_tick, mode=machine.Timer.PERIODIC, callback=lambda t: rpm_calculation())

timer_dsSensor_reading = machine.Timer(TIMER_ID) # Timer for DS18B20 reading
timer_dsSensor_reading.init(period=dsSensor_read_time_tick, mode=machine.Timer.PERIODIC, callback=lambda t: DS18B20_reading())

timer_control_fan_speed = machine.Timer(TIMER_ID) # Timer for fan speed control
timer_control_fan_speed.init(period=control_time_tick, mode=machine.Timer.PERIODIC, callback=lambda t: control_fan_speed())

server = initWebServer() # Initialize web server
print("Server: ", server) # Debug print

time.sleep(1) # Wait for initial setup to complete
while True:
    try:
        # Toggle LED based on RPM
        if ledToggle_time_tick < time.ticks_diff(time.ticks_ms(), ledToggle_time):
            toggle_led()

        web_page(server) # Handle web page requests

    except KeyboardInterrupt:
        break

