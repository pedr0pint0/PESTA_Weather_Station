from smbus import SMBus
import struct
import time

# Endereço I2C do BMP388
BMP388_I2C_ADDR = 0x76
BMP388_CALIB_DATA_START = 0x31
i2cbus = SMBus(1)  

# Ler o valor atual do registo 0x1C -> mode 00 sleep ; 01/10 forced ; 11 normal em [5:4]
# mete normal no 5:4 e da enable aos sensores no 0:1 duhh
# Ler o valor atual do registo 0x1B -> Controlo oversampling T e P -> x4 e x4 -> 010
def init_bmp388():
    
    #0x1B - Enable sensores
    mode = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1B)
    #print(f"Valor inicial de 0x1B: {mode:08b}")
    
    novo_mode = (mode & 0b11111100) | 0b00000011  
    i2cbus.write_byte_data(BMP388_I2C_ADDR, 0x1B, novo_mode)
    time.sleep(0.2)
    
    teste = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1B)
    #print(f"enable sensores: {teste:08b}")
    
    #0x1C - oversampling
    osr = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1C)
    #print(f"Valor inicial de 0x1C: {osr:08b}")
    
    novo_osr = (osr & 0b11000000) | 0b00000010  
    i2cbus.write_byte_data(BMP388_I2C_ADDR, 0x1C, novo_osr)
    time.sleep(0.2)
    
    teste2 = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1C)
    #print(f"oversampling: {teste2:08b}")
    
    #0x1D - Amostragem
    odr = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1D)
    #print(f"Valor inicial de 0x1d: {odr:08b}")
    
    novo_odr = (odr & 0b11100000) | 0b00001000  
    i2cbus.write_byte_data(BMP388_I2C_ADDR, 0x1D, novo_odr)
    time.sleep(0.2)
    #print(f"amostragem: {odr:08b}")
    
    #0x1B
    mode1 = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1B)
    #print(f"Valor inicial de 0x1B: {mode1:08b}")
    
    novo_mode1 = (mode1 & 0b11001111) | 0b00110000  
    i2cbus.write_byte_data(BMP388_I2C_ADDR, 0x1B, novo_mode1)
    time.sleep(0.5)
    
    teste = i2cbus.read_byte_data(BMP388_I2C_ADDR, 0x1B)
    #print(f"modo atualizado: {teste:08b}")
    

def bmp388_read_and_unpack_calibration_data_and_float_coefficient():
   
    global T1, T2, T3
    global P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11
    
    calib_data = i2cbus.read_i2c_block_data(BMP388_I2C_ADDR, BMP388_CALIB_DATA_START, 22)  # 22 bytes de calibração
    
    # Leitura do trimming coeficient
    #[0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x3B,0x3C,0x3D,0x3E,0x3F,0x40,0x41,0x42,0x43,0x44,0x45]
    NVM_PAR_T1 = struct.unpack('<H', bytes(calib_data[0:2]))[0]   #struct.unpack('formato',data) -> data [A:B] A inclusivo , B exclusivo ; returna tuple neste caso é só um valor [0].
    NVM_PAR_T2 = struct.unpack('<H', bytes(calib_data[2:4]))[0]   # <: Little-endian (menor byte primeiro) H: 16-bit unsigned.b: 8-bit signed.h: 16-bit signed.
    NVM_PAR_T3 = struct.unpack('<b', bytes(calib_data[4:5]))[0]   #H: 16-bit unsigned ; b: 8-bit signed ; h: 16-bit signed.
    
    NVM_PAR_P1  = struct.unpack('<h', bytes(calib_data[5:7]))[0] 
    NVM_PAR_P2  = struct.unpack('<h', bytes(calib_data[7:9]))[0]  
    NVM_PAR_P3  = struct.unpack('<b', bytes(calib_data[9:10]))[0]  
    NVM_PAR_P4  = struct.unpack('<b', bytes(calib_data[10:11]))[0]
    NVM_PAR_P5  = struct.unpack('<H', bytes(calib_data[11:13]))[0] 
    NVM_PAR_P6  = struct.unpack('<H', bytes(calib_data[13:15]))[0] 
    NVM_PAR_P7  = struct.unpack('<b', bytes(calib_data[15:16]))[0] 
    NVM_PAR_P8  = struct.unpack('<b', bytes(calib_data[16:17]))[0] 
    NVM_PAR_P9  = struct.unpack('<h', bytes(calib_data[17:19]))[0] 
    NVM_PAR_P10 = struct.unpack('<b', bytes(calib_data[19:20]))[0] 
    NVM_PAR_P11 = struct.unpack('<b', bytes(calib_data[20:21]))[0]  
    
    #Aplicar Calibration coefficient
    
    T1 = NVM_PAR_T1 / (2 ** -8)
    T2 = NVM_PAR_T2 / (2 ** 30)
    T3 = NVM_PAR_T3 / (2 ** 48)

    P1 = (NVM_PAR_P1 - (2**14)) / (2 ** 20)
    P2 = (NVM_PAR_P2 - (2**14)) / (2 ** 29)
    P3 = NVM_PAR_P3 / (2 ** 32)
    P4 = NVM_PAR_P4 / (2 ** 37)
    P5 = NVM_PAR_P5 / (2 ** -3)
    P6 = NVM_PAR_P6 / (2 ** 6)
    P7 = NVM_PAR_P7 / (2 ** 8)
    P8 = NVM_PAR_P8 / (2 ** 15)
    P9 = NVM_PAR_P9 / (2 ** 48)
    P10 = NVM_PAR_P10 / (2 ** 48)
    P11 = NVM_PAR_P11 / (2 ** 65)
 
 
def BMP388_temperature():
    
    global t_lin
    
    data = i2cbus.read_i2c_block_data(BMP388_I2C_ADDR, 0x07, 3) #temp esta em 0x07,0x08 e 0x09 -> ver tabela 27
    uncomp_temp = (data[2] << 16) | (data[1] << 8) | data[0]
    #é um valor de 24bits litle endian logo a ordem é 0x05+0x08+0x09
    #ando com o [0]= 16 bits formando um numero de 24 bits, ando com o [1] 8 ate ficar no meio e coloco no fim o [2]
    
    partial_data1 = float(uncomp_temp - T1)
    partial_data2 = partial_data1 * T2
    t_lin = partial_data2 + (partial_data1 * partial_data1) * T3
    
    print(f"t:{t_lin:.2f}")
    
    return t_lin

def BMP388_pressure():
    
    #print(f"t_linpressure:{t_lin:.2f}")
    
    data = i2cbus.read_i2c_block_data(BMP388_I2C_ADDR, 0x04, 3) #pressao está em 0x04,0x05,0x06
    uncomp_press = (data[2] << 16) | (data[1] << 8) | data[0]

    
    partial_data1 = P6 * t_lin
    partial_data2 = P7 * (t_lin * t_lin)
    partial_data3 = P8 * (t_lin * t_lin * t_lin)
    partial_out1 = P5 + partial_data1 + partial_data2 + partial_data3
    #print(f"partial_out1:{partial_out1}")
    partial_data1 = P2 * t_lin
    partial_data2 = P3 * (t_lin * t_lin)
    partial_data3 = P4 * (t_lin * t_lin * t_lin)
    partial_out2 = uncomp_press * (P1 + partial_data1 + partial_data2 + partial_data3)
    #print(f"partial_out2:{partial_out2}")
    partial_data1 = uncomp_press * uncomp_press
    partial_data2 = P9 + (P10 * t_lin)
    partial_data3 = partial_data1 * partial_data2
    partial_data4 = partial_data3 + (uncomp_press * uncomp_press * uncomp_press) * P11
    #print(f"partial_data:{partial_data4 }")
    comp_press = partial_out1 + partial_out2 + partial_data4
    pressure_hpa = comp_press /100
    
    print(f"p:{pressure_hpa:.2f}hPa")
    return comp_press

init_bmp388()
time.sleep(0.1)
bmp388_read_and_unpack_calibration_data_and_float_coefficient()
time.sleep(0.1)

while True:
    print("BMP388:")
    BMP388_temperature()
    time.sleep(0.1)
    BMP388_pressure()
    time.sleep(1)

