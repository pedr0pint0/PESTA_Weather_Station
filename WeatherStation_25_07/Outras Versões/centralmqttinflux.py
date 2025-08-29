import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

from mqtt_module import init_mqtt, get_mqtt_values, stop_mqtt  

from BMP280_BMP380 import init_bmp280, init_bmp388, read_temperature_bmp280, read_pressure_bmp280, read_temperature_bmp388, read_pressure_bmp388
from ADC_1115 import read_adc, write_config_adc

from datetime import datetime
import subprocess
import time

# Ativar ou desativar MQTT manualmente
mqtt_ativo = True  # Muda para True para ativar leitura de dados mqtt <----------

# InfluxDB Config
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

# Inicia MQTT
if mqtt_ativo:
    sucesso_mqtt = init_mqtt()
    if sucesso_mqtt:
        print("MQTT inicializado")
    else:
        print("MQTT desativado automaticamente (falha na ligação).")
        mqtt_ativo = False
else:
    print("MQTT desativado manualmente")

# Inicializa sensores
init_bmp280()
init_bmp388()
write_config_adc()
print("Sensores BMP280,99999 BMP388 e ADC1115 inicializados")

# Processo do vento
vento_proc = subprocess.Popen(
    ["/home/cister/WeatherStation/ventostdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
print("Sensores de vento inicializados")

# Lista de direções do vento
WindDirection = [
    "Norte", "Norte-Nordeste", "Nordeste", "Este-Nordeste",
    "Este", "Este-Sudeste", "Sudeste", "Sul-Sudeste",
    "Sul", "Sul-Sudoeste", "Sudoeste", "Oeste-Sudoeste",
    "Oeste", "Oeste-Noroeste", "Noroeste", "Norte-Noroeste"
]

def graus_para_direcao(graus):
    if graus < 0 or graus > 360:
        return "Desconhecida"
    index = int((graus + 11.25) / 22.5) % 16
    return WindDirection[index]

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

        # Escreve dados locais na InfluxDB
        p = influxdb_client.Point("weather_station_v2") \
            .field("Direcao_Texto", direcao_txt) \
            .field("Temp_BMP280", temp280) \
            .field("Press_BMP280", press280) \
            .field("Temp_BMP388", temp388) \
            .field("Press_BMP388", press388) \
            .field("Tensao_ADC", voltage) \
            .field("Raw_ADC", raw_adc) \
            .field("Velocidade_Vento", velocidade if velocidade is not None else 1000.0) \
            .field("Direcao_Graus", direcao if direcao is not None else 1000) \
            .time(datetime.utcnow())

        write_api.write(bucket=bucket, org=org, record=p)

        # Lê e escreve dados do MQTT
        if mqtt_ativo == True:
            
            mqtt_data = get_mqtt_values()
            
            if mqtt_data:
                p_mqtt = influxdb_client.Point("air_quality") \
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
                    .time(datetime.utcnow())

                write_api.write(bucket=bucket, org=org, record=p_mqtt)
            else:
                print("MQTT: Sem dados.")
                
        else: 
            mqtt_data= None
        
        # Mostra no terminal
        print("\n==========================================")
        print(f"BMP280:     Temp = {temp280:.2f} °C   Press = {press280:.2f} hPa")
        print(f"BMP388:     Temp = {temp388:.2f} °C   Press = {press388:.2f} hPa")
        print(f"ADC1115:    Tensão = {voltage:.2f} V   Raw_ADC = {raw_adc}")
        #print(f"Vento:      Velocidade = {velocidade:.2f} m/s   Direção = {direcao}° - {direcao_txt}")
        if velocidade is not None and direcao is not None:
            print(f"Vento:      Velocidade = {velocidade:.2f} m/s   Direção = {direcao}° - {direcao_txt}")
        else:
            print("Vento:      Erro ao ler dados do vento.")

        if mqtt_ativo:
            print(f"Partículas: PM2.5 = {mqtt_data['pm25']}  PM10 = {mqtt_data['pm10']}  Part >2.5 = {mqtt_data['part25']}  Part >10 = {mqtt_data['part10']}  AQI = {mqtt_data['aqi']}")
            print(f"Ar:         Temp = {mqtt_data['temperature']} °C  Humidade = {mqtt_data['humidity']} %  Formaldeído = {mqtt_data['formaldehyde']}")
            print(f"Gases:      CO2eq = {mqtt_data['co2eq']} ppm  VOC = {mqtt_data['voc']}")
            print(f"GPS:        Lat = {mqtt_data['lat']}  Lon = {mqtt_data['lon']}  Alt = {mqtt_data['alt']} m  Sats = {mqtt_data['sats']}  SOG = {mqtt_data['sog']}  COG = {mqtt_data['cog']}")
        else:
            print("MQTT: Desativado.")

            
        print("==========================================\n")
        
        time.sleep(1)

except KeyboardInterrupt:
    print("\nPrograma interrompido.")
    vento_proc.terminate()
    if mqtt_ativo:
        stop_mqtt()
