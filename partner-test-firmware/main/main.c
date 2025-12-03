/**
 * @file main.c
 * @brief Partner Test Firmware - Joystick + BLE
 * 
 * Reads joystick and buttons, sends to main device via BLE.
 * 
 * Wiring:
 *   Joystick VRx → GPIO 34
 *   Joystick VRy → GPIO 35
 *   Joystick SW  → GPIO 32
 *   Home button  → GPIO 33
 *   Back button  → GPIO 25
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "partner";

/* ============================================================================
 * Pin Configuration
 * ============================================================================ */
#define JOYSTICK_X_PIN      34
#define JOYSTICK_Y_PIN      35
#define JOYSTICK_BTN_PIN    32
#define BUTTON_HOME_PIN     33
#define BUTTON_BACK_PIN     25

#define JOYSTICK_CENTER     2048
#define JOYSTICK_DEADZONE   164

/* ============================================================================
 * BLE Configuration
 * ============================================================================ */
#define DEVICE_NAME         "TransPartner"

/* Remote Input Service UUID: 4f9a0001-8c3f-4a0e-89a7-6d277cf9a000 */
static const ble_uuid128_t remote_input_svc_uuid = BLE_UUID128_INIT(
    0x00, 0xa0, 0xf9, 0x7c, 0x27, 0x6d, 0xa7, 0x89,
    0x0e, 0x4a, 0x3f, 0x8c, 0x01, 0x00, 0x9a, 0x4f
);

/* JoystickEvent characteristic UUID: 4f9a0002-8c3f-4a0e-89a7-6d277cf9a000 */
static const ble_uuid128_t joystick_chr_uuid = BLE_UUID128_INIT(
    0x00, 0xa0, 0xf9, 0x7c, 0x27, 0x6d, 0xa7, 0x89,
    0x0e, 0x4a, 0x3f, 0x8c, 0x02, 0x00, 0x9a, 0x4f
);

/* ============================================================================
 * State
 * ============================================================================ */

/* Joystick event structure (8 bytes) */
typedef struct __attribute__((packed)) {
    int8_t x;
    int8_t y;
    uint8_t buttons;
    uint8_t layer;
    uint32_t seq;
} joystick_event_t;

static uint16_t s_conn_handle = 0;
static bool s_connected = false;
static bool s_notify_enabled = false;
static uint16_t s_joystick_chr_val_handle;
static uint32_t s_seq = 0;

static joystick_event_t s_current_state = {0};
static joystick_event_t s_last_sent_state = {0};

/* Button state for gesture detection */
static uint32_t s_btn_down_time = 0;
static bool s_btn_was_pressed = false;
static bool s_long_triggered = false;
static uint8_t s_press_count = 0;
static uint32_t s_last_press_time = 0;

/* ============================================================================
 * ADC / Joystick Reading
 * ============================================================================ */

static esp_adc_cal_characteristics_t s_adc_chars;

static void init_adc(void)
{
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);  /* GPIO34 */
    adc1_config_channel_atten(ADC1_CHANNEL_7, ADC_ATTEN_DB_11);  /* GPIO35 */
    
    esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_11, ADC_WIDTH_BIT_12,
                             1100, &s_adc_chars);
}

static int8_t read_axis(adc1_channel_t channel, bool invert)
{
    int raw = adc1_get_raw(channel);
    int centered = raw - JOYSTICK_CENTER;
    
    if (abs(centered) < JOYSTICK_DEADZONE) {
        return 0;
    }
    
    /* Remove deadzone from range */
    if (centered > 0) centered -= JOYSTICK_DEADZONE;
    else centered += JOYSTICK_DEADZONE;
    
    int16_t normalized = (centered * 100) / (JOYSTICK_CENTER - JOYSTICK_DEADZONE);
    if (normalized > 100) normalized = 100;
    if (normalized < -100) normalized = -100;
    
    return invert ? -normalized : normalized;
}

static void init_buttons(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << JOYSTICK_BTN_PIN) | 
                        (1ULL << BUTTON_HOME_PIN) | 
                        (1ULL << BUTTON_BACK_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
}

static void read_input(joystick_event_t *evt)
{
    /* Read joystick */
    evt->x = read_axis(ADC1_CHANNEL_6, false);
    evt->y = read_axis(ADC1_CHANNEL_7, true);  /* Y often inverted */
    
    /* Read buttons */
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    bool btn_pressed = (gpio_get_level(JOYSTICK_BTN_PIN) == 0);
    bool home_pressed = (gpio_get_level(BUTTON_HOME_PIN) == 0);
    bool back_pressed = (gpio_get_level(BUTTON_BACK_PIN) == 0);
    
    evt->buttons = 0;
    
    /* Joystick button with gesture detection */
    if (btn_pressed && !s_btn_was_pressed) {
        /* Button just pressed */
        s_btn_down_time = now;
        s_long_triggered = false;
        
        if (now - s_last_press_time < 300) {
            s_press_count++;
        } else {
            s_press_count = 1;
        }
        s_last_press_time = now;
    }
    
    if (btn_pressed) {
        evt->buttons |= 0x01;  /* Press */
        
        if (!s_long_triggered && (now - s_btn_down_time > 700)) {
            evt->buttons |= 0x04;  /* Long press */
            s_long_triggered = true;
        }
    }
    
    /* Double press detection */
    if (!btn_pressed && s_btn_was_pressed && s_press_count >= 2) {
        evt->buttons |= 0x02;  /* Double press */
    }
    
    s_btn_was_pressed = btn_pressed;
    
    /* Home/Back buttons */
    if (home_pressed) evt->buttons |= 0x08;
    if (back_pressed) evt->buttons |= 0x10;
    
    /* Layer is managed by main device, we just send 0 */
    evt->layer = 0;
}

/* ============================================================================
 * BLE GATT
 * ============================================================================ */

static int joystick_chr_access(uint16_t conn_handle, uint16_t attr_handle,
                               struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, &s_current_state, sizeof(s_current_state));
        return 0;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

static const struct ble_gatt_svc_def gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &remote_input_svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = &joystick_chr_uuid.u,
                .access_cb = joystick_chr_access,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_joystick_chr_val_handle,
            },
            { 0 }  /* End of characteristics */
        },
    },
    { 0 }  /* End of services */
};

/* ============================================================================
 * BLE GAP
 * ============================================================================ */

static void start_advertising(void)
{
    struct ble_gap_adv_params adv_params = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,
        .disc_mode = BLE_GAP_DISC_MODE_GEN,
        .itvl_min = 0x0020,
        .itvl_max = 0x0040,
    };
    
    struct ble_hs_adv_fields fields = {
        .flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP,
        .name = (uint8_t *)DEVICE_NAME,
        .name_len = strlen(DEVICE_NAME),
        .name_is_complete = 1,
    };
    
    ble_gap_adv_set_fields(&fields);
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv_params,
                      NULL, NULL);
    
    ESP_LOGI(TAG, "Advertising as '%s'", DEVICE_NAME);
}

static int gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            ESP_LOGI(TAG, "Connected!");
            s_connected = true;
            s_conn_handle = event->connect.conn_handle;
        } else {
            start_advertising();
        }
        break;
        
    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGI(TAG, "Disconnected");
        s_connected = false;
        s_notify_enabled = false;
        start_advertising();
        break;
        
    case BLE_GAP_EVENT_SUBSCRIBE:
        if (event->subscribe.attr_handle == s_joystick_chr_val_handle) {
            s_notify_enabled = event->subscribe.cur_notify;
            ESP_LOGI(TAG, "Notifications %s", s_notify_enabled ? "enabled" : "disabled");
        }
        break;
    }
    
    return 0;
}

static void on_sync(void)
{
    ble_hs_id_infer_auto(0, NULL);
    start_advertising();
}

static void ble_host_task(void *param)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

/* ============================================================================
 * Main
 * ============================================================================ */

static void send_joystick_notification(void)
{
    if (!s_connected || !s_notify_enabled) {
        return;
    }
    
    struct os_mbuf *om = ble_hs_mbuf_from_flat(&s_current_state, sizeof(s_current_state));
    if (om) {
        ble_gatts_notify_custom(s_conn_handle, s_joystick_chr_val_handle, om);
    }
}

static bool state_changed(void)
{
    if (abs(s_current_state.x - s_last_sent_state.x) > 2) return true;
    if (abs(s_current_state.y - s_last_sent_state.y) > 2) return true;
    if (s_current_state.buttons != s_last_sent_state.buttons) return true;
    return false;
}

static void input_task(void *arg)
{
    ESP_LOGI(TAG, "Input task started");
    
    while (1) {
        read_input(&s_current_state);
        
        if (state_changed()) {
            s_current_state.seq = ++s_seq;
            send_joystick_notification();
            memcpy(&s_last_sent_state, &s_current_state, sizeof(joystick_event_t));
            
            ESP_LOGD(TAG, "Joy: x=%+4d y=%+4d btn=0x%02x seq=%lu",
                     s_current_state.x, s_current_state.y,
                     s_current_state.buttons, (unsigned long)s_current_state.seq);
        }
        
        vTaskDelay(pdMS_TO_TICKS(10));  /* 100 Hz */
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Partner Test Firmware Starting");
    
    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }
    
    /* Initialize hardware */
    init_adc();
    init_buttons();
    ESP_LOGI(TAG, "Hardware initialized");
    
    /* Initialize NimBLE */
    ESP_ERROR_CHECK(nimble_port_init());
    
    ble_hs_cfg.sync_cb = on_sync;
    ble_hs_cfg.gatts_register_cb = NULL;
    
    ble_svc_gap_init();
    ble_svc_gatt_init();
    
    ble_gatts_count_cfg(gatt_svcs);
    ble_gatts_add_svcs(gatt_svcs);
    
    ble_svc_gap_device_name_set(DEVICE_NAME);
    
    nimble_port_freertos_init(ble_host_task);
    ESP_LOGI(TAG, "BLE initialized");
    
    /* Start input reading task */
    xTaskCreate(input_task, "input", 4096, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "Ready! Waiting for connection...");
}

