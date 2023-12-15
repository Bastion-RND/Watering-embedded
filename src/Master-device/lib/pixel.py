import machine
import neopixel
import const

np = neopixel.NeoPixel(machine.Pin(3), 1)

def green_pixel():
    
    np[0] = (0, 128, 0)
    np.write()
        
def yellow_pixel():
    
    np[0] = (255, 255, 0, 1)
    np.write()
    
def red_pixel():
    
    np[0] = (255, 0, 0)
    np.write()
    
        
