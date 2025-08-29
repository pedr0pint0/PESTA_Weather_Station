# ==================================================
#Link KY053ADC (ADC 16BITS):
#https://www.joy-it.net/en/products/COM-KY053ADC
#
#Link datasheet:
#https://www.ti.com/lit/ds/symlink/ads1115.pdf
#
#Link codigo oficial (referencia de implementação):
#https://github.com/adafruit/Adafruit_CircuitPython_ADS1x15/blob/main/adafruit_ads1x15/ads1x15.py#L385
#
# ==================================================

import time
import struct
from smbus import SMBus

I2C_ADDRESS = 0x48
CONFIG_REGISTER = 0x01
CONVERSION_REGISTER = 0x00

i2cbus=SMBus(1)

# Configuração 
# Ver Table 8-3. Config Register Field Descriptions no datasheet
# Configuração: Modo single-shot, leitura de A0 vs GND, ganho ±4.096V, 128 SPS, ultimos 5 default (00011)

CONFIG = 0b1100001110000011

def write_config_adc():

    config_high = (CONFIG >> 8) & 0xFF #de config extrai o msb
    config_low = CONFIG & 0xFF #extrai o lsb 
    i2cbus.write_i2c_block_data(I2C_ADDRESS, CONFIG_REGISTER, [config_high, config_low]) # é necessario enviar uma lista
    #write_i2c_block_data(addr, cmd, [vals])
    time.sleep(0.1) 

def read_adc():
    write_config_adc()
    data = i2cbus.read_i2c_block_data(I2C_ADDRESS, CONVERSION_REGISTER, 2) # lê 2 bytes ( 16bits da conversao)
    raw_adc = struct.unpack('>h', bytes(data))[0] 

    #8.1.2 Conversion Register (P[1:0] = 00b) [reset = 0000h] 
    # The 16-bit Conversion register contains the result of the last conversion in binary two's-complement format.

    voltage = (raw_adc * 4.096) / 32767  # 16 bits signed de -32768 a 32767
    #print(f"Tensão: {voltage} V")
    return voltage, raw_adc #devolve tuple
    
if __name__ == "__main__":
   write_config_adc()
   while True:
        voltage, raw = read_adc()
        print(f"{voltage:.4f}, {raw}")
        time.sleep(1800)
