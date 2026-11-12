// Entry point: ESP-IDF calls app_main(); we hand over to the sketch's
// setup()/loop(). The sketch itself is main/sketch.cpp, which `ws` copies in
// from teams/<name>.cpp or examples/<name>.cpp before every build.
#include "workshop.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

const char* sketch_name();  // generated into sketch.cpp by ws

extern "C" void app_main() {
    setvbuf(stdout, nullptr, _IONBF, 0);  // show printf() output immediately, even without \n
    printf("\n=== sketch '%s' on %s ===\n", sketch_name(), CONFIG_IDF_TARGET);
    setup();
    for (;;) {
        loop();
        taskYIELD();
    }
}
