# mqtt_module.py
import paho.mqtt.client as mqtt
import warnings
import time

warnings.filterwarnings("ignore")

# Estrutura padrão dos dados recebidos via MQTT
ESTRUTURA = {
    'date': "N/A",           # Data da leitura
    'hour': "N/A",           # Hora da leitura
    'pm25': 999999999.0,         # Partículas PM2.5 e PM10
    'pm10': 999999999.0,         
    'part25': 999999999.0,       
    'part10': 999999999.0,       
    'aqi': 999999999.0,          # Índice de qualidade do ar
    'formaldehyde': 999999999.0, # Formaldeído
    'temperature': 999999999.0,  # Temperatura
    'humidity': 999999999.0,     # Humidade
    'co2eq': 999999999.0,        # CO2 equivalente
    'voc': 999999999.0,          # Compostos orgânicos voláteis
    'lat': 999999999.0,          # Latitude GPS
    'lon': 999999999.0,          # Longitude GPS
    'alt': 999999999.0,          # Altitude GPS
    'sats': 999999999,           # Número de satélites
    'sog': 999999999.0,          # Velocidade sobre o solo ?
    'cog': 999999999.0           # Curso sobre o solo ?
    }

#Variavel global para armazenar os dados mais recentes 
mqtt_recente = ESTRUTURA.copy()


def on_connect(client, userdata, flags, rc):
    if rc == 0: #rc = connection result !=0 connection refused
        print("Conectado ao broker MQTT")
        client.subscribe("quad_sensor/sensors") #,qos = 0
    else:
        print(f"Falha de conexão. Erro: {rc}")

def on_message(client, userdata, msg):
    global mqtt_recente
    payload = msg.payload.decode('utf-8').strip()
    #print(f"Mensagem recebida: {payload}")  #Escreve no terminal a mensagem do topico
    
    #Separa todos os valores separados por espaços
    values = payload.split()

    if len(values) != 18:
        print("Número de campos errado")
        return

    try:
        mqtt_recente = {
            'date': values[0],
            'hour': values[1],
            'pm25': float(values[2]), #particulas
            'pm10': float(values[3]),
            'part25': float(values[4]),
            'part10': float(values[5]),
            'aqi': float(values[6]),
            'formaldehyde': float(values[7]),
            'temperature': float(values[8]),
            'humidity': float(values[9]),
            'co2eq': float(values[10]), #co2
            'voc': float(values[11]),
            'lat': float(values[12]),#gps
            'lon': float(values[13]),
            'alt': float(values[14]),
            'sats': int(values[15]),
            'sog': float(values[16]),
            'cog': float(values[17])
        }
    except ValueError as e:
        print("Erro na conversão de valores:", e)
         
    
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def init_mqtt(broker_address, broker_port):
    client.connect(broker_address, broker_port, 60)
    client.loop_start()


def get_mqtt_values():
    global mqtt_recente
    dados = mqtt_recente.copy()
    mqtt_recente = ESTRUTURA.copy()

    return dados

    
def stop_mqtt():
    client.loop_stop()
    client.disconnect()

