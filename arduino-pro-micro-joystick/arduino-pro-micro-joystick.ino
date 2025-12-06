/**
 * Arduino Pro Micro Joystick Controller
 * 
 * Reads analog joystick and buttons, sends as keyboard/mouse input
 * Works with built-in libraries - no external libraries needed!
 * Compatible with Raspberry Pi (shows up as keyboard/mouse)
 */

#include <Keyboard.h>
#include <Mouse.h>

// Pin definitions
#define JOYSTICK_X_PIN A0  // X axis analog input
#define JOYSTICK_Y_PIN A1  // Y axis analog input
#define JOYSTICK_BTN_PIN 2  // Joystick button (with internal pull-up)
#define BUTTON_HOME_PIN 3  // Home button (with internal pull-up)

// Calibration
int x_center = 512;
int y_center = 512;

// Deadzone
#define DEADZONE 50

// Movement settings
#define MOUSE_SPEED 5  // Pixels per movement
#define MOVEMENT_THRESHOLD 3  // Minimum movement to trigger

// State
int last_x = 0;
int last_y = 0;

void setup() {
  // Initialize pins
  pinMode(JOYSTICK_BTN_PIN, INPUT_PULLUP);
  pinMode(BUTTON_HOME_PIN, INPUT_PULLUP);
  
  // Initialize Keyboard and Mouse
  Keyboard.begin();
  Mouse.begin();
  
  // Calibrate center position (assume joystick is centered at startup)
  delay(100);
  calibrate();
  
  // Small delay to let everything settle
  delay(100);
}

void loop() {
  // Read joystick
  int x_raw = analogRead(JOYSTICK_X_PIN);
  int y_raw = analogRead(JOYSTICK_Y_PIN);
  
  // Convert to -127 to +127 range (centered around calibrated center)
  int x_val = (x_raw - x_center) * 127 / 512;
  int y_val = (y_raw - y_center) * 127 / 512;
  
  // Apply deadzone
  if (abs(x_val) < DEADZONE) x_val = 0;
  if (abs(y_val) < DEADZONE) y_val = 0;
  
  // Convert to mouse movement
  int dx = x_val * MOUSE_SPEED / 127;
  int dy = y_val * MOUSE_SPEED / 127;
  
  // Only move if change is significant
  if (abs(dx) >= MOVEMENT_THRESHOLD || abs(dy) >= MOVEMENT_THRESHOLD) {
    Mouse.move(dx, -dy, 0);  // Negative Y because screen coordinates
    last_x = dx;
    last_y = dy;
  }
  
  // Read buttons
  bool joystick_btn = !digitalRead(JOYSTICK_BTN_PIN);  // LOW = pressed
  bool home_btn = !digitalRead(BUTTON_HOME_PIN);
  
  // Handle joystick button (left mouse click)
  static bool last_joystick_btn = false;
  if (joystick_btn && !last_joystick_btn) {
    Mouse.press(MOUSE_LEFT);
  } else if (!joystick_btn && last_joystick_btn) {
    Mouse.release(MOUSE_LEFT);
  }
  last_joystick_btn = joystick_btn;
  
  // Handle home button (ESC key)
  static bool last_home_btn = false;
  if (home_btn && !last_home_btn) {
    Keyboard.press(KEY_ESC);
  } else if (!home_btn && last_home_btn) {
    Keyboard.release(KEY_ESC);
  }
  last_home_btn = home_btn;
  
  // Small delay for stability
  delay(10);  // ~100Hz update rate
}

void calibrate() {
  // Read center position
  int x_sum = 0;
  int y_sum = 0;
  int samples = 20;
  
  for (int i = 0; i < samples; i++) {
    x_sum += analogRead(JOYSTICK_X_PIN);
    y_sum += analogRead(JOYSTICK_Y_PIN);
    delay(10);
  }
  
  x_center = x_sum / samples;
  y_center = y_sum / samples;
}
