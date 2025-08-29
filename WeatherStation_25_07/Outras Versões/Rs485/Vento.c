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

// Calcula CRC16 para verificação --> Cyclic Redundancy Check utiliza XOR (^=)
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

// Função leitura de um sensor RS485 - MODBUSRTU
int readSensor(unsigned char Address, float *data) {
    unsigned char request[8] = {Address, 0x03, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00}; //comando Modbus a ser enviado
    //Endereço ; codigo da funçao neste caso ler ; as 4 pos seguintes sao referentes a posição e quantidade de registros; as ultimas 2 sera colocado o crc16
    unsigned char response[7] = {0}; //armazena a resposta
    struct timeval start, now;
    long elapsed;
    char ch;
    int ret = 0;

    addedCRC(request, 6); // adiciona o crc calculado em cr16_2
    write(Sfd, request, 8); //envia o pedido
    gettimeofday(&start, NULL);

    while (!ret) { //leitura ate sucesso ou timeout
        
        gettimeofday(&now, NULL);
        elapsed = ((now.tv_sec - start.tv_sec) * 1000 + (now.tv_usec - start.tv_usec) / 1000) + 0.5;
        
        if (elapsed > 1000){
             break; // Timeout
         }

        usleep(10000); //10ms
        if (read(Sfd, &ch, 1) == 1) { //tenta ler o primeiro byte e compara com o adress
            if (ch == Address) {
                response[0] = ch;
                if (read(Sfd, &response[1], 6) == 6) { // se adress igual le os 6 bytes seguintes
                    if (CRC16_2(response, 5) == (response[5] * 256 + response[6])) { //verifica a integridade dos dados com o rcr16 *256 desloca pra a parte mais significativa
                                                                                    // e soma o [6] que contem a parte menos significativa compara o calculado da resposta com o que veio na resposta 
                                                                                    // é por isso que só faz crc16 ate ao byte 5 da resposta
                        ret = 1;
                        *data = (response[3] * 256 + response[4]) / 10.0f; //modifica o valor 
                    }
                }
            }
        }
    }
    return ret; // 1=sucesso 0=erro
}

// Leitura da velocidade do vento
float readWindSpeed() {
    float value;
    int attempts = 0;
    
    while (attempts < 3) {
        if (readSensor(WIND_SPEED_ADDR, &value) == 1) {
            return value;
        }
        usleep(10000); // Espera 10ms antes de tentar novamente
        attempts++;
    }

    return -1; // Erro após 3 tentativas
}
// Leitura da direcao do vento
int readWindDirection() {
    float value;
    int attempts = 0;
    
    while (attempts < 3) {
        if (readSensor(WIND_DIRECTION_ADDR, &value) == 1) {
            return value;
        }
        usleep(10000); // Espera 10ms antes de tentar novamente
        attempts++;
    }

    return -1; // Erro após 3 tentativas
}


int main() {
    
    const char *WindDirection[] = {
        "Norte", "Norte-Nordeste", "Nordeste", "Este-Nordeste",
        "Este", "Este-Sudeste", "Sudeste", "Sul-Sudeste",
        "Sul", "Sul-Sudoeste", "Sudoeste", "Oeste-Sudoeste",
        "Oeste", "Oeste-Noroeste", "Noroeste", "Norte-Noroeste"
    };


    while (InitSensor("/dev/serial0") == 0) { //Modificar para a porta utilizada
    usleep(1000000); //1s
    }

    while (1) {
        float windSpeed = readWindSpeed();
        int windDir = readWindDirection();

        if (windSpeed >= 0) {
            printf("Velocidade: %.1f m/s\n", windSpeed);
        } else {
            printf("Erro ao ler a velocidade do vento!\n");
        }

        if (windDir >= 0 && windDir <= 360) {
            int index = (int)((windDir + 11.25) / 22.5) % 16;
            printf("Direção: %s (%d°)\n", WindDirection[index], windDir);
        } else {
            printf("Erro ao ler a direção do vento!\n");
        }
        usleep(50000);
    }

    return 0;
}
