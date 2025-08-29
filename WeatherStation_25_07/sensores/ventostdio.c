//==================================================
//Link sensores de Vento, SEN0483 (Speed) e SEN0482 (Dir):
//https://wiki.dfrobot.com/RS485_Wind_Speed_Transmitter_SKU_SEN0483
//https://wiki.dfrobot.com/RS485_Wind_Direction_Transmitter_SKU_SEN0482
//
//
//Link codigo oficial (referencia de implementação):
//Dir - https://github.com/DFRobotdl/RS485_Wind_Direction_Transmitter.git
//Speed - https://github.com/DFRobotdl/RS485_Wind_Speed_Transmitter.git
//
//Nota : Para modificar o endereço dos sensores segue os passos dados pelo fabricante, utilizando o código de função ModifyAddress
//==================================================

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <sys/time.h>


#define WIND_SPEED_ADDR 3
#define WIND_DIRECTION_ADDR 5

int Sfd;

// Inicializa a comunicação 
char InitSensor(char *dev) {
    struct termios tio;
    memset(&tio, 0, sizeof(tio));
    tio.c_iflag = 0;
    tio.c_oflag = 0;
    tio.c_cflag = CS8 | CREAD | CLOCAL;
    tio.c_lflag = 0;
    tio.c_cc[VMIN] = 1;
    tio.c_cc[VTIME] = 5;

    Sfd = open(dev, O_RDWR | O_NONBLOCK);
    if (Sfd < 0) {
        perror("Erro ao abrir porta serie");
        return 0;
    }

    cfsetospeed(&tio, B9600);
    cfsetispeed(&tio, B9600);
    tcsetattr(Sfd, TCSANOW, &tio);
    
    return 1;
}

// Adiciona CRC16 ao pacote Modbus
void addedCRC(unsigned char *buf, int len) {
    unsigned int crc = 0xFFFF;
    for (int pos = 0; pos < len; pos++) {
        crc ^= (unsigned int)buf[pos];
        for (int i = 8; i != 0; i--) {
            if ((crc & 0x0001) != 0) {
                crc >>= 1;
                crc ^= 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    buf[len] = crc & 0xFF;
    buf[len + 1] = (crc >> 8) & 0xFF;
}

// Verifica CRC16
unsigned int CRC16_2(unsigned char *buf, int len) {
    unsigned int crc = 0xFFFF;
    for (int pos = 0; pos < len; pos++) {
        crc ^= (unsigned int)buf[pos];
        for (int i = 8; i != 0; i--) {
            if ((crc & 0x0001) != 0) {
                crc >>= 1;
                crc ^= 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    crc = ((crc & 0x00ff) << 8) | ((crc & 0xff00) >> 8);
    return crc;
}

// Leitura de sensor 
int readSensor(unsigned char Address, float *data) {
    unsigned char request[8] = {Address, 0x03, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00};
    unsigned char response[7] = {0};
    struct timeval start, now;
    long elapsed;
    char ch;
    int ret = 0;

    addedCRC(request, 6);
    write(Sfd, request, 8);
    gettimeofday(&start, NULL);

    while (!ret) {
        gettimeofday(&now, NULL);
        elapsed = ((now.tv_sec - start.tv_sec) * 1000 + (now.tv_usec - start.tv_usec) / 1000) + 0.5;
        if (elapsed > 1000) break;

        usleep(10000);
        if (read(Sfd, &ch, 1) == 1) {
            if (ch == Address) {
                response[0] = ch;
                if (read(Sfd, &response[1], 6) == 6) {
                    if (CRC16_2(response, 5) == (response[5] * 256 + response[6])) {
                        ret = 1;
                        *data = (response[3] * 256 + response[4]) / 10.0f;
                    }
                }
            }
        }
    }
    return ret;
}

float readWindSpeed() {
    float value;
    int attempts = 0;
    while (attempts < 3) {
        if (readSensor(WIND_SPEED_ADDR, &value) == 1) return value;
        usleep(10000);
        attempts++;
    }
    return -1;
}

int readWindDirection() {
    float value;
    int attempts = 0;
    while (attempts < 3) {
        if (readSensor(WIND_DIRECTION_ADDR, &value) == 1) return value;
        usleep(10000);
        attempts++;
    }
    return -1;
}

int main() {
    int sensor_ok = 0;
    while (!sensor_ok) {
        //printf("A tentar inicializar o sensor...\n");
        sensor_ok = InitSensor("/dev/serial0");
        if (!sensor_ok) {
            //printf("Falhou. A tentar novamente em 1 segundo.\n");
            sleep(1);
        }
    }

   // printf("Sensor inicializado com sucesso!\n");

    char buffer[32];  // onde vamos guardar o comando lido

    while (1) {
       // printf("À espera de LER)...\n");

        // Lê o comando do stdin
        if (fgets(buffer, sizeof(buffer), stdin) != NULL) {
            // Remover o \n no fim do input 
            buffer[strcspn(buffer, "\n")] = '\0';

            //Verificar se é "LER"
            if (strcmp(buffer, "LER") == 0) {
                // Ler valores do sensor
                float velocidade = readWindSpeed();
                int direcao = readWindDirection();

                if (velocidade >= 0 && direcao >= 0 && direcao <= 360) {
                    // Escrever os dados no stdout
                    printf("%.2f %d\n", velocidade, direcao);
                    fflush(stdout);  // importante!
                } else {
                    printf("erro erro\n");
                    fflush(stdout);
                }

            } else {
                // Comando desconhecido
                //fprintf(stderr, "Comando desconhecido: \"%s\"\n", buffer);
                //fflush(stderr);
            }

        } else {
           // fprintf(stderr, "Erro ao ler fechar prog.\n");
            break;  
        }

        usleep(10000);  // 10 ms
    }

    //fprintf(stderr,"Programa terminado.\n");
    return 0;
}


