import time

from machine import SPI, Pin
from ubinascii import hexlify

class Lora:
    def __init__(self, spi: SPI, cs: Pin, reset: Pin, busy: Pin, dio1: Pin, txen: Pin, rxen: Pin):
        self.spi = spi
        self.cs = cs
        self.reset = reset
        self.busy = busy
        self.dio1 = dio1
        self.txen = txen
        self.rxen = rxen
        
        self.irq_state = 0x0000
        self.payload = 6
        self.index = 0x00
        self.rssi_pkg = 0
        self.snr_pkg = 1
        self.rssi_signal = 0
        self.status = 0

#============================SPI_FUNC==========================
        
    def spi_read_write(self, tx_buf, rx_buf):
        self.check_busy()
        self.cs.value(0)
        self.spi.write_readinto(tx_buf, rx_buf)
        self.cs.value(1)

    def spi_write(self, tx_buf):
        self.check_busy()
        self.cs.value(0)
        self.spi.write(tx_buf)
        self.cs.value(1)

    def spi_read_register(self, addr, rx_size):
        tx_data = [0x1D, (addr >> 8) & 0xFF, addr & 0xFF, 0x00]
        for i in range (rx_size):
            tx_data.append(0)
        rx_data = bytearray(len(tx_data))
        self.spi_read_write(bytearray(tx_data), rx_data)
        return rx_data[4:]

    def spi_write_register(self, addr, buf):
        tx_data = [0x0D, (addr >> 8) & 0xFF, addr & 0xFF]
        for i in buf:
            tx_data.append(i)
        self.spi_write(bytearray(tx_data))
   
    def spi_read_cmd(self, cmd, rx_size):
        tx_data = [cmd, 0x00]
        for i in range (rx_size):
            tx_data.append(0)
        rx_data = bytearray(len(tx_data))
        self.spi_read_write(bytearray(tx_data), rx_data)
        return rx_data[2:]
    
    def spi_write_cmd(self, cmd, buf):
        tx_data = [cmd]
        for i in buf:
            tx_data.append(i)
#         print(tx_data)
        self.spi_write(bytearray(tx_data))

    def spi_read_buffer(self, index, size):
        tx_data = [0x1E, index, 0x00]
        for i in range (size):
            tx_data.append(0)
        rx_data = bytearray(len(tx_data))
        self.spi_read_write(bytearray(tx_data), rx_data)
        return rx_data[3:]
        
#============================HARDWARE==========================
        
    def reset_lora(self):
        self.reset(0)
        time.sleep_ms(10)
        self.reset(1)
        time.sleep_ms(100)
        return not self.check_busy()

    def check_busy(self):
        state = self.busy()
        timeout = 10000
        while state == 1:
            state = self.busy()
            if timeout == 0:
                return True
            timeout -= 1
        return False
    
    def rx_init(self):
        self.rxen.value(1)
        self.txen.value(0)

    def tx_init(self):
        self.txen.value(1)
        self.rxen.value(0)

    def tx_rx_deinit(self):
        self.txen.value(0)
        self.rxen.value(0)
    
    def callback(self):
#         print('get_callback')
        self.fix_rx_timeout()
        self.get_device_errors()
        self.clear_device_errors()
        self.clear_irq_status()
        self.payload, self.index = self.get_rx_buffer_state()
#         print(self.payload, self.index)

#==========================LORA_SET==========================

    def set_standby(self, mode):
        self.spi_write_cmd(0x80, [mode])

    def set_packet_type(self):
        self.spi_write_cmd(0x8A, [0x01])
    
    def set_frequency(self):
        frequency = 868000000
        cal_min = 0xD7
        cal_max = 0xDB
        self.spi_write_cmd(0x98, [cal_min, cal_max])
        
        rf_freq = int(frequency * 33554432 / 32000000)
        self.spi_write_cmd(0x86, [(rf_freq >> 24) & 0xFF, (rf_freq >> 16) & 0xFF,
                                  (rf_freq >> 8) & 0xFF, rf_freq & 0xFF])
        
    def set_rx_gain(self):
        gain = 0x94
        self.spi_write_register(0x08AC, [gain])
#         self.spi_write_register(0x029F, [0x01, 0x08, 0xAC])

    def set_lora_modulation(self):
        sf = 7
        bw = 0x05
        cr = 0x01
        ldro = 0x00
        self.spi_write_cmd(0x8B, [sf, bw, cr, ldro, 0, 0, 0, 0])

    def set_lora_packet(self):
        head = 0x00
        preamble = 6
        payload = 255
        crc_type = 0x01
        invert = 0x00
        self.spi_write_cmd(0x8C, [(preamble >> 8) & 0xFF, preamble & 0xFF, head,
                                  payload, crc_type, invert, 0, 0, 0])
        self.fix_inverted_iq()

    def set_sync_word(self):
        syncword = 0x3444
        buf = [(syncword >> 8) & 0xFF,
                (syncword >> 0) & 0xFF]
        self.spi_write_register(0x0740, buf)

    def set_irq(self, irqmask):
        self.spi_write_cmd(0x02, [(0x03FF >> 8) & 0xFF, 0x03FF & 0xFF])
        self.spi_write_cmd(0x08, [(irqmask >> 8) & 0xFF, irqmask & 0xFF, 
                                  (irqmask >> 8) & 0xFF, irqmask & 0xFF, 0, 0, 0, 0])

    def set_rx(self, timeout):
        self.spi_write_cmd(0x82, [(timeout >> 16) & 0xFF, 
                                  (timeout >> 8) & 0xFF, timeout & 0xFF])

    def set_dio3_tcxo_ctrl(self):
        voltage = 0x07
        txco_delay = 0x0560
        self.spi_write_cmd(0x97, [voltage & 0xFF, (txco_delay >> 16) & 0xFF, (txco_delay >> 8) & 0xFF, txco_delay & 0xFF])

    def set_regulator_mode(self):
        regulator = 0x01
        self.spi_write_cmd(0x96, [regulator])
    
    def set_xta_xtb_trim(self):
        trim = 0x1C
        self.spi_write_register(0x0911, [0x1C])
        self.spi_write_register(0x0912, [0x1C])
        
    def set_buffer_base_addr(self):
        tx = 0x00
        rx = 0x00
        self.spi_write_cmd(0x8F, [tx, rx])
        
    def set_ocp(self):
        ocp = 0x38
        self.spi_write_register(0x08E7, [ocp])
    
    def set_tx_params(self):
        buf = [20, 0x07]
        self.spi_write_cmd(0x8E, buf)

#==========================LORA_GET==========================

    def get_irq_status(self):
        buf = self.spi_read_cmd(0x12, 2)
        self.irq_state = buf[0] << 8 | buf[1]
    
    def clear_irq_status(self):
        self.spi_write_cmd(0x02, [0x03, 0xFF])
    
    def get_rx_buffer_state(self):
        buf = self.spi_read_cmd(0x13, 2)
#         print(buf)
        return buf[0], buf[1]

    def get_mode(self):
        buf = self.spi_read_cmd(0xC0, 1)
        return buf[0] & 0x70
    
    def get_rssi_and_snr(self):
        (self.rssi_pkg, self.snr_pkg, self.rssi_signal) = get_packet_status()
        return self.rssi_pkg, self.snr_pkg
    
    def get_packet_status(self):
        buf = self.spi_read_cmd(0x14, 3)
        return buf[0]
#         return buf[0:3]
    
    def get_device_errors(self):
        buf = self.spi_read_cmd(0x17, 1)
        return buf[0]
    
    def clear_device_errors(self):
        self.spi_write_cmd(0x07, [0x00, 0x00])

#==========================LORA_LOGIC==========================

    def begin(self):
        self.reset_lora()
        self.cs(0)
        if self.check_busy():
            return False
        self.set_standby(0x00)
        if self.get_mode() != 0x20:
            print('RC start problem')
            return False
        self.fix_antenna()
        self.set_dio3_tcxo_ctrl()
        self.set_regulator_mode()
        self.set_standby(0x01)
        self.set_xta_xtb_trim()
        if self.get_mode() != 0x30:
            print('TXCO start problem')
            return False
        self.set_buffer_base_addr()
        self.set_packet_type()
        
#         control = 125
#         self.spi_write_register(0x06BC, [control])
#         control1 = self.spi_read_register(0x06BC, 1)
#         print(control1[0])

        print(self.get_device_errors())
        return True

    def request(self):
        self.set_standby(0x01)
        self.set_xta_xtb_trim()
        if self.get_mode() == 0x50 : return False
        self.set_irq(0x0002 | 0x0200 | 0x0020 | 0x0040)
        self.irq_state = 0x0000
        self.status = 5
        self.rx_init()
        self.set_rx(0xFFFFFF)

    def available(self):
        return self.payload

    def read(self):
        a = []
        for i in range(0, self.payload):
            buf = (self.spi_read_buffer((self.index+i), 1))
            a.append(buf)
#             print(f' --> 0x{hexlify(buf).decode().upper()}')
#         self.index = self.index + self.payload
        self.index = self.index + self.payload
        self.payload = 0
        return hexlify(a[0]+a[1]+a[2]+a[3]).decode().lower(), a[4][0], a[5][0]
        #return buf.hex()
    
    def get_status(self):
        irq_state = self.irq_state
        if self.status == 5:
            self.irq_state = 0x0000
        if irq_state & 0x0200: return 6
        elif irq_state & 0x0020: return 8
        elif irq_state & 0x0040: return 9
        elif irq_state & 0x0002: return 7
        return self.status
        
#============================FIXES==========================
        
    def fix_antenna(self):
        buf = self.spi_read_register(0x0902, 1)
        value = buf[0] | 0x1E
        self.spi_write_register(0x0902, [value])
    
    def fix_inverted_iq(self):
        buf = self.spi_read_register(0x0736, 1)
        value = buf[0] & 0xFB
        self.spi_write_register(0x0736, [value])
        
    def fix_rx_timeout(self):
        self.spi_write_register(0x0902, [0])
        buf = self.spi_read_register(0x0944, 1)
        value = buf[0] | 0x02
        self.spi_write_register(0x0944, [value])

    def fix_tx_modulation(self):
        buf = self.spi_read_register(0x0889, 1)
        value = buf[0] | 0x04
        self.spi_write_register(0x0889, [value])
        