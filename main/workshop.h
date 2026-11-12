// workshop.h — the tiny API for club sketches.
//
// Your sketch defines two functions:
//   void setup()   runs once after power-up / reset
//   void loop()    runs again and again, forever
//
// and can call these:
//   pinMode(pin, OUTPUT | INPUT | INPUT_PULLUP | INPUT_PULLDOWN)
//   digitalWrite(pin, HIGH | LOW)      digitalRead(pin) -> HIGH or LOW
//   analogWrite(pin, 0..255)           PWM brightness (LED fade)
//   analogRead(pin) -> 0..4095         voltage on the pin (knob, light sensor)
//   tone(pin, hz)  noTone(pin)         square wave for a passive buzzer
//   delay(ms)  millis()                wait / time since boot in ms
//   randomBetween(lo, hi)              random int, lo <= n <= hi
//   printf("x = %d\n", x);             prints in the serial monitor
//
// Pin names for the shared breadboard layout (RED, YELLOW, GREEN, BUTTON,
// BUZZER, KNOB) are picked per chip below, so the same sketch runs on any board.
//
// Under the hood this is plain ESP-IDF (the same toolchain as the flight
// computer); see workshop.cpp.
#pragma once

#include <cstdint>
#include <cstdio>
#include "sdkconfig.h"

enum PinMode { OUTPUT, INPUT, INPUT_PULLUP, INPUT_PULLDOWN };
constexpr int HIGH = 1;
constexpr int LOW = 0;

void setup();
void loop();

void pinMode(int pin, PinMode mode);
void digitalWrite(int pin, int level);
int digitalRead(int pin);
void analogWrite(int pin, int duty);  // 0 = off .. 255 = fully on
int analogRead(int pin);              // 0 .. 4095 (about 0 V .. 3.1 V)
void tone(int pin, int hz);
void noTone(int pin);
void delay(uint32_t ms);
uint32_t millis();
int randomBetween(int lo, int hi);

// ---- Workshop breadboard pins (see the deck: "The launch pad layout") ----
#if CONFIG_IDF_TARGET_ESP32
// ESP32 DevKit (30- or 38-pin): one run of pins down the left-hand header.
constexpr int KNOB = 34, BUZZER = 32, BUTTON = 33, RED = 25, YELLOW = 26, GREEN = 27;
#elif CONFIG_IDF_TARGET_ESP32S3
// ESP32-S3-DevKitC-1: left-hand header, top to bottom.
constexpr int KNOB = 4, BUZZER = 5, BUTTON = 6, RED = 7, YELLOW = 15, GREEN = 16;
#elif CONFIG_IDF_TARGET_ESP32C6
// XIAO ESP32-C6 pads D0..D5 (also fine on the C6 DevKitC-1).
constexpr int KNOB = 0, BUZZER = 1, BUTTON = 2, RED = 21, YELLOW = 22, GREEN = 23;
#elif CONFIG_IDF_TARGET_ESP32C3
// ESP32-C3 SuperMini / DevKitM-1.
constexpr int KNOB = 0, BUZZER = 1, BUTTON = 3, RED = 4, YELLOW = 5, GREEN = 6;
#elif CONFIG_IDF_TARGET_ESP32S2
constexpr int KNOB = 1, BUZZER = 2, BUTTON = 3, RED = 4, YELLOW = 5, GREEN = 6;
#else
#error "No workshop pin map for this chip yet: add one in workshop.h"
#endif
