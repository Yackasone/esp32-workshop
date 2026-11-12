// 06 Buzzer: beep codes and tunes, the way a flight computer reports on the pad.
// Wiring: buzzer + leg -> BUZZER pin, - leg -> GND.
// Passive buzzer/piezo: tone() sets the pitch. Active buzzer (it beeps by itself on 3.3 V):
// tone() still works but only clicks; use digitalWrite(BUZZER, HIGH/LOW) for its own beep.
#include "workshop.h"

void beep(int hz, int ms) {
    tone(BUZZER, hz);
    delay(ms);
    noTone(BUZZER);
    delay(50);
}

void setup() {
    pinMode(BUTTON, INPUT_PULLUP);
    // "All sensors OK": three rising beeps.
    beep(1000, 150);
    beep(1500, 150);
    beep(2000, 150);
    printf("Hold the button for a siren.\n");
}

void loop() {
    if (digitalRead(BUTTON) == LOW) {
        for (int hz = 600; hz <= 1400; hz += 20) { tone(BUZZER, hz); delay(5); }  // siren up
        for (int hz = 1400; hz >= 600; hz -= 20) { tone(BUZZER, hz); delay(5); }  // and down
    } else {
        noTone(BUZZER);
        delay(10);
    }
    // Try: play a tune when the button is tapped (C=523, D=587, E=659, G=784 Hz).
}
