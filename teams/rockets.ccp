// boared:3
// 00 Hello: board self-test. Prints, then walks every workshop LED.
// The instructor flashes this to every board before class (ws flash-all 00_hello).
#include "workshop.h"

void setup() {
    pinMode(RED, OUTPUT);
    pinMode(YELLOW, OUTPUT);
    pinMode(GREEN, OUTPUT);
    pinMode(BUTTON, INPUT_PULLUP);
    printf("Hello from the ESP32! Pins: RED=%d YELLOW=%d GREEN=%d BUTTON=%d BUZZER=%d\n",
           RED, YELLOW, GREEN, BUTTON, BUZZER);
}

void loop() {
    int leds[] = {RED, YELLOW, GREEN};
    for (int led : leds) {
        digitalWrite(led, HIGH);
        delay(200);
        digitalWrite(led, LOW);
    }
    printf("up %lu ms, button %s\n", (unsigned long)millis(),
           digitalRead(BUTTON) == LOW ? "PRESSED" : "up");
    delay(400);
}
