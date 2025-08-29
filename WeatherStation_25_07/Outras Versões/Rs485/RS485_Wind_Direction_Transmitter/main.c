#include "RS485_Wind_Direction_Transmitter.h"
#include <stdio.h>

int main() {
    char Address = 2;
    
    // Definição das direções do vento
    const char *WindDirection[] = {
        "North", "North-Northeast", "Northeast", "East-Northeast",
        "East", "East-Southeast", "Southeast", "South-Southeast",
        "South", "South-Southwest", "Southwest", "West-Southwest",
        "West", "West-Northwest", "Northwest", "North-Northwest"
    };

    while (InitSensor("/dev/serial0") == 0) {
        delayms(1000);
    }

    // Modificar endereço do sensor
    if (ModifyAddress(0, Address)) {
        printf("Address modified successfully.\n");
    } else {
        printf("Address modification failed!\n");
        printf("Please check whether the sensor connection is normal\n");
        return 0;
    }

    while (1) {
        int windIndex = readWindDirection(Address);

        // Normalizar o índice e mapear para direções
        if (windIndex >= 0 && windIndex <= 360) {
            int index = (windIndex + 11.25) / 22.5; // Arredondamento para o intervalo correto
            index = index % 16; // Garantir que permanece dentro do range 0-15
            
            printf("Wind Direction: %s (%d°)\n", WindDirection[index], windIndex);
        } else {
            printf("Invalid wind direction value: %d\n", windIndex);
        }

        delayms(50);
    }

    return 1;
}
