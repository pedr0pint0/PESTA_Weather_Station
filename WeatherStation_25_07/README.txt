Para rodar o script python weatherstation.py é necessario um virtualenv (para a biblioteca do influxdb) para intalar todas as bibliotecas necessarias utiliza o requirements.txt, fazer :

	python -m venv nome_da_venv
	source nome_da_venv/bin/activate
	pip install -r requirements.txt

Project Tree:

WeatherStation/
├── README.txt
├── requirements.txt
├── weatherstation.py           # script principal
├── sensores/                   # Módulo com sensores
│   ├── ADC_1115.py
│   ├── BMP280_BMP380.py
│   ├── mqtt_module.py
│   ├── sensors_air.py
│   ├── ventostdio              # É necessario recompilar numa nova maquina ou mudar as permissões 
│   ├── ventostdio.c            # Código-fonte 


Config Crontab : sudo crontab -e

adicionar: @reboot sleep 100 && /home/cister/WeatherStation/weather/bin/python /home/cister/WeatherStation/weatherstation.py >> /home/cister/WeatherStation/log.txt 2>&1
		
