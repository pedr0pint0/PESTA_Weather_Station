from BMP280_BMP380 import init_bmp280, init_bmp388, read_temperature_bmp280, read_pressure_bmp280, read_temperature_bmp388, read_pressure_bmp388
from ADC_1115 import read_adc, write_config_adc
from datetime import datetime

import time
import os

pipe_request = "/tmp/vento_request"
pipe_response = "/tmp/vento_response"

# Inicializa os sensores BMP280 e BMP388
init_bmp280()
init_bmp388()
write_config_adc()
print("Sensores BMP280, BMP388 e ADC1115 inicializados com sucesso!")

# Direções do vento em 16 sectores de 22.5 graus
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
        # Pedir dados ao vento.c
        with open(pipe_request, "w") as req:
            req.write("pedido\n")
            req.flush()

        time.sleep(1)

        # Ler resposta
        with open(pipe_response, "r") as resp:
            linha = resp.readline().strip()
            if linha:
                velocidade_str, direcao_str = linha.split()
                velocidade = float(velocidade_str)
                direcao = float(direcao_str)
                direcao_txt = graus_para_direcao(direcao)
            else:
                direcao = None
                velocidade = None
                direcao_txt = "Erro"
        
        now = datetime.now()
        print(f"\nHora atual: {now.strftime('%H:%M:%S')}")
        data_str = now.strftime("%Y-%m-%d")
        hora_str = now.strftime("%H:%M:%S")

        temp280 = read_temperature_bmp280()
        press280 = read_pressure_bmp280()
        temp388 = read_temperature_bmp388()
        press388 = read_pressure_bmp388()
        voltage = read_adc()

        dados = {
            "data": data_str,
            "hora": hora_str,
            "temp_bmp280": temp280,
            "press_bmp280": press280,
            "temp_bmp388": temp388,
            "press_bmp388": press388,
            "tensao_adc": voltage,
            "velocidade_vento": velocidade,
            "direcao_vento_graus": direcao,
            "direcao_vento_txt": direcao_txt
        }

        print(f"Dados: {dados}")
        print(f"Vento: {direcao:.0f}° - {direcao_txt}, {velocidade:.1f} m/s")
        time.sleep(20)

except KeyboardInterrupt:
    print("\nPrograma interrompido.")
