# Weather Station - Python Script
# Coleta dados de sensores ambientais, armazena em InfluxDB e CSV, e exibe no terminal.
# Sensores: BMP280, BMP388, ADC1115 (sensor Humidade Solo), Dir e Speed Vento, e dados via MQTT (qualidade do ar, GPS, etc.)

from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import time
import pandas as pd
import os

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

from sensores.mqtt_module import * 
from sensores.ADC_1115 import *
from sensores.BMP280_BMP380 import init_bmp280, init_bmp388, read_temperature_bmp280, read_pressure_bmp280, read_temperature_bmp388, read_pressure_bmp388

################################### Configuração MQTT #############################################

mqtt_ativo = True      # True para ativar leitura de dados MQTT, False para desativar
broker_ip = "192.168.10.150"
broker_port = 1883

###################################################################################################

################################## Configuração InfluxDB ##########################################

bucket = "weather"
org = "cister"
token = "-790oFb-_gdC4tCG6x7jkHwDWM1U0xwSsNLumJOXiPQ1-PgKQbrnKMLYVBYCN3WxMARSATzczpTpmnKavUv8qw=="
url = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(
    url=url,
    token=token,
    org=org
)

write_api = client.write_api(write_options=SYNCHRONOUS)

##################################################################################################

################################## Caminho e Estrutura CSV #######################################

inicio = datetime.now(ZoneInfo("Europe/Lisbon"))
timestamp_str = inicio.strftime("%Y-%m-%d_%H-%M-%S")

csv_dir = f"/home/cister/WeatherStation/{timestamp_str}"
os.makedirs(csv_dir, exist_ok=True)

csv_file = os.path.join(csv_dir, "dataset.csv")

columns = [
    "timestamp",
    "Temp_BMP280",
    "Press_BMP280",
    "Temp_BMP388",
    "Press_BMP388",
    "Tensao_ADC",
    "Raw_ADC",
    "Humidade_ADC",
    "Velocidade_Vento",
    "Direcao_Graus",
    "Direcao_Texto",
    "pm25",
    "pm10",
    "part25",
    "part10",
    "aqi",
    "formaldehyde",
    "temperature",
    "humidity",
    "co2eq",
    "voc",
    "lat",
    "lon",
    "alt",
    "sats",
    "sog",
    "cog"
]

##################################################################################################

################################## Inicialização dos Sensores ###################################

# Inicia MQTT se ativo
if mqtt_ativo == True:
    init_mqtt(broker_ip,broker_port)
    print("MQTT inicializado")
else:
    print("MQTT desativado manualmente")

# Inicializa sensores BMP280, BMP388 e ADC1115
init_bmp280()
init_bmp388()
write_config_adc()
print("Sensores BMP280, BMP388 e ADC1115 inicializados")

# Processo iniciação script vento.c
vento_proc = subprocess.Popen(
    ["/home/cister/WeatherStation/sensores/ventostdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
print("Sensores de vento inicializados")

##################################################################################################

# Lista de direções do vento
WindDirection = [
    "Norte", "Norte-Nordeste", "Nordeste", "Este-Nordeste",
    "Este", "Este-Sudeste", "Sudeste", "Sul-Sudeste",
    "Sul", "Sul-Sudoeste", "Sudoeste", "Oeste-Sudoeste",
    "Oeste", "Oeste-Noroeste", "Noroeste", "Norte-Noroeste"
]

#Funções Auxiliares
def graus_para_direcao(graus):
    if graus < 0 or graus > 360:
        return "Desconhecida"
    index = int((graus + 11.25) / 22.5) % 16
    return WindDirection[index]
    
def adc_para_humidade(voltage): #Humidade sempre relativa à terra escolhida (fabricante dizia 50-60%)
    # Calibração do sensor:
    seco = 0    # Tensão em solo seco relativo (2.2604 - 0% humidade) ou sensor fora da terra - 0V 
    humido = 2.5  # Tensão em solo húmido (100% humidade)

    if voltage <= seco:
        return 0
    if voltage >= humido:
        return 100

    return ((voltage - seco) / (humido - seco)) * 100


#Leitura e envio para o influx dos dados dos sensores
try:
    while True:
        # Lê vento
        vento_proc.stdin.write("LER\n")
        vento_proc.stdin.flush()

        linha = vento_proc.stdout.readline().strip()
        if linha: # linha está vazia ? 
            try:
                velocidade_str, direcao_str = linha.split()
                velocidade = float(velocidade_str)
                direcao = int(direcao_str)
                direcao_txt = graus_para_direcao(direcao)
            except:
                #print("Erro ao ler dados sensor de Vento")
                velocidade = None
                direcao = None
                direcao_txt = "Sem resposta"
                
        else:
            velocidade = None
            direcao = None
            direcao_txt = "Sem resposta"

        # Lê sensores
        
        temp280 = read_temperature_bmp280()
        press280 = read_pressure_bmp280()
        temp388 = read_temperature_bmp388()
        press388 = read_pressure_bmp388()
        voltage,raw_adc = read_adc()
        humidade = adc_para_humidade(voltage)

        # Escreve dados locais na InfluxDB
        p = influxdb_client.Point("weather_station_v4") \
            .field("Direcao_Texto", direcao_txt) \
            .field("Temp_BMP280", temp280) \
            .field("Press_BMP280", press280) \
            .field("Temp_BMP388", temp388) \
            .field("Press_BMP388", press388) \
            .field("Tensao_ADC", voltage) \
            .field("Raw_ADC", raw_adc) \
            .field("Humidade_Solo", humidade) \
            .field("Velocidade_Vento", velocidade if velocidade is not None else 1000.0) \
            .field("Direcao_Graus", direcao if direcao is not None else 1000) \
            .time(datetime.now(ZoneInfo("Europe/Lisbon")))

        write_api.write(bucket=bucket, org=org, record=p)

        # Lê e escreve dados do MQTT
        if mqtt_ativo == True:
            
            mqtt_data = get_mqtt_values()
            
            if mqtt_data:
                p_mqtt = influxdb_client.Point("air_quality_v3") \
                    .field("pm25", mqtt_data["pm25"]) \
                    .field("pm10", mqtt_data["pm10"]) \
                    .field("part25", mqtt_data["part25"]) \
                    .field("part10", mqtt_data["part10"]) \
                    .field("aqi", mqtt_data["aqi"]) \
                    .field("formaldehyde", mqtt_data["formaldehyde"]) \
                    .field("temperature", mqtt_data["temperature"]) \
                    .field("humidity", mqtt_data["humidity"]) \
                    .field("co2eq", mqtt_data["co2eq"]) \
                    .field("voc", mqtt_data["voc"]) \
                    .field("lat", float(mqtt_data["lat"])) \
                    .field("lon", float(mqtt_data["lon"])) \
                    .field("alt", float(mqtt_data["alt"])) \
                    .field("sats", mqtt_data["sats"]) \
                    .field("sog", mqtt_data["sog"]) \
                    .field("cog", mqtt_data["cog"]) \
                    .time(datetime.now(ZoneInfo("Europe/Lisbon")))


                write_api.write(bucket=bucket, org=org, record=p_mqtt)
            else:
                print("MQTT: Sem dados.")
                
        else: 
            mqtt_data= None

        #Escreve no csv            
        if mqtt_ativo and mqtt_data:
            linha = {
            "timestamp": datetime.now(ZoneInfo("Europe/Lisbon")).isoformat(),
            "Temp_BMP280": temp280,
            "Press_BMP280": press280,
            "Temp_BMP388": temp388,
            "Press_BMP388": press388,
            "Tensao_ADC": voltage,
            "Raw_ADC": raw_adc,
            "Humidade_ADC": humidade,
            "Velocidade_Vento": velocidade if velocidade is not None else None,
            "Direcao_Graus": direcao if direcao is not None else None,
            "Direcao_Texto": direcao_txt,
            "pm25": mqtt_data.get("pm25"),
            "pm10": mqtt_data.get("pm10"),
            "part25": mqtt_data.get("part25"),
            "part10": mqtt_data.get("part10"),
            "aqi": mqtt_data.get("aqi"),
            "formaldehyde": mqtt_data.get("formaldehyde"),
            "temperature": mqtt_data.get("temperature"),
            "humidity": mqtt_data.get("humidity"),
            "co2eq": mqtt_data.get("co2eq"),
            "voc": mqtt_data.get("voc"),
            "lat": float(mqtt_data.get("lat", 0)),
            "lon": float(mqtt_data.get("lon", 0)),
            "alt": float(mqtt_data.get("alt", 0)),
            "sats": mqtt_data.get("sats"),
            "sog": mqtt_data.get("sog"),
            "cog": mqtt_data.get("cog"),
        }

        df_linha = pd.DataFrame([linha], columns=columns)

        if not os.path.isfile(csv_file):
            df_linha.to_csv(csv_file, mode='w', index=False, header=True)
        else:
            df_linha.to_csv(csv_file, mode='a', index=False, header=False)
            
        # Mostra no terminal
        print("\n==========================================")
        print(f"{datetime.now(ZoneInfo('Europe/Lisbon'))}")
        print(f"BMP280:     Temp = {temp280:.2f} °C   Press = {press280:.2f} hPa")
        print(f"BMP388:     Temp = {temp388:.2f} °C   Press = {press388:.2f} hPa")
        print(f"ADC1115:    Tensão = {voltage:.2f} V   Raw_ADC = {raw_adc}    Humidade Solo = {humidade} %")
        #print(f"Vento:      Velocidade = {velocidade:.2f} m/s   Direção = {direcao}° - {direcao_txt}")
        if velocidade is not None and direcao is not None:
            print(f"Vento:      Velocidade = {velocidade:.2f} m/s   Direção = {direcao}° - {direcao_txt}")
        else:
            print("Vento:      Erro ao ler dados do vento.")

        if mqtt_ativo:
            print(f"Partículas: PM2.5 (ug/m^3) = {mqtt_data['pm25']}  PM1.0 (ug/m^3) = {mqtt_data['pm10']} Nº Part2.5 (em 0.1l de ar) = {mqtt_data['part25']}  Nº Part1.0 (em 0.1l de ar) = {mqtt_data['part10']}  AQI = {mqtt_data['aqi']}")
            print(f"Ar:         Temp = {mqtt_data['temperature']} °C  Humidade = {mqtt_data['humidity']} %  Formaldeído = {mqtt_data['formaldehyde']} ppm")
            print(f"Gases:      CO2eq = {mqtt_data['co2eq']} ppm  VOC = {mqtt_data['voc']} ppm")
            print(f"GPS:        Lat = {mqtt_data['lat']}º  Lon = {mqtt_data['lon']}º  Alt = {mqtt_data['alt']} m  NºSats = {mqtt_data['sats']}  SOG = {mqtt_data['sog']} knots COG = {mqtt_data['cog']}º")
        else:
            print("MQTT: Desativado.")

            
        print("==========================================\n")
        
        time.sleep(60)

except KeyboardInterrupt:
    print("\nPrograma interrompido.")
    vento_proc.terminate()
    if mqtt_ativo:
        stop_mqtt()
