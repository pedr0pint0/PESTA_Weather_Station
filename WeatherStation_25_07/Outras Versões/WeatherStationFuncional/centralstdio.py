from BMP280_BMP380 import init_bmp280, init_bmp388, read_temperature_bmp280, read_pressure_bmp280, read_temperature_bmp388, read_pressure_bmp388
from ADC_1115 import read_adc, write_config_adc

from datetime import datetime
import pandas as pd
import subprocess
import time
import os

# Inicializa os sensores
init_bmp280()
init_bmp388()
write_config_adc()
print("Sensores BMP280, BMP388 e ADC1115 inicializados")

# Inicia o processo vento
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

# Nome do ficheiro CSV
csv_filename = "dados_sensores.csv"

# Cria o cabeçalho se o ficheiro ainda não existir
if not os.path.exists(csv_filename):
    df = pd.DataFrame(columns=[
        "Data", "Hora",
        "Temp_BMP280", "Press_BMP280",
        "Temp_BMP388", "Press_BMP388",
        "Tensao_ADC",
        "Velocidade_Vento", "Direcao_Graus", "Direcao_Texto"
    ])
    df.to_csv(csv_filename, index=False)

try:
    while True:
        # Envia pedido ao programa C
        vento_proc.stdin.write("LER\n")
        vento_proc.stdin.flush()

        # Lê resposta do vento
        linha = vento_proc.stdout.readline().strip()
        if linha:
            #try:
                velocidade_str, direcao_str = linha.split()
                velocidade = float(velocidade_str)
                direcao = int(direcao_str)
                direcao_txt = graus_para_direcao(direcao)
            #except ValueError:
                #velocidade = None
                #direcao = None
                #direcao_txt = "Erro ao converter"
        else:
            velocidade = None
            direcao = None
            direcao_txt = "Sem resposta"

        now = datetime.now()
        data_str = now.strftime("%Y-%m-%d")
        hora_str = now.strftime("%H:%M:%S")

        temp280 = read_temperature_bmp280()
        press280 = read_pressure_bmp280()
        temp388 = read_temperature_bmp388()
        press388 = read_pressure_bmp388()
        voltage = read_adc()

        # Criar DataFrame com uma linha
        df_linha = pd.DataFrame([{
            "Data": data_str,
            "Hora": hora_str,
            "Temp_BMP280": temp280,
            "Press_BMP280": press280,
            "Temp_BMP388": temp388,
            "Press_BMP388": press388,
            "Tensao_ADC": voltage,
            "Velocidade_Vento": velocidade,
            "Direcao_Graus": direcao,
            "Direcao_Texto": direcao_txt
        }])

        # Escrever no CSV (modo append, sem cabeçalho)
        df_linha.to_csv(csv_filename, mode='a', index=False, header=False,float_format='%.2f')

        # Mostrar no terminal
        print("\n==========================================")
        print(f"Data: {data_str}  Hora: {hora_str}")
        print(f"BMP280:  Temp={temp280:.2f} °C  Press={press280:.2f} hPa")
        print(f"BMP388:  Temp={temp388:.2f} °C  Press={press388:.2f} hPa")
        print(f"ADC1115: Tensão={voltage:.2f} V")
        if velocidade is not None and direcao is not None:
            print(f"Vento:   Velocidade={velocidade:.2f} m/s  Direção={direcao}° - {direcao_txt}")
        else:
            print("Erro ao ler dados do vento.")
        print("==========================================\n")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nPrograma interrompido.")
    vento_proc.terminate()
