import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

from BMP280_BMP380 import init_bmp280, init_bmp388, read_temperature_bmp280, read_pressure_bmp280, read_temperature_bmp388, read_pressure_bmp388
from ADC_1115 import read_adc, write_config_adc

from datetime import datetime
import subprocess
import time

# InfluxDB Config (https://docs.influxdata.com/influxdb/v2/api-guide/client-libraries/python/)
bucket = "weather"
org = "cister"
token = "8d_3CkcrtbBTJtqwSDnKgCbYhp9AkuhIFR8JrpEpWo0azWqd7aSOqlWDTWAizLBN6NpfXRozdKyQ3jwgZCowg=="
url = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(
    url=url,
    token=token,
    org=org
)

write_api = client.write_api(write_options=SYNCHRONOUS)

# Inicializa sensores
init_bmp280()
init_bmp388()
write_config_adc()
print("Sensores BMP280, BMP388 e ADC1115 inicializados")

# Processo do vento
vento_proc = subprocess.Popen(
    ["./ventostdio"],
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
        if linha:
            velocidade_str, direcao_str = linha.split()
            velocidade = float(velocidade_str)
            direcao = int(direcao_str)
            direcao_txt = graus_para_direcao(direcao)
        else:
            velocidade = None
            direcao = None
            direcao_txt = "Sem resposta"

        # Lê sensores
        temp280 = read_temperature_bmp280()
        press280 = read_pressure_bmp280()
        temp388 = read_temperature_bmp388()
        press388 = read_pressure_bmp388()
        voltage = read_adc()

        # Mostra no terminal
        print("\n==========================================")
        print(f"BMP280:  Temp={temp280:.2f} °C  Press={press280:.2f} hPa")
        print(f"BMP388:  Temp={temp388:.2f} °C  Press={press388:.2f} hPa")
        print(f"ADC1115: Tensão={voltage:.2f} V")
        if velocidade is not None and direcao is not None:
            print(f"Vento:   Velocidade={velocidade:.2f} m/s  Direção={direcao}° - {direcao_txt}")
        else:
            print("Erro ao ler dados do vento.")
        print("==========================================\n")

        # Escreve no InfluxDB (seguindo exemplo oficial)
        p = influxdb_client.Point("weather_station") \
            .tag("Direcao_Texto", direcao_txt) \
            .field("Temp_BMP280", temp280) \
            .field("Press_BMP280", press280) \
            .field("Temp_BMP388", temp388) \
            .field("Press_BMP388", press388) \
            .field("Tensao_ADC", voltage) \
            .field("Velocidade_Vento", velocidade if velocidade is not None else 0.0) \
            .field("Direcao_Graus", direcao if direcao is not None else 0) \
            .time(datetime.utcnow())

        write_api.write(bucket=bucket, org=org, record=p)

        time.sleep(1)

except KeyboardInterrupt:
    print("\nPrograma interrompido.")
    vento_proc.terminate()

