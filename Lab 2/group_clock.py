# rpi5_minipitft_st7789.py
# Works on Raspberry Pi 5 with Adafruit Blinka backend (lgpio) and SPI enabled.
# Wiring change: connect the display's CS to GPIO5 (pin 29), not CE0.

import time
import digitalio
import board
from PIL import Image, ImageSequence

from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789

# ---------------------------
# SPI + Display configuration
# ---------------------------
# Use a FREE GPIO for CS to avoid conflicts with the SPI driver owning CE0/CE1.
cs_pin = digitalio.DigitalInOut(board.D5) # GPIO5  (PIN 29)  <-- wire display CS here
dc_pin = digitalio.DigitalInOut(board.D25)  # GPIO25 (PIN 22)
reset_pin = None

# Safer baudrate for stability; you can try 64_000_000 if your wiring is short/clean.
BAUDRATE = 64000000

# Create SPI object on SPI0 (spidev0.* must exist; enable SPI in raspi-config).
spi = board.SPI()

WIDTH = 135
HEIGHT = 240

# For Adafruit mini PiTFT 1.14" (240x135) ST7789 use width=135, height=240, x/y offsets below.
# If you actually have a 240x240 panel, set width=240, height=240 and x_offset=y_offset=0.
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=WIDTH,
    height=HEIGHT,
    x_offset=53,
    y_offset=40,
    rotation=90
)

screen_width = disp.height
screen_height = disp.width

# ---------------------------
# Backlight + Buttons
# ---------------------------
backlight = digitalio.DigitalInOut(board.D22) # GPIO22 (PIN 15)
backlight.switch_to_output(value=True)

buttonA = digitalio.DigitalInOut(board.D23)    # GPIO23 (PIN 16)
buttonB = digitalio.DigitalInOut(board.D24)    # GPIO24 (PIN 18)
# Use internal pull-ups; buttons then read LOW when pressed.
buttonA.switch_to_input(pull=digitalio.Pull.UP)
buttonB.switch_to_input(pull=digitalio.Pull.UP)

# ---------------------------
# Load clock digit images
# ---------------------------
image_files = [
    "images/group_clock_zero.jpg",
    "images/group_clock_one.jpg",
    "images/group_clock_two.jpg",
    "images/group_clock_three.jpg",
    "images/group_clock_four.jpg",
    "images/group_clock_five.jpg",
    "images/group_clock_six.jpg",
    "images/group_clock_seven.jpg",
    "images/group_clock_eight.jpg",
    "images/group_clock_nine.jpg"
]

images = [Image.open(f) for f in image_files]

# ---------------------------
# Load GIFs
# ---------------------------
stick_gif = Image.open("images/run-chase.gif")
stick_frames = [frame.convert("RGB").resize((40, 40), Image.BICUBIC)
                for frame in ImageSequence.Iterator(stick_gif)]

ball_gif = Image.open("images/ball-bounce-crop.gif")
ball_frames = [frame.convert("RGB").resize((25, 70), Image.BICUBIC).rotate(180)
               for frame in ImageSequence.Iterator(ball_gif)]

pow_gif = Image.open("images/pow-warped.gif")
pow_frames = [frame.convert("RGBA").resize((120, 120), Image.BICUBIC)
              for frame in ImageSequence.Iterator(pow_gif)]

celebration_gif = Image.open("images/celebration.gif")
celebration_frames = [frame.convert("RGBA").resize((screen_width, screen_height), Image.BICUBIC)
              for frame in ImageSequence.Iterator(celebration_gif)]

death_gif = Image.open("images/death.gif")
death_frames = [frame.convert("RGBA").resize((screen_width, screen_height), Image.BICUBIC)
              for frame in ImageSequence.Iterator(death_gif)]
# ---------------------------
# Function to draw the clock
# ---------------------------
def show_clock():
    timestring = time.strftime("%H%M")
    num_digits = len(timestring)
    img_width = screen_width // num_digits
    img_height = screen_height
    screen = Image.new("RGB", (screen_width, screen_height), (255, 255, 255))
    for idx, digit in enumerate(timestring):
        img = images[int(digit)].resize((img_width, img_height), Image.BICUBIC)
        screen.paste(img, (idx * img_width, 0))
    disp.image(screen)

# ---------------------------
# Main loop
# ---------------------------
last_time = ""


#welcome image  (only at start)
while True:
    img = Image.open("images/welcome_screen.png").convert("RGBA").resize((screen_width, screen_height))
    screen = Image.new("RGBA", (screen_width, screen_height), (255, 255, 255, 255))
    screen.paste(img, (0, 0), img)  
    disp.image(screen.convert("RGB")) 
    print("A:", buttonA.value, "B:", buttonB.value)
    if (not buttonA.value) or (not buttonB.value):
        break

#clock (b) & game (a)
while True:
    a_pressed = not buttonA.value
    b_pressed = not buttonB.value

    timestring = time.strftime("%H%M")
    if timestring != last_time or b_pressed:
        last_time = timestring
        show_clock()


    if a_pressed: #start game
        stick_index = 0
        ball_index = 0
        pow_index =0
        celebration_index = 0
        death_index = 0
        ball_x = 0     
        ball_y = 50      
        b_pressed = False

        count = 4
        stick_size = 40
        spacing = 0

        #starts the stick figure & ball animation (ends when hitting the person or if 4 people then stops before hitting)
        while not b_pressed and ball_x < screen_width - (((count+2)//2)*(stick_size+spacing)) :  
            screen = Image.new("RGB", (screen_width, screen_height), (255, 255, 255))

            count = 4
            
            timestring = time.strftime("%H%M")
            for i in timestring:
                if i == "0" or i== "5" or i=="6" or i=="8":
                    count+=1
            for i in range(count):
                x_pos = screen_width - 15 - stick_size*((i//2) + 1)
                y_pos = screen_height - ((i%2+1) * (stick_size + spacing))
                #print(i,"'s x: ", x_pos)
                #print(i,"'s y: ", y_pos)
                screen.paste(stick_frames[stick_index % len(stick_frames)], (x_pos, y_pos))
            
            stick_index += 1

            screen.paste(ball_frames[ball_index % len(ball_frames)],
                        (ball_x, ball_y))
            ball_index += 1

            ball_x += 1  

            disp.image(screen)
            time.sleep(0.05)

            b_pressed = not buttonB.value
        ##goes into ending cards
        while not b_pressed:
            if (count != 4):#winning animation sequence
                for _ in range(len(pow_frames)): 
                    screen = Image.new("RGB", (screen_width, screen_height), (0, 0, 0))
                    screen.paste(pow_frames[pow_index % len(pow_frames)], (50, 10))
                    pow_index += 1
                    disp.image(screen)
                    time.sleep(0.08)
                
                for _ in range(len(death_frames)): 
                    screen = Image.new("RGBA", (screen_width, screen_height), (255, 255, 255))
                    screen.paste(death_frames[death_index % len(death_frames)], (0, 0))
                    death_index += 1
                    disp.image(screen)
                    time.sleep(0.08)
                break
            else:#losing animation sequence
                for _ in range(len(celebration_frames) * 5):  
                    screen = Image.new("RGB", (screen_width, screen_height), (0, 0, 0))
                    screen.paste(celebration_frames[celebration_index % len(celebration_frames)], (0, 0))
                    celebration_index += 1
                    disp.image(screen)
                    time.sleep(0.08)
                break


    
        # Restore clock after animation ends 
        show_clock()
    

    time.sleep(0.05)
