/**
 * @file display.h
 * @brief Display abstraction layer for main device
 * 
 * Supports multiple display backends:
 * - I2C SSD1306 128x64 (for testing)
 * - SPI Transparent OLED 128x64 (production)
 */

#pragma once

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Display dimensions
 */
#define DISPLAY_WIDTH       128
#define DISPLAY_HEIGHT      64

/**
 * @brief Display type selection
 */
typedef enum {
    DISPLAY_TYPE_SSD1306_I2C,       ///< I2C SSD1306 (test OLED)
    DISPLAY_TYPE_TRANSPARENT_SPI,   ///< SPI Transparent OLED (production)
} display_type_t;

/**
 * @brief I2C display configuration
 */
typedef struct {
    uint8_t i2c_addr;       ///< I2C address (default 0x3C)
    int sda_pin;            ///< SDA GPIO
    int scl_pin;            ///< SCL GPIO
} display_i2c_config_t;

/**
 * @brief SPI display configuration (for future transparent OLED)
 */
typedef struct {
    int mosi_pin;
    int sclk_pin;
    int cs_pin;
    int dc_pin;
    int rst_pin;
} display_spi_config_t;

/**
 * @brief Display configuration
 */
typedef struct {
    display_type_t type;
    union {
        display_i2c_config_t i2c;
        display_spi_config_t spi;
    };
    bool flip_horizontal;
    bool flip_vertical;
} display_config_t;

/**
 * @brief Color values
 */
typedef enum {
    COLOR_BLACK = 0,
    COLOR_WHITE = 1,
    COLOR_INVERSE = 2
} display_color_t;

/**
 * @brief Initialize display
 * @param config Display configuration
 * @return ESP_OK on success
 */
esp_err_t display_init(const display_config_t *config);

/**
 * @brief Deinitialize display
 */
void display_deinit(void);

/**
 * @brief Clear display buffer
 */
void display_clear(void);

/**
 * @brief Push buffer to display
 */
void display_refresh(void);

/**
 * @brief Set brightness (0-255)
 */
void display_set_brightness(uint8_t brightness);

/**
 * @brief Turn display on/off
 */
void display_power(bool on);

/* ============================================================================
 * Drawing Functions
 * ============================================================================ */

void display_draw_pixel(int x, int y, display_color_t color);
void display_draw_line(int x0, int y0, int x1, int y1, display_color_t color);
void display_draw_hline(int x, int y, int w, display_color_t color);
void display_draw_vline(int x, int y, int h, display_color_t color);
void display_draw_rect(int x, int y, int w, int h, display_color_t color);
void display_fill_rect(int x, int y, int w, int h, display_color_t color);
void display_draw_circle(int cx, int cy, int r, display_color_t color);
void display_fill_circle(int cx, int cy, int r, display_color_t color);

/**
 * @brief Draw a bitmap
 * @param x X position
 * @param y Y position
 * @param bitmap Bitmap data (packed horizontally)
 * @param w Width in pixels
 * @param h Height in pixels
 * @param color Color to draw
 */
void display_draw_bitmap(int x, int y, const uint8_t *bitmap, int w, int h, display_color_t color);

/**
 * @brief Draw character
 * @param x X position
 * @param y Y position  
 * @param c Character
 * @param color Color
 * @param size Size multiplier (1=6x8, 2=12x16)
 */
void display_draw_char(int x, int y, char c, display_color_t color, uint8_t size);

/**
 * @brief Draw string
 */
void display_draw_string(int x, int y, const char *str, display_color_t color, uint8_t size);

/**
 * @brief Printf to display
 */
void display_printf(int x, int y, display_color_t color, uint8_t size, const char *fmt, ...);

/**
 * @brief Draw progress bar
 */
void display_draw_progress(int x, int y, int w, int h, int progress);

/* ============================================================================
 * UI Helper Functions
 * ============================================================================ */

/**
 * @brief Draw a status bar at top of screen
 * @param mesh_connected Mesh network status
 * @param unread_count Unread message count
 * @param battery_pct Battery percentage (0-100, -1 to hide)
 */
void display_draw_status_bar(bool mesh_connected, int unread_count, int battery_pct);

/**
 * @brief Draw joystick position indicator
 * @param x Center X
 * @param y Center Y
 * @param radius Radius
 * @param joy_x Joystick X (-100 to 100)
 * @param joy_y Joystick Y (-100 to 100)
 */
void display_draw_joystick_indicator(int x, int y, int radius, int8_t joy_x, int8_t joy_y);

/**
 * @brief Draw a message bubble
 * @param x X position
 * @param y Y position
 * @param from Sender name
 * @param message Message text (will be truncated to fit)
 * @param is_incoming true if received, false if sent
 */
void display_draw_message(int x, int y, const char *from, const char *message, bool is_incoming);

/**
 * @brief Draw text input field
 * @param x X position
 * @param y Y position
 * @param w Width
 * @param text Current text
 * @param cursor_pos Cursor position (-1 to hide cursor)
 */
void display_draw_text_input(int x, int y, int w, const char *text, int cursor_pos);

#ifdef __cplusplus
}
#endif

