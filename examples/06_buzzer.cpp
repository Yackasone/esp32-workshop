// 06 Buzzer: beep codes, the way a flight computer reports on the pad.
// Wiring: buzzer + leg -> BUZZER pin, - leg -> GND.
// Passive buzzer/piezo: tone() sets the pitch. Active buzzer: use digitalWrite HIGH/LOW instead.
#include "workshop.h"

void beep(int hz, int ms) {
    tone(BUZZER, hz);
    delay(ms);
    noTone(BUZZER);
    delay(ms);
}

void setup() {
    // "All sensors OK": three rising beeps.
    beep(1000, 150);
    beep(1500, 150);
    beep(2000, 150);
}

void loop() {
    // Turn the knob to change the pitch.
    int hz = 200 + analogRead(KNOB) / 2;
    tone(BUZZER, hz);
    delay(50);
}
