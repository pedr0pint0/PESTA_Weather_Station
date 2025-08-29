#include "RS485_Wind_Speed_Transmitter.h"

int main() {
  char Address = 2;
  float WindSpeed = 0;
  while (InitSensor("/dev/serial0") == 0) {
    delayms(1000);
  }

  // Modify sensor address
  if (ModifyAddress(0, Address)) {
    printf("Address modified successfully.\n");
  } else {
    printf("Address modification failed!\n");
    printf("Please check whether the sensor connection is normal\n");
    return 0;
  }

  while (1) {
    WindSpeed = readWindSpeed(Address);
    if (WindSpeed >= 0) {
      printf("WindSpeed:%g m/s\n\n", WindSpeed);
    } else {
      printf("Please check whether the sensor connection is normal\n");
      return 0;
    }
    delayms(50);
  }
  // serialClose(fd);
  return 1;
}
