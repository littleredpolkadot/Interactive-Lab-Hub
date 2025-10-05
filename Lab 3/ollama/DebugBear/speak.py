#!/usr/bin/env python3
import os
import queue
import sys
import time
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from gtts import gTTS
import playsound
import qwiic_button
import threading

# ----------------
# Setup Vosk & Bear
# ----------------
model_path = "/home/pi/Interactive-Lab-Hub/Lab 3/ollama/DebugBear/vosk-models/vosk-model-small-en-us-0.15"
model = Model(model_path)

audio_queue = queue.Queue()
interaction_active = False  # tracks if bear session is active
recording = False           # tracks if user is recording
buffer_queue = queue.Queue()  # temporary buffer for recording

def speak(text):
    tts = gTTS(text=text, lang="en")
    filename = "/tmp/temp.mp3"
    tts.save(filename)
    playsound.playsound(filename)

def callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    if recording:
        buffer_queue.put(bytes(indata))  # only store audio when recording

# ----------------
# Bear Dialogue Logic
# ----------------
def bear_dialogue_from_buffer():
    global interaction_active
    interaction_active = True
    # Combine all buffered audio into a single processing
    combined_audio = b""
    while not buffer_queue.empty():
        combined_audio += buffer_queue.get()
    
    # Feed combined audio to recognizer
    if rec.AcceptWaveform(combined_audio):
        result = json.loads(rec.Result())
        text = result.get("text", "").lower()
        print("User (button recorded):", text)
        # Process same as normal dialogue
        if "yes" in text or "again" in text:
            speak("That's great! Let's try again, be more detailed and walk through every step.")
        elif "no" in text or "stop" in text:
            speak("Stopping the interaction. I'll reset.")
            interaction_active = False
            return
        elif "figured" in text or "got it" in text:
            speak("That's great that you figured it out! I'm glad I could help!")
            interaction_active = False
            return

    # Start regular bear dialogue after processed message
    speak("Alright, let's walk things through. Why don't you tell me what's wrong?")
    while interaction_active:
        data = audio_queue.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()
            print("User:", text)
            if "yes" in text or "again" in text:
                speak("That's great! Let's try again, be more detailed and walk through every step.")
            elif "no" in text or "stop" in text:
                speak("Stopping the interaction. I'll reset.")
                interaction_active = False
            elif "figured" in text or "got it" in text:
                speak("That's great that you figured it out! I'm glad I could help!")
                interaction_active = False

# ----------------
# Qwiic Button Logic
# ----------------
def run_buttons():
    global recording, interaction_active
    button_record = qwiic_button.QwiicButton(address=0x6F)  # Start / Record
    button_end = qwiic_button.QwiicButton(address=0x5B)     # End / Reset

    if not button_record.begin():
        print("Button 1 (record) not connected.", file=sys.stderr)
    if not button_end.begin():
        print("Button 2 (end/reset) not connected.", file=sys.stderr)

    print("Buttons ready! Button 1 = Record toggle, Button 2 = End/Reset")

    while True:
        # Toggle recording with Button 1
        if button_record.is_button_pressed():
            recording = not recording
            button_record.LED_on(recording)
            print(f"Button 1 pressed: Recording {'started' if recording else 'stopped'}")
            
            # If just stopped recording, process the buffer
            if not recording:
                threading.Thread(target=bear_dialogue_from_buffer, daemon=True).start()
            
            while button_record.is_button_pressed():
                time.sleep(0.02)

        # Stop any active interaction with Button 2
        if button_end.is_button_pressed() and interaction_active:
            print("Button 2 pressed: Stopping bear interaction")
            interaction_active = False
            button_record.LED_on(False)  # ensure LED off
            recording = False
            while button_end.is_button_pressed():
                time.sleep(0.02)
        
        time.sleep(0.05)

# ----------------
# Start Vosk and Buttons
# ----------------
with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                       channels=1, callback=callback):
    rec = KaldiRecognizer(model, 16000)
    last_empty = 0
    print("DebugBear is listening... Press the record button to start interaction.")

    # Run button logic in a separate thread
    threading.Thread(target=run_buttons, daemon=True).start()

    while True:
        data = audio_queue.get()
        audio_queue.put(data)  # store in main queue for ongoing dialogue
        time.sleep(0.01)
