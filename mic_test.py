import speech_recognition as sr

recognizer = sr.Recognizer()

print("JARVIS: Microphone test starting!")

try:
    with sr.Microphone() as source:
        print("JARVIS: Adjusting microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        print("JARVIS: Speak something now!")
        audio = recognizer.listen(source, timeout=8, phrase_time_limit=6)

    print("JARVIS: Processing your voice...")

    text = recognizer.recognize_google(audio)
    print("You said:", text)

except sr.WaitTimeoutError:
    print("JARVIS: I didn't hear anything.")
except sr.UnknownValueError:
    print("JARVIS: I couldn't understand that.")
except sr.RequestError as e:
    print("JARVIS: Internet recognition error:", e)
except Exception as e:
    print("JARVIS: Error:", e)