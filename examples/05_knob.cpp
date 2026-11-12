// 05 Knob: read a voltage, use it to set the brightness.
// Wiring: potentiometer outer legs -> 3V3 and GND, middle leg (wiper) -> KNOB pin.
// (No pot? A light sensor (LDR) from 3V3 to KNOB plus 10k from KNOB to GND works too.)
#include "workshop.h"

void setup() {}

void loop() {
    int raw = analogRead(KNOB);        // 0 .. 4095
    int brightness = raw * 255 / 4095; // scale to 0 .. 255
    analogWrite(YELLOW, brightness);
    printf("knob %4d -> brightness %3d\n", raw, brightness);
    delay(100);
    // Try: light RED, YELLOW or GREEN depending on which third the knob is in.
}
