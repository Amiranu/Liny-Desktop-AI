"""
Main Application Entry Point, Single-Instance Orchestrator, and Lifecycle Coordinator.
Manages Qt event loop, SystemTray, FloatingWidget, VoiceWorker, LLMWorker,
and global system-wide hotkeys with clean multi-thread shutdown hooks.
"""

from __future__ import annotations

import logging
import queue
import sys
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from audio.voice_worker import VoiceWorker
from core.config_loader import load_config
from core.llm_manager import LLMManager
from core.prompt_manager import PromptManager
from core.tool_router import ToolRouter
from interface.floating_widget import FloatingWidget
from interface.hotkeys import GlobalHotkeyManager
from interface.settings_dialog import SettingsDialog
from interface.tray import SystemTray, generate_tray_icon

# Configure Root Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("desktop_ai.main")

SINGLE_INSTANCE_SERVER_NAME = "liny.desktop.assistant.v1"


class LLMWorker(QThread):
    """
    Dedicated QThread worker handling non-blocking LLM reasoning
    and multi-turn autonomous tool execution loops.
    """

    chunk_received = pyqtSignal(str)
    status_changed = pyqtSignal(str, str)  # status_text, state_key
    tool_dispatched = pyqtSignal(str, dict)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, llm_manager: LLMManager, tool_router: ToolRouter) -> None:
        super().__init__()
        self.llm = llm_manager
        self.tools = tool_router
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._prompt_manager = PromptManager()
        self._is_running = True
        self._abort_current = False

    def submit_prompt(self, prompt: str) -> None:
        """Enqueue prompt safely from UI or Voice threads."""
        self._abort_current = False
        self._queue.put(prompt)

    def abort_active(self) -> None:
        """Emergency abort current generation."""
        self._abort_current = True

    def stop(self) -> None:
        """Stop worker thread loop gracefully."""
        self._is_running = False
        self._abort_current = True
        self._queue.put(None)
        if not self.wait(600):
            self.terminate()

    def run(self) -> None:
        """Worker thread processing loop with multi-turn autonomous tool loop."""
        logger.info("LLMWorker thread running.")

        while self._is_running:
            try:
                prompt = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue

            if prompt is None:
                break

            self._abort_current = False
            lowered = prompt.lower().strip()

            # 1. Screen Vision Query Auto-Capture
            image_b64 = None
            if any(w in lowered for w in ["screen", "display", "looking at", "what's on my", "what is on my", "see my screen", "read my screen", "inspect screen"]):
                try:
                    from actions.vision import capture_screen_base64
                    self.status_changed.emit("Capturing screen...", "executing")
                    image_b64 = capture_screen_base64()
                except Exception as e:
                    logger.warning("Screen auto-capture error: %s", e)

            self.status_changed.emit("Thinking...", "thinking")
            self._prompt_manager.add_user_message(prompt, image_base64=image_b64)

            # 2. Guaranteed Action Pre-Dispatch: physically launch apps/urls immediately!
            import re
            direct_tool = None
            direct_args: Dict[str, Any] = {}

            app_match = re.search(r"\b(?:open|launch|start|run)\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+and\b|$)", lowered)
            if app_match and not any(w in lowered for w in ["how to", "what is", "can you", "why", "tutorial"]):
                candidate = app_match.group(1).strip()
                if any(ext in candidate for ext in [".com", ".org", ".io", ".net", "http", "www."]):
                    direct_tool = "open_url"
                    direct_args = {"url": candidate}
                else:
                    direct_tool = "open_application"
                    direct_args = {"app_name": candidate}

            url_match = re.search(r"\b(?:visit|go to|browse)\s+(https?://\S+|www\.\S+|[a-zA-Z0-9_\-]+\.(?:com|org|io|dev|net|ai))\b", lowered)
            if url_match:
                direct_tool = "open_url"
                direct_args = {"url": url_match.group(1).strip()}

            if direct_tool:
                self.status_changed.emit(f"Action: {direct_tool}", "executing")
                self.tool_dispatched.emit(direct_tool, direct_args)
                result_msg = self.tools.dispatch(direct_tool, direct_args)
                self.chunk_received.emit(f"\n⚡ [{direct_tool}]: {result_msg}\n")
                self._prompt_manager.add_assistant_tool_call(direct_tool, direct_args)
                self._prompt_manager.add_tool_result(direct_tool, result_msg)

            max_tool_iterations = 5
            iteration = 0
            final_spoken_response = ""

            try:
                while iteration < max_tool_iterations and self._is_running and not self._abort_current:
                    iteration += 1
                    messages = self._prompt_manager.get_messages()

                    accumulated_tokens: List[str] = []
                    tool_calls_in_turn: List[Dict[str, Any]] = []

                    for chunk in self.llm.stream_chat(messages):
                        if self._abort_current:
                            break

                        chunk_type = chunk.get("type")
                        if chunk_type == "chunk":
                            content = chunk.get("content", "")
                            accumulated_tokens.append(content)
                            self.chunk_received.emit(content)

                        elif chunk_type == "tool_call":
                            tool_calls_in_turn.append(chunk)

                    if self._abort_current:
                        self.status_changed.emit("Aborted", "error")
                        break

                    turn_text = "".join(accumulated_tokens)

                    if tool_calls_in_turn:
                        for tc in tool_calls_in_turn:
                            if self._abort_current:
                                break
                            tool_name = tc.get("name", "")
                            tool_args = tc.get("arguments", {})

                            self.status_changed.emit(f"Action: {tool_name}", "executing")
                            self.tool_dispatched.emit(tool_name, tool_args)

                            # Dispatch tool via ToolRouter
                            result_msg = self.tools.dispatch(tool_name, tool_args)
                            self.chunk_received.emit(f"\n⚡ [{tool_name}]: {result_msg}\n")

                            img_attach = None
                            if tool_name == "inspect_screen":
                                from actions.vision import capture_screen_base64
                                img_attach = capture_screen_base64()

                            self._prompt_manager.add_assistant_tool_call(tool_name, tool_args)
                            self._prompt_manager.add_tool_result(tool_name, result_msg, image_base64=img_attach)

                        self.status_changed.emit("Thinking...", "thinking")
                        continue
                    else:
                        final_spoken_response = turn_text
                        self._prompt_manager.add_assistant_message(final_spoken_response)
                        break

                if not self._abort_current:
                    self.status_changed.emit("Ready", "idle")
                    self.finished.emit(final_spoken_response)

            except Exception as e:
                logger.exception("LLM generation error: %s", e)
                self.status_changed.emit("Error", "error")
                self.error_occurred.emit(str(e))

            finally:
                self._queue.task_done()

        logger.info("LLMWorker thread stopped.")


class DesktopAssistantCoordinator(QObject):
    """
    Coordinates UI interactions, the SystemTray, background LLM worker,
    VoiceWorker (wake-word, STT, and TTS), and global hotkeys.
    """

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.config = load_config()

        # 1. Core Brain & Tool Router (auto-registers actions)
        self.llm_manager = LLMManager(self.config)
        self.tool_router = ToolRouter()

        # 2. Background Thread Workers
        self.llm_worker = LLMWorker(self.llm_manager, self.tool_router)
        self.voice_worker = VoiceWorker(self.config)
        self.hotkey_manager = GlobalHotkeyManager(self.config)

        # 3. UI Layer: System Tray & Floating Overlay Widget
        self.tray = SystemTray(app_name="Liny Desktop AI")
        self.floating_widget = FloatingWidget()
        self._update_provider_label()

        # 4. Connect Signals and Slots across all domains
        self._connect_signals()

        # 5. Single-instance local server
        self._local_server: Optional[QLocalServer] = None
        self._setup_single_instance_listener()

    def _setup_single_instance_listener(self) -> None:
        """Listen for subsequent application invocations to summon existing window."""
        self._local_server = QLocalServer(self)
        self._local_server.newConnection.connect(self._on_duplicate_instance_ping)
        self._local_server.listen(SINGLE_INSTANCE_SERVER_NAME)

    def _on_duplicate_instance_ping(self) -> None:
        if self._local_server and self._local_server.hasPendingConnections():
            client_socket = self._local_server.nextPendingConnection()
            client_socket.close()
            logger.info("Duplicate instance launched; summoning existing assistant.")
            self.summon_assistant()

    def _connect_signals(self) -> None:
        # --- Tray Interactions ---
        self.tray.toggle_assistant_requested.connect(self.toggle_assistant)
        self.tray.toggle_voice_requested.connect(self._toggle_voice_mute)
        self.tray.model_provider_changed.connect(self._on_model_provider_changed)
        self.tray.settings_requested.connect(self._on_settings_requested)
        self.tray.exit_requested.connect(self.shutdown)

        # --- Global Hotkey Actions ---
        self.hotkey_manager.summon_requested.connect(self.summon_assistant)
        self.hotkey_manager.voice_trigger_requested.connect(self.voice_worker.trigger_voice_manually)
        self.hotkey_manager.abort_requested.connect(self.emergency_abort)

        # --- UI -> Workers ---
        self.floating_widget.prompt_submitted.connect(self.llm_worker.submit_prompt)
        self.floating_widget.provider_toggle_requested.connect(self._toggle_provider)
        self.floating_widget.mute_toggled.connect(self._toggle_voice_mute)
        self.floating_widget.voice_trigger_requested.connect(self.voice_worker.trigger_voice_manually)
        self.floating_widget.closed.connect(self.shutdown)

        # --- Voice Worker -> UI & LLM Worker ---
        self.voice_worker.wake_word_detected.connect(self._on_wake_word_detected)
        self.voice_worker.audio_state_changed.connect(self._on_audio_state_changed)
        self.voice_worker.transcription_ready.connect(self._on_voice_transcription)
        self.voice_worker.status_message.connect(lambda msg: self.floating_widget.set_status(msg, "idle"))

        # --- LLM Worker -> UI & Voice Worker (TTS) ---
        self.llm_worker.chunk_received.connect(self.floating_widget.append_chunk)
        self.llm_worker.status_changed.connect(self._on_worker_status_changed)
        self.llm_worker.tool_dispatched.connect(self._on_tool_dispatched)
        self.llm_worker.error_occurred.connect(self._on_llm_error)
        self.llm_worker.finished.connect(self._on_llm_finished)

    def summon_assistant(self) -> None:
        """Summon, focus, and expand the floating widget from any application."""
        if not self.floating_widget.isVisible():
            self.floating_widget.show()
            self.tray.update_visibility_state(True)

        self.floating_widget.raise_()
        self.floating_widget.activateWindow()
        self.floating_widget.expand()

    def toggle_assistant(self) -> None:
        """Toggle floating widget visibility from tray."""
        is_visible = not self.floating_widget.isVisible()
        self.floating_widget.setVisible(is_visible)
        self.tray.update_visibility_state(is_visible)
        if is_visible:
            self.floating_widget.raise_()
            self.floating_widget.activateWindow()

    def emergency_abort(self) -> None:
        """Emergency abort: stops active TTS, VAD recording, and LLM processing."""
        logger.warning("Emergency Abort invoked via global shortcut!")
        self.llm_worker.abort_active()
        self.voice_worker.tts_engine.stop()
        self.voice_worker.stt_engine.stop_recording()
        self.floating_widget.set_status("Emergency Abort Triggered", "error")
        self.floating_widget.append_chunk("\n⛔ [Emergency Abort Triggered: Active actions stopped.]\n")

    def _on_worker_status_changed(self, text: str, state: str) -> None:
        self.floating_widget.set_status(text, state)
        self.tray.update_status(text)

    def _on_wake_word_detected(self, keyword: str) -> None:
        logger.info("Wake word '%s' detected! Activating UI.", keyword)
        self.summon_assistant()
        self.floating_widget.set_status(f"Heard '{keyword}' - Listening...", "listening")

    def _on_audio_state_changed(self, state: str) -> None:
        state_labels = {
            "idle": "Ready",
            "listening": "Listening...",
            "transcribing": "Transcribing speech...",
            "speaking": "Speaking...",
            "muted": "Muted",
        }
        label = state_labels.get(state, state.capitalize())
        self.floating_widget.set_status(label, state)
        self.tray.update_status(label)

    def _on_tool_dispatched(self, tool_name: str, args: dict) -> None:
        logger.info("Action dispatched: %s with %s", tool_name, args)
        self.floating_widget.set_status(f"Action: {tool_name}", "executing")

    def _on_voice_transcription(self, user_text: str) -> None:
        logger.info("Feeding voice prompt to LLM: '%s'", user_text)
        self.floating_widget.clear_response()
        self.floating_widget.append_chunk(f"🎤 {user_text}\n\n")
        self.llm_worker.submit_prompt(user_text)

    def _on_llm_finished(self, full_response: str) -> None:
        if full_response.strip():
            self.voice_worker.speak_response(full_response)

    def _toggle_voice_mute(self) -> None:
        is_muted = self.voice_worker.toggle_mute()
        self.floating_widget.set_mute_state(is_muted)
        self.tray.update_voice_state(is_muted)

    def _on_model_provider_changed(self, provider: str) -> None:
        self.llm_manager.set_provider(provider)
        self._update_provider_label()

    def _toggle_provider(self) -> None:
        order = ["gemini", "lm_studio"]
        current = self.llm_manager.provider
        next_idx = (order.index(current) + 1) % len(order) if current in order else 0
        new_provider = order[next_idx]
        self.llm_manager.set_provider(new_provider)
        self._update_provider_label()
        self.tray.show_notification("Model Provider Switched", f"Active Engine: {new_provider.upper()}")

    def _update_provider_label(self) -> None:
        prov = self.llm_manager.provider
        label_map = {
            "lm_studio": "LM Studio",
            "gemini": "Gemini",
        }
        self.floating_widget.set_provider_label(label_map.get(prov, "Gemini"))

    def _on_settings_requested(self) -> None:
        dialog = SettingsDialog(self.config, self.floating_widget)
        if dialog.exec():
            # Refresh runtime configuration
            self.llm_manager.set_provider(self.config.get("llm", {}).get("provider", "gemini"))
            self._update_provider_label()
            self.tray.show_notification("Settings Saved", "Configuration updated successfully.")

    def _on_llm_error(self, err_msg: str) -> None:
        self.floating_widget.append_chunk(f"\n⚠️ Error: {err_msg}\n")
        self.tray.show_notification("Assistant Notice", err_msg)

    def start(self) -> None:
        """Start background workers, global hooks, and display shell."""
        self.llm_worker.start()
        self.voice_worker.start()
        self.hotkey_manager.start()

        self.tray.show()
        self.floating_widget.show()
        self.floating_widget.raise_()
        self.floating_widget.activateWindow()
        self.floating_widget.expand()
        self.tray.update_visibility_state(True)

        hotkeys = self.config.get("hotkeys", {})
        self.tray.show_notification(
            "Liny Desktop AI Active",
            f"Assistant running in background.\nPress {hotkeys.get('summon', 'Ctrl+Alt+Space')} or say 'Computer' to summon.",
        )
        logger.info("Desktop Assistant successfully started with full persistence.")

    def shutdown(self) -> None:
        """Gracefully release all threads, OS hooks, and exit."""
        logger.info("Shutting down Desktop Assistant...")
        try:
            self.hotkey_manager.stop()
        except Exception:
            pass
        try:
            self.voice_worker.stop_all()
        except Exception:
            pass
        try:
            self.llm_worker.stop()
        except Exception:
            pass
        try:
            self.tray.hide()
            self.floating_widget.close()
        except Exception:
            pass
        try:
            if self._local_server:
                self._local_server.close()
        except Exception:
            pass

        self.app.quit()


def check_single_instance() -> bool:
    """Return True if this is the only instance, or False if another is active."""
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_SERVER_NAME)
    if socket.waitForConnected(400):
        socket.close()
        return False
    QLocalServer.removeServer(SINGLE_INSTANCE_SERVER_NAME)
    return True


def global_exception_hook(exctype, value, traceback) -> None:
    """Catch unhandled exceptions without crashing the Qt event loop."""
    logger.critical("Unhandled exception:", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)


def main() -> None:
    sys.excepthook = global_exception_hook

    # Set explicit Windows AppUserModelID so Windows taskbar groups and displays custom icon
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "liny.desktop.ai.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app_icon = generate_tray_icon(size=128)
    app.setWindowIcon(app_icon)
    app.setQuitOnLastWindowClosed(False)

    # Check Single-Instance Lock
    if not check_single_instance():
        logger.info("Assistant is already running in background. Sent wake signal and exiting.")
        sys.exit(0)

    coordinator = DesktopAssistantCoordinator(app)
    coordinator.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
