import threading
import argparse
import os
import paho.mqtt.client as mqtt
import time
import smbus2
from smbus2 import SMBus
from datetime import datetime
import csv
import logging
import warnings
warnings.filterwarnings("ignore")

# Configurações MQTT
#BROKER = "100.65.235.61"   # Opção 1 - VPN
#BROKER = "192.168.10.200"  # Opção 2 - Access Point
BROKER = "192.168.10.150"   # Pedro
PORT = 1883                 # Porta 

# Tópicos MQTT
TOPIC_PARTICLES = "quad_sensor/particles"
TOPIC_FORMALDEHYDE = "quad_sensor/formaldehyde"
TOPIC_TEMP_HUM = "quad_sensor/temp_hum"
TOPIC_GAS = "quad_sensor/gas"
TOPIC_GPS = "quad_sensor/gps"
TOPIC_SENSORS = "quad_sensor/sensors"

# Endereços I2C
I2C_BUS = 1
SENSOR_ADDRESS_PART = 0x19
SENSOR_ADDRESS_FORMAL = 0x5D
SENSOR_ADDRESS_GAS = 0x58
GNSS_I2C_ADDR = 0x20

# Parar todas as threads
stop_event = threading.Event()

#Criar pastas para guardar dados
timestamp_str = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
main_dir = f"data_{timestamp_str}"

# Cria a pasta principal
os.makedirs(main_dir, exist_ok=True)

# Cria subpastas
log_dir = os.path.join(main_dir, "log")
csv_dir = os.path.join(main_dir, "csv")

os.makedirs(log_dir, exist_ok=True)
os.makedirs(csv_dir, exist_ok=True)


# === FILTRO para limitar até um certo nível ===
class MaxLevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno <= self.level

# === FORMATADOR COMUM ===
log_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

info_log_filename = os.path.join(log_dir, "sensor_info.log")
error_log_filename = os.path.join(log_dir, "sensor_erro.log")

# === FICHEIRO PARA INFO (apenas INFO ou inferior) ===
info_handler = logging.FileHandler(info_log_filename, mode='w')
info_handler.setLevel(logging.DEBUG)  # Aceita DEBUG e INFO
info_handler.addFilter(MaxLevelFilter(logging.INFO))  # Limita até INFO
info_handler.setFormatter(log_formatter)

# === FICHEIRO PARA ERROS (apenas ERROR e superior) ===
error_handler = logging.FileHandler(error_log_filename, mode='w')
error_handler.setLevel(logging.ERROR)  # Apenas ERROR ou superior
error_handler.setFormatter(log_formatter)

# === TERMINAL (só mostra erros) ===
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(log_formatter)

# === CONFIGURA O LOGGER ===
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Garante que o logger capta tudo
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)



#########################################################################
# Dicionário global para armazenar os dados mais recentes
sensor_data = {
	#"timestamp": None,
    "pm25": 999999999,
    "pm10": 999999999,
    "part25": 999999999,
    "part10": 999999999,
    "aqi": 999999999,
    "formal": 999999999,
    "temp": 999999999,
    "hum": 999999999,
    "co2eq": 999999999,
    "voc": 999999999,
    "lat": 999999999,
    "lon": 999999999,
    "alt": 999999999,
    "sats": 999999999,
    "sog": 999999999,
    "cog": 999999999
}
sensor_data_lock = threading.Lock()
#########################################################################

# Funções timestamp local
class TIMESTAMP:
	
	def get_date(self):
		try:
			timestamp = datetime.now()
			date = timestamp.strftime('%Y-%m-%d')
			return date
			
		except Exception as e:
			logger.error(f"[TIMESTAMP - DATE] Readind Error: {e}")
			return None

	def get_time(self):
		try:
			timestamp = datetime.now()
			hour = timestamp.strftime('%H:%M:%S.%f')[:-3]
			return hour

		except Exception as e:
			logger.error(f"[TIMESTAMP - HOUR] Reading Error: {e}")
			return None


########################################################################


# Função para detetar ENTER
def wait_for_enter():
    input("Press ENTER to STOP...\n\n")  # Aguarda a tecla Enter
    stop_event.set()

# Função para leitura PARTICULAS
def run_codigo1():
	REGISTERS = {
		"PM2.5 Concentration": 0x07,
		"PM10 Concentration": 0x09,
		"PM2.5 N Partícles": 0x17,
		"PM10 N Particles": 0x1B
	}

	def calculate_aqi(conc25, conc10):
		pm25 = float(conc25)
		pm10 = float(conc10)
		
		if pm25 <= 12:
			aqi_pm25 = pm25 * 50 / 12
		elif pm25 <= 35.4:
			aqi_pm25 = ((pm25 - 12.1) * 50 / (35.4 - 12.1)) + 51
		elif pm25 <= 55.4:
			aqi_pm25 = ((pm25 - 35.5) * 50 / (55.4 - 35.5)) + 101
		else:
			aqi_pm25 = ((pm25 - 55.5) * 100 / (150.4 - 55.5)) + 151

		if pm10 <= 54:
			aqi_pm10 = pm10 * 50 / 54
		elif pm10 <= 154:
			aqi_pm10 = ((pm10 - 55) * 50 / (154 - 55)) + 51
		elif pm10 <= 254:
			aqi_pm10 = ((pm10 - 155) * 50 / (254 - 155)) + 101
		else:
			aqi_pm10 = ((pm10 - 255) * 100 / (354 - 255)) + 151

		return max(aqi_pm25, aqi_pm10)

	def read_16bit_register(bus, address, reg):
		try:
			buf = bus.read_i2c_block_data(address, reg, 2)
			value = (buf[0] << 8) + buf[1]
			return value
		except Exception as e:
			logger.error(f"[PARTICLE SENSOR] Reading Error: {e}")
			return None

	bus = smbus2.SMBus(I2C_BUS)  
	try:
		timestamp = TIMESTAMP()
		time.sleep(3)

		while not stop_event.is_set():
			
			try:
				
				pm25 = read_16bit_register(bus, SENSOR_ADDRESS_PART, REGISTERS["PM2.5 Concentration"])
				pm10 = read_16bit_register(bus, SENSOR_ADDRESS_PART, REGISTERS["PM10 Concentration"])
				part25 = read_16bit_register(bus, SENSOR_ADDRESS_PART, REGISTERS["PM2.5 N Partícles"])
				part10 = read_16bit_register(bus, SENSOR_ADDRESS_PART, REGISTERS["PM10 N Particles"])

				if pm25 is not None and pm10 is not None:
					aqi = calculate_aqi(pm25, pm10)

					date = timestamp.get_date()
					hour = timestamp.get_time()
					
				if None in (pm25, pm10, part25, part10, aqi):
					particle_sensor = f"Time: {date} {hour} Incomplete Data"
					logger.error(f"Particles: {particle_sensor}")
					with sensor_data_lock:
						sensor_data["pm25"] = None
						sensor_data["pm10"] = None
						sensor_data["part25"] = None
						sensor_data["part10"] = None
						sensor_data["aqi"] = None
					time.sleep(0.5)
					continue

				particle_sensor = f"Time: {date} {hour} Particles: {pm25:.2f} {pm10:.2f} {part25:.2f} {part10:.2f} {aqi:.2f}"

				logger.info(f"Particles: {particle_sensor}")  

				# Atualiza dados globais com lock para segurança
				with sensor_data_lock:
					# sensor_data["pm25"] = pm25, pm10, part25, part10,  aqi
					sensor_data["pm25"] = f"{pm25:.2f}"
					sensor_data["pm10"] = f"{pm10:.2f}"
					sensor_data["part25"] = f"{part25:.2f}"
					sensor_data["part10"] = f"{part10:.2f}"
					sensor_data["aqi"] = f"{aqi:.2f}"

				client.publish(TOPIC_PARTICLES, particle_sensor)

				time.sleep(0.5)

			except Exception as e:
				logger.error(f"[PARTICLE SENSOR] Error: {e}")
				with sensor_data_lock:
					sensor_data["pm25"] = None
					sensor_data["pm10"] = None
					sensor_data["part25"] = None
					sensor_data["part10"] = None
					sensor_data["aqi"] = None
				time.sleep(0.5)

	finally:
		bus.close()


# Função para leitura FORMALDEIDO, TEMPERATURA, HUMIDADE
def run_codigo2(): 
	def calc_crc(data):
		crc = 0xFF
		for byte in data:
			crc ^= byte
			for _ in range(8):
				if crc & 0X80:
					crc = (crc << 1) ^ 0x31
				else:
					crc <<= 1
				crc &= 0XFF
		return crc

	def reset_sensor(bus):
		bus.write_i2c_block_data(SENSOR_ADDRESS_FORMAL, 0xD3, [0x04])
		time.sleep(0.1)

	def start_measurement(bus):
		bus.write_i2c_block_data(SENSOR_ADDRESS_FORMAL, 0x00, [0x06])

	def read_measurements(bus):
		try:
			bus.write_i2c_block_data(SENSOR_ADDRESS_FORMAL, 0x03, [0x27])
			time.sleep(0.1)
			data = bus.read_i2c_block_data(SENSOR_ADDRESS_FORMAL, 0x00, 9)
		except Exception:
			# Se falhar a comunicação com o sensor, retorna None para todos os valores
			return None, None, None

		try:
			if calc_crc(data[0:2]) != data[2]:
				logger.error("CRC mismatch for Formaldehyde")
			formaldehyde = int.from_bytes(data[0:2], byteorder='big', signed=True) / 5000.0
		except Exception:
			formaldehyde = None

		try:
			if calc_crc(data[3:5]) != data[5]:
				logger.error("CRC mismatch for Humidity")
			humidity = int.from_bytes(data[3:5], byteorder='big', signed=True) / 100.0
		except Exception:
			humidity = None

		try:
			if calc_crc(data[6:8]) != data[8]:
				logger.error("CRC mismatch for Temperature")
			temperature = int.from_bytes(data[6:8], byteorder='big', signed=True) / 200.0
		except Exception:
			temperature = None

		return formaldehyde, humidity, temperature


	bus = smbus2.SMBus(I2C_BUS)
	try:
		timestamp = TIMESTAMP()
		reset_sensor(bus)
		start_measurement(bus)
		time.sleep(3)
		

		while not stop_event.is_set():
			try:
				formaldehyde, humidity, temperature = read_measurements(bus)
				
				date = timestamp.get_date()
				hour = timestamp.get_time()
				
				if None in (formaldehyde, humidity, temperature):
					formal_temp_sensor = f"Time: {date} {hour} Incomplete Data"
					logger.error(f"Formal Temp Sensor: {formal_temp_sensor}")
					with sensor_data_lock:
						sensor_data["formal"] = None
						sensor_data["temp"] = None
						sensor_data["hum"] = None
					time.sleep(0.5)
					continue
				
				formal_temp_sensor = f"Time: {date} {hour} Formaldehyde: {formaldehyde:.4f} ppm Temperature: {temperature:.2f} ºC Humidity: {humidity:.2f} %RH"

				logger.info(f"Formaldehyde: {formal_temp_sensor}")  
				

				with sensor_data_lock:
					sensor_data["formal"] = f"{formaldehyde:.4f}"
					sensor_data["temp"] = f"{temperature:.2f}"
					sensor_data["hum"] = f"{humidity:.2f}"

				client.publish(TOPIC_FORMALDEHYDE, formal_temp_sensor)

				time.sleep(0.5)
				
				
			except Exception as e:
				logger.error(f"[FORMAL TEMP SENSOR] Error: {e}")
				with sensor_data_lock:
					sensor_data["formal"] = None
					sensor_data["temp"] = None
					sensor_data["hum"] = None
				continue
				
	finally:
		bus.close()


# Função para leitura CO2, VOC
def run_codigo3():
	def calc_crc(data):
		crc = 0xFF
		for byte in data:
			crc ^= byte
			for _ in range(8):
				if crc & 0X80:
					crc = (crc << 1) ^ 0x31
				else:
					crc <<= 1
				crc &= 0XFF
		return crc

	def start_measurement(bus):
		bus.write_i2c_block_data(SENSOR_ADDRESS_GAS, 0x20, [0x03])

	def read_measurements(bus):
		try:
			bus.write_i2c_block_data(SENSOR_ADDRESS_GAS, 0x20, [0x08])
			time.sleep(0.1)
			data = bus.read_i2c_block_data(SENSOR_ADDRESS_GAS, 0x00, 6)
		except Exception as e:
			return None, None

		try:
			if calc_crc(data[0:2]) != data[2]:
				logger.error("CRC mismatch for CO2eq")
			co2eq = int.from_bytes(data[0:2], byteorder='big', signed=True)
		except Exception:
			co2eq = None

		try:
			if calc_crc(data[3:5]) != data[5]:
				logger.error("CRC mismatch for VOC")
			voc = int.from_bytes(data[3:5], byteorder='big', signed=True) / 1000.0
		except Exception:
			voc = None

		return co2eq, voc

	bus = smbus2.SMBus(I2C_BUS)
	try:
		timestamp = TIMESTAMP()
		start_measurement(bus)
		time.sleep(3)
		

		while not stop_event.is_set():
			try:
				co2eq, voc = read_measurements(bus)

				date = timestamp.get_date()
				hour = timestamp.get_time()
				
				if None in (co2eq, voc):
					gas_sensor = f"Time: {date} {hour} Incomplete Data"
					logger.error(f"Gas Sensor: {gas_sensor}")
					with sensor_data_lock:
						sensor_data["co2eq"] = None
						sensor_data["voc"] = None
					time.sleep(0.5)
					continue


				gas_sensor = f"Time: {date} {hour} CO2eq: {co2eq:.2f} ppm VOC: {voc:.2f} ppm"

				logger.info(f"Gas Sensor: {gas_sensor}") 
				
				with sensor_data_lock:
					sensor_data["co2eq"] = f"{co2eq:.2f}"
					sensor_data["voc"] = f"{voc:.2f}"

				client.publish(TOPIC_GAS, gas_sensor)

				
				time.sleep(0.5)
				
			except Exception as e:
				logger.error(f"[GAS SENSOR] Error: {e}")
				with sensor_data_lock:
					sensor_data["co2eq"] = None
					sensor_data["voc"] = None
				continue
					
	finally:
		bus.close()



def run_codigo4():

	I2C_YEAR_H = 0
	I2C_HOUR = 4
	I2C_LAT_1 = 7
	I2C_LAT_DIS = 18
	I2C_LON_1 = 13
	I2C_LON_DIS = 12
	I2C_ALT_H = 20
	I2C_USE_STAR = 19
	I2C_SOG_H = 23
	I2C_COG_H = 26
	I2C_RGB_MODE = 36
	I2C_SLEEP_MODE = 35
	I2C_GNSS_MODE = 34

	RGB_ON = 0x05
	ENABLE_POWER = 0
	GPS_BeiDou_GLONASS = 7

	class GNSS:
		
		def __init__(self):
			self.bus = smbus2.SMBus(I2C_BUS)

		def read_bytes(self, reg, length):
			return self.bus.read_i2c_block_data(GNSS_I2C_ADDR, reg, length)

		def write_byte(self, reg, value):
			self.bus.write_byte_data(GNSS_I2C_ADDR, reg, value)

		def enable_power(self):
			self.write_byte(I2C_SLEEP_MODE, ENABLE_POWER)

		def rgb_on(self):
			self.write_byte(I2C_RGB_MODE, RGB_ON)
		
		def get_latitude(self):
			try:
				data = self.read_bytes(I2C_LAT_1, 6)
				direction = self.read_bytes(I2C_LAT_DIS, 1)[0]
				dd, mm = data[0], data[1]
				mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]
				lat_deg = dd + mm / 60.0 + mmmmm / 100000.0 / 60.0
				if direction == 83:  # 'S'
					lat_deg = -lat_deg
				return lat_deg
			except Exception as e:
				logger.error(f"[GNSS RECEIVER - LAT] Reading Error: {e}")
				return None

		def get_longitude(self):
			try:
				data = self.read_bytes(I2C_LON_1, 6)
				direction = self.read_bytes(I2C_LON_DIS, 1)[0]
				ddd, mm = data[0], data[1]
				mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]
				lon_deg = ddd + mm / 60.0 + mmmmm / 100000.0 / 60.0
				if direction == 87:  # 'W'
					lon_deg = -lon_deg
				return lon_deg
			except Exception as e:
				logger.error(f"[GNSS RECEIVER - LON] Reading Error: {e}")
				return None

		def get_altitude(self):
			try:
				data = self.read_bytes(I2C_ALT_H, 3)
				return ((data[0] & 0x7F) << 8 | data[1]) + data[2] / 100.0
			except Exception as e:
				logger.error(f"[GNSS RECEIVER - ALT] Reading Error: {e}")
				return None

		def get_num_sats(self):
			try:
				return self.read_bytes(I2C_USE_STAR, 1)[0]
			except Exception as e:
				logger.error(f"[GNSS RECEIVER - SATS] Reading Error: {e}")
				return None
			
		def get_sog(self):
			try:
				data = self.read_bytes(I2C_SOG_H, 3)
				sog = ((data[0] & 0x7F) << 8 | data[1]) + data[2] / 100.0
				return sog
			except Exception as e:
				logger.error(f"[GNSS RECEIVER - SOG] Reading Error: {e}")
				return None


		def get_cog(self):
			try:
				data = self.read_bytes(I2C_COG_H, 3)
				cog = ((data[0] & 0x7F) << 8 | data[1]) + data[2] / 100.0
				return cog
			except Exception as e:
				logger.error(f"[GNSS RECEIVER - COG] Reading Error: {e}")
				return None
		

	try:
		timestamp = TIMESTAMP()
		gnss = GNSS()
		gnss.enable_power()
		gnss.rgb_on()
		
		time.sleep(3)
		

		while not stop_event.is_set():
			try:
				date = timestamp.get_date()
				hour = timestamp.get_time()
				lat = gnss.get_latitude()
				lon = gnss.get_longitude()
				alt = gnss.get_altitude()
				sats = gnss.get_num_sats()
				sog = gnss.get_sog()
				cog = gnss.get_cog()
				
				# Se qualquer valor for None, ignora o ciclo
				if None in (lat, lon, alt, sats, sog, cog):
					gnss_receiver = f"Time: {date} {hour} Incomplete Data"
					logger.error(f"GNSS Receiver: {gnss_receiver}")
					with sensor_data_lock:
						sensor_data["lat"] = None
						sensor_data["lon"] = None
						sensor_data["alt"] = None
						sensor_data["sats"] = None
						sensor_data["sog"] = None
						sensor_data["cog"] = None
					time.sleep(0.5)
					continue
				

				gnss_receiver = f"Time: {date} {hour} Lat: {lat:.6f} Lon: {lon:.6f} Alt: {alt:.2f} N_Sats: {sats} Sog: {sog:.2f} Cog: {cog:.2f}"
				
				logger.info(f"GNSS Receiver: {gnss_receiver}")  
				
				with sensor_data_lock:
					sensor_data["lat"] = f"{lat:.6f}"
					sensor_data["lon"] = f"{lon:.6f}"
					sensor_data["alt"] = f"{alt:.2f}"
					sensor_data["sats"] = sats
					sensor_data["sog"] = f"{sog:.2f}"
					sensor_data["cog"] = f"{cog:.2f}"
					
				client.publish(TOPIC_GPS, gnss_receiver)
				
				time.sleep(0.5)
			

			except Exception as e:
				logger.error(f"[GNSS RECEIVER] Error: {e}")
				with sensor_data_lock:
					sensor_data["lat"] = None
					sensor_data["lon"] = None
					sensor_data["alt"] = None
					sensor_data["sats"] = None
					sensor_data["sog"] = None
					sensor_data["cog"] = None
				continue
	finally:
		pass
				
			


# Thread para salvar dados CSV continuamente
def salvar_csv_thread():
    timestamp = TIMESTAMP()
    
    date = timestamp.get_date()
    hour = timestamp.get_time()
   
    file_path = os.path.join(csv_dir, "dataset.csv")

    logger.info(f"READY - START Saving data to file: {file_path}")
    print(f"READY - START Saving data to file: {file_path}")
    print("")
    
    time.sleep(1)
    
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        # Cabeçalho
        writer.writerow(["date", "hour",  "pm25", "pm10", "part25", "part10", "aqi", "formaldehyde", "temperature", "humidity",  "co2eq", "voc", "lat", "lon", "alt", "sats", "sog", "cog"])
        
        while not stop_event.is_set():
            with sensor_data_lock:
                values = sensor_data.copy()
            
            date = timestamp.get_date()
            hour = timestamp.get_time()
            
            sats = values.get('sats')
            
            # Se sats for menor que 3, considera esses valores como "NA"
            if sats is not None and sats < 3:
                lat = ""
                lon = ""
                alt = ""
                sog = ""
                cog = ""
            else:
                lat = values['lat'] if values['lat'] is not None else ""
                lon = values['lon'] if values['lon'] is not None else ""
                alt = values['alt'] if values['alt'] is not None else ""
                sog = values['sog'] if values['sog'] is not None else ""
                cog = values['cog'] if values['cog'] is not None else ""

            linha = [
                date if date is not None else "",
                hour if hour is not None else "",
                values['pm25'] if values["pm25"] is not None else "",
                values['pm10'] if values["pm10"] is not None else "",
                values['part25'] if values["part25"] is not None else "",
                values['part10'] if values["part10"] is not None else "",
                values['aqi'] if values["aqi"] is not None else "",
                values['formal'] if values["formal"] is not None else "",
                values['temp'] if values["temp"] is not None else "",
                values['hum'] if values["hum"] is not None else "",
                values['co2eq'] if values["co2eq"] is not None else "",
                values['voc'] if values["voc"] is not None else "",
                lat,
                lon,
                alt,
                sats if sats not in (None, 0) else "",
                sog,
                cog,
            ]


            writer.writerow(linha)
            csvfile.flush() # Garante escrita no disco

            linha_str = " ".join(str(x) if x != "" else "NA" for x in linha)

            if "NA" not in linha_str:
                client.publish(TOPIC_SENSORS, linha_str)
                logger.info(f"Complete: {linha_str}")
                print(f"Complete: {linha_str}")
			
            else:
                logger.error(f"Incomplete: {linha_str}")  # <-- imprime no terminal
            
            time.sleep(0.5)


# Funções de callback MQTT
def on_connect(client, userdata, flags, rc):
    logger.info("Broker Connected - SENSORS")
    print("Broker Connected - SENSORS")

def on_message(client, userdata, msg):
    logger.info(f"Message Received: {msg.topic} {msg.payload}")

# Inicializar cliente MQTT com callbacks
client = mqtt.Client(client_id="sensor-client")
client.on_connect = on_connect  
client.on_message = on_message  

def setup_mqtt():
    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Broker MQTT not Connected - Error: {e}")

# Programa principal
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("gps", nargs="?", default=None, help="gps")
    args = parser.parse_args()

    setup_mqtt()

    thread1 = threading.Thread(target=run_codigo1)
    thread2 = threading.Thread(target=run_codigo2)
    thread3 = threading.Thread(target=run_codigo3)

    if args.gps == "gps":
        thread4 = threading.Thread(target=run_codigo4)

    thread_stop = threading.Thread(target=wait_for_enter)
    thread_csv = threading.Thread(target=salvar_csv_thread)

    thread1.start()
    thread2.start()
    thread3.start()
    if args.gps == "gps":
        thread4.start()
    thread_stop.start()

    logger.info("Waiting for Sensor Warm UP")
    logger.info("")
    time.sleep(5)

    thread_csv.start()

    thread_stop.join()
    thread1.join()
    thread2.join()
    thread3.join()
    if args.gps == "gps":
        thread4.join()
    thread_csv.join()

    client.loop_stop()
    client.disconnect()

    logger.info("Program Stopped.")
    print("Program Stopped.")

if __name__ == "__main__":
    main()
