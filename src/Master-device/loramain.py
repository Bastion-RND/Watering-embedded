from lora import LoRa
from machine import Pin, SPI
from time import sleep

SCK  = 14
MOSI = 13
MISO = 12
CS   = 11
RX   = 47

spi = SPI(
    2,
    baudrate=625000,
    sck=Pin(SCK, Pin.OUT, Pin.PULL_DOWN),
    mosi=Pin(MOSI, Pin.OUT, Pin.PULL_UP),
    miso=Pin(MISO, Pin.IN, Pin.PULL_UP),
)

spi.init()

# Setup LoRa
lora = LoRa(
    spi,
    cs=Pin(CS, Pin.OUT),
    rx=Pin(RX, Pin.IN),
)

lora.send(1)
print("fdf")
#sleep(1)