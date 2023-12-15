from machine import SPI, Pin


class LoRaSpi:

    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs

    def transfer(self, tx_buf):
        rx_buf = bytearray(len(tx_buf))# * len(tx_buf)
        try:
            self.cs(0)  # Select peripheral.
            self.spi.write_readinto(tx_buf, rx_buf)  # Write 8 bytes
        finally:
            self.cs(1)
        return rx_buf


# class LoRaGpio:
#     def __init__(self, chip: int, offset: int):
#         self.chip = "gpiochip" + str(chip)
#         self.offset = offset
#
#     def output(self, value: int):
#         chip = gpiod.Chip(self.chip)
#         line = chip.get_line(self.offset)
#         try:
#             line.request(consumer="LoRaGpio", type=gpiod.LINE_REQ_DIR_OUT)
#             line.set_value(value)
#         except:
#             return
#         finally:
#             line.release()
#             chip.close()
#
#     def input(self) -> int:
#         chip = gpiod.Chip(self.chip)
#         line = chip.get_line(self.offset)
#         try:
#             line.request(consumer="LoRaGpio", type=gpiod.LINE_REQ_DIR_IN)
#             value = line.get_value()
#         except:
#             return -1
#         finally:
#             line.release()
#             chip.close()
#         return value
#
#     def monitor(self, callback, timeout: float):
#         seconds = int(timeout)
#         chip = gpiod.Chip(self.chip)
#         line = chip.get_line(self.offset)
#         try:
#             line.request(consumer="LoRaGpio", type=gpiod.LINE_REQ_EV_RISING_EDGE)
#             if line.event_wait(seconds, int((timeout - seconds) * 1000000000)):
#                 callback()
#         except:
#             return
#         finally:
#             line.release()
#             chip.close()
#
#     def monitor_continuous(self, callback, timeout: float):
#         seconds = int(timeout)
#         while True:
#             chip = gpiod.Chip(self.chip)
#             line = chip.get_line(self.offset)
#             try:
#                 line.request(consumer="LoRaGpio", type=gpiod.LINE_REQ_EV_RISING_EDGE)
#                 if line.event_wait(seconds, int((timeout - seconds) * 1000000000)):
#                     callback()
#             except:
#                 continue
#             finally:
#                 line.release()
#                 chip.close()
#
#
# class BaseLoRa:
#
#     def begin(self):
#         raise NotImplementedError
#
#     def end(self):
#         raise NotImplementedError
#
#     def reset(self):
#         raise NotImplementedError
#
#     def beginPacket(self):
#         raise NotImplementedError
#
#     def endPacket(self, timeout: int) -> bool:
#         raise NotImplementedError
#
#     def write(self, data, length: int):
#         raise NotImplementedError
#
#     def request(self, timeout: int) -> bool:
#         raise NotImplementedError
#
#     def available(self):
#         raise NotImplementedError
#
#     def read(self, length: int):
#         raise NotImplementedError
#
#     def wait(self, timeout: int) -> bool:
#         raise NotImplementedError
#
#     def status(self):
#         raise NotImplementedError
