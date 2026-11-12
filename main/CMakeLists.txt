idf_component_register(SRCS "main.cpp" "workshop.cpp" "sketch.cpp"
                       INCLUDE_DIRS "."
                       REQUIRES esp_driver_gpio esp_driver_ledc esp_adc esp_timer)
# Beginners' code: warnings stay warnings, never build failures.
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-error)
