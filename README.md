<div align="center">

<img src="assets/liny_animated.gif" alt="Liny Desktop AI" width="160" />

# Liny Desktop AI

**A native, production-grade desktop AI assistant with OS-level automation, multimodal screen vision, hands-free voice control, and a minimalist floating command palette.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![GUI PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52.svg?style=flat&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Model Gemini](https://img.shields.io/badge/LLM-Gemini_3.5_Flash-4285F4.svg?style=flat&logo=google&logoColor=white)](https://aistudio.google.com/)
[![License MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](LICENSE)
[![Platform Windows](https://img.shields.io/badge/platform-Windows_10%2F11-0078D6.svg?style=flat&logo=windows&logoColor=white)](https://microsoft.com)

</div>

---

## 🌟 Highlights

- **Mascot & Minimalist UI**: Frameless, draggable floating mascot action button with cubic edge-snapping physics, expanding into a Raycast / Spotlight-style dark obsidian command palette (`#0B0B0E`).
- **Multimodal Screen Vision**: Ask *"What's on my screen?"* and Liny captures your active desktop in millisecond-speed (`mss`), passing the image directly to Gemini's vision engine to inspect and summarize your active windows, code, or browser tabs.
- **Hands-Free Wake Word ("Liny")**: 100% free, zero-cloud, local wake-word listener with dynamic ambient noise calibration and acoustic chime feedback (`winsound.MessageBeep`).
- **Guaranteed OS Action Engine (Hands)**: Autonomous tool execution layer that launches desktop applications (Notepad, Chrome, VS Code, Calculator, Terminal), navigates websites, simulates Unicode typing, presses hotkeys, and inspects foreground window titles.
- **Zero UI Freezing**: True concurrent background architecture with dedicated `QThread` workers communicating over Qt signals/slots.
- **Natural Neural Voice (Mouth)**: High-fidelity natural speech synthesis powered by `edge-tts` (`en-US-ChristopherNeural`) with deadlock-free Windows multimedia audio playback.
- **Global Shortcuts**: System-wide low-overhead global hotkey daemon (`pynput`) to summon or emergency-abort anywhere in Windows.
- **Standalone Executable**: One-click PyInstaller bundling pipeline produces a standalone Windows binary (`dist/LinyDesktopAI/LinyDesktopAI.exe`) with embedded multi-resolution icon.

---

## ⌨️ Global Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd> | **Summon / Toggle** | Expands or collapses the assistant from anywhere in Windows |
| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>M</kbd> | **Voice Mic Trigger** | Instantly begins voice recording without saying the wake word |
| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>X</kbd> | **Emergency Abort** | Instantly stops active TTS vocalization, VAD recording, or automation |

---

## 🎙️ Hands-Free Voice Interaction

1. Say **"Computer"** (or click the floating mascot button / press `Ctrl+Alt+Space`).
2. An audio chime plays, and the orb indicator turns electric cyan (`Listening...`).
3. Speak your command naturally:
   - *"What's on my screen?"*
   - *"Open Notepad and write project plan"*
   - *"Visit github.com"*
   - *"What application is currently focused?"*
4. Liny executes the system action on your computer and confirms out loud using neural speech.

---

## 📁 Architecture Overview

```text
liny_desktop_assistant/
├── main.py                     # Entry point, single-instance mutex & thread coordinator
├── config.yaml                 # Configuration for LLM, Voice, Hotkeys, and UI
├── build.py                    # Standalone PyInstaller build pipeline
├── desktop_assistant.spec      # Production PyInstaller specification
├── assets/                     # Mascot logos, tray icons, and multi-resolution .ico
│   ├── logo.png
│   ├── app_icon.png
│   ├── app_icon_64.png
│   └── app_icon.ico
├── core/
│   ├── llm_manager.py          # Gemini 3.5 Flash-Lite & LM Studio orchestrator
│   ├── prompt_manager.py       # Conversational turns, multimodal image parts & tool results
│   ├── tool_router.py          # OpenAI-compatible function calling schemas & dispatcher
│   └── config_loader.py        # YAML loader with recursive env var expansion (.env)
├── interface/
│   ├── floating_widget.py      # Floating mascot overlay with edge-snapping & command palette
│   ├── tray.py                 # Windows system tray integration & contextual menu
│   ├── hotkeys.py              # Global OS-level keyboard shortcut daemon (pynput)
│   └── settings_dialog.py      # Graphical preferences dialog
├── audio/
│   ├── wake_word.py            # Local free wake-word listener with dynamic noise calibration
│   ├── stt.py                  # 16kHz VAD silence detector & SpeechRecognition engine
│   ├── tts.py                  # Deadlock-free edge-tts synthesis & Windows MCI player
│   └── voice_worker.py         # Dedicated audio state machine QThread worker
├── actions/
│   ├── system_control.py       # Cross-platform application launching & URL navigation
│   ├── keyboard_mouse.py       # PyAutoGUI mouse, hotkey & Unicode typing automation
│   └── vision.py               # Ultra-fast mss primary display screen capture
└── tests/                      # Automated test suites & end-to-end integration tests
```

---

## 🚀 Quickstart Guide

### 1. Clone Repository
```bash
git clone https://github.com/your-username/liny-desktop-ai.git
cd liny-desktop-ai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file in the project root:
```bash
cp .env.example .env
```
Add your free Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Get a free API key at [Google AI Studio](https://aistudio.google.com/)).*

### 4. Run Assistant
```powershell
python main.py
```

---

## 📦 Building Standalone Executable

To compile into a standalone `.exe` that runs without requiring Python:
```powershell
python build.py
```
The output executable will be generated at:
```text
dist/LinyDesktopAI/LinyDesktopAI.exe
```

---

## 🧪 Testing

Run all unit and integration test suites:
```powershell
python tests/test_actions.py
python tests/test_audio.py
python tests/test_architecture.py
python tests/test_packaging.py
python tests/test_software_e2e.py
```

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
