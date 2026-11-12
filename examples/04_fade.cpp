// 04 Fade: PWM switches the pin on and off 5000 times a second;
// the fraction of time it is on (0..255) sets the brightness.
#include "workshop.h"

void setup() {}

void loop() {
    for (int b = 0; b <= 255; b += 5) {
        analogWrite(GREEN, b);
        delay(20);
    }
    for (int b = 255; b >= 0; b -= 5) {
        analogWrite(GREEN, b);
        delay(20);
    }
    // Try: make the red LED fade the opposite way at the same time.
}
