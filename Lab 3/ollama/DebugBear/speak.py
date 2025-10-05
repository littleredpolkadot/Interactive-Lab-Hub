#!/usr/bin/env python3
import os
import queue
import sys
import time
import json
import threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from gtts import gTTS
import simpleaudio as sa
import qwiic_button

# ----------------
# Setup
# ----------------
model_path = "/home/pi/Interactive-Lab-Hub/Lab 3/ollama/DebugBear/vosk-models/vosk-model-small-en-us-0.15"
model = Model(model_path)

audio_queue = queue.Queue()
interaction_active = False
awaiting_problem_trigger = False
awaiting_solution_feedback = False

# ----------------
# Speak
# ----------------
def speak(text):
    tts = gTTS(text=text, lang="en")
    tts.save("/tmp/temp.mp3")
    os.system("ffmpeg -y -i /tmp/temp.mp3 /tmp/temp.wav >/dev/null 2>&1")
    wave_obj = sa.WaveObject.from_wave_file("/tmp/temp.wav")
    play_obj = wave_obj.play()
    play_obj.wait_done()

# ----------------
# Audio callback
# ----------------
def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

# ----------------
# Process audio (called after button release)
# ----------------
def process_audio():
    global interaction_active, awaiting_problem_trigger, awaiting_solution_feedback

    print("Processing recording...")
    combined_audio = b""
    while not audio_queue.empty():
        combined_audio += audio_queue.get()

    if not combined_audio:
        print("No audio captured")
        return

    rec = KaldiRecognizer(model, 16000)
    rec.AcceptWaveform(combined_audio)
    result_json = rec.Result()
    result = json.loads(result_json)
    text = result.get("text", "").lower()
    print("User said:", text)

    response = ""  # always define a response

    # --- Interaction logic ---
    if not interaction_active:
        if any(word in text for word in ["hi", "hello"]):
            response = "Hi, what do you need help with?"
            interaction_active = True
            awaiting_problem_trigger = True
        else:
            response = "I only respond to 'hi' or 'hello'."
    elif awaiting_problem_trigger:
        if any(word in text for word in ["problem", "issue", "coding", "bug"]):
            response = "Alright, let's walk through your problem and solution."
            awaiting_problem_trigger = False
            awaiting_solution_feedback = True
        else:
            response = "I am not equipped for that, sorry."
            interaction_active = False
    elif awaiting_solution_feedback:
        if any(word in text for word in ["figured", "got it", "understand now"]):
            response = "I am glad that you figured it out!"
            interaction_active = False
            awaiting_solution_feedback = False
        elif any(word in text for word in ["no", "nah"]):
            response = "I am sorry you couldn't figure it out."
            interaction_active = False
            awaiting_solution_feedback = False
        elif any(word in text for word in ["yes", "again"]):
            response = "That's great! Let's try again, be more detailed and walk through every step."

    # speak immediately after processing
    if response:
        speak(response)

# ----------------
# Button handling
# ----------------
recording = False
last_state = False

def run_buttons():
    global recording
    button_record = qwiic_button.QwiicButton(address=0x6F)
    button_end = qwiic_button.QwiicButton(address=0x5B)

    if not button_record.begin():
        print("Button 1 not connected.", file=sys.stderr)
    if not button_end.begin():
        print("Button 2 not connected.", file=sys.stderr)

    print("Buttons ready! Button 1 = Start/Stop, Button 2 = Stop interaction")

    while True:
        pressed = button_record.is_button_pressed()

        # Toggle recording on single press
        if pressed and not last_state:
            if not recording:
                print("Button 1 pressed: Recording started")
                button_record.LED_on(True)
                recording = True
            else:
                print("Button 1 pressed: Recording stopped")
                button_record.LED_on(False)
                recording = False
                process_audio()  # process immediately

        last_state = pressed

        if button_end.is_button_pressed():
            print("Button 2 pressed: Stopping interaction")
            global interaction_active, awaiting_problem_trigger, awaiting_solution_feedback
            interaction_active = False
            awaiting_problem_trigger = False
            awaiting_solution_feedback = False
            while button_end.is_button_pressed():
                time.sleep(0.02)

        time.sleep(0.05)

# ----------------
# Main
# ----------------
with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                       channels=1, callback=callback):
    threading.Thread(target=run_buttons, daemon=True).start()
    print("DebugBear listening. Press Button 1 to start/stop recording.")

    while True:
        time.sleep(0.1)
