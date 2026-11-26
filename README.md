J.A.R.V.I.S — Local AI Voice Assistant

A futuristic desktop AI assistant built with Python, Tkinter, Ollama, Qwen3 and Vosk.

Features

* 🤖 Local AI responses using Qwen3 4B
* 🎙️ Offline speech recognition using Vosk
* 🔊 Text-to-speech using pyttsx3
* 🎨 Futuristic dark-themed GUI
* 🎤 Manual microphone activation
* 💤 Wake-word and sleep mode
* 💻 Launch Windows applications
* 🌐 Open websites using voice or text commands
* 📊 CPU and RAM monitoring

Technologies Used

* Python
* Tkinter
* Ollama
* Qwen3 4B
* Vosk
* PyAudio
* pyttsx3
* psutil

Requirements

* Windows 10 or 11
* Python 3
* Ollama
* Qwen3 4B model
* Vosk offline speech recognition model

Installation

1. Clone this repository:

git clone https://github.com/YOUR_USERNAME/JARVIS-AI-Assistant.git

2. Open the project folder:

cd JARVIS-AI-Assistant

3. Create a virtual environment:

python -m venv venv

4. Activate it:

.\venv\Scripts\Activate.ps1

5. Install dependencies:

pip install -r requirements.txt

6. Install Ollama and download the model:

ollama pull qwen3:4b

7. Download and configure a Vosk model. Update MODEL_PATH in gui.py to point to its folder.
8. Run JARVIS:

python gui.py

Project Structure

JARVIS/
├── gui.py
├── requirements.txt
├── .gitignore
└── README.md

Note

This project runs AI inference locally through Ollama. The Vosk model must be downloaded separately and is not included in this repository.

Author

Created as a personal Python AI assistant project.

⸻

⭐ If you find this project interesting, consider starring the repository!


## JARVIS GUI
![JARVIS Dashboard](jarvis-dashboard.png)
