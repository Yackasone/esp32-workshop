// The workshop API on top of ESP-IDF drivers. Students never need to open this,
// but it is the "what's really happening" answer: GPIO matrix, LEDC PWM, ADC.
#include "workshop.h"

#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "soc/soc_caps.h"

namespace {

// Pins wired to the flash chip or the USB port: touching them crashes the board
// or kills the connection to the laptop, so refuse with a readable message.
bool reserved_pin(int pin) {
#if CONFIG_IDF_TARGET_ESP32
    return pin >= 6 && pin <= 11;
#elif CONFIG_IDF_TARGET_ESP32S3
    // 26-32 flash, 33-37 octal PSRAM on N16R8-type modules, 19/20 USB.
    return (pin >= 26 && pin <= 37) || pin == 19 || pin == 20;
#elif CONFIG_IDF_TARGET_ESP32C6
    return (pin >= 24 && pin <= 30) || pin == 12 || pin == 13;
#elif CONFIG_IDF_TARGET_ESP32C3
    return (pin >= 12 && pin <= 17) || pin == 18 || pin == 19;
#else
    return false;
#endif
}

bool check_pin(int pin, bool output, const char* fn) {
    if (!GPIO_IS_VALID_GPIO(pin)) {
        printf("!! %s(%d): this chip has no GPIO %d\n", fn, pin, pin);
        return false;
    }
    if (reserved_pin(pin)) {
        printf("!! %s(%d): GPIO %d belongs to the flash/PSRAM chip or USB. Pick another pin.\n", fn, pin, pin);
        return false;
    }
    if (output && !GPIO_IS_VALID_OUTPUT_GPIO(pin)) {
        printf("!! %s(%d): GPIO %d can only be an INPUT on this chip\n", fn, pin, pin);
        return false;
    }
    return true;
}

// ---- PWM (LEDC): timer 0 = analogWrite at 5 kHz/8 bit, timer 1 = tone() ----
constexpr ledc_mode_t kMode = LEDC_LOW_SPEED_MODE;
int8_t pwm_channel[SOC_GPIO_PIN_COUNT];  // -1 = pin not on PWM
int8_t pwm_timer[SOC_GPIO_PIN_COUNT];
int next_channel = 0;
bool timers_ready = false;

void init_timers() {
    if (timers_ready) return;
    ledc_timer_config_t t = {};
    t.speed_mode = kMode;
    t.duty_resolution = LEDC_TIMER_8_BIT;
    t.timer_num = LEDC_TIMER_0;
    t.freq_hz = 5000;
    t.clk_cfg = LEDC_AUTO_CLK;
    ESP_ERROR_CHECK(ledc_timer_config(&t));
    t.timer_num = LEDC_TIMER_1;
    t.freq_hz = 1000;
    ESP_ERROR_CHECK(ledc_timer_config(&t));
    for (int i = 0; i < SOC_GPIO_PIN_COUNT; i++) pwm_channel[i] = pwm_timer[i] = -1;
    timers_ready = true;
}

// Bind `pin` to a PWM channel driven by `timer`; returns the channel or -1.
int pwm_attach(int pin, ledc_timer_t timer, const char* fn) {
    init_timers();
    if (pwm_channel[pin] < 0) {
        if (next_channel >= SOC_LEDC_CHANNEL_NUM) {
            printf("!! %s(%d): out of PWM channels (max %d pins)\n", fn, pin, SOC_LEDC_CHANNEL_NUM);
            return -1;
        }
        pwm_channel[pin] = next_channel++;
    }
    if (pwm_timer[pin] != timer) {
        ledc_channel_config_t c = {};
        c.gpio_num = pin;
        c.speed_mode = kMode;
        c.channel = static_cast<ledc_channel_t>(pwm_channel[pin]);
        c.timer_sel = timer;
        c.duty = 0;
        ESP_ERROR_CHECK(ledc_channel_config(&c));
        pwm_timer[pin] = timer;
    }
    return pwm_channel[pin];
}

void pwm_release(int pin, int level) {
    if (!timers_ready || pwm_channel[pin] < 0 || pwm_timer[pin] < 0) return;
    ledc_stop(kMode, static_cast<ledc_channel_t>(pwm_channel[pin]), level);
    pwm_timer[pin] = -1;  // next analogWrite/tone re-attaches
    gpio_set_direction(static_cast<gpio_num_t>(pin), GPIO_MODE_OUTPUT);
}

// ---- ADC ----
adc_oneshot_unit_handle_t adc_units[SOC_ADC_PERIPH_NUM] = {};
uint64_t adc_configured = 0;  // bit per GPIO

}  // namespace

void pinMode(int pin, PinMode mode) {
    if (!check_pin(pin, mode == OUTPUT, "pinMode")) return;
    pwm_release(pin, 0);
    gpio_config_t c = {};
    c.pin_bit_mask = 1ULL << pin;
    c.mode = mode == OUTPUT ? GPIO_MODE_INPUT_OUTPUT : GPIO_MODE_INPUT;
    c.pull_up_en = mode == INPUT_PULLUP ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE;
    c.pull_down_en = mode == INPUT_PULLDOWN ? GPIO_PULLDOWN_ENABLE : GPIO_PULLDOWN_DISABLE;
    c.intr_type = GPIO_INTR_DISABLE;
    gpio_config(&c);
}

void digitalWrite(int pin, int level) {
    if (!check_pin(pin, true, "digitalWrite")) return;
    pwm_release(pin, level ? 1 : 0);
    gpio_set_level(static_cast<gpio_num_t>(pin), level ? 1 : 0);
}

int digitalRead(int pin) {
    if (!check_pin(pin, false, "digitalRead")) return LOW;
    return gpio_get_level(static_cast<gpio_num_t>(pin)) ? HIGH : LOW;
}

void analogWrite(int pin, int duty) {
    if (!check_pin(pin, true, "analogWrite")) return;
    duty = duty < 0 ? 0 : duty > 255 ? 255 : duty;
    int ch = pwm_attach(pin, LEDC_TIMER_0, "analogWrite");
    if (ch < 0) return;
    ledc_set_duty(kMode, static_cast<ledc_channel_t>(ch), duty);
    ledc_update_duty(kMode, static_cast<ledc_channel_t>(ch));
}

void tone(int pin, int hz) {
    if (!check_pin(pin, true, "tone")) return;
    if (hz < 20 || hz > 20000) {
        printf("!! tone(%d, %d): pick a frequency between 20 and 20000 Hz\n", pin, hz);
        return;
    }
    int ch = pwm_attach(pin, LEDC_TIMER_1, "tone");
    if (ch < 0) return;
    ledc_set_freq(kMode, LEDC_TIMER_1, hz);
    ledc_set_duty(kMode, static_cast<ledc_channel_t>(ch), 128);  // 50 % square wave
    ledc_update_duty(kMode, static_cast<ledc_channel_t>(ch));
}

void noTone(int pin) {
    if (!check_pin(pin, true, "noTone")) return;
    pwm_release(pin, 0);
    gpio_set_level(static_cast<gpio_num_t>(pin), 0);
}

int analogRead(int pin) {
    if (!check_pin(pin, false, "analogRead")) return 0;
    adc_unit_t unit;
    adc_channel_t chan;
    if (adc_oneshot_io_to_channel(pin, &unit, &chan) != ESP_OK) {
        printf("!! analogRead(%d): GPIO %d has no ADC. Use the KNOB pin (%d).\n", pin, pin, KNOB);
        return 0;
    }
    if (!adc_units[unit]) {
        adc_oneshot_unit_init_cfg_t u = {};
        u.unit_id = unit;
        if (adc_oneshot_new_unit(&u, &adc_units[unit]) != ESP_OK) {
            printf("!! analogRead(%d): ADC unit busy\n", pin);
            return 0;
        }
    }
    if (!(adc_configured & (1ULL << pin))) {
        adc_oneshot_chan_cfg_t c = {};
        c.atten = ADC_ATTEN_DB_12;  // full 0..3.3 V range
        c.bitwidth = ADC_BITWIDTH_12;
        adc_oneshot_config_channel(adc_units[unit], chan, &c);
        adc_configured |= 1ULL << pin;
    }
    int raw = 0;
    adc_oneshot_read(adc_units[unit], chan, &raw);
    return raw;
}

void delay(uint32_t ms) {
    // At least one tick, so a loop() made of nothing but delay(0) still yields.
    vTaskDelay(ms ? pdMS_TO_TICKS(ms) : 1);
}

uint32_t millis() { return static_cast<uint32_t>(esp_timer_get_time() / 1000); }

int randomBetween(int lo, int hi) {
    if (hi < lo) { int t = lo; lo = hi; hi = t; }
    return lo + static_cast<int>(esp_random() % static_cast<uint32_t>(hi - lo + 1));
}
