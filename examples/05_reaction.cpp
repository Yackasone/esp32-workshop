// 05 Reaction: how fast are you? Wait for green, then hit the button.
// Uses the button and LEDs from the launch pad layout.
#include "workshop.h"

void setup() {
    pinMode(RED, OUTPUT);
    pinMode(GREEN, OUTPUT);
    pinMode(BUTTON, INPUT_PULLUP);
    printf("Reaction test: when GREEN lights, press the button!\n");
}

void loop() {
    digitalWrite(RED, HIGH);                 // red = get ready
    delay(randomBetween(2000, 5000));        // random wait, so you can't guess
    if (digitalRead(BUTTON) == LOW) {        // pressed too early?
        printf("Too soon! Wait for green.\n");
        delay(1000);
        return;
    }
    digitalWrite(RED, LOW);
    digitalWrite(GREEN, HIGH);
    uint32_t start = millis();
    while (digitalRead(BUTTON) == HIGH) {}   // wait for the press
    uint32_t ms = millis() - start;
    digitalWrite(GREEN, LOW);
    printf("Your time: %lu ms\n", (unsigned long)ms);
    delay(2000);
    // Try: keep your best time in a variable and print "NEW RECORD!" when you beat it.
}
