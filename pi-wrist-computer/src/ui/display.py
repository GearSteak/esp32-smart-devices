"""
ST7789V 240x320 LCD Display Driver

Uses luma.lcd for hardware abstraction.
Provides drawing primitives and image display.
"""

from luma.lcd.device import st7789
from luma.core.interface.serial import spi
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import os

# Default font path
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class Display:
    """ST7789V LCD Display wrapper with drawing utilities."""
    
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
        
        # GPIO for backlight
        self.gpio_bl = config.get('gpio_bl', 24)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_bl, GPIO.OUT)
        self._pwm = GPIO.PWM(self.gpio_bl, 1000)
        self._pwm.start(self.brightness)
        
        # Initialize SPI and device
        serial = spi(
            port=config.get('spi_port', 0),
            device=config.get('spi_device', 0),
            gpio_DC=config.get('gpio_dc', 25),
            gpio_RST=config.get('gpio_rst', 27),
            bus_speed_hz=32000000
        )
        
        self.device = st7789(
            serial,
            width=self.width,
            height=self.height,
            rotate=self.rotation,
            bgr=True
        )
        
        # Create framebuffer
        self._buffer = Image.new('RGB', (self.width, self.height), 'black')
        self._draw = ImageDraw.Draw(self._buffer)
        
        # Load fonts
        self._fonts = {}
        self._load_fonts()
    
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
        # Find closest available size
        available = sorted(self._fonts.keys())
        closest = min(available, key=lambda x: abs(x - size))
        return self._fonts[closest]
    
    def set_brightness(self, brightness: int):
        """Set backlight brightness (0-100)."""
        self.brightness = max(0, min(100, brightness))
        self._pwm.ChangeDutyCycle(self.brightness)
    
    def clear(self, color='black'):
        """Clear the framebuffer."""
        self._draw.rectangle([0, 0, self.width, self.height], fill=color)
    
    def refresh(self):
        """Push framebuffer to display."""
        self.device.display(self._buffer)
    
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
    
    def draw_status_bar(self, time_str: str, wifi: bool, bt: bool, battery: int):
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
        
        # Battery (right)
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
        self._pwm.stop()
        GPIO.cleanup(self.gpio_bl)
        self.device.cleanup()

