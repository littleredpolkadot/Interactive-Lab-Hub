import time
import board
import busio
import adafruit_ssd1306
import qwiic_proximity

# --- Initialize I2C ---
i2c = busio.I2C(board.SCL, board.SDA)

# --- Initialize OLED ---
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# --- Initialize SparkFun VCNL4040 ---
distance_sensor = qwiic_proximity.QwiicProximity()

if not distance_sensor.connected:
    print("VCNL4040 not connected. Check wiring.")
    exit(1)

distance_sensor.begin()

while True:
    try:
        distance_mm = distance_sensor.get_proximity()  
        distance_cm = distance_mm / 10.0  
        object_near = distance_cm < 10
        oled.fill(1 if object_near else 0)
        oled.show()

    except Exception as e:
        print("Distance read failed:", e)
        oled.fill(0)
        oled.show()

    time.sleep(0.05)
