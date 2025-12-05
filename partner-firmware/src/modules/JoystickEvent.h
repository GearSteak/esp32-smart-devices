/**
 * @file JoystickEvent.h
 * @brief Joystick event structure for USB Serial communication
 * 
 * This 8-byte structure is sent via USB Serial to the pi wrist computer.
 * It must be packed to ensure correct byte alignment.
 */

#pragma once

#include <stdint.h>

/**
 * @brief Joystick event structure (8 bytes, packed)
 * 
 * Sent via USB Serial at 115200 baud to pi wrist computer.
 */
struct __attribute__((packed)) JoystickEvent {
    int8_t x;           ///< X-axis: -100 (left) to +100 (right)
    int8_t y;           ///< Y-axis: -100 (down) to +100 (up)
    uint8_t buttons;    ///< Button bitmask: bit0=press, bit1=double, bit2=long, bit3=home, bit4=back
    uint8_t layer;      ///< Context layer: 0=global, 1=text, 2=csv, 3=modifier, 4=mesh_compose, 5=mesh_inbox
    uint32_t seq;       ///< Sequence number for tracking (little-endian)
};

