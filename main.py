import threading
import datetime
import json
import urllib.request
import speech_recognition as sr
import pyttsx3

recognizer = sr.Recognizer()
conversation = []

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b"

def speak(text):
    print("\nJARVIS:", text, flush=True)

    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.setProperty("volume", 1.0)

    def interrupt_callback(rec, audio):
        try:
            heard = rec.recognize_google(audio).lower().strip()

            if heard in ["stop", "stop speaking", "be quiet", "quiet"]:
                print("\nJARVIS: Okay, stopping!")
                engine.stop()

        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            pass

    # IMPORTANT: Do not use 'with' here!
    microphone = sr.Microphone()

    stop_listening = recognizer.listen_in_background(
        microphone,
        interrupt_callback,
        phrase_time_limit=2
    )

    try:
        engine.say(text)
        engine.runAndWait()

    finally:
        stop_listening(wait_for_stop=True)
        engine.stop()

def listen():
    try:
        with sr.Microphone() as source:
            print("\nJARVIS: Listening...")
            audio = recognizer.listen(
                source, timeout=8, phrase_time_limit=10
            )
        text = recognizer.recognize_google(audio)
        print("You:", text)
        return text.strip()

    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        speak("Sorry, I didn't understand.")
        return ""
    except sr.RequestError:
        speak("Speech recognition needs an internet connection.")
        return ""

def ask_ai(question):
    global conversation

    conversation.append({
        "role": "user",
        "content": question
    })

    messages = [
        {
            "role": "system",
            "content": (
                "You are JARVIS, a friendly and intelligent personal "
                "assistant. Give helpful, clear and concise answers. "
                "Do not claim to perform actions you have not performed."
            )
        }
    ] + conversation[-10:]

    data = {
        "model": MODEL,
        "messages": messages,
        "stream": False
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        answer = result["message"]["content"].strip()

        conversation.append({
            "role": "assistant",
            "content": answer
        })

        return answer

    except Exception as error:
        return "I couldn't connect to my AI brain. " + str(error)

def run_jarvis():
    speak("JARVIS is online.")
    speak("Say Hey JARVIS whenever you need me.")

    while True:
        heard = listen()

        if not heard:
            continue

        command = heard.lower().strip()

        # Wait for the wake phrase
        if "hey jarvis" not in command:
            continue

        # Remove the wake phrase
        command = command.replace("hey jarvis", "", 1).strip(" ,.!?")

        speak("Yes? I'm listening.")

        # If no command was included with the wake phrase,
        # listen for the next sentence.
        if not command:
            command = listen()

        if not command:
            continue

        if command.lower() in [
            "exit", "quit", "goodbye", "shutdown"
        ]:
            speak("Goodbye! JARVIS shutting down.")
            break

        if "clear conversation" in command.lower():
            conversation.clear()
            speak("Conversation cleared.")
            continue

        answer = ask_ai(command)
        speak(answer)

if __name__ == "__main__":
    run_jarvis()