// board: 1
// 00 Hello: board self-test. Prints, then walks every workshop LED and beeps.
// The instructor flashes this to every board before class (ws flash-all 00_hello).
#include "workshop.h"

void setup() {
    pinMode(RED, OUTPUT);
    pinMode(YELLOW, OUTPUT);
    pinMode(GREEN, OUTPUT);
    pinMode(BUTTON, INPUT_PULLUP);
    printf("Hello from lab test board 1! Pins: RED=%d YELLOW=%d GREEN=%d BUTTON=%d BUZZER=%d KNOB=%d\n",
           RED, YELLOW, GREEN, BUTTON, BUZZER, KNOB);
}

void loop() {
    int leds[] = {RED, YELLOW, GREEN};
    for (int led : leds) {
        digitalWrite(led, HIGH);
        delay(200);
        digitalWrite(led, LOW);
    }
    printf("up %lu ms, button %s, knob %d\n", (unsigned long)millis(),
           digitalRead(BUTTON) == LOW ? "PRESSED" : "up", analogRead(KNOB));
    delay(400);
}
