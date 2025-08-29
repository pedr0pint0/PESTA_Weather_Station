from smbus import SMBus
import struct
import time

#I2C bus
i2cbus = SMBus(1)

# BMP280 
BMP280_ADDRESS = 0x77
BMP280_START_ADDRESS = 0x88

# BMP388 
BMP388_ADDRESS = 0x76
BMP388_CALIB_DATA_START = 0x31

# BMP280 Globals
dig_T1, dig_T2, dig_T3 = 0, 0, 0
dig_P1, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9 = 0, 0, 0, 0, 0, 0, 0, 0, 0
t_fine = 0

# BMP388 Globals
T1, T2, T3 = 0, 0, 0
P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
t_lin = 0

'''
Global variables in Python are defined outside of any function and can be 
accessed from anywhere in the code, including inside functions. 
To modify a global variable within a function, you need to use the global keyword.
'''
# BMP280 Functions
def init_bmp280():
    i2cbus.write_byte_data(BMP280_ADDRESS, 0xF4, 0b00101111)  # Normal mode, oversampling x1 temp, x4 press
    time.sleep(0.2)
    read_and_unpack_calibration_data_bmp280()


def read_and_unpack_calibration_data_bmp280():
    global dig_T1, dig_T2, dig_T3, dig_P1, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9
    
    raw_data = i2cbus.read_i2c_block_data(BMP280_ADDRESS, BMP280_START_ADDRESS, 24)
    dig_T1 = struct.unpack('<H', bytes(raw_data[0:2]))[0]
    dig_T2 = struct.unpack('<h', bytes(raw_data[2:4]))[0]
    dig_T3 = struct.unpack('<h', bytes(raw_data[4:6]))[0]
    
    dig_P1 = struct.unpack('<H', bytes(raw_data[6:8]))[0]
    dig_P2 = struct.unpack('<h', bytes(raw_data[8:10]))[0]
    dig_P3 = struct.unpack('<h', bytes(raw_data[10:12]))[0]
    dig_P4 = struct.unpack('<h', bytes(raw_data[12:14]))[0]
    dig_P5 = struct.unpack('<h', bytes(raw_data[14:16]))[0]
    dig_P6 = struct.unpack('<h', bytes(raw_data[16:18]))[0]
    dig_P7 = struct.unpack('<h', bytes(raw_data[18:20]))[0]
    dig_P8 = struct.unpack('<h', bytes(raw_data[20:22]))[0]
    dig_P9 = struct.unpack('<h', bytes(raw_data[22:24]))[0]


def read_temperature_bmp280():
    global t_fine
    
    t_data = i2cbus.read_i2c_block_data(BMP280_ADDRESS, 0xFA, 3)
    adc_T = (t_data[0] << 12) | (t_data[1] << 4) | (t_data[2] >> 4)
    
    var1 = ((adc_T)/16384.0-(dig_T1)/1024.0)*(dig_T2)
    var2 = (((adc_T)/131072.0-(dig_T1)/8192.0)*((adc_T)/131072.0-(dig_T1)/8192.0))*(dig_T3)
    t_fine = var1 + var2
   
    return (var1 + var2) / 5120.0 #temperature BMP280


def read_pressure_bmp280():
    p_data = i2cbus.read_i2c_block_data(BMP280_ADDRESS, 0xF7, 3)
    adc_P = (p_data[0] << 12) | (p_data[1] << 4) | (p_data[2] >> 4)
    
    var1 = (t_fine / 2.0) - 64000.0
    var2 = var1 * var1 *(dig_P6) / 32768.0
    var2 = var2 + var1 * (dig_P5)*2.0
    var2 = (var2 / 4.0) + ((dig_P4) * 65536.0)
    var1 = ((dig_P3) * var1 * var1 / 524288.0 + (dig_P2) * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * (dig_P1)
    p = 1048576.0 - adc_P
    p = (p - (var2 / 4096.0)) * 6250.0 / var1
    var1 = (dig_P9) * p * p / 2147483648.0
    var2 = p * (dig_P8) / 32768.0
    return (p + (var1 + var2 + dig_P7) / 16.0) / 100 #pressure BMP280 em hPa


# BMP388 Functions
def init_bmp388(): #Bits reservados
    #0x1B - Enable sensores
    mode = i2cbus.read_byte_data(BMP388_ADDRESS, 0x1B)
    enable_sensors = (mode & 0b11111100) | 0b00000011  
    i2cbus.write_byte_data(BMP388_ADDRESS, 0x1B, enable_sensors)
    time.sleep(0.1)
    
    #0x1C - Oversampling
    osr = i2cbus.read_byte_data(BMP388_ADDRESS, 0x1C)
    novo_osr = (osr & 0b11000000) | 0b00000010  
    i2cbus.write_byte_data(BMP388_ADDRESS, 0x1C, novo_osr)
    time.sleep(0.1)
    
    #0x1D - Amostragem
    odr = i2cbus.read_byte_data(BMP388_ADDRESS, 0x1D)
    novo_odr = (odr & 0b11100000) | 0b00001000  
    i2cbus.write_byte_data(BMP388_ADDRESS, 0x1D, novo_odr)
    time.sleep(0.1)
    
    #0x1B - Modo normal Bit 5..4 -< 11
    mode = i2cbus.read_byte_data(BMP388_ADDRESS, 0x1B)
    novo_mode = (mode & 0b11001111) | 0b00110000  
    i2cbus.write_byte_data(BMP388_ADDRESS, 0x1B, novo_mode)
    time.sleep(0.2)
    read_and_unpack_calibration_data_bmp388()



def read_and_unpack_calibration_data_bmp388():  #Aplica os Calibration coefficient (divisoes)
    global T1, T2, T3, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11
    
    calib_data = i2cbus.read_i2c_block_data(BMP388_ADDRESS, BMP388_CALIB_DATA_START, 22)
    
    T1 = struct.unpack('<H', bytes(calib_data[0:2]))[0] / (2 ** -8)
    T2 = struct.unpack('<H', bytes(calib_data[2:4]))[0] / (2 ** 30)
    T3 = struct.unpack('<b', bytes(calib_data[4:5]))[0] / (2 ** 48)
    
    P1 = (struct.unpack('<h', bytes(calib_data[5:7]))[0] - (2 ** 14)) / (2 ** 20)
    P2 = (struct.unpack('<h', bytes(calib_data[7:9]))[0] - (2 ** 14)) / (2 ** 29)
    P3 = struct.unpack('<b', bytes(calib_data[9:10]))[0] / (2 ** 32)
    P4 = struct.unpack('<b', bytes(calib_data[10:11]))[0] / (2 ** 37)
    P5 = struct.unpack('<H', bytes(calib_data[11:13]))[0] / (2 ** -3)
    P6 = struct.unpack('<H', bytes(calib_data[13:15]))[0] / (2 ** 6)
    P7 = struct.unpack('<b', bytes(calib_data[15:16]))[0] / (2 ** 8)
    P8 = struct.unpack('<b', bytes(calib_data[16:17]))[0] / (2 ** 15)
    P9 = struct.unpack('<h', bytes(calib_data[17:19]))[0] / (2 ** 48)
    P10 = struct.unpack('<b', bytes(calib_data[19:20]))[0] / (2 ** 48)
    P11 = struct.unpack('<b', bytes(calib_data[20:21]))[0] / (2 ** 65)

    

def read_temperature_bmp388():
    global t_lin
    
    data = i2cbus.read_i2c_block_data(BMP388_ADDRESS, 0x07, 3)
    uncomp_temp = (data[2] << 16) | (data[1] << 8) | data[0]
    partial_data1 = float(uncomp_temp - T1)
    partial_data2 = partial_data1 * T2
    t_lin = partial_data2 + (partial_data1 * partial_data1) * T3
    
    return t_lin #Temperatura BMP388


def read_pressure_bmp388():
    data = i2cbus.read_i2c_block_data(BMP388_ADDRESS, 0x04, 3)
    uncomp_press = (data[2] << 16) | (data[1] << 8) | data[0]
    
    partial_data1 = P6 * t_lin
    partial_data2 = P7 * (t_lin * t_lin)
    partial_data3 = P8 * (t_lin * t_lin * t_lin)
    partial_out1 = P5 + partial_data1 + partial_data2 + partial_data3

    partial_data1 = P2 * t_lin
    partial_data2 = P3 * (t_lin * t_lin)
    partial_data3 = P4 * (t_lin * t_lin * t_lin)
    partial_out2 = uncomp_press * (P1 + partial_data1 + partial_data2 + partial_data3)

    partial_data1 = uncomp_press * uncomp_press
    partial_data2 = P9 + (P10 * t_lin)
    partial_data3 = partial_data1 * partial_data2
    partial_data4 = partial_data3 + (uncomp_press * uncomp_press * uncomp_press) * P11

    comp_press = partial_out1 + partial_out2 + partial_data4
    return comp_press / 100  #Pressure BMP388 em hPa


def main():
    init_bmp280()
    init_bmp388()

    while True:
        time.sleep(2)

        # BMP280 Readings
        temp280 = read_temperature_bmp280()
        press280 = read_pressure_bmp280()
        print(f"BMP280 -> T: {temp280:.2f}°C, P: {press280:.2f} hPa")

        # BMP388 Readings
        temp388 = read_temperature_bmp388()
        press388 = read_pressure_bmp388()
        print(f"BMP388 -> T: {temp388:.2f}°C, P: {press388:.2f} hPa")


if __name__ == "__main__":
    main()
