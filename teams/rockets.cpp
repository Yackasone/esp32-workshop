// board: 1
// 02 Traffic light: three LEDs, one at a time.
// Wiring: RED, YELLOW, GREEN pins, each -> 220 ohm -> LED -> GND.
#include "workshop.h"

void setup() {
    pinMode(RED, OUTPUT);
    pinMode(YELLOW, OUTPUT);
    pinMode(GREEN, OUTPUT);
}

void show(int pin, int ms) {
    digitalWrite(RED, LOW);
    digitalWrite(YELLOW, LOW);
    digitalWrite(GREEN, LOW);
    digitalWrite(pin, HIGH);
    printf("light on pin %d for %d ms\n", pin, ms);
    delay(ms);
}

void loop() {
    show(GREEN, 3000);
    show(YELLOW, 1000);
    show(RED, 3000);
    // Try: add the UK "red + yellow together" step before green.
}
