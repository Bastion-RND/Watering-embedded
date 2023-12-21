import machine
import neopixel

class Indication:
    def __init__(self, np):
        self.np = neopixel.NeoPixel(machine.Pin(3), 1)
    
    def green_pixel(self):
        self.np[0] = (0, 128, 0)
        self.np.write()
        
    def yellow_pixel(self):
        self.np[0] = (255, 255, 0, 1)
        self.np.write()
        
    def red_pixel(self):        
        self.np[0] = (255, 0, 0)
        self.np.write()
        
        
