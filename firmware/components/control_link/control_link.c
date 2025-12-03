/**
 * @file control_link.c
 * @brief BLE control link - connects to partner device and receives joystick events
 */

#include "control_link.h"

#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"

ESP_EVENT_DEFINE_BASE(CONTROL_LINK_EVENT);

static const char *TAG = "control_link";

/* Partner device name to scan for */
#define PARTNER_DEVICE_NAME     "TransPartner"

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

/* State */
static bool s_initialized = false;
static bool s_scanning = false;
static bool s_connected = false;
static uint16_t s_conn_handle = 0;
static uint16_t s_joystick_val_handle = 0;

/* Callbacks */
static void (*s_macro_handler)(const control_link_packet_t *packet) = NULL;
static void (*s_joystick_handler)(const control_link_joystick_t *state) = NULL;

/* Forward declarations */
static void ble_host_task(void *param);
static int ble_gap_event(struct ble_gap_event *event, void *arg);
static void start_scan(void);

/**
 * @brief Called when joystick notification received
 */
static void on_joystick_notify(const uint8_t *data, size_t len)
{
    if (!s_joystick_handler || len < 8) {
        return;
    }

    control_link_joystick_t state = {
        .x = (int8_t)data[0],
        .y = (int8_t)data[1],
        .buttons = data[2],
        .layer = data[3],
        .seq = (uint32_t)data[4] | ((uint32_t)data[5] << 8) | 
               ((uint32_t)data[6] << 16) | ((uint32_t)data[7] << 24),
    };

    s_joystick_handler(&state);
    esp_event_post(CONTROL_LINK_EVENT, CONTROL_LINK_EVENT_JOYSTICK, 
                   &state, sizeof(state), 0);
}

/**
 * @brief GATT attribute event callback
 */
static int on_gatt_attr(uint16_t conn_handle, const struct ble_gatt_error *error,
                        struct ble_gatt_attr *attr, void *arg)
{
    if (error->status == 0 && attr != NULL) {
        /* Notification data */
        on_joystick_notify(attr->om->om_data, attr->om->om_len);
    }
    return 0;
}

/**
 * @brief Called after subscribing to notifications
 */
static int on_subscribe(uint16_t conn_handle, const struct ble_gatt_error *error,
                        struct ble_gatt_attr *attr, void *arg)
{
    if (error->status == 0) {
        ESP_LOGI(TAG, "Subscribed to joystick notifications");
    } else {
        ESP_LOGE(TAG, "Subscribe failed: %d", error->status);
    }
    return 0;
}

/**
 * @brief Called when characteristic discovered
 */
static int on_chr_discovered(uint16_t conn_handle,
                             const struct ble_gatt_error *error,
                             const struct ble_gatt_chr *chr, void *arg)
{
    if (error->status == 0 && chr != NULL) {
        /* Check if this is the joystick characteristic */
        if (ble_uuid_cmp(&chr->uuid.u, &joystick_chr_uuid.u) == 0) {
            ESP_LOGI(TAG, "Found joystick characteristic, handle=%d", chr->val_handle);
            s_joystick_val_handle = chr->val_handle;
            
            /* Subscribe to notifications */
            uint8_t value[2] = {0x01, 0x00};  /* Enable notifications */
            ble_gattc_write_flat(conn_handle, chr->val_handle + 1, 
                                 value, sizeof(value), on_subscribe, NULL);
        }
    } else if (error->status == BLE_HS_EDONE) {
        ESP_LOGI(TAG, "Characteristic discovery complete");
    }
    return 0;
}

/**
 * @brief Called when service discovered
 */
static int on_svc_discovered(uint16_t conn_handle,
                             const struct ble_gatt_error *error,
                             const struct ble_gatt_svc *svc, void *arg)
{
    if (error->status == 0 && svc != NULL) {
        ESP_LOGI(TAG, "Found Remote Input service");
        
        /* Discover characteristics */
        ble_gattc_disc_chrs_by_uuid(conn_handle, svc->start_handle, svc->end_handle,
                                    &joystick_chr_uuid.u, on_chr_discovered, NULL);
    } else if (error->status == BLE_HS_EDONE) {
        ESP_LOGI(TAG, "Service discovery complete");
    }
    return 0;
}

/**
 * @brief GAP event handler
 */
static int ble_gap_event(struct ble_gap_event *event, void *arg)
{
    struct ble_gap_conn_desc desc;
    
    switch (event->type) {
    case BLE_GAP_EVENT_DISC:
        /* Check if this is our partner device */
        if (event->disc.event_type == BLE_HCI_ADV_RPT_EVTYPE_ADV_IND ||
            event->disc.event_type == BLE_HCI_ADV_RPT_EVTYPE_SCAN_RSP) {
            
            struct ble_hs_adv_fields fields;
            ble_hs_adv_parse_fields(&fields, event->disc.data, event->disc.length_data);
            
            if (fields.name != NULL && fields.name_len > 0) {
                if (strncmp((char *)fields.name, PARTNER_DEVICE_NAME, fields.name_len) == 0) {
                    ESP_LOGI(TAG, "Found partner device: %s", PARTNER_DEVICE_NAME);
                    
                    /* Stop scanning and connect */
                    ble_gap_disc_cancel();
                    s_scanning = false;
                    
                    ble_gap_connect(BLE_OWN_ADDR_PUBLIC, &event->disc.addr,
                                    30000, NULL, ble_gap_event, NULL);
                }
            }
        }
        break;

    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            ESP_LOGI(TAG, "Connected to partner device");
            s_connected = true;
            s_conn_handle = event->connect.conn_handle;
            
            esp_event_post(CONTROL_LINK_EVENT, CONTROL_LINK_EVENT_CONNECTED, NULL, 0, 0);
            
            /* Discover services */
            ble_gattc_disc_svc_by_uuid(s_conn_handle, &remote_input_svc_uuid.u,
                                       on_svc_discovered, NULL);
        } else {
            ESP_LOGE(TAG, "Connection failed: %d", event->connect.status);
            start_scan();
        }
        break;

    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGW(TAG, "Disconnected from partner device");
        s_connected = false;
        s_conn_handle = 0;
        s_joystick_val_handle = 0;
        
        esp_event_post(CONTROL_LINK_EVENT, CONTROL_LINK_EVENT_DISCONNECTED, NULL, 0, 0);
        
        /* Restart scanning */
        start_scan();
        break;

    case BLE_GAP_EVENT_DISC_COMPLETE:
        ESP_LOGI(TAG, "Scan complete");
        s_scanning = false;
        if (!s_connected) {
            /* Restart scan after a delay */
            vTaskDelay(pdMS_TO_TICKS(1000));
            start_scan();
        }
        break;

    case BLE_GAP_EVENT_NOTIFY_RX:
        /* Received notification from partner */
        if (event->notify_rx.attr_handle == s_joystick_val_handle) {
            uint8_t buf[16];
            uint16_t len = OS_MBUF_PKTLEN(event->notify_rx.om);
            if (len > sizeof(buf)) len = sizeof(buf);
            os_mbuf_copydata(event->notify_rx.om, 0, len, buf);
            on_joystick_notify(buf, len);
        }
        break;

    default:
        break;
    }
    
    return 0;
}

/**
 * @brief Start scanning for partner device
 */
static void start_scan(void)
{
    if (s_scanning || s_connected) {
        return;
    }
    
    struct ble_gap_disc_params scan_params = {
        .itvl = 0x0010,
        .window = 0x0010,
        .filter_policy = BLE_HCI_SCAN_FILT_NO_WL,
        .limited = 0,
        .passive = 0,
        .filter_duplicates = 1,
    };
    
    int rc = ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 10000, &scan_params, ble_gap_event, NULL);
    if (rc == 0) {
        s_scanning = true;
        ESP_LOGI(TAG, "Scanning for partner device...");
    } else {
        ESP_LOGE(TAG, "Failed to start scan: %d", rc);
    }
}

/**
 * @brief BLE sync callback
 */
static void on_ble_sync(void)
{
    /* Start scanning for partner */
    start_scan();
}

/**
 * @brief BLE reset callback
 */
static void on_ble_reset(int reason)
{
    ESP_LOGE(TAG, "BLE reset, reason=%d", reason);
}

/**
 * @brief NimBLE host task
 */
static void ble_host_task(void *param)
{
    ESP_LOGI(TAG, "BLE host task started");
    nimble_port_run();
    nimble_port_freertos_deinit();
}

/* ============================================================================
 * Public API
 * ============================================================================ */

esp_err_t control_link_init(void)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    
    ESP_LOGI(TAG, "Initializing BLE control link");
    
    /* Initialize NimBLE */
    esp_err_t ret = nimble_port_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init NimBLE: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Configure host callbacks */
    ble_hs_cfg.sync_cb = on_ble_sync;
    ble_hs_cfg.reset_cb = on_ble_reset;
    
    /* Set device name */
    ble_svc_gap_device_name_set("Translator");
    
    /* Start host task */
    nimble_port_freertos_init(ble_host_task);
    
    s_initialized = true;
    ESP_LOGI(TAG, "BLE control link initialized");
    
    return ESP_OK;
}

esp_err_t control_link_start_advertising(void)
{
    /* This device is a client, not advertising. Start scanning instead. */
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    
    /* Scanning starts automatically via on_ble_sync callback */
    ESP_LOGI(TAG, "BLE ready, will scan for partner device");
    return ESP_OK;
}

esp_err_t control_link_send_ack(uint32_t seq)
{
    /* TODO: Send ACK back to partner if needed */
    ESP_LOGD(TAG, "ACK seq %lu", (unsigned long)seq);
    return ESP_OK;
}

esp_err_t control_link_subscribe_macros(void (*handler)(const control_link_packet_t *packet))
{
    if (!handler) {
        return ESP_ERR_INVALID_ARG;
    }
    s_macro_handler = handler;
    return ESP_OK;
}

esp_err_t control_link_subscribe_joystick(void (*handler)(const control_link_joystick_t *state))
{
    if (!handler) {
        return ESP_ERR_INVALID_ARG;
    }
    s_joystick_handler = handler;
    return ESP_OK;
}

bool control_link_is_connected(void)
{
    return s_connected;
}
