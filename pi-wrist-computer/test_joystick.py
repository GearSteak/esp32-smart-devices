#!/usr/bin/env python3
"""
Test script to check if ESP32 joystick packets are being received.
Run this to verify the USB serial connection is working.
"""

import serial
import serial.tools.list_ports
import time
import sys

def find_esp32_port():
    """Find ESP32 USB serial port."""
    esp32_identifiers = ['CP210', 'CH340', 'CH341', 'FT232', 'Silicon Labs', 'USB Serial']
    
    ports = serial.tools.list_ports.comports()
    for port in ports:
        description = port.description.upper()
        for identifier in esp32_identifiers:
            if identifier.upper() in description:
                print(f"Found ESP32 on {port.device}")
                return port.device
    
    # Fallback: try common ports
    common_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyUSB1', '/dev/ttyACM1']
    for port_name in common_ports:
        try:
            test_serial = serial.Serial(port_name, 115200, timeout=0.1)
            test_serial.close()
            print(f"Found port {port_name}")
            return port_name
        except:
            pass
    
    return None

def test_joystick():
    """Test receiving joystick packets."""
    port = find_esp32_port()
    
    if not port:
        print("ERROR: No ESP32 device found!")
        print("\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device} - {p.description}")
        return False
    
    print(f"\nConnecting to {port} at 115200 baud...")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=1.0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # Flush any stale data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        print("Connected! Waiting for packets...")
        print("Move the joystick or press buttons to see data.\n")
        print("Format: x=XXX y=YYY btn=0xXX (raw bytes)")
        print("-" * 50)
        
        packet_count = 0
        start_time = time.time()
        
        while True:
            # Wait for 8 bytes
            if ser.in_waiting >= 8:
                data = ser.read(8)
                
                if len(data) == 8:
                    # Parse packet
                    x = int.from_bytes([data[0]], byteorder='little', signed=True)
                    y = int.from_bytes([data[1]], byteorder='little', signed=True)
                    buttons = data[2]
                    layer = data[3]
                    seq = int.from_bytes(data[4:8], byteorder='little')
                    
                    # Validate packet
                    if abs(x) <= 100 and abs(y) <= 100:
                        packet_count += 1
                        elapsed = time.time() - start_time
                        rate = packet_count / elapsed if elapsed > 0 else 0
                        
                        print(f"Packet #{packet_count}: x={x:4d} y={y:4d} btn=0x{buttons:02x} layer={layer} seq={seq} "
                              f"({rate:.1f} pkt/s)")
                    else:
                        print(f"Invalid packet: x={x} y={y} (skipping)")
                        print(f"Raw bytes: {data.hex()}")
            else:
                time.sleep(0.01)
                
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n\nReceived {packet_count} packets total")
        print("Test stopped.")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    print("=" * 50)
    print("ESP32 Joystick Packet Receiver Test")
    print("=" * 50)
    print()
    
    success = test_joystick()
    sys.exit(0 if success else 1)

