// 07 Launch control: everything on the launch pad layout together.
// Press the button to start a 10 s countdown. Press again to ABORT.
#include "workshop.h"

bool pressed() {
    if (digitalRead(BUTTON) == HIGH) return false;
    delay(30);                                    // ignore contact bounce
    while (digitalRead(BUTTON) == LOW) delay(5);  // wait for release
    return true;
}

void all_off() {
    digitalWrite(RED, LOW);
    digitalWrite(YELLOW, LOW);
    digitalWrite(GREEN, LOW);
    noTone(BUZZER);
}

void setup() {
    pinMode(RED, OUTPUT);
    pinMode(YELLOW, OUTPUT);
    pinMode(GREEN, OUTPUT);
    pinMode(BUTTON, INPUT_PULLUP);
    all_off();
    printf("Pad armed. Press the button to start the countdown.\n");
}

void loop() {
    digitalWrite(GREEN, HIGH);  // green = safe, waiting
    if (!pressed()) return;

    digitalWrite(GREEN, LOW);
    for (int t = 10; t > 0; t--) {
        printf("T-%d\n", t);
        int led = t > 3 ? YELLOW : RED;
        digitalWrite(led, HIGH);
        tone(BUZZER, t > 3 ? 1000 : 2000);
        delay(100);
        noTone(BUZZER);
        for (int i = 0; i < 18; i++) {           // rest of the second, watching for abort
            delay(50);
            if (pressed()) {
                all_off();
                printf("ABORT at T-%d\n", t);
                for (int k = 0; k < 3; k++) { digitalWrite(RED, HIGH); delay(150); digitalWrite(RED, LOW); delay(150); }
                return;
            }
        }
        digitalWrite(led, LOW);
    }
    printf("LIFTOFF!\n");
    for (int hz = 400; hz < 3000; hz += 40) {    // rising whoosh
        tone(BUZZER, hz);
        analogWrite(RED, randomBetween(0, 255)); // flicker like a motor
        analogWrite(YELLOW, randomBetween(0, 255));
        delay(15);
    }
    all_off();
    delay(2000);
    // Try: add a "hold" -- a long press pauses the count instead of aborting.
}
