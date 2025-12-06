"""
ST7789V 240x320 LCD Display Driver

Direct SPI driver using spidev and PIL - no luma dependency.
"""

import spidev
from PIL import Image, ImageDraw, ImageFont
import time

# Use centralized GPIO manager
from ..utils.gpio_manager import gpio

# Default font path
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ST7789 Commands
ST7789_NOP = 0x00
ST7789_SWRESET = 0x01
ST7789_SLPOUT = 0x11
ST7789_NORON = 0x13
ST7789_INVON = 0x21
ST7789_DISPON = 0x29
ST7789_CASET = 0x2A
ST7789_RASET = 0x2B
ST7789_RAMWR = 0x2C
ST7789_MADCTL = 0x36
ST7789_COLMOD = 0x3A


class Display:
    """ST7789V LCD Display driver with drawing utilities."""
    
    def __init__(self, config: dict):
        """
        Initialize the display.
        
        Args:
            config: Display configuration dict with:
                - width, height: Display dimensions
                - spi_port, spi_device: SPI settings
                - gpio_dc, gpio_rst, gpio_bl: GPIO pins
                - brightness: 0-100
                - rotation: 0, 90, 180, 270
        """
        self.width = config.get('width', 240)
        self.height = config.get('height', 320)
        self.rotation = config.get('rotation', 0)
        self.brightness = config.get('brightness', 100)
        self.invert_colors = config.get('invert_colors', True)  # Some displays need False
        
        # GPIO pins
        self.gpio_dc = config.get('gpio_dc', 25)
        self.gpio_rst = config.get('gpio_rst', 27)
        self.gpio_bl = config.get('gpio_bl', 24)
        
        # Track if already initialized
        self._initialized = False
        
        # Setup GPIO using centralized manager
        # Note: Don't set up backlight as regular output - PWM will handle it
        gpio.setup_output(self.gpio_dc)
        gpio.setup_output(self.gpio_rst)
        
        # Backlight PWM (this will set up the pin as output internally)
        self._pwm = gpio.setup_pwm(self.gpio_bl, 1000)
        if self._pwm:
            self._pwm.start(self.brightness)
        else:
            # Fallback: if PWM fails, try regular output
            gpio.setup_output(self.gpio_bl)
            gpio.output(self.gpio_bl, True)  # Turn on backlight
        
        # Setup SPI
        self._spi = spidev.SpiDev()
        self._spi.open(config.get('spi_port', 0), config.get('spi_device', 0))
        self._spi.max_speed_hz = 40000000  # 40MHz
        self._spi.mode = 0
        
        # Initialize display
        self._init_display()
        
        # Create framebuffer
        self._buffer = Image.new('RGB', (self.width, self.height), 'black')
        self._draw = ImageDraw.Draw(self._buffer)
        
        # Load fonts
        self._fonts = {}
        self._load_fonts()
    
    def _reset(self):
        """Hardware reset the display."""
        gpio.output(self.gpio_rst, True)
        time.sleep(0.05)
        gpio.output(self.gpio_rst, False)
        time.sleep(0.05)
        gpio.output(self.gpio_rst, True)
        time.sleep(0.15)
    
    def _command(self, cmd):
        """Send command byte."""
        gpio.output(self.gpio_dc, False)
        self._spi.writebytes([cmd])
    
    def _data(self, data):
        """Send data bytes."""
        gpio.output(self.gpio_dc, True)
        if isinstance(data, int):
            self._spi.writebytes([data])
        else:
            # Send in chunks for large data
            chunk_size = 4096
            for i in range(0, len(data), chunk_size):
                self._spi.writebytes(list(data[i:i + chunk_size]))
    
    def _init_display(self):
        """Initialize ST7789 display."""
        if self._initialized:
            return  # Don't re-initialize
        
        self._reset()
        
        # Software reset
        self._command(ST7789_SWRESET)
        time.sleep(0.15)
        
        # Sleep out
        self._command(ST7789_SLPOUT)
        time.sleep(0.5)
        
        # Color mode: 16-bit
        self._command(ST7789_COLMOD)
        self._data(0x55)
        time.sleep(0.01)
        
        # Memory access control (rotation)
        # Store original dimensions
        orig_width = self.width
        orig_height = self.height
        
        self._command(ST7789_MADCTL)
        if self.rotation == 0:
            self._data(0x00)
        elif self.rotation == 90:
            self._data(0x60)
            self.width, self.height = orig_height, orig_width
        elif self.rotation == 180:
            self._data(0xC0)
        elif self.rotation == 270:
            self._data(0xA0)
            self.width, self.height = orig_height, orig_width
        
        # Recreate buffer with correct dimensions
        self._buffer = Image.new('RGB', (self.width, self.height), 'black')
        self._draw = ImageDraw.Draw(self._buffer)
        
        # Color inversion - some displays need INVON, others need INVOFF
        if self.invert_colors:
            self._command(ST7789_INVON)
        else:
            self._command(0x20)  # INVOFF
        time.sleep(0.01)
        
        # Normal display mode
        self._command(ST7789_NORON)
        time.sleep(0.01)
        
        # Display on
        self._command(ST7789_DISPON)
        time.sleep(0.1)
        
        self._initialized = True
    
    def _set_window(self, x0, y0, x1, y1):
        """Set the drawing window."""
        self._command(ST7789_CASET)
        self._data(x0 >> 8)
        self._data(x0 & 0xFF)
        self._data(x1 >> 8)
        self._data(x1 & 0xFF)
        
        self._command(ST7789_RASET)
        self._data(y0 >> 8)
        self._data(y0 & 0xFF)
        self._data(y1 >> 8)
        self._data(y1 & 0xFF)
        
        self._command(ST7789_RAMWR)
    
    def _load_fonts(self):
        """Load default fonts."""
        try:
            for size in [10, 12, 14, 16, 18, 20, 24, 28, 32]:
                self._fonts[size] = ImageFont.truetype(FONT_PATH, size)
        except OSError:
            # Fallback to default font
            for size in [10, 12, 14, 16, 18, 20, 24, 28, 32]:
                self._fonts[size] = ImageFont.load_default()
    
    def get_font(self, size: int = 14) -> ImageFont:
        """Get font of specified size."""
        available = sorted(self._fonts.keys())
        closest = min(available, key=lambda x: abs(x - size))
        return self._fonts[closest]
    
    def set_brightness(self, brightness: int):
        """Set backlight brightness (0-100)."""
        self.brightness = max(0, min(100, brightness))
        if self._pwm:
            self._pwm.ChangeDutyCycle(self.brightness)
    
    def clear(self, color='black'):
        """Clear the framebuffer."""
        self._draw.rectangle([0, 0, self.width, self.height], fill=color)
    
    def refresh(self):
        """Push framebuffer to display."""
        # Convert to RGB565
        pixels = self._buffer.convert('RGB')
        data = []
        
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = pixels.getpixel((x, y))
                # RGB888 to RGB565
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                data.append(rgb565 >> 8)
                data.append(rgb565 & 0xFF)
        
        self._set_window(0, 0, self.width - 1, self.height - 1)
        self._data(bytes(data))
    
    # Drawing primitives
    
    def pixel(self, x: int, y: int, color='white'):
        """Draw a single pixel."""
        self._draw.point((x, y), fill=color)
    
    def line(self, x1: int, y1: int, x2: int, y2: int, color='white', width: int = 1):
        """Draw a line."""
        self._draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    
    def rect(self, x: int, y: int, w: int, h: int, color='white', fill=None, width: int = 1):
        """Draw a rectangle (outline or filled)."""
        if fill:
            self._draw.rectangle([x, y, x + w, y + h], fill=fill, outline=color, width=width)
        else:
            self._draw.rectangle([x, y, x + w, y + h], outline=color, width=width)
    
    def circle(self, cx: int, cy: int, r: int, color='white', fill=None, width: int = 1):
        """Draw a circle."""
        self._draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=color, width=width)
    
    def text(self, x: int, y: int, text: str, color='white', size: int = 14, anchor='lt'):
        """
        Draw text.
        
        Args:
            x, y: Position
            text: Text string
            color: Text color
            size: Font size
            anchor: Anchor point (lt=left-top, mm=middle-middle, etc.)
        """
        font = self.get_font(size)
        self._draw.text((x, y), text, fill=color, font=font, anchor=anchor)
    
    def text_size(self, text: str, size: int = 14) -> tuple:
        """Get text dimensions."""
        font = self.get_font(size)
        bbox = self._draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    def image(self, x: int, y: int, img: Image.Image):
        """Draw an image at position."""
        self._buffer.paste(img, (x, y))
    
    def blit(self, surface, x: int, y: int):
        """Blit a surface (PIL Image) to the framebuffer."""
        if surface.mode != 'RGB':
            surface = surface.convert('RGB')
        self._buffer.paste(surface, (x, y))
    
    # High-level UI elements
    
    def draw_cursor(self, x: int, y: int, size: int = 8, color='white'):
        """Draw cursor pointer at position."""
        points = [
            (x, y),
            (x, y + size),
            (x + size // 2, y + size * 3 // 4),
            (x + size, y + size // 2),
        ]
        self._draw.polygon(points, fill=color, outline='black')
    
    def draw_status_bar(self, time_str: str, wifi: bool, bt: bool, 
                        battery: int = None, notif_count: int = 0):
        """Draw status bar at top of screen."""
        bar_height = 20
        self.rect(0, 0, self.width, bar_height, fill='#222222')
        
        # Time (center)
        self.text(self.width // 2, 2, time_str, color='white', size=14, anchor='mt')
        
        # WiFi indicator (left)
        wifi_color = '#00ff00' if wifi else '#666666'
        self.text(5, 2, 'W', color=wifi_color, size=12)
        
        # Bluetooth indicator
        bt_color = '#0088ff' if bt else '#666666'
        self.text(20, 2, 'B', color=bt_color, size=12)
        
        # Notification indicator (after BT)
        if notif_count > 0:
            # Bell icon with count
            self.text(35, 2, '🔔', color='#ffcc00', size=10)
            if notif_count <= 9:
                self.text(48, 2, str(notif_count), color='#ffcc00', size=10)
            else:
                self.text(48, 2, '9+', color='#ffcc00', size=9)
        
        # Battery (right) - only show if battery is not None
        if battery is not None:
            batt_x = self.width - 35
            batt_color = '#00ff00' if battery > 20 else '#ff0000'
            self.rect(batt_x, 4, 25, 12, color='white')
            self.rect(batt_x + 25, 7, 3, 6, fill='white')
            fill_width = int(23 * battery / 100)
            if fill_width > 0:
                self.rect(batt_x + 1, 5, fill_width, 10, fill=batt_color)
    
    def draw_button(self, x: int, y: int, w: int, h: int, text: str, 
                    selected: bool = False, enabled: bool = True):
        """Draw a button."""
        if not enabled:
            bg = '#333333'
            fg = '#666666'
        elif selected:
            bg = '#0066cc'
            fg = 'white'
        else:
            bg = '#444444'
            fg = 'white'
        
        self.rect(x, y, w, h, fill=bg, color='#666666' if not selected else '#0088ff')
        self.text(x + w // 2, y + h // 2, text, color=fg, size=14, anchor='mm')
    
    def draw_progress_bar(self, x: int, y: int, w: int, h: int, 
                          progress: float, color='#0066cc'):
        """Draw a progress bar (0.0 to 1.0)."""
        self.rect(x, y, w, h, color='#666666')
        fill_width = int((w - 4) * max(0, min(1, progress)))
        if fill_width > 0:
            self.rect(x + 2, y + 2, fill_width, h - 4, fill=color)
    
    def draw_list_item(self, x: int, y: int, w: int, h: int, text: str,
                       selected: bool = False, icon: str = None):
        """Draw a list item."""
        if selected:
            self.rect(x, y, w, h, fill='#0066cc')
            fg = 'white'
        else:
            fg = 'white'
        
        text_x = x + 10
        if icon:
            self.text(x + 5, y + h // 2, icon, color=fg, size=16, anchor='lm')
            text_x = x + 30
        
        # Truncate text if too long
        max_chars = (w - text_x - 10) // 8
        display_text = text[:max_chars] + '...' if len(text) > max_chars else text
        self.text(text_x, y + h // 2, display_text, color=fg, size=14, anchor='lm')
    
    def shutdown(self):
        """Clean up resources."""
        if self._pwm:
            self._pwm.stop()
        self._spi.close()
        gpio.cleanup([self.gpio_dc, self.gpio_rst, self.gpio_bl])
