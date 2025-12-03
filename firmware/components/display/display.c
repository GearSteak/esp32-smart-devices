/**
 * @file display.c
 * @brief Display driver implementation
 */

#include "display.h"
#include "driver/i2c.h"
#include "esp_log.h"
#include <string.h>
#include <stdarg.h>
#include <stdio.h>

static const char *TAG = "display";

#define I2C_PORT I2C_NUM_0

/* SSD1306 commands */
#define CMD_DISPLAY_OFF         0xAE
#define CMD_DISPLAY_ON          0xAF
#define CMD_SET_CONTRAST        0x81
#define CMD_NORMAL_DISPLAY      0xA6
#define CMD_INVERT_DISPLAY      0xA7
#define CMD_SET_MUX_RATIO       0xA8
#define CMD_SET_DISPLAY_OFFSET  0xD3
#define CMD_SET_START_LINE      0x40
#define CMD_SET_SEG_REMAP       0xA0
#define CMD_SET_COM_SCAN_DIR    0xC0
#define CMD_SET_COM_PINS        0xDA
#define CMD_SET_CLOCK_DIV       0xD5
#define CMD_SET_PRECHARGE       0xD9
#define CMD_SET_VCOM_DESELECT   0xDB
#define CMD_CHARGE_PUMP         0x8D
#define CMD_MEMORY_MODE         0x20
#define CMD_SET_COLUMN_ADDR     0x21
#define CMD_SET_PAGE_ADDR       0x22

/* Display buffer */
static uint8_t s_buffer[DISPLAY_WIDTH * DISPLAY_HEIGHT / 8];
static uint8_t s_i2c_addr = 0x3C;
static bool s_initialized = false;
static display_type_t s_type = DISPLAY_TYPE_SSD1306_I2C;

/* 6x8 font */
static const uint8_t font6x8[] = {
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x5F,0x00,0x00,0x00,
    0x00,0x07,0x00,0x07,0x00,0x00,0x14,0x7F,0x14,0x7F,0x14,0x00,
    0x24,0x2A,0x7F,0x2A,0x12,0x00,0x23,0x13,0x08,0x64,0x62,0x00,
    0x36,0x49,0x56,0x20,0x50,0x00,0x00,0x08,0x07,0x03,0x00,0x00,
    0x00,0x1C,0x22,0x41,0x00,0x00,0x00,0x41,0x22,0x1C,0x00,0x00,
    0x2A,0x1C,0x7F,0x1C,0x2A,0x00,0x08,0x08,0x3E,0x08,0x08,0x00,
    0x00,0x80,0x70,0x30,0x00,0x00,0x08,0x08,0x08,0x08,0x08,0x00,
    0x00,0x00,0x60,0x60,0x00,0x00,0x20,0x10,0x08,0x04,0x02,0x00,
    0x3E,0x51,0x49,0x45,0x3E,0x00,0x00,0x42,0x7F,0x40,0x00,0x00,
    0x72,0x49,0x49,0x49,0x46,0x00,0x21,0x41,0x49,0x4D,0x33,0x00,
    0x18,0x14,0x12,0x7F,0x10,0x00,0x27,0x45,0x45,0x45,0x39,0x00,
    0x3C,0x4A,0x49,0x49,0x31,0x00,0x41,0x21,0x11,0x09,0x07,0x00,
    0x36,0x49,0x49,0x49,0x36,0x00,0x46,0x49,0x49,0x29,0x1E,0x00,
    0x00,0x00,0x14,0x00,0x00,0x00,0x00,0x40,0x34,0x00,0x00,0x00,
    0x00,0x08,0x14,0x22,0x41,0x00,0x14,0x14,0x14,0x14,0x14,0x00,
    0x00,0x41,0x22,0x14,0x08,0x00,0x02,0x01,0x59,0x09,0x06,0x00,
    0x3E,0x41,0x5D,0x59,0x4E,0x00,0x7C,0x12,0x11,0x12,0x7C,0x00,
    0x7F,0x49,0x49,0x49,0x36,0x00,0x3E,0x41,0x41,0x41,0x22,0x00,
    0x7F,0x41,0x41,0x41,0x3E,0x00,0x7F,0x49,0x49,0x49,0x41,0x00,
    0x7F,0x09,0x09,0x09,0x01,0x00,0x3E,0x41,0x41,0x51,0x73,0x00,
    0x7F,0x08,0x08,0x08,0x7F,0x00,0x00,0x41,0x7F,0x41,0x00,0x00,
    0x20,0x40,0x41,0x3F,0x01,0x00,0x7F,0x08,0x14,0x22,0x41,0x00,
    0x7F,0x40,0x40,0x40,0x40,0x00,0x7F,0x02,0x1C,0x02,0x7F,0x00,
    0x7F,0x04,0x08,0x10,0x7F,0x00,0x3E,0x41,0x41,0x41,0x3E,0x00,
    0x7F,0x09,0x09,0x09,0x06,0x00,0x3E,0x41,0x51,0x21,0x5E,0x00,
    0x7F,0x09,0x19,0x29,0x46,0x00,0x26,0x49,0x49,0x49,0x32,0x00,
    0x03,0x01,0x7F,0x01,0x03,0x00,0x3F,0x40,0x40,0x40,0x3F,0x00,
    0x1F,0x20,0x40,0x20,0x1F,0x00,0x3F,0x40,0x38,0x40,0x3F,0x00,
    0x63,0x14,0x08,0x14,0x63,0x00,0x03,0x04,0x78,0x04,0x03,0x00,
    0x61,0x59,0x49,0x4D,0x43,0x00,0x00,0x7F,0x41,0x41,0x41,0x00,
    0x02,0x04,0x08,0x10,0x20,0x00,0x00,0x41,0x41,0x41,0x7F,0x00,
    0x04,0x02,0x01,0x02,0x04,0x00,0x40,0x40,0x40,0x40,0x40,0x00,
    0x00,0x03,0x07,0x08,0x00,0x00,0x20,0x54,0x54,0x78,0x40,0x00,
    0x7F,0x28,0x44,0x44,0x38,0x00,0x38,0x44,0x44,0x44,0x28,0x00,
    0x38,0x44,0x44,0x28,0x7F,0x00,0x38,0x54,0x54,0x54,0x18,0x00,
    0x00,0x08,0x7E,0x09,0x02,0x00,0x18,0xA4,0xA4,0x9C,0x78,0x00,
    0x7F,0x08,0x04,0x04,0x78,0x00,0x00,0x44,0x7D,0x40,0x00,0x00,
    0x20,0x40,0x40,0x3D,0x00,0x00,0x7F,0x10,0x28,0x44,0x00,0x00,
    0x00,0x41,0x7F,0x40,0x00,0x00,0x7C,0x04,0x78,0x04,0x78,0x00,
    0x7C,0x08,0x04,0x04,0x78,0x00,0x38,0x44,0x44,0x44,0x38,0x00,
    0xFC,0x18,0x24,0x24,0x18,0x00,0x18,0x24,0x24,0x18,0xFC,0x00,
    0x7C,0x08,0x04,0x04,0x08,0x00,0x48,0x54,0x54,0x54,0x24,0x00,
    0x04,0x04,0x3F,0x44,0x24,0x00,0x3C,0x40,0x40,0x20,0x7C,0x00,
    0x1C,0x20,0x40,0x20,0x1C,0x00,0x3C,0x40,0x30,0x40,0x3C,0x00,
    0x44,0x28,0x10,0x28,0x44,0x00,0x4C,0x90,0x90,0x90,0x7C,0x00,
    0x44,0x64,0x54,0x4C,0x44,0x00,0x00,0x08,0x36,0x41,0x00,0x00,
    0x00,0x00,0x77,0x00,0x00,0x00,0x00,0x41,0x36,0x08,0x00,0x00,
    0x02,0x01,0x02,0x04,0x02,0x00,0x3C,0x26,0x23,0x26,0x3C,0x00,
};

/* I2C helpers */
static esp_err_t send_cmd(uint8_t cmd)
{
    uint8_t data[2] = {0x00, cmd};
    return i2c_master_write_to_device(I2C_PORT, s_i2c_addr, data, 2, pdMS_TO_TICKS(100));
}

static esp_err_t send_data(const uint8_t *data, size_t len)
{
    uint8_t *buf = malloc(len + 1);
    if (!buf) return ESP_ERR_NO_MEM;
    
    buf[0] = 0x40;
    memcpy(buf + 1, data, len);
    
    esp_err_t ret = i2c_master_write_to_device(I2C_PORT, s_i2c_addr, buf, len + 1, pdMS_TO_TICKS(100));
    free(buf);
    return ret;
}

static esp_err_t init_ssd1306_i2c(const display_config_t *config)
{
    int sda = config->i2c.sda_pin;
    int scl = config->i2c.scl_pin;
    s_i2c_addr = config->i2c.i2c_addr;
    
    i2c_config_t i2c_conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = sda,
        .scl_io_num = scl,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 400000,
    };
    
    esp_err_t ret = i2c_param_config(I2C_PORT, &i2c_conf);
    if (ret != ESP_OK) return ret;
    
    ret = i2c_driver_install(I2C_PORT, I2C_MODE_MASTER, 0, 0, 0);
    if (ret != ESP_OK) return ret;
    
    /* Init sequence */
    send_cmd(CMD_DISPLAY_OFF);
    send_cmd(CMD_SET_CLOCK_DIV); send_cmd(0x80);
    send_cmd(CMD_SET_MUX_RATIO); send_cmd(0x3F);
    send_cmd(CMD_SET_DISPLAY_OFFSET); send_cmd(0x00);
    send_cmd(CMD_SET_START_LINE | 0x00);
    send_cmd(CMD_CHARGE_PUMP); send_cmd(0x14);
    send_cmd(CMD_MEMORY_MODE); send_cmd(0x00);
    send_cmd(CMD_SET_SEG_REMAP | (config->flip_horizontal ? 0x00 : 0x01));
    send_cmd(CMD_SET_COM_SCAN_DIR | (config->flip_vertical ? 0x00 : 0x08));
    send_cmd(CMD_SET_COM_PINS); send_cmd(0x12);
    send_cmd(CMD_SET_CONTRAST); send_cmd(0xCF);
    send_cmd(CMD_SET_PRECHARGE); send_cmd(0xF1);
    send_cmd(CMD_SET_VCOM_DESELECT); send_cmd(0x40);
    send_cmd(CMD_NORMAL_DISPLAY);
    send_cmd(CMD_DISPLAY_ON);
    
    ESP_LOGI(TAG, "SSD1306 I2C initialized (addr=0x%02X, SDA=%d, SCL=%d)", s_i2c_addr, sda, scl);
    return ESP_OK;
}

esp_err_t display_init(const display_config_t *config)
{
    if (s_initialized) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_ERR_INVALID_STATE;
    }
    
    s_type = config->type;
    esp_err_t ret = ESP_FAIL;
    
    switch (config->type) {
        case DISPLAY_TYPE_SSD1306_I2C:
            ret = init_ssd1306_i2c(config);
            break;
        case DISPLAY_TYPE_TRANSPARENT_SPI:
            ESP_LOGE(TAG, "Transparent SPI not yet implemented");
            return ESP_ERR_NOT_SUPPORTED;
        default:
            return ESP_ERR_INVALID_ARG;
    }
    
    if (ret == ESP_OK) {
        display_clear();
        display_refresh();
        s_initialized = true;
    }
    
    return ret;
}

void display_deinit(void)
{
    if (s_initialized) {
        display_power(false);
        i2c_driver_delete(I2C_PORT);
        s_initialized = false;
    }
}

void display_clear(void)
{
    memset(s_buffer, 0, sizeof(s_buffer));
}

void display_refresh(void)
{
    if (!s_initialized) return;
    
    send_cmd(CMD_SET_COLUMN_ADDR); send_cmd(0); send_cmd(127);
    send_cmd(CMD_SET_PAGE_ADDR); send_cmd(0); send_cmd(7);
    send_data(s_buffer, sizeof(s_buffer));
}

void display_set_brightness(uint8_t brightness)
{
    if (!s_initialized) return;
    send_cmd(CMD_SET_CONTRAST);
    send_cmd(brightness);
}

void display_power(bool on)
{
    if (!s_initialized) return;
    send_cmd(on ? CMD_DISPLAY_ON : CMD_DISPLAY_OFF);
}

void display_draw_pixel(int x, int y, display_color_t color)
{
    if (x < 0 || x >= DISPLAY_WIDTH || y < 0 || y >= DISPLAY_HEIGHT) return;
    
    int idx = x + (y / 8) * DISPLAY_WIDTH;
    uint8_t bit = 1 << (y & 7);
    
    switch (color) {
        case COLOR_WHITE: s_buffer[idx] |= bit; break;
        case COLOR_BLACK: s_buffer[idx] &= ~bit; break;
        case COLOR_INVERSE: s_buffer[idx] ^= bit; break;
    }
}

void display_draw_hline(int x, int y, int w, display_color_t color)
{
    for (int i = 0; i < w; i++) display_draw_pixel(x + i, y, color);
}

void display_draw_vline(int x, int y, int h, display_color_t color)
{
    for (int i = 0; i < h; i++) display_draw_pixel(x, y + i, color);
}

void display_draw_line(int x0, int y0, int x1, int y1, display_color_t color)
{
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx - dy;
    
    while (1) {
        display_draw_pixel(x0, y0, color);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 < dx) { err += dx; y0 += sy; }
    }
}

void display_draw_rect(int x, int y, int w, int h, display_color_t color)
{
    display_draw_hline(x, y, w, color);
    display_draw_hline(x, y + h - 1, w, color);
    display_draw_vline(x, y, h, color);
    display_draw_vline(x + w - 1, y, h, color);
}

void display_fill_rect(int x, int y, int w, int h, display_color_t color)
{
    for (int i = 0; i < h; i++) display_draw_hline(x, y + i, w, color);
}

void display_draw_circle(int cx, int cy, int r, display_color_t color)
{
    int x = r, y = 0, err = 0;
    while (x >= y) {
        display_draw_pixel(cx + x, cy + y, color);
        display_draw_pixel(cx + y, cy + x, color);
        display_draw_pixel(cx - y, cy + x, color);
        display_draw_pixel(cx - x, cy + y, color);
        display_draw_pixel(cx - x, cy - y, color);
        display_draw_pixel(cx - y, cy - x, color);
        display_draw_pixel(cx + y, cy - x, color);
        display_draw_pixel(cx + x, cy - y, color);
        y++;
        err += 1 + 2 * y;
        if (2 * (err - x) + 1 > 0) { x--; err += 1 - 2 * x; }
    }
}

void display_fill_circle(int cx, int cy, int r, display_color_t color)
{
    for (int y = -r; y <= r; y++) {
        for (int x = -r; x <= r; x++) {
            if (x * x + y * y <= r * r) display_draw_pixel(cx + x, cy + y, color);
        }
    }
}

void display_draw_char(int x, int y, char c, display_color_t color, uint8_t size)
{
    if (c < 32 || c > 127) c = '?';
    const uint8_t *glyph = &font6x8[(c - 32) * 6];
    
    for (int col = 0; col < 6; col++) {
        uint8_t line = glyph[col];
        for (int row = 0; row < 8; row++) {
            if (line & (1 << row)) {
                if (size == 1) display_draw_pixel(x + col, y + row, color);
                else display_fill_rect(x + col * size, y + row * size, size, size, color);
            }
        }
    }
}

void display_draw_string(int x, int y, const char *str, display_color_t color, uint8_t size)
{
    int cx = x;
    while (*str) {
        if (*str == '\n') { cx = x; y += 8 * size; }
        else { display_draw_char(cx, y, *str, color, size); cx += 6 * size; }
        str++;
    }
}

void display_printf(int x, int y, display_color_t color, uint8_t size, const char *fmt, ...)
{
    char buf[128];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    display_draw_string(x, y, buf, color, size);
}

void display_draw_progress(int x, int y, int w, int h, int progress)
{
    if (progress < 0) progress = 0;
    if (progress > 100) progress = 100;
    display_draw_rect(x, y, w, h, COLOR_WHITE);
    int fill = (w - 4) * progress / 100;
    if (fill > 0) display_fill_rect(x + 2, y + 2, fill, h - 4, COLOR_WHITE);
}

/* ============================================================================
 * UI Helper Functions
 * ============================================================================ */

void display_draw_status_bar(bool mesh_connected, int unread_count, int battery_pct)
{
    /* Clear status bar area */
    display_fill_rect(0, 0, DISPLAY_WIDTH, 10, COLOR_BLACK);
    
    /* Mesh icon (left) */
    if (mesh_connected) {
        /* Connected: signal bars */
        display_draw_vline(2, 6, 3, COLOR_WHITE);
        display_draw_vline(5, 4, 5, COLOR_WHITE);
        display_draw_vline(8, 2, 7, COLOR_WHITE);
    } else {
        /* Disconnected: X */
        display_draw_line(2, 2, 8, 8, COLOR_WHITE);
        display_draw_line(8, 2, 2, 8, COLOR_WHITE);
    }
    
    /* Unread count (center) */
    if (unread_count > 0) {
        display_printf(50, 1, COLOR_WHITE, 1, "%d msg", unread_count);
    }
    
    /* Battery (right) */
    if (battery_pct >= 0) {
        int bx = DISPLAY_WIDTH - 22;
        display_draw_rect(bx, 2, 18, 7, COLOR_WHITE);
        display_fill_rect(bx + 18, 4, 2, 3, COLOR_WHITE);
        int fill = 14 * battery_pct / 100;
        if (fill > 0) display_fill_rect(bx + 2, 4, fill, 3, COLOR_WHITE);
    }
    
    /* Separator line */
    display_draw_hline(0, 10, DISPLAY_WIDTH, COLOR_WHITE);
}

void display_draw_joystick_indicator(int x, int y, int radius, int8_t joy_x, int8_t joy_y)
{
    /* Outer circle */
    display_draw_circle(x, y, radius, COLOR_WHITE);
    
    /* Crosshairs */
    display_draw_hline(x - radius + 2, y, radius * 2 - 3, COLOR_WHITE);
    display_draw_vline(x, y - radius + 2, radius * 2 - 3, COLOR_WHITE);
    
    /* Joystick position dot */
    int px = x + (joy_x * (radius - 3)) / 100;
    int py = y - (joy_y * (radius - 3)) / 100;  /* Y inverted for screen coords */
    display_fill_circle(px, py, 3, COLOR_WHITE);
}

void display_draw_message(int x, int y, const char *from, const char *message, bool is_incoming)
{
    /* From name */
    display_printf(x, y, COLOR_WHITE, 1, "%s:", from);
    
    /* Message (truncate if needed) */
    char buf[22];
    strncpy(buf, message, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    
    display_draw_string(x, y + 10, buf, COLOR_WHITE, 1);
    
    /* Direction indicator */
    if (is_incoming) {
        display_draw_string(x + 120, y, "<", COLOR_WHITE, 1);
    } else {
        display_draw_string(x + 120, y, ">", COLOR_WHITE, 1);
    }
}

void display_draw_bitmap(int x, int y, const uint8_t *bitmap, int w, int h, display_color_t color)
{
    if (!bitmap) return;
    
    /* Bitmap is packed horizontally, 8 pixels per byte */
    int bytes_per_row = (w + 7) / 8;
    
    for (int row = 0; row < h; row++) {
        for (int col = 0; col < w; col++) {
            int byte_idx = row * bytes_per_row + col / 8;
            int bit_idx = 7 - (col % 8);
            if (bitmap[byte_idx] & (1 << bit_idx)) {
                display_draw_pixel(x + col, y + row, color);
            }
        }
    }
}

void display_draw_text_input(int x, int y, int w, const char *text, int cursor_pos)
{
    /* Input box */
    display_draw_rect(x, y, w, 12, COLOR_WHITE);
    
    /* Text */
    int tx = x + 2;
    int max_chars = (w - 4) / 6;
    
    if (text) {
        int len = strlen(text);
        int start = 0;
        
        /* Scroll if cursor is past visible area */
        if (cursor_pos >= max_chars) {
            start = cursor_pos - max_chars + 1;
        }
        
        /* Draw visible portion */
        for (int i = 0; i < max_chars && (start + i) < len; i++) {
            display_draw_char(tx + i * 6, y + 2, text[start + i], COLOR_WHITE, 1);
        }
        
        /* Cursor */
        if (cursor_pos >= 0) {
            int cx = tx + (cursor_pos - start) * 6;
            if (cx >= x && cx < x + w - 6) {
                display_draw_vline(cx, y + 2, 8, COLOR_INVERSE);
            }
        }
    }
}

