import time
import board
from adafruit_seesaw import seesaw, rotaryio
import busio
import adafruit_ssd1306
import qwiic_proximity
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import os
import subprocess

# --- I2C ---
i2c = board.I2C()

# --- Rotary encoder ---
seesaw_device = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw_device)
last_encoder_position = encoder.position

# --- OLED ---
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# --- Distance sensor ---
sensor = qwiic_proximity.QwiicProximity()
if not sensor.connected:
    print("VCNL4040 not connected")
    exit(1)
sensor.begin()

# --- Font ---
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
if os.path.exists(font_path):
    font = ImageFont.truetype(font_path, 12)
else:
    font = ImageFont.load_default()

# --- State ---
last_taken = None
next_time = None
object_present = False
display_mode = 0  # 0 = last_taken, 1 = next_time, 2 = medication name
reminder_spoken = False  # prevents repeated speech

def speak_message(message):
    """Speak a message using espeak."""
    try:
        subprocess.run(["espeak", message], check=True)
    except Exception as e:
        print("Speech error:", e)

while True:
    try:
        now = datetime.now()

        # --- Rotary encoder ---
        current_position = -encoder.position
        if current_position != last_encoder_position:
            display_mode = (display_mode + 1) % 3  # 3 screens
            last_encoder_position = current_position

        # --- Distance sensor ---
        distance_cm = sensor.get_proximity() / 10.0
        currently_present = distance_cm < 10

        # --- Handle medication taken event ---
        if currently_present and not object_present:
            last_taken = now
            next_time = last_taken + timedelta(minutes=1)
            reminder_spoken = False  # reset reminder
            object_present = True
        elif not currently_present:
            object_present = False

        # --- Speak reminder if time reached ---
        if next_time and not reminder_spoken and now >= next_time:
            speak_message("Please take your medication right now. Please take your medication right now. Please take your medication right now.")
            reminder_spoken = True

        # --- Draw OLED ---
        image = Image.new("1", (oled.width, oled.height))
        draw = ImageDraw.Draw(image)

        if display_mode == 0:
            draw.text((0, 0), "Last taken:", font=font, fill=255)
            draw.text((0, 14), last_taken.strftime("%H:%M:%S") if last_taken else "None", font=font, fill=255)

        elif display_mode == 1:
            draw.text((0, 0), "Next time:", font=font, fill=255)
            draw.text((0, 14), next_time.strftime("%H:%M:%S") if next_time else "None", font=font, fill=255)

        else:
            draw.text((0, 0), "Medication:", font=font, fill=255)
            draw.text((0, 14), "Tylenol", font=font, fill=255)

        oled.image(image)
        oled.show()

    except Exception as e:
        print("Error:", e)
        oled.fill(0)
        oled.show()

    time.sleep(0.2)
