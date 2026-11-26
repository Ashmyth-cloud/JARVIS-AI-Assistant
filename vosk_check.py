from vosk import Model
import os

MODEL_PATH = r"C:\JARVIS\offline_models"

print("Checking model folder...")

if os.path.exists(MODEL_PATH):
    print("Folder found!")

    try:
        model = Model(MODEL_PATH)
        print("SUCCESS! VOSK MODEL LOADED!")
    except Exception as e:
        print("MODEL ERROR:", e)
else:
    print("MODEL FOLDER NOT FOUND!")