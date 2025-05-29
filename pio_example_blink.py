import time
import rp2
from machine import Pin

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def blink():
    wrap_target()
    set(pins, 1)               [31]
    nop()                      [31]
    nop()                      [31]
    nop()                      [31]
    nop()                      [31]
    set(pins, 0)               [31]
    nop()                      [31]
    nop()                      [31]
    nop()                      [31]
    nop()                      [31]
    wrap()


# Instantiate a state machine with the blink program, at 2000Hz, with set bound to Pin(25) (LED on the Pico board)
sm = rp2.StateMachine(0, blink, freq=2000, set_base=Pin(25))

# Run the state machine for 3 seconds. The LED should blink
sm.active(1)
time.sleep(3)
sm.active(0)

