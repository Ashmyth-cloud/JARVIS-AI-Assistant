import tkinter as tk
from tkinter import scrolledtext
import webbrowser
import subprocess
import json
import time
import math
import threading
import urllib.request
import datetime
import pyttsx3
import pyaudio
from vosk import Model, KaldiRecognizer

# Optional system monitor. JARVIS still works without psutil.
try:
    import psutil
except ImportError:
    psutil = None


# =========================================================
# CONFIGURATION
# =========================================================

MODEL = "qwen3:4b"
URL = "http://localhost:11434/api/chat"
MODEL_PATH = r"C:\JARVIS\offline_models"

conversation = []
wake_word = "jarvis"
wake_enabled = True
wake_listening = False
conversation_mode = False
jarvis_sleeping = False
manual_listening = False
busy = False

wake_thread = None
wake_stop = threading.Event()
speech_stop = threading.Event()
stop_monitor_stop = threading.Event()
speech_thread = None

jarvis_state = "ONLINE"
vosk_model = Model(MODEL_PATH)


# =========================================================
# THEME
# =========================================================

BG = "#05080f"
PANEL = "#0a1220"
PANEL_ALT = "#0e1b2b"
PANEL_SOFT = "#101f30"
CYAN = "#00d9ff"
CYAN_DARK = "#087c9a"
GREEN = "#00f5a0"
AMBER = "#ffb547"
RED = "#ff5364"
TEXT = "#e8f7ff"
MUTED = "#7893a8"
BORDER = "#183247"

STATE_COLORS = {
    "ONLINE": CYAN,
    "OFFLINE": RED,
    "LISTENING": GREEN,
    "THINKING": AMBER,
    "SPEAKING": GREEN,
    "ERROR": RED
}


# =========================================================
# AI BRAIN
# =========================================================

def ask_ai(question):
    conversation.append({"role": "user", "content": question})

    messages = [{
        "role": "system",
        "content": (
            "You are JARVIS, a friendly and intelligent AI assistant. "
            "Answer clearly and helpfully. Keep answers reasonably concise."
        )
    }] + conversation[-4:]

    data = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "num_predict": 150,
            "temperature": 0.5,
            "num_ctx": 2048,
            "num_thread": 4
        }
    }

    request = urllib.request.Request(
        URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result["message"]["content"].strip()
    conversation.append({"role": "assistant", "content": answer})
    return answer


# =========================================================
# UI HELPERS
# =========================================================

root = tk.Tk()
root.title("J.A.R.V.I.S | COMMAND CENTER")
root.geometry("1180x700")
root.minsize(900, 600)
root.configure(bg=BG)

def make_label(parent, text, size=10, color=TEXT, bold=False, bg=PANEL):
    return tk.Label(
        parent,
        text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        fg=color,
        bg=bg
    )


def make_button(parent, text, command, bg=PANEL_ALT, fg=TEXT):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=CYAN,
        activeforeground=BG,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        bd=0,
        padx=14,
        pady=12,
        cursor="hand2",
        highlightthickness=1,
        highlightbackground=BORDER
    )
    button.bind("<Enter>", lambda _e: button.config(highlightbackground=CYAN))
    button.bind("<Leave>", lambda _e: button.config(highlightbackground=BORDER))
    return button


def ui_call(callback, *args):
    """Safely schedule UI work from a background thread."""
    try:
        if root.winfo_exists():
            root.after(0, callback, *args)
    except tk.TclError:
        pass


def update_status(message, color=GREEN):
    status_label.config(text="● " + message, fg=color)


def set_jarvis_state(state):
    global jarvis_state
    jarvis_state = state.upper()

    def update():
        if root.winfo_exists():
            color = STATE_COLORS.get(jarvis_state, CYAN)
            core_status.config(text=f"J.A.R.V.I.S  //  {jarvis_state}", fg=color)
            state_dot.config(fg=color)
            state_text.config(text=jarvis_state, fg=color)

    ui_call(update)


def add_message(sender, message):
    chat.config(state="normal")
    stamp = datetime.datetime.now().strftime("%I:%M %p")

    if sender == "YOU":
        chat.insert(tk.END, f"\nYOU   ·   {stamp}\n", "user")
    else:
        chat.insert(tk.END, f"\nJARVIS   ·   {stamp}\n", "jarvis")

    chat.insert(tk.END, message + "\n", "message")
    chat.config(state="disabled")
    chat.see(tk.END)


# =========================================================
# APP / WEBSITE COMMANDS
# =========================================================

def open_app_or_website(command):
    command = command.lower().strip()

    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "chatgpt": "https://chatgpt.com",
        "instagram": "https://www.instagram.com",
        "facebook": "https://www.facebook.com",
        "github": "https://github.com",
        "spotify web": "https://open.spotify.com"
    }

    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "chrome": "chrome.exe",
        "vs code": "code",
        "vscode": "code"
    }

    for name, url in websites.items():
        if command == f"open {name}":
            webbrowser.open(url)
            return f"Opening {name}, boss."

    for name, app in apps.items():
        if command == f"open {name}":
            try:
                subprocess.Popen(app, shell=False)
                return f"Opening {name}, boss."
            except Exception as error:
                return f"I couldn't open {name}: {error}"

    return None


# =========================================================
# CHAT + AI WORKER
# =========================================================

def send_message(event=None):
    global busy

    message = entry.get().strip()
    if not message or busy:
        return

    entry.delete(0, tk.END)
    add_message("YOU", message)

    result = open_app_or_website(message)
    if result:
        add_message("JARVIS", result)
        speak_answer(result)
        return

    busy = True
    send_button.config(state="disabled", text="WORKING...")
    update_status("JARVIS IS THINKING", AMBER)
    set_jarvis_state("THINKING")

    threading.Thread(target=ai_worker, args=(message,), daemon=True).start()


def ai_worker(message):
    global busy
    try:
        answer = ask_ai(message)
        ui_call(display_answer, answer)
    except Exception as error:
        error_message = str(error)

        def show_error():
            add_message("JARVIS", "Connection error: " + error_message)
            update_status("CONNECTION ERROR", RED)
            set_jarvis_state("ERROR")

        ui_call(show_error)
    finally:
        busy = False
        ui_call(lambda: send_button.config(state="normal", text="SEND  ➤"))


def display_answer(answer):
    add_message("JARVIS", answer)
    update_status("SYSTEM ONLINE", GREEN)
    speak_answer(answer)


def clear_chat():
    global conversation
    if busy:
        return

    conversation.clear()
    chat.config(state="normal")
    chat.delete("1.0", tk.END)
    chat.config(state="disabled")
    add_message("JARVIS", "Conversation cleared. All systems are ready.")


# =========================================================
# SPEECH OUTPUT + STOP-WORD MONITOR
# =========================================================

def start_stop_listener():
    stop_monitor_stop.clear()

    def stop_worker():
        audio_interface = None
        stream = None
        try:
            audio_interface = pyaudio.PyAudio()
            stream = audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=2000
            )
            recognizer = KaldiRecognizer(vosk_model, 16000)

            while not stop_monitor_stop.is_set():
                data = stream.read(2000, exception_on_overflow=False)

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    heard = result.get("text", "").lower()
                else:
                    result = json.loads(recognizer.PartialResult())
                    heard = result.get("partial", "").lower()

                if "stop" in heard.split():
                    speech_stop.set()
                    break

        except Exception as error:
            print("STOP listener error:", error)
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio_interface is not None:
                audio_interface.terminate()

    threading.Thread(target=stop_worker, daemon=True).start()


def speak_answer(text):
    global speech_thread

    speech_stop.clear()
    stop_monitor_stop.clear()
    start_stop_listener()

    set_jarvis_state("SPEAKING")
    update_status("JARVIS SPEAKING", GREEN)

    def voice_worker():
        engine = None
        loop_started = False
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.setProperty("volume", 1.0)
            engine.startLoop(False)
            loop_started = True
            engine.say(text)

            while engine.isBusy():
                if speech_stop.is_set():
                    engine.stop()
                    break
                engine.iterate()
                time.sleep(0.01)

        except Exception as error:
            print("Voice error:", error)
        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
                if loop_started:
                    try:
                        engine.endLoop()
                    except Exception:
                        pass

            stop_monitor_stop.set()
            if not jarvis_sleeping:
                ui_call(set_jarvis_state, "ONLINE")
                if conversation_mode:
                    ui_call_later(500, listen_for_command)
                else:
                    ui_call_later(1500, start_wake_listener)

    speech_thread = threading.Thread(target=voice_worker, daemon=True)
    speech_thread.start()


def ui_call_later(delay, callback):
    try:
        if root.winfo_exists():
            root.after(delay, callback)
    except tk.TclError:
        pass


# =========================================================
# MICROPHONE LISTENING
# =========================================================

def start_listening():
    global manual_listening

    if manual_listening or busy or jarvis_sleeping:
        return

    manual_listening = True
    wake_stop.set()
    speech_stop.clear()
    update_status("STARTING MICROPHONE", CYAN)
    set_jarvis_state("LISTENING")

    def listen_worker():
        global manual_listening
        audio_interface = None
        stream = None
        recognized_text = ""

        try:
            audio_interface = pyaudio.PyAudio()
            stream = audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            recognizer = KaldiRecognizer(vosk_model, 16000)
            ui_call(update_status, "LISTENING OFFLINE", GREEN)

            while not speech_stop.is_set():
                data = stream.read(2000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    recognized_text = result.get("text", "").strip()
                    if recognized_text:
                        break

        except Exception as error:
            print("Manual microphone error:", error)
            ui_call(update_status, "MICROPHONE ERROR", RED)
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio_interface is not None:
                audio_interface.terminate()

            manual_listening = False

            if recognized_text:
                def submit_voice():
                    entry.delete(0, tk.END)
                    entry.insert(0, recognized_text)
                    update_status("VOICE RECEIVED", GREEN)
                    send_message()
                ui_call(submit_voice)
            else:
                ui_call(update_status, "NO SPEECH DETECTED", CYAN)
                ui_call(set_jarvis_state, "ONLINE")

            if not jarvis_sleeping:
                ui_call_later(1200, start_wake_listener)

    def launch():
        threading.Thread(target=listen_worker, daemon=True).start()

    ui_call_later(350, launch)


# =========================================================
# WAKE WORD / SLEEP MODE
# =========================================================

def put_jarvis_to_sleep():
    global jarvis_sleeping, conversation_mode

    jarvis_sleeping = True
    conversation_mode = False
    wake_stop.set()
    speech_stop.set()
    stop_monitor_stop.set()

    update_status("SLEEP MODE · SAY WAKE UP", RED)
    set_jarvis_state("OFFLINE")
    ui_call_later(700, sleep_wake_listener)


def wake_jarvis():
    global jarvis_sleeping, conversation_mode
    jarvis_sleeping = False
    conversation_mode = True
    update_status("JARVIS WAKING UP", GREEN)
    set_jarvis_state("ONLINE")
    speak_answer("Welcome back boss! JARVIS is online. How can I assist you?")


def sleep_wake_listener():
    global wake_listening, wake_thread

    if not jarvis_sleeping or wake_listening or manual_listening:
        return

    wake_stop.clear()
    wake_listening = True

    def sleep_worker():
        global wake_listening
        audio_interface = None
        stream = None
        woke_up = False

        try:
            audio_interface = pyaudio.PyAudio()
            stream = audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            recognizer = KaldiRecognizer(vosk_model, 16000)
            ui_call(update_status, "SLEEP MODE · WAITING FOR WAKE UP", RED)

            while not wake_stop.is_set() and jarvis_sleeping:
                data = stream.read(2000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    heard = json.loads(recognizer.Result()).get("text", "").lower().strip()
                    print("Sleep listener heard:", heard)
                    if "wake" in heard.split():
                        woke_up = True
                        break
        except Exception as error:
            print("Sleep listener error:", error)
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio_interface is not None:
                audio_interface.terminate()

            wake_listening = False
            if woke_up and jarvis_sleeping and not wake_stop.is_set():
                ui_call(wake_jarvis)

    wake_thread = threading.Thread(target=sleep_worker, daemon=True)
    wake_thread.start()


def start_wake_listener():
    global wake_listening, wake_thread, conversation_mode

    if jarvis_sleeping or not wake_enabled or wake_listening or manual_listening or busy:
        return

    wake_stop.clear()
    wake_listening = True

    def wake_worker():
        global wake_listening, conversation_mode
        audio_interface = None
        stream = None
        wake_detected = False
        pending_action = None

        try:
            audio_interface = pyaudio.PyAudio()
            stream = audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            recognizer = KaldiRecognizer(vosk_model, 16000)
            ui_call(update_status, "WAITING FOR WAKE WORD · JARVIS", CYAN)

            while not wake_stop.is_set():
                data = stream.read(2000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    heard = json.loads(recognizer.Result()).get("text", "").lower().split()
                    if wake_word in heard:
                        wake_detected = True
                        break

            if wake_detected:
                conversation_mode = True
                pending_action = lambda: speak_answer(
                    "Hello boss! JARVIS is online. How can I assist you?"
                )

        except Exception as error:
            print("Wake listener error:", error)
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio_interface is not None:
                audio_interface.terminate()

            wake_listening = False
            if pending_action is not None and not wake_stop.is_set():
                ui_call_later(200, pending_action)
            elif not wake_stop.is_set() and not jarvis_sleeping:
                ui_call_later(1000, start_wake_listener)

    wake_thread = threading.Thread(target=wake_worker, daemon=True)
    wake_thread.start()


def listen_for_command():
    global wake_listening, wake_thread, conversation_mode

    if jarvis_sleeping or manual_listening or wake_listening or busy:
        return

    wake_stop.clear()
    wake_listening = True

    def command_worker():
        global wake_listening, conversation_mode
        audio_interface = None
        stream = None
        command = ""

        try:
            audio_interface = pyaudio.PyAudio()
            stream = audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            recognizer = KaldiRecognizer(vosk_model, 16000)
            ui_call(update_status, "LISTENING FOR YOUR COMMAND", GREEN)
            deadline = time.monotonic() + 12

            while not wake_stop.is_set() and time.monotonic() < deadline:
                data = stream.read(2000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    detected = json.loads(recognizer.Result()).get("text", "").strip().lower()
                    if detected:
                        command = detected
                        break

            if not command and not wake_stop.is_set():
                command = json.loads(recognizer.FinalResult()).get("text", "").strip().lower()

        except Exception as error:
            print("Command listening error:", error)
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio_interface is not None:
                audio_interface.terminate()

            wake_listening = False

            if command and not wake_stop.is_set():
                if "go to sleep" in command or command == "sleep":
                    ui_call(put_jarvis_to_sleep)
                elif command in ("goodbye", "good bye", "bye", "goodbye jarvis", "bye jarvis"):
                    conversation_mode = False
                    ui_call_later(200, lambda: speak_answer(
                        "Goodbye, boss! I'll be waiting for your call."
                    ))
                else:
                    def submit_command(text=command):
                        entry.delete(0, tk.END)
                        entry.insert(0, text)
                        send_message()
                    ui_call_later(200, submit_command)
            elif not wake_stop.is_set() and not jarvis_sleeping:
                conversation_mode = False
                ui_call_later(500, start_wake_listener)

    wake_thread = threading.Thread(target=command_worker, daemon=True)
    wake_thread.start()


# =========================================================
# HEADER
# =========================================================

header = tk.Frame(root, bg=PANEL, height=76)
header.pack(fill="x")
header.pack_propagate(False)

header_left = tk.Frame(header, bg=PANEL)
header_left.pack(side="left", padx=26, fill="y")

make_label(header_left, "J.A.R.V.I.S", 23, CYAN, True).pack(side="left", pady=18)
make_label(header_left, "//  LOCAL AI COMMAND CENTER", 9, MUTED, True).pack(side="left", padx=12, pady=27)

header_right = tk.Frame(header, bg=PANEL)
header_right.pack(side="right", padx=25, fill="y")

clock_label = make_label(header_right, "", 10, TEXT, True)
clock_label.pack(side="right", padx=(18, 0), pady=27)

status_label = make_label(header_right, "● SYSTEM ONLINE", 9, GREEN, True)
status_label.pack(side="right", pady=27)


def update_clock():
    if not root.winfo_exists():
        return
    clock_label.config(text=datetime.datetime.now().strftime("%d %b %Y   |   %I:%M:%S %p"))
    root.after(1000, update_clock)


update_clock()
tk.Frame(root, bg=CYAN, height=2).pack(fill="x")


# =========================================================
# MAIN LAYOUT
# =========================================================

content = tk.Frame(root, bg=BG)
content.pack(fill="both", expand=True, padx=18, pady=18)

sidebar = tk.Frame(content, bg=PANEL, width=238, highlightthickness=1, highlightbackground=BORDER)
sidebar.pack(side="left", fill="y", padx=(0, 16))
sidebar.pack_propagate(False)

make_label(sidebar, "COMMAND DECK", 9, CYAN, True).pack(anchor="w", padx=19, pady=(22, 14))

# Engine card
engine_card = tk.Frame(sidebar, bg=PANEL_ALT, padx=14, pady=14, highlightthickness=1, highlightbackground=BORDER)
engine_card.pack(fill="x", padx=12, pady=5)
make_label(engine_card, "AI ENGINE", 8, MUTED, True, PANEL_ALT).pack(anchor="w")
make_label(engine_card, "QWEN3  /  4B", 14, GREEN, True, PANEL_ALT).pack(anchor="w", pady=(8, 3))
make_label(engine_card, "OLLAMA LOCAL INFERENCE", 8, MUTED, False, PANEL_ALT).pack(anchor="w")

# Voice card
voice_card = tk.Frame(sidebar, bg=PANEL_ALT, padx=14, pady=14, highlightthickness=1, highlightbackground=BORDER)
voice_card.pack(fill="x", padx=12, pady=9)
make_label(voice_card, "VOICE SYSTEM", 8, MUTED, True, PANEL_ALT).pack(anchor="w")
make_label(voice_card, "VOSK OFFLINE", 12, CYAN, True, PANEL_ALT).pack(anchor="w", pady=(8, 3))
make_label(voice_card, "PYTTSX3  /  SPEECH", 8, TEXT, False, PANEL_ALT).pack(anchor="w")

make_label(sidebar, "QUICK CONTROLS", 8, MUTED, True).pack(anchor="w", padx=19, pady=(22, 10))

make_button(sidebar, "◉   ACTIVATE MIC", start_listening, CYAN, BG).pack(fill="x", padx=12, pady=5)
make_button(sidebar, "■   STOP SPEECH", speech_stop.set, "#47212b", "#ff9aa5").pack(fill="x", padx=12, pady=5)
make_button(sidebar, "⌫   CLEAR CHAT", clear_chat, PANEL_ALT, TEXT).pack(fill="x", padx=12, pady=5)

# System status card
monitor_card = tk.Frame(sidebar, bg=PANEL_ALT, padx=14, pady=13, highlightthickness=1, highlightbackground=BORDER)
monitor_card.pack(fill="x", padx=12, pady=(20, 8))
make_label(monitor_card, "SYSTEM TELEMETRY", 8, CYAN, True, PANEL_ALT).pack(anchor="w")
cpu_value = make_label(monitor_card, "CPU       --", 9, TEXT, True, PANEL_ALT)
cpu_value.pack(anchor="w", pady=(10, 4))
ram_value = make_label(monitor_card, "RAM       --", 9, TEXT, True, PANEL_ALT)
ram_value.pack(anchor="w", pady=4)
gpu_value = make_label(monitor_card, "NVIDIA  --", 9, TEXT, True, PANEL_ALT)
gpu_value.pack(anchor="w", pady=4)

sidebar_bottom = tk.Frame(sidebar, bg=PANEL)
sidebar_bottom.pack(side="bottom", fill="x", padx=17, pady=18)
make_label(sidebar_bottom, "J.A.R.V.I.S  //  BUILD 2.1", 8, CYAN, True).pack(anchor="w")
make_label(sidebar_bottom, "ALL PROCESSING LOCAL", 8, MUTED).pack(anchor="w", pady=4)


# Workspace
workspace = tk.Frame(content, bg=BG)
workspace.pack(side="left", fill="both", expand=True)


# =========================================================
# TOP STATUS STRIP
# =========================================================

top_strip = tk.Frame(workspace, bg=BG)
top_strip.pack(fill="x", pady=(0, 12))

strip_left = tk.Frame(top_strip, bg=PANEL, padx=14, pady=10, highlightthickness=1, highlightbackground=BORDER)
strip_left.pack(side="left", fill="x", expand=True)
make_label(strip_left, "NEURAL INTERFACE", 9, CYAN, True, PANEL).pack(side="left")
make_label(strip_left, "   /   SECURE LOCAL SESSION", 8, MUTED, False, PANEL).pack(side="left")

state_box = tk.Frame(top_strip, bg=PANEL, padx=14, pady=10, highlightthickness=1, highlightbackground=BORDER)
state_box.pack(side="right", padx=(10, 0))
state_dot = make_label(state_box, "●", 10, CYAN, True, PANEL)
state_dot.pack(side="left")
state_text = make_label(state_box, "ONLINE", 8, CYAN, True, PANEL)
state_text.pack(side="left", padx=(6, 0))


# =========================================================
# REACTOR PANEL
# =========================================================

core_panel = tk.Frame(workspace, bg=PANEL, padx=16, pady=12, highlightthickness=1, highlightbackground=BORDER)
core_panel.pack(fill="x", pady=(0, 12))

make_label(core_panel, "ARTIFICIAL INTELLIGENCE CORE", 9, CYAN, True).pack(pady=(2, 4))

core_frame = tk.Frame(core_panel, bg=PANEL)
core_frame.pack(fill="x")

core = tk.Canvas(core_frame, width=210, height=190, bg=PANEL, highlightthickness=0)
core.pack()

core_status = make_label(core_frame, "J.A.R.V.I.S  //  ONLINE", 9, CYAN, True)
core_status.pack(pady=(0, 6))

wave_canvas = tk.Canvas(core_panel, height=38, bg=PANEL, highlightthickness=0)
wave_canvas.pack(fill="x", padx=80)


# =========================================================
# CHAT PANEL + INPUT — FIXED LAYOUT
# =========================================================

chat_panel = tk.Frame(
    workspace,
    bg=PANEL,
    padx=14,
    pady=12,
    highlightthickness=1,
    highlightbackground=BORDER
)
chat_panel.pack(fill="both", expand=True)

chat_header = tk.Frame(chat_panel, bg=PANEL)
chat_header.pack(fill="x", pady=(0, 10))

make_label(
    chat_header,
    "COMMUNICATION TERMINAL",
    9, CYAN, True
).pack(side="left")

make_label(
    chat_header,
    "LOCAL ENCRYPTED SESSION",
    8, MUTED
).pack(side="right")

# Create chat history
chat = scrolledtext.ScrolledText(
    chat_panel,
    bg="#070e18",
    fg=TEXT,
    font=("Segoe UI", 10),
    wrap=tk.WORD,
    borderwidth=0,
    padx=18,
    pady=14,
    insertbackground=CYAN,
    selectbackground="#16465b",
    relief="flat"
)

chat.tag_config(
    "user",
    foreground=CYAN,
    font=("Segoe UI", 9, "bold"),
    spacing1=12
)
chat.tag_config(
    "jarvis",
    foreground=GREEN,
    font=("Segoe UI", 9, "bold"),
    spacing1=12
)
chat.tag_config(
    "message",
    foreground=TEXT,
    font=("Segoe UI", 10),
    lmargin1=8,
    lmargin2=8,
    spacing3=5
)

chat.config(state="disabled")

# Create input panel FIRST and reserve its space
input_panel = tk.Frame(
    chat_panel,
    bg=PANEL,
    padx=12,
    pady=10,
    highlightthickness=1,
    highlightbackground=BORDER
)
input_panel.pack(
    side="bottom",
    fill="x",
    pady=(10, 0)
)

make_label(
    input_panel,
    "COMMAND INPUT",
    8, CYAN, True
).pack(anchor="w", pady=(0, 7))

input_row = tk.Frame(input_panel, bg=PANEL)
input_row.pack(fill="x")

entry = tk.Entry(
    input_row,
    bg="#101f30",
    fg=TEXT,
    insertbackground=CYAN,
    font=("Segoe UI", 11),
    relief="flat",
    bd=0
)
entry.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=12,
    padx=(0, 8)
)
entry.bind("<Return>", send_message)

send_button = tk.Button(
    input_row,
    text="SEND  ➤",
    command=send_message,
    bg=CYAN,
    fg=BG,
    activebackground="#7cecff",
    activeforeground=BG,
    font=("Segoe UI", 9, "bold"),
    relief="flat",
    bd=0,
    padx=22,
    pady=11,
    cursor="hand2"
)
send_button.pack(side="right")

# Pack chat history LAST so it uses only the remaining space
chat.pack(
    side="top",
    fill="both",
    expand=True
)


# =========================================================
# ANIMATIONS
# =========================================================

animation_angle = 0
wave_offset = 0
pulse_phase = 0


def animate_core():
    global animation_angle, pulse_phase

    if not root.winfo_exists():
        return

    core.delete("all")
    animation_angle = (animation_angle + 3) % 360
    pulse_phase += 0.10

    color = STATE_COLORS.get(jarvis_state, CYAN)
    cx, cy = 105, 95
    pulse = 4 * (1 + math.sin(pulse_phase))

    # Outer rings and rotating arcs
    core.create_oval(18, 8, 192, 182, outline="#173d53", width=2)
    for i in range(8):
        core.create_arc(
            18, 8, 192, 182,
            start=animation_angle + i * 45,
            extent=24,
            style="arc",
            outline=color,
            width=3
        )

    core.create_oval(37, 27, 173, 163, outline="#14506b", width=2)
    for i in range(6):
        core.create_arc(
            37, 27, 173, 163,
            start=-animation_angle * 1.5 + i * 60,
            extent=32,
            style="arc",
            outline=CYAN,
            width=3
        )

    core.create_oval(55, 45, 155, 145, outline=color, width=2)

    for i in range(24):
        angle = math.radians(i * 15 + animation_angle)
        x1 = cx + math.cos(angle) * 75
        y1 = cy + math.sin(angle) * 75
        x2 = cx + math.cos(angle) * 84
        y2 = cy + math.sin(angle) * 84
        core.create_line(x1, y1, x2, y2, fill=color if i % 3 == 0 else "#28536b", width=2)

    core.create_oval(70, 60, 140, 130, outline=color, width=2)
    core.create_oval(
        82 - pulse / 2, 72 - pulse / 2,
        128 + pulse / 2, 118 + pulse / 2,
        fill="#102d43", outline=CYAN, width=2
    )
    core.create_oval(91, 81, 119, 109, fill=color, outline="")
    core.create_oval(99, 89, 111, 101, fill="#ffffff", outline="")

    root.after(35, animate_core)


def animate_waveform():
    global wave_offset

    if not root.winfo_exists():
        return

    wave_canvas.delete("all")
    wave_offset += 1
    width = max(wave_canvas.winfo_width(), 360)
    center = 19
    color = STATE_COLORS.get(jarvis_state, CYAN)

    if jarvis_state == "LISTENING":
        amplitude, speed = 13, 0.12
    elif jarvis_state == "THINKING":
        amplitude, speed = 5, 0.035
    elif jarvis_state == "SPEAKING":
        amplitude, speed = 15, 0.16
    else:
        amplitude, speed = 3, 0.06

    points = []
    for x in range(0, width, 4):
        y = center + (
            math.sin((x + wave_offset * 4) * speed) * amplitude * 0.7
            + math.sin((x - wave_offset * 2) * speed * 1.7) * amplitude * 0.3
        )
        points.extend((x, y))

    if len(points) >= 4:
        wave_canvas.create_line(*points, fill=color, width=2, smooth=True)

    root.after(40, animate_waveform)


# =========================================================
# SYSTEM TELEMETRY
# =========================================================

def update_telemetry():
    if not root.winfo_exists():
        return

    if psutil:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            cpu_value.config(text=f"CPU       {cpu:4.0f}%")
            ram_value.config(text=f"RAM       {ram:4.0f}%")
        except Exception:
            pass
    else:
        cpu_value.config(text="CPU       install psutil")
        ram_value.config(text="RAM       unavailable")

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = [part.strip() for part in result.stdout.strip().split(",")]
            if len(parts) >= 3:
                gpu_value.config(text=f"GPU       {parts[0]}%  ·  {parts[1]}/{parts[2]} MB")
            else:
                gpu_value.config(text="NVIDIA  DETECTED")
        else:
            gpu_value.config(text="NVIDIA  NOT FOUND")
    except Exception:
        gpu_value.config(text="NVIDIA  UNAVAILABLE")

    root.after(3000, update_telemetry)


# =========================================================
# WELCOME + STARTUP
# =========================================================

add_message(
    "JARVIS",
    "Good day, boss. JARVIS command center is online. "
    "Qwen3 is standing by, and offline voice recognition is ready. "
    "How may I assist you?"
)

entry.focus_set()
animate_core()
animate_waveform()
update_telemetry()
root.after(1000, start_wake_listener)


def on_close():
    wake_stop.set()
    speech_stop.set()
    stop_monitor_stop.set()
    try:
        root.destroy()
    except tk.TclError:
        pass


root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()