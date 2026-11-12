// board: 4
// 00 Hello: board self-test. Prints, then walks every workshop LED.
// The instructor flashes this to every board before class (ws flash-all 00_hello).
// 01 Blink: one LED on and off.
// Wiring: RED pin -> 220 ohm resistor -> LED long leg; LED short leg -> GND.
#include "workshop.h"

void setup() {
    pinMode(RED, OUTPUT);
}

void loop() {
    digitalWrite(RED, HIGH);
    delay(500);
    digitalWrite(RED, LOW);
    delay(500);
    // Try: make it blink faster. What's the fastest blink you can still see?
}
