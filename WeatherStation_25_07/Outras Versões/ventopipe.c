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

// Inicializa a comunicação RS485
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

// Leitura de sensor via Modbus RTU
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
    while (InitSensor("/dev/serial0") == 0) {
        usleep(1000000); // Espera 1s
    }

    FILE *request_fp;
    FILE *response_fp;
    char buffer[32];

    while (1) {
        request_fp = fopen("/tmp/vento_request", "r");
        if (request_fp == NULL) {
            perror("Erro ao abrir /tmp/vento_request");
            sleep(1);
        }

        if (fgets(buffer, sizeof(buffer), request_fp) != NULL) {
            fclose(request_fp);

            float windSpeed = readWindSpeed();
            int windDir = readWindDirection();

            response_fp = fopen("/tmp/vento_response", "w");
            if (response_fp == NULL) {
                perror("Erro ao abrir /tmp/vento_response");
              
            }

            if (windSpeed >= 0 && windDir >= 0 && windDir <= 360) {
                fprintf(response_fp, "%.2f %d\n", windSpeed, windDir);
            } else {
                fprintf(response_fp, "erro erro\n");
            }

            fflush(response_fp);
            fclose(response_fp);
        } else {
            fclose(request_fp);
        }

        usleep(100000); // 100ms
    }

    return 0;
}
