// board: 1
// 03 Button: press to light the LED.
// Wiring: button across the breadboard's middle gap.
//         One leg -> BUTTON pin, the opposite leg -> GND. No resistor needed:
//         INPUT_PULLUP turns on a resistor inside the chip that holds the pin HIGH.
#include "workshop.h"

void setup() {
    pinMode(RED, OUTPUT);
    pinMode(BUTTON, INPUT_PULLUP);
}

void loop() {
    bool pressed = digitalRead(BUTTON) == LOW;  // pressing connects the pin to GND
    digitalWrite(RED, pressed ? HIGH : LOW);
    delay(10);
    // Try: make each press TOGGLE the LED instead (hint: remember the last state).
}
