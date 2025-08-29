from smbus import SMBus
import struct
import time

BMP280_ADDRESS = 0x77  # Endereço do sensor BMP280
START_ADDRESS = 0x88  # Primeiro endereço 
i2cbus=SMBus(1) 

i2cbus.write_byte_data(BMP280_ADDRESS, 0xF4,  0b00101111)  # Modo normal, oversampling x1 temp e x4 press
time.sleep(0.2)

'''
T_OVERSAMPLING (Bits 7:5)	P_OVERSAMPLING (Bits 4:2)	MODE (Bits 1:0)
'''

def read_and_unpack_calibration_data():
    
    raw_data = i2cbus.read_i2c_block_data(BMP280_ADDRESS, START_ADDRESS, 24) #Lê os 24 bytes de calibração do BMP280 e retorna como uma lista de inteiros. 
    
    global dig_T1, dig_T2, dig_T3
    global dig_P1, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9
    
    # Temperatura
    dig_T1 = struct.unpack('<H', bytes(raw_data[0:2]))[0]  # "<H" = unsigned short little-endian
    dig_T2 = struct.unpack('<h', bytes(raw_data[2:4]))[0]  # "<h" = signed short little-endian
    dig_T3 = struct.unpack('<h', bytes(raw_data[4:6]))[0]  # < little-endian > big-endian
    #print(f"dig_T1: {dig_T1}, dig_T2: {dig_T2}, dig_T3: {dig_T3}")
    
    # Pressão
    dig_P1 = struct.unpack('<H', bytes(raw_data[6:8]))[0]  # .unpack sempre retorna tuplo mas so mandei um valor unico logo preencho o segundo com 0 --> [0]
    dig_P2 = struct.unpack('<h', bytes(raw_data[8:10]))[0]
    dig_P3 = struct.unpack('<h', bytes(raw_data[10:12]))[0]
    dig_P4 = struct.unpack('<h', bytes(raw_data[12:14]))[0]
    dig_P5 = struct.unpack('<h', bytes(raw_data[14:16]))[0]
    dig_P6 = struct.unpack('<h', bytes(raw_data[16:18]))[0]
    dig_P7 = struct.unpack('<h', bytes(raw_data[18:20]))[0]
    dig_P8 = struct.unpack('<h', bytes(raw_data[20:22]))[0]
    dig_P9 = struct.unpack('<h', bytes(raw_data[22:24]))[0]
    
def temperature():
    global t_fine 
    
    t_data =  i2cbus.read_i2c_block_data(BMP280_ADDRESS, 0xFA ,3)
    adc_T = (t_data[0] << 12) | (t_data[1] << 4) | (t_data[2] >> 4) 
    
    #ando 12 para a esquerda para criar um numero de 20 bits, ando 4 para a esquerda para encostar o data1 ao data0 
    #o ultimo byte é o xlsb que tem os ultimos 4 bits a zero logo ando para a direita 4, litle endian logo o 0xFC fica a esquerda (xlsb)
                                                                    
    #print(f"adc_T raw: {adc_T}")
    var1 = ((adc_T)/16384.0-(dig_T1)/1024.0)*(dig_T2)
    var2 = (((adc_T)/131072.0-(dig_T1)/8192.0)*((adc_T)/131072.0-(dig_T1)/8192.0))*(dig_T3)
    t_fine = var1 + var2
    temperature = (var1 +var2) / 5120.0
    
    return temperature
    
def pressure():
    
    p_data =  i2cbus.read_i2c_block_data(BMP280_ADDRESS, 0xF7 ,3)
    adc_P = (p_data[0] << 12) | (p_data[1] << 4) | (p_data[2] >> 4) #unpack so funciona para 2 ou 4 nao 3 T_T
    #print(f"adc_P raw: {adc_P}")
    #adc_P = ((p_data[0] & 0xFF) << 12) | ((p_data[1] & 0xFF) << 4) | ((p_data[2] & 0xF0) >> 4)

    var1 = (t_fine / 2.0) - 64000.0
    var2 = var1 * var1 *(dig_P6) / 32768.0
    var2 = var2 + var1 * (dig_P5)*2.0
    var2 = (var2 / 4.0) + ((dig_P4) * 65536.0)
    var1 = ((dig_P3) * var1 * var1 / 524288.0 + (dig_P2) * var1) / 524288.0;
    var1 = (1.0 + var1 / 32768.0) * (dig_P1)
    p = 1048576.0 - adc_P
    p = (p - (var2 / 4096.0)) * 6250.0 / var1
    var1 = (dig_P9) * p * p / 2147483648.0
    var2 = p * (dig_P8) / 32768.0

    pressure = p + (var1 + var2 + (dig_P7)) / 16.0
    
    return pressure

if __name__ == "__main__":
  while True:
    time.sleep(2)
    read_and_unpack_calibration_data()
    temp = temperature()
    press = pressure()
    
    altitude = 44330 * (1 - (press / 100750) ** (1/5.255)) #100750 pressao ao nivel do mar porto mas meti do aeroporto 
    print(f"Altitude: {altitude:.2f} m")

    print(f"T: {temp:.2f}°C")
    print(f"P: {press / 100:.2f}hPa")
   
