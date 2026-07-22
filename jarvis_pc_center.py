import tkinter as tk
import psutil
import time
import threadingimport tkinter as tk
import psutil
import time
import threading
import queue
import os
import json
import shutil
import subprocess
import datetime
import math
import tempfile
import urllib.request
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from plyer import notification as plyer_notification
    _NOTIFY_AVAILABLE = True
except ImportError:
    plyer_notification = None
    _NOTIFY_AVAILABLE = False

try:
    import speech_recognition as sr
    _VOICE_AVAILABLE = True
except ImportError:
    sr = None
    _VOICE_AVAILABLE = False

import sys
import hashlib
from tkinter import ttk, messagebox

try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_AVAILABLE = True
except ImportError:
    pystray = None
    _TRAY_AVAILABLE = False

try:
    import send2trash
    _SEND2TRASH_AVAILABLE = True
except ImportError:
    send2trash = None
    _SEND2TRASH_AVAILABLE = False

try:
    import winreg
    _WINREG_AVAILABLE = os.name == "nt"
except ImportError:
    winreg = None
    _WINREG_AVAILABLE = False

# =========================================================
# Voix naturelle : edge-tts (voix neuronale) avec repli sur pyttsx3
# =========================================================
try:
    import edge_tts
    import asyncio
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    _EDGE_TTS_AVAILABLE = False

try:
    import pygame
    pygame.mixer.init()
    _PYGAME_AVAILABLE = True
except Exception:
    _PYGAME_AVAILABLE = False

try:
    from playsound import playsound as _playsound
    _PLAYSOUND_AVAILABLE = True
except ImportError:
    _playsound = None
    _PLAYSOUND_AVAILABLE = False

import pyttsx3
_pyttsx3_engine = pyttsx3.init()
_pyttsx3_engine.setProperty('rate', 178)

# Voix masculine française neuronale, chaude et naturelle (edge-tts)
EDGE_VOICE = "fr-FR-HenriNeural"
_VOICE_TMP_PATH = os.path.join(tempfile.gettempdir(), "jarvis_voice.mp3")

# --- Variables HUD ---
hud_speed = 0.05          # vitesse de "respiration" du HUD (radians/frame)
hud_color = "#e0a85c"

# --- Energy tracking ---
total_energy_wh = 0.0
hour_energy_wh = 0.0
day_energy_wh = 0.0
week_energy_wh = 0.0
month_energy_wh = 0.0

last_hour = datetime.datetime.now().hour
last_day = datetime.datetime.now().day
last_week = datetime.datetime.now().isocalendar()[1]
last_month = datetime.datetime.now().month

price_per_kwh = 0.25  # euros par kWh

ENERGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_energy_data.json")


def load_energy_data():
    global total_energy_wh, hour_energy_wh, day_energy_wh, week_energy_wh, month_energy_wh
    global last_hour, last_day, last_week, last_month

    if not os.path.exists(ENERGY_FILE):
        return
    try:
        with open(ENERGY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    now = datetime.datetime.now()
    total_energy_wh = data.get("total_energy_wh", 0.0)
    hour_energy_wh = data.get("hour_energy_wh", 0.0) if data.get("last_hour") == now.hour else 0.0
    day_energy_wh = data.get("day_energy_wh", 0.0) if data.get("last_day") == now.day else 0.0
    week_energy_wh = data.get("week_energy_wh", 0.0) if data.get("last_week") == now.isocalendar()[1] else 0.0
    month_energy_wh = data.get("month_energy_wh", 0.0) if data.get("last_month") == now.month else 0.0


def save_energy_data():
    data = {
        "total_energy_wh": total_energy_wh,
        "hour_energy_wh": hour_energy_wh,
        "day_energy_wh": day_energy_wh,
        "week_energy_wh": week_energy_wh,
        "month_energy_wh": month_energy_wh,
        "last_hour": last_hour,
        "last_day": last_day,
        "last_week": last_week,
        "last_month": last_month,
    }
    try:
        with open(ENERGY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


load_energy_data()

# =========================================================
# Config personnalisée (prénom de l'utilisateur, demandé une seule fois)
# =========================================================
from tkinter import simpledialog

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


_config = load_config()
USER_NAME = _config.get("user_name")

# --- Fenêtre principale ---
root = tk.Tk()
root.withdraw()

if not USER_NAME:
    USER_NAME = simpledialog.askstring(
        "Bienvenue",
        "Quel est ton prénom ?",
        parent=root
    ) or "Ami"
    _config["user_name"] = USER_NAME
    save_config(_config)


def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return f"Bonjour {USER_NAME}."
    elif 12 <= hour < 18:
        return f"Bon après-midi {USER_NAME}."
    elif 18 <= hour < 23:
        return f"Bonsoir {USER_NAME}."
    else:
        return f"Bonne nuit {USER_NAME}."


root.deiconify()
root.title(f"Jarvis — {USER_NAME}")
root.geometry("1050x900")
root.minsize(900, 700)
try:
    root.state("zoomed")
except tk.TclError:
    pass

# =========================================================
# Palette : ardoise chaude + or doux, plus sobre que le style "hacker cyan"
# =========================================================
BG_COLOR = "#14161f"
CARD_BG = "#1c2030"
CARD_BORDER = "#2a2f45"
ACCENT = "#e0a85c"       # or doux
ACCENT_SOFT = "#7c8aa8"  # bleu-gris discret
TEXT_COLOR = "#c9ccd6"
TEXT_DIM = "#7f8496"
TITLE_COLOR = "#f0d9b5"

root.config(bg=BG_COLOR)

_ttk_style = ttk.Style()
try:
    _ttk_style.theme_use("clam")
except tk.TclError:
    pass
_ttk_style.configure("Jarvis.Treeview", background=CARD_BG, fieldbackground=CARD_BG,
                      foreground=TEXT_COLOR, borderwidth=0, rowheight=24)
_ttk_style.configure("Jarvis.Treeview.Heading", background=CARD_BORDER, foreground=TITLE_COLOR,
                      relief="flat")
_ttk_style.map("Jarvis.Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#1c1408")])

# =========================================================
# Voix (thread-safe via une queue + un seul worker)
# =========================================================
speech_queue = queue.Queue()


def _speak_with_pyttsx3(text):
    try:
        _pyttsx3_engine.say(text)
        _pyttsx3_engine.runAndWait()
    except Exception:
        pass


def _speak_with_edge(text):
    async def _run():
        communicate = edge_tts.Communicate(text, EDGE_VOICE)
        await communicate.save(_VOICE_TMP_PATH)

    asyncio.run(_run())
    if _PYGAME_AVAILABLE:
        pygame.mixer.music.load(_VOICE_TMP_PATH)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    elif _PLAYSOUND_AVAILABLE:
        _playsound(_VOICE_TMP_PATH)
    elif os.name == "nt":
        os.startfile(_VOICE_TMP_PATH)
    else:
        raise RuntimeError("Aucun lecteur audio disponible")


def _speech_worker():
    while True:
        text = speech_queue.get()
        if text is None:
            continue
        spoken = False
        if _EDGE_TTS_AVAILABLE:
            try:
                _speak_with_edge(text)
                spoken = True
            except Exception:
                spoken = False
        if not spoken:
            _speak_with_pyttsx3(text)
        speech_queue.task_done()


threading.Thread(target=_speech_worker, daemon=True).start()


def jarvis_say(text):
    speech_queue.put(text)


# --- Diagnostic du moteur vocal : dit clairement quelle voix est active,
# au lieu de basculer silencieusement sur pyttsx3 sans que ça se voie. ---
_voice_state = {"text": "Voix : vérification en cours…"}


def _probe_voice_engine():
    if not _EDGE_TTS_AVAILABLE:
        _voice_state["text"] = "Voix : standard (pyttsx3) — installe 'edge-tts' pour la voix naturelle"
        return
    if not (_PYGAME_AVAILABLE or _PLAYSOUND_AVAILABLE):
        _voice_state["text"] = "Voix : standard (pyttsx3) — installe 'pygame' ou 'playsound' pour lire la voix edge-tts"
        return
    try:
        async def _run():
            communicate = edge_tts.Communicate("test", EDGE_VOICE)
            await communicate.save(_VOICE_TMP_PATH)
        asyncio.run(_run())
        _voice_state["text"] = f"Voix : neuronale active ({EDGE_VOICE})"
    except Exception:
        _voice_state["text"] = "Voix : standard (pyttsx3) — edge-tts nécessite une connexion internet"


threading.Thread(target=_probe_voice_engine, daemon=True).start()


# =========================================================
# Notifications Windows
# =========================================================
def send_notification(title, message):
    if not _NOTIFY_AVAILABLE:
        return
    try:
        plyer_notification.notify(title=title, message=message, app_name="Jarvis", timeout=5)
    except Exception:
        pass


if os.name == "nt":
    _SUBPROCESS_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _SUBPROCESS_KWARGS = {}

# =========================================================
# Actions système réelles (plans d'alimentation, priorité CPU, DNS)
# =========================================================
try:
    import win32gui
    import win32process
    _WIN32_AVAILABLE = True
except ImportError:
    win32gui = None
    win32process = None
    _WIN32_AVAILABLE = False

POWER_PLANS = {
    "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
}

_current_power_plan = None  # évite de rappeler powercfg si on est déjà sur le bon plan


def set_power_plan(plan_key):
    global _current_power_plan
    if os.name != "nt":
        return False
    if _current_power_plan == plan_key:
        return True  # déjà appliqué, on ne relance pas powercfg pour rien
    guid = POWER_PLANS.get(plan_key)
    if not guid:
        return False
    try:
        subprocess.run(["powercfg", "/setactive", guid], check=True, **_SUBPROCESS_KWARGS)
        _current_power_plan = plan_key
        return True
    except Exception:
        return False


def flush_dns():
    if os.name != "nt":
        return
    try:
        subprocess.run(["ipconfig", "/flushdns"], check=True, **_SUBPROCESS_KWARGS)
    except Exception:
        pass


# =========================================================
# Démarrage automatique avec Windows (clé de registre Run,
# ne nécessite pas les droits administrateur — HKCU seulement)
# =========================================================
_STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_VALUE_NAME = "JarvisControlCenter"


def _startup_command():
    if getattr(sys, "frozen", False):
        # Empaqueté en .exe (PyInstaller) : on lance l'exécutable directement.
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pythonw if os.path.exists(pythonw) else sys.executable
    script = os.path.abspath(__file__)
    return f'"{exe}" "{script}"'


def is_startup_enabled():
    if not _WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _STARTUP_VALUE_NAME)
        return True
    except Exception:
        return False


def enable_startup():
    if not _WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _STARTUP_VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
        return True
    except Exception:
        return False


def disable_startup():
    if not _WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _STARTUP_VALUE_NAME)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


startup_button = None


def _refresh_startup_button():
    if startup_button:
        startup_button.config(
            text="DÉMARRAGE AUTO : ON" if is_startup_enabled() else "DÉMARRAGE AUTO : OFF"
        )


def toggle_startup():
    if not _WINREG_AVAILABLE:
        set_status("Jarvis : démarrage automatique disponible uniquement sur Windows.", speak=True)
        return
    if is_startup_enabled():
        disable_startup()
        set_status("Jarvis : démarrage automatique désactivé.", speak=True)
    else:
        enable_startup()
        set_status("Jarvis : démarrage automatique activé.", speak=True)
    _refresh_startup_button()


# =========================================================
# Mise à jour automatique — hébergée sur un dépôt GitHub public.
#
# Marche à suivre (5 minutes, une seule fois) :
#   1. Crée un compte GitHub (gratuit) et un nouveau dépôt PUBLIC,
#      par ex. "jarvis-updates".
#   2. Mets dedans ce fichier jarvis_pc_center.py et un fichier
#      "version.txt" qui contient juste un numéro, ex. : 1.0.0
#   3. Sur chaque fichier, clique "Raw" en haut à droite sur GitHub
#      et copie l'URL affichée dans la barre d'adresse.
#   4. Colle ces deux URLs ci-dessous (UPDATE_VERSION_URL /
#      UPDATE_SCRIPT_URL).
#
# Pour publier une mise à jour plus tard : augmente le numéro dans
# version.txt (ex. 1.1.0) et remplace jarvis_pc_center.py sur le
# dépôt par la nouvelle version — c'est tout, Jarvis la détectera.
# =========================================================
JARVIS_VERSION = "1.0.0"
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/TON-PSEUDO/TON-DEPOT/main/version.txt"
UPDATE_SCRIPT_URL = "https://raw.githubusercontent.com/TON-PSEUDO/TON-DEPOT/main/jarvis_pc_center.py"
UPDATE_EXE_URL = "https://raw.githubusercontent.com/TON-PSEUDO/TON-DEPOT/main/Jarvis.exe"


def check_for_update(silent=False):
    def worker():
        try:
            with urllib.request.urlopen(UPDATE_VERSION_URL, timeout=5) as resp:
                remote_version = resp.read().decode("utf-8").strip()
        except Exception:
            if not silent:
                root.after(0, lambda: set_status(
                    "Jarvis : impossible de vérifier les mises à jour (connexion ou URL non configurée).", speak=True
                ))
            return

        if remote_version == JARVIS_VERSION:
            if not silent:
                root.after(0, lambda: set_status(f"Jarvis : déjà à jour (version {JARVIS_VERSION}).", speak=True))
            return

        root.after(0, lambda: _prompt_update(remote_version))

    threading.Thread(target=worker, daemon=True).start()


def _prompt_update(remote_version):
    if not messagebox.askyesno(
        "Jarvis — Mise à jour",
        f"Nouvelle version disponible : {remote_version} (actuelle : {JARVIS_VERSION}).\nMettre à jour maintenant ?"
    ):
        return
    threading.Thread(target=_download_and_install_update, daemon=True).start()


def _restart_script():
    save_energy_data()
    if _tray_icon:
        _tray_icon.stop()
    python = sys.executable
    os.execl(python, python, os.path.abspath(__file__))


def _restart_frozen_exe(new_exe_path):
    """Windows verrouille l'exécutable tant qu'il tourne : on passe par un
    petit script qui attend la fermeture de Jarvis avant de remplacer le
    fichier, puis relance la nouvelle version."""
    current_exe = sys.executable
    bat_path = os.path.join(tempfile.gettempdir(), "jarvis_update.bat")
    bat_content = (
        "@echo off\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'copy /y "{new_exe_path}" "{current_exe}" >nul\r\n'
        f'start "" "{current_exe}"\r\n'
        f'del "%~f0"\r\n'
    )
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    subprocess.Popen(["cmd", "/c", bat_path], **_SUBPROCESS_KWARGS)
    if _tray_icon:
        _tray_icon.stop()
    root.destroy()
    os._exit(0)


def _download_and_install_update():
    is_frozen = getattr(sys, "frozen", False)
    download_url = UPDATE_EXE_URL if is_frozen else UPDATE_SCRIPT_URL
    try:
        with urllib.request.urlopen(download_url, timeout=30) as resp:
            new_content = resp.read()
    except Exception:
        root.after(0, lambda: messagebox.showerror("Jarvis", "Échec du téléchargement de la mise à jour."))
        return

    if is_frozen:
        temp_new = os.path.join(tempfile.gettempdir(), "jarvis_new.exe")
        try:
            with open(temp_new, "wb") as f:
                f.write(new_content)
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("Jarvis", f"Échec de l'écriture de la mise à jour : {e}"))
            return
        root.after(0, lambda: set_status("Jarvis : mise à jour installée, redémarrage…", speak=True))
        root.after(800, lambda: _restart_frozen_exe(temp_new))
    else:
        script_path = os.path.abspath(__file__)
        backup_path = script_path + ".bak"
        try:
            shutil.copy2(script_path, backup_path)
            with open(script_path, "wb") as f:
                f.write(new_content)
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("Jarvis", f"Échec de l'installation de la mise à jour : {e}"))
            return
        root.after(0, lambda: set_status("Jarvis : mise à jour installée, redémarrage…", speak=True))
        root.after(800, _restart_script)


def check_for_update_button():
    check_for_update(silent=False)


# =========================================================
# Icône dans la barre des tâches (system tray) — Jarvis continue de
# tourner en arrière-plan quand on ferme la fenêtre, comme une vraie
# appli système, au lieu de se fermer complètement.
# =========================================================
_tray_icon = None
_tray_notified_once = False


def _make_tray_image():
    size = 64
    img = Image.new("RGBA", (size, size), (20, 22, 31, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([6, 6, size - 6, size - 6], outline=(224, 168, 92, 255), width=4)
    draw.ellipse([22, 22, size - 22, size - 22], fill=(224, 168, 92, 255))
    return img


def _do_show_window():
    root.deiconify()
    try:
        root.state("zoomed")
    except tk.TclError:
        pass
    root.lift()
    root.focus_force()


def show_window(icon=None, item=None):
    root.after(0, _do_show_window)


def hide_window():
    global _tray_notified_once
    root.withdraw()
    if _TRAY_AVAILABLE:
        start_tray_icon()
        if not _tray_notified_once:
            send_notification("Jarvis", "Toujours actif dans la barre des tâches.")
            _tray_notified_once = True


def real_quit(icon=None, item=None):
    def _do():
        save_energy_data()
        restore_foreground_process()
        restore_lowered_processes()
        set_power_plan("balanced")
        if _tray_icon:
            _tray_icon.stop()
        root.destroy()
    root.after(0, _do)


def _toggle_startup_menu(icon, item):
    root.after(0, toggle_startup)


def start_tray_icon():
    global _tray_icon
    if not _TRAY_AVAILABLE or _tray_icon is not None:
        return
    menu = pystray.Menu(
        pystray.MenuItem("Afficher Jarvis", show_window, default=True),
        pystray.MenuItem("Démarrage auto avec Windows", _toggle_startup_menu,
                          checked=lambda item: is_startup_enabled()),
        pystray.MenuItem("Quitter", real_quit),
    )
    _tray_icon = pystray.Icon("jarvis", _make_tray_image(), "Jarvis Control Center", menu)
    threading.Thread(target=_tray_icon.run, daemon=True).start()


def get_foreground_pid():
    if not _WIN32_AVAILABLE:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception:
        return None


_boosted_pid = None


def boost_foreground_process():
    global _boosted_pid
    pid = get_foreground_pid()
    if pid is None:
        return None
    try:
        p = psutil.Process(pid)
        if os.name == "nt":
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            p.nice(-5)
        _boosted_pid = pid
        return p.name()
    except Exception:
        return None


def restore_foreground_process():
    global _boosted_pid
    if _boosted_pid is None:
        return
    try:
        p = psutil.Process(_boosted_pid)
        p.nice(psutil.NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
    except Exception:
        pass
    _boosted_pid = None


_CRITICAL_PROCESS_NAMES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe", "explorer.exe",
    "dwm.exe", "python.exe", "pythonw.exe",
}

_lowered_pids = []


def lower_background_processes(limit=5):
    global _lowered_pids
    restore_lowered_processes()

    foreground_pid = get_foreground_pid()
    own_pid = os.getpid()
    candidates = []

    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            name = (proc.info["name"] or "").lower()
            pid = proc.info["pid"]
            if name in _CRITICAL_PROCESS_NAMES or pid in (foreground_pid, own_pid):
                continue
            candidates.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    candidates.sort(key=lambda p: p.info.get("memory_percent") or 0, reverse=True)

    for proc in candidates[:limit]:
        try:
            proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 5)
            _lowered_pids.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def restore_lowered_processes():
    global _lowered_pids
    for pid in _lowered_pids:
        try:
            p = psutil.Process(pid)
            p.nice(psutil.NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _lowered_pids = []


# =========================================================
# Utilitaires de dessin : rectangle arrondi + interpolation de couleur.
# Tout est dessiné une seule fois (statique) — ça n'ajoute aucun coût
# en continu, seul l'aspect visuel change.
# =========================================================
def rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    c1, c2 = c1.lstrip('#'), c2.lstrip('#')
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class CanvasLabel:
    """Petit adaptateur pour garder l'API .config(text=...) des anciens
    tk.Label, mais en dessinant sur un Canvas (nécessaire pour les coins
    arrondis)."""
    def __init__(self, canvas, item_id):
        self.canvas = canvas
        self.item_id = item_id

    def config(self, **kwargs):
        if "text" in kwargs:
            self.canvas.itemconfig(self.item_id, text=kwargs["text"])


# --- Titre ---
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(fill="x", pady=(16, 0))

title = tk.Label(header_frame, text="JARVIS", font=("Segoe UI Semibold", 22), fg=TITLE_COLOR, bg=BG_COLOR)
title.pack(side="left", padx=24)

subtitle = tk.Label(header_frame, text=f"pour {USER_NAME}", font=("Segoe UI", 13), fg=TEXT_DIM, bg=BG_COLOR)
subtitle.pack(side="left", padx=(2, 0))

clock_label = tk.Label(header_frame, text="", font=("Segoe UI", 12), fg=TEXT_COLOR, bg=BG_COLOR)
clock_label.pack(side="right", padx=24)


def update_clock():
    now = datetime.datetime.now()
    clock_label.config(text=now.strftime("%A %d %B %Y — %H:%M:%S"))
    root.after(1000, update_clock)


update_clock()

# =========================================================
# HUD : un seul anneau qui "respire" doucement — animé via root.after,
# jamais via un thread qui martèle canvas.update() en continu.
# =========================================================
hud_canvas = tk.Canvas(root, width=260, height=260, bg=BG_COLOR, highlightthickness=0)
hud_canvas.pack(side="right", padx=24, pady=10)

_HUD_CX, _HUD_CY, _HUD_BASE_R = 130, 130, 88

# Halo statique : quelques cercles dessinés une seule fois avec une couleur
# qui s'estompe vers le fond, pour donner un effet de lueur sans animer quoi
# que ce soit (zéro coût CPU en continu).
for _i, _rad in enumerate([120, 108, 98]):
    hud_canvas.create_oval(
        _HUD_CX - _rad, _HUD_CY - _rad, _HUD_CX + _rad, _HUD_CY + _rad,
        outline=_blend(ACCENT, BG_COLOR, 0.55 + _i * 0.15), width=1
    )

ring_outer = hud_canvas.create_oval(0, 0, 0, 0, outline=hud_color, width=2)
ring_inner = hud_canvas.create_oval(0, 0, 0, 0, outline=ACCENT_SOFT, width=1)
hud_dot = hud_canvas.create_oval(0, 0, 0, 0, fill=hud_color, outline="")

_hud_phase = 0.0


def animate_hud():
    global _hud_phase
    _hud_phase += hud_speed
    r1 = _HUD_BASE_R + 6 * math.sin(_hud_phase)
    r2 = _HUD_BASE_R * 0.6 + 4 * math.sin(_hud_phase * 1.3 + 1.0)
    hud_canvas.coords(ring_outer, _HUD_CX - r1, _HUD_CY - r1, _HUD_CX + r1, _HUD_CY + r1)
    hud_canvas.coords(ring_inner, _HUD_CX - r2, _HUD_CY - r2, _HUD_CX + r2, _HUD_CY + r2)
    hud_canvas.coords(hud_dot, _HUD_CX - 3, _HUD_CY - 3, _HUD_CX + 3, _HUD_CY + 3)
    hud_canvas.itemconfig(ring_outer, outline=hud_color)
    hud_canvas.itemconfig(hud_dot, fill=hud_color)
    root.after(40, animate_hud)  # ~25 images/seconde, planifié proprement, pas de boucle bloquante


# --- Infos système ---
main_frame = tk.Frame(root, bg=BG_COLOR)
main_frame.pack(side="left", fill="both", expand=True, padx=24, pady=10)


def create_card(parent, title_text, width=320, height=118):
    cv = tk.Canvas(parent, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
    rounded_rect(cv, 2, 2, width - 2, height - 2, 18, fill=CARD_BG, outline=CARD_BORDER, width=1)
    cv.create_text(18, 20, text=title_text, anchor="nw", font=("Segoe UI Semibold", 11), fill=ACCENT)
    value_id = cv.create_text(18, 48, text="…", anchor="nw", font=("Segoe UI", 14),
                               fill=TEXT_COLOR, width=width - 36)
    return cv, CanvasLabel(cv, value_id)


cpu_frame, cpu_value = create_card(main_frame, "PROCESSEUR")
ram_frame, ram_value = create_card(main_frame, "MÉMOIRE")
disk_frame, disk_value = create_card(main_frame, "DISQUE")
net_frame, net_value = create_card(main_frame, "RÉSEAU")

cpu_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
ram_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
disk_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
net_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)

main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_rowconfigure(1, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_columnconfigure(1, weight=1)

# --- Tableau de bord avancé ---
advanced_frame = tk.Frame(root, bg=BG_COLOR)
advanced_frame.pack(fill="x", padx=24, pady=10)

tk.Label(advanced_frame, text="DIAGNOSTIC AVANCÉ", font=("Segoe UI Semibold", 13), fg=TITLE_COLOR, bg=BG_COLOR).grid(
    row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))


def create_adv_card(parent, title_text, width=480, height=130):
    cv = tk.Canvas(parent, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
    rounded_rect(cv, 2, 2, width - 2, height - 2, 16, fill=CARD_BG, outline=CARD_BORDER, width=1)
    cv.create_text(16, 16, text=title_text, anchor="nw", font=("Segoe UI Semibold", 10), fill=ACCENT)
    value_id = cv.create_text(16, 42, text="…", anchor="nw", font=("Segoe UI", 10),
                               fill=TEXT_COLOR, width=width - 32, justify="left")
    return cv, CanvasLabel(cv, value_id)


gpu_frame, gpu_value = create_adv_card(advanced_frame, "GPU (NVIDIA)")
cpu_adv_frame, cpu_adv_value = create_adv_card(advanced_frame, "DÉTAIL CPU")
power_frame, power_value = create_adv_card(advanced_frame, "ESTIMATION PUISSANCE")
net_adv_frame, net_adv_value = create_adv_card(advanced_frame, "DÉBIT RÉSEAU")
energy_frame, energy_value = create_adv_card(advanced_frame, "SUIVI ÉNERGÉTIQUE", width=976, height=140)

gpu_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
cpu_adv_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=6)
power_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)
net_adv_frame.grid(row=2, column=1, sticky="nsew", padx=8, pady=6)
energy_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=8, pady=6)

advanced_frame.grid_columnconfigure(0, weight=1)
advanced_frame.grid_columnconfigure(1, weight=1)

# =========================================================
# Historique graphique (CPU / RAM)
# =========================================================
HISTORY_LEN = 60
cpu_history = deque(maxlen=HISTORY_LEN)
ram_history = deque(maxlen=HISTORY_LEN)

history_frame = tk.Frame(root, bg=BG_COLOR)
history_frame.pack(fill="x", padx=24, pady=(0, 10))

tk.Label(history_frame, text="HISTORIQUE (60 dernières secondes)", font=("Segoe UI Semibold", 11),
         fg=TITLE_COLOR, bg=BG_COLOR).pack(anchor="w", padx=8)

fig = Figure(figsize=(8, 1.3), dpi=80, facecolor=CARD_BG)
ax = fig.add_subplot(111)
ax.set_facecolor(CARD_BG)
ax.tick_params(colors=TEXT_DIM, labelsize=7)
for spine in ax.spines.values():
    spine.set_color(CARD_BORDER)
line_cpu, = ax.plot([], [], color=ACCENT, label="CPU %")
line_ram, = ax.plot([], [], color=ACCENT_SOFT, label="RAM %")
ax.set_ylim(0, 100)
ax.set_xlim(0, HISTORY_LEN)
legend = ax.legend(loc="upper right", fontsize=7, facecolor=CARD_BG)
for text_ in legend.get_texts():
    text_.set_color(TEXT_DIM)
fig.tight_layout()

history_canvas = FigureCanvasTkAgg(fig, master=history_frame)
history_canvas.get_tk_widget().pack(fill="x", padx=8)


def update_history_graph():
    x = list(range(len(cpu_history)))
    line_cpu.set_data(x, list(cpu_history))
    line_ram.set_data(x, list(ram_history))
    history_canvas.draw_idle()


# --- Status ---
status_label = tk.Label(root, text=f"Jarvis prêt, {USER_NAME}.", font=("Segoe UI", 11), fg=TEXT_DIM, bg=BG_COLOR)
status_label.pack(pady=6)

voice_status_label = tk.Label(root, text=_voice_state["text"], font=("Segoe UI", 9), fg=ACCENT_SOFT, bg=BG_COLOR)
voice_status_label.pack(pady=(0, 6))


def _refresh_voice_status_label():
    voice_status_label.config(text=_voice_state["text"])
    root.after(1500, _refresh_voice_status_label)


_refresh_voice_status_label()


def set_status(text, speak=False):
    status_label.config(text=text)
    if speak:
        jarvis_say(text)


# =========================================================
# Alertes intelligentes
# =========================================================
ALERT_CPU_HIGH = 90
ALERT_RAM_HIGH = 90
ALERT_DISK_HIGH = 90
ALERT_GPU_TEMP_HIGH = 85

_alert_state = {"cpu": False, "ram": False, "disk": False, "gpu_temp": False}


def trigger_alert(key, message):
    set_status(f"Jarvis : {message}", speak=True)
    send_notification("Jarvis - Alerte", message)


def check_alerts(cpu, ram, disk, gpu_temp):
    if cpu > ALERT_CPU_HIGH and not _alert_state["cpu"]:
        _alert_state["cpu"] = True
        trigger_alert("cpu", f"attention {USER_NAME}, le processeur dépasse {ALERT_CPU_HIGH} pourcent.")
    elif cpu < ALERT_CPU_HIGH - 15:
        _alert_state["cpu"] = False

    if ram > ALERT_RAM_HIGH and not _alert_state["ram"]:
        _alert_state["ram"] = True
        trigger_alert("ram", f"attention {USER_NAME}, la mémoire vive dépasse {ALERT_RAM_HIGH} pourcent.")
    elif ram < ALERT_RAM_HIGH - 15:
        _alert_state["ram"] = False

    if disk > ALERT_DISK_HIGH and not _alert_state["disk"]:
        _alert_state["disk"] = True
        trigger_alert("disk", f"attention {USER_NAME}, le disque est presque plein, {disk:.0f} pourcent utilisé.")
    elif disk < ALERT_DISK_HIGH - 5:
        _alert_state["disk"] = False

    if gpu_temp is not None:
        if gpu_temp > ALERT_GPU_TEMP_HIGH and not _alert_state["gpu_temp"]:
            _alert_state["gpu_temp"] = True
            trigger_alert("gpu_temp", f"attention {USER_NAME}, la température du GPU atteint {gpu_temp:.0f} degrés.")
        elif gpu_temp < ALERT_GPU_TEMP_HIGH - 10:
            _alert_state["gpu_temp"] = False


# --- Actions ---
def boost_ram():
    import gc
    gc.collect()
    set_status("Jarvis : optimisation de la mémoire.", speak=True)


def clean_temp():
    set_status("Jarvis : nettoyage des fichiers temporaires…", speak=True)
    temp_dirs = [os.getenv("TEMP"), os.getenv("TMP"), r"C:\Windows\Temp"]
    for d in temp_dirs:
        if d and os.path.exists(d):
            for item in os.listdir(d):
                path = os.path.join(d, item)
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass
    set_status("Jarvis : nettoyage terminé.", speak=True)


# =========================================================
# Nettoyage avancé : gros fichiers, doublons, apps au démarrage.
# Le scan tourne toujours dans un thread séparé (jamais sur le thread
# Tkinter), et les fichiers sont envoyés à la corbeille (send2trash)
# quand c'est disponible plutôt que supprimés définitivement.
# =========================================================
def _scan_dirs():
    home = os.path.expanduser("~")
    candidates = ["Downloads", "Téléchargements", "Documents", "Desktop", "Bureau", "Pictures", "Videos", "Music"]
    seen = set()
    dirs = []
    for c in candidates:
        p = os.path.join(home, c)
        if os.path.isdir(p) and p not in seen:
            seen.add(p)
            dirs.append(p)
    return dirs


def find_large_files(threshold_mb=200, progress_cb=None):
    threshold_bytes = threshold_mb * 1024 * 1024
    results = []
    for base in _scan_dirs():
        for root_dir, _dirs, files in os.walk(base):
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size >= threshold_bytes:
                    results.append((fpath, size))
        if progress_cb:
            progress_cb(base)
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _partial_hash(path, chunk=8192):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read(chunk)).hexdigest()
    except Exception:
        return None


def _full_hash(path):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def find_duplicates(progress_cb=None):
    size_map = {}
    for base in _scan_dirs():
        for root_dir, _dirs, files in os.walk(base):
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size == 0:
                    continue
                size_map.setdefault(size, []).append(fpath)
        if progress_cb:
            progress_cb(base)

    dup_groups = []
    for _size, paths in size_map.items():
        if len(paths) < 2:
            continue
        partial_map = {}
        for p in paths:
            h = _partial_hash(p)
            if h is not None:
                partial_map.setdefault(h, []).append(p)
        for _h, plist in partial_map.items():
            if len(plist) < 2:
                continue
            full_map = {}
            for p in plist:
                fh = _full_hash(p)
                if fh is not None:
                    full_map.setdefault(fh, []).append(p)
            for _fh, flist in full_map.items():
                if len(flist) >= 2:
                    dup_groups.append(flist)
    return dup_groups


def delete_files_safely(paths):
    deleted = 0
    for p in paths:
        try:
            if _SEND2TRASH_AVAILABLE:
                send2trash.send2trash(p)
            else:
                os.remove(p)
            deleted += 1
        except Exception:
            pass
    return deleted


# --- Apps au démarrage (registre Run HKCU/HKLM + dossier Démarrage) ---
_DISABLED_STARTUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_disabled_startup.json")


def _load_disabled_startup():
    if os.path.exists(_DISABLED_STARTUP_FILE):
        try:
            with open(_DISABLED_STARTUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_disabled_startup(data):
    try:
        with open(_DISABLED_STARTUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def list_startup_registry_apps():
    apps = []
    if not _WINREG_AVAILABLE:
        return apps
    for hive, hive_name in [(winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")]:
        try:
            with winreg.OpenKey(hive, _STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _t = winreg.EnumValue(key, i)
                        if name != _STARTUP_VALUE_NAME:
                            apps.append({"source": hive_name, "name": name, "command": value, "enabled": True})
                        i += 1
                    except OSError:
                        break
        except Exception:
            continue
    disabled = _load_disabled_startup()
    for name, info in disabled.items():
        apps.append({"source": info.get("source", "HKCU"), "name": name,
                     "command": info.get("command", ""), "enabled": False})
    return apps


def disable_startup_app(hive_name, name, command):
    if not _WINREG_AVAILABLE:
        return False
    hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        with winreg.OpenKey(hive, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        disabled = _load_disabled_startup()
        disabled[name] = {"source": hive_name, "command": command}
        _save_disabled_startup(disabled)
        return True
    except Exception:
        return False


def enable_startup_app(name):
    disabled = _load_disabled_startup()
    info = disabled.get(name)
    if not info or not _WINREG_AVAILABLE:
        return False
    hive = winreg.HKEY_CURRENT_USER if info.get("source") == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        with winreg.OpenKey(hive, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, info.get("command", ""))
        del disabled[name]
        _save_disabled_startup(disabled)
        return True
    except Exception:
        return False


# --- Fenêtres d'affichage (Treeview stylé pour rester dans l'ambiance Jarvis) ---
def open_large_files_window():
    win = tk.Toplevel(root)
    win.title("Jarvis — Gros fichiers")
    win.configure(bg=BG_COLOR)
    win.geometry("760x480")

    info_label = tk.Label(win, text="Analyse en cours…", font=("Segoe UI", 11), fg=TEXT_COLOR, bg=BG_COLOR)
    info_label.pack(pady=8)

    tree = ttk.Treeview(win, columns=("path", "size"), show="headings", style="Jarvis.Treeview", height=16)
    tree.heading("path", text="Fichier")
    tree.heading("size", text="Taille")
    tree.column("path", width=580)
    tree.column("size", width=120, anchor="e")
    tree.pack(fill="both", expand=True, padx=12, pady=6)

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=8)

    def do_delete():
        selected = tree.selection()
        if not selected:
            return
        paths = [tree.item(iid, "values")[0] for iid in selected]
        if not messagebox.askyesno("Confirmer", f"Supprimer {len(paths)} fichier(s) ?", parent=win):
            return
        deleted = delete_files_safely(paths)
        for iid in selected:
            tree.delete(iid)
        set_status(f"Jarvis : {deleted} fichier(s) supprimé(s).", speak=True)

    label_suffix = "" if _SEND2TRASH_AVAILABLE else " (définitif — installe 'send2trash' pour la corbeille)"
    tk.Button(btn_frame, text="TOUT SÉLECTIONNER", command=lambda: tree.selection_set(tree.get_children()),
              **btn_style).pack(side="left", padx=6)
    tk.Button(btn_frame, text="SUPPRIMER LA SÉLECTION" + label_suffix, command=do_delete, **btn_style).pack(side="left", padx=6)

    def scan():
        def progress(base):
            info_label.config(text=f"Analyse : {base}…")
        results = find_large_files(threshold_mb=200, progress_cb=lambda b: root.after(0, progress, b))

        def populate():
            info_label.config(text=f"{len(results)} fichier(s) de plus de 200 Mo trouvés.")
            for path, size in results:
                tree.insert("", "end", values=(path, f"{size / (1024 * 1024):.1f} Mo"))
        root.after(0, populate)

    threading.Thread(target=scan, daemon=True).start()


def open_duplicates_window():
    win = tk.Toplevel(root)
    win.title("Jarvis — Doublons")
    win.configure(bg=BG_COLOR)
    win.geometry("760x480")

    info_label = tk.Label(win, text="Analyse en cours…", font=("Segoe UI", 11), fg=TEXT_COLOR, bg=BG_COLOR)
    info_label.pack(pady=8)

    tree = ttk.Treeview(win, columns=("path", "size"), show="tree headings", style="Jarvis.Treeview", height=16)
    tree.heading("#0", text="Groupe")
    tree.heading("path", text="Fichier")
    tree.heading("size", text="Taille")
    tree.column("#0", width=90)
    tree.column("path", width=500)
    tree.column("size", width=100, anchor="e")
    tree.pack(fill="both", expand=True, padx=12, pady=6)

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=8)

    def do_delete():
        selected = [iid for iid in tree.selection() if tree.parent(iid)]
        if not selected:
            return
        paths = [tree.item(iid, "values")[0] for iid in selected]
        if not messagebox.askyesno("Confirmer", f"Supprimer {len(paths)} fichier(s) en double ?", parent=win):
            return
        deleted = delete_files_safely(paths)
        for iid in selected:
            tree.delete(iid)
        set_status(f"Jarvis : {deleted} doublon(s) supprimé(s).", speak=True)

    def select_all_dupes():
        to_select = []
        for parent_iid in tree.get_children():
            children = tree.get_children(parent_iid)
            to_select.extend(children[1:])  # on garde le 1er de chaque groupe
        tree.selection_set(to_select)

    tk.Button(btn_frame, text="TOUT SÉLECTIONNER (sauf le 1er de chaque groupe)",
              command=select_all_dupes, **btn_style).pack(side="left", padx=6)
    tk.Button(btn_frame, text="SUPPRIMER LA SÉLECTION (garde le 1er de chaque groupe)",
              command=do_delete, **btn_style).pack(side="left", padx=6)

    def scan():
        def progress(base):
            info_label.config(text=f"Analyse : {base}…")
        groups = find_duplicates(progress_cb=lambda b: root.after(0, progress, b))

        def populate():
            total_dupes = sum(len(g) - 1 for g in groups)
            info_label.config(text=f"{len(groups)} groupe(s) de doublons — {total_dupes} fichier(s) redondant(s).")
            for i, group in enumerate(groups, 1):
                parent = tree.insert("", "end", text=f"Groupe {i}", open=False)
                for p in group:
                    try:
                        size = os.path.getsize(p)
                    except OSError:
                        size = 0
                    tree.insert(parent, "end", values=(p, f"{size / (1024 * 1024):.1f} Mo"))
        root.after(0, populate)

    threading.Thread(target=scan, daemon=True).start()


def open_startup_manager_window():
    win = tk.Toplevel(root)
    win.title("Jarvis — Applications au démarrage")
    win.configure(bg=BG_COLOR)
    win.geometry("700x420")

    if not _WINREG_AVAILABLE:
        tk.Label(win, text="Fonctionnalité disponible uniquement sur Windows.",
                 font=("Segoe UI", 11), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=20)
        return

    tree = ttk.Treeview(win, columns=("source", "name", "state"), show="headings",
                         style="Jarvis.Treeview", height=14)
    tree.heading("source", text="Origine")
    tree.heading("name", text="Application")
    tree.heading("state", text="État")
    tree.column("source", width=80, anchor="center")
    tree.column("name", width=420)
    tree.column("state", width=100, anchor="center")
    tree.pack(fill="both", expand=True, padx=12, pady=10)

    apps_by_iid = {}

    def refresh():
        tree.delete(*tree.get_children())
        apps_by_iid.clear()
        for app in list_startup_registry_apps():
            iid = tree.insert("", "end", values=(app["source"], app["name"],
                                                  "Activé" if app["enabled"] else "Désactivé"))
            apps_by_iid[iid] = app

    def do_toggle():
        selected = tree.selection()
        if not selected:
            return
        for iid in selected:
            app = apps_by_iid.get(iid)
            if not app:
                continue
            if app["enabled"]:
                ok = disable_startup_app(app["source"], app["name"], app["command"])
            else:
                ok = enable_startup_app(app["name"])
            if not ok:
                messagebox.showwarning(
                    "Jarvis",
                    f"Impossible de modifier {app['name']} (droits administrateur requis pour HKLM ?)",
                    parent=win
                )
        refresh()

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=8)
    tk.Button(btn_frame, text="ACTIVER / DÉSACTIVER LA SÉLECTION", command=do_toggle, **btn_style).pack(side="left", padx=6)
    tk.Button(btn_frame, text="ACTUALISER", command=refresh, **btn_style).pack(side="left", padx=6)

    refresh()


# =========================================================
# Modes — chaque mode a maintenant une fonction "toggle" (pour les boutons,
# actionnée une fois par un clic humain) ET s'appuie sur un état explicite
# que le mode Auto peut lire/forcer sans re-déclencher sans arrêt les
# actions système (c'est ce qui faisait ramer le PC avant).
# =========================================================
gaming_mode = False
performance_mode = False
stealth_mode = False
turbo_mode = False
auto_mode = False


def _set_hud_for_mode():
    global hud_color, hud_speed
    if turbo_mode:
        hud_color, hud_speed = "#e0703c", 0.09
    elif gaming_mode:
        hud_color, hud_speed = "#c94f6d", 0.08
    elif performance_mode:
        hud_color, hud_speed = "#7cc48a", 0.06
    elif stealth_mode:
        hud_color, hud_speed = "#6b7280", 0.03
    else:
        hud_color, hud_speed = ACCENT, 0.05


def mode_gaming():
    global gaming_mode
    gaming_mode = not gaming_mode
    _set_hud_for_mode()

    if gaming_mode:
        set_power_plan("high_performance")
        lower_background_processes(limit=8)
        boosted_name = boost_foreground_process()
        if boosted_name:
            set_status(f"Jarvis : mode Gaming activé, priorité augmentée pour {boosted_name}.", speak=True)
        elif not _WIN32_AVAILABLE:
            set_status("Jarvis : mode Gaming activé (installe pywin32 pour booster le jeu actif).", speak=True)
        else:
            set_status("Jarvis : mode Gaming activé.", speak=True)
    else:
        restore_foreground_process()
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Gaming désactivé.", speak=True)


def mode_performance():
    global performance_mode
    performance_mode = not performance_mode
    _set_hud_for_mode()

    if performance_mode:
        set_power_plan("high_performance")
        lower_background_processes(limit=5)
        boost_ram()
        set_status("Jarvis : mode Performance activé.", speak=True)
    else:
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Performance désactivé.", speak=True)


def mode_stealth():
    global stealth_mode
    stealth_mode = not stealth_mode
    _set_hud_for_mode()

    if stealth_mode:
        set_power_plan("power_saver")
        lower_background_processes(limit=10)
        set_status("Jarvis : mode Discret activé, consommation réduite au minimum.", speak=True)
    else:
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Discret désactivé.", speak=True)


def mode_turbo():
    global turbo_mode
    turbo_mode = not turbo_mode
    _set_hud_for_mode()

    if turbo_mode:
        set_power_plan("high_performance")
        lower_background_processes(limit=10)
        clean_temp()
        boost_ram()
        flush_dns()
        set_status("Jarvis : mode Turbo activé.", speak=True)
    else:
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Turbo désactivé.", speak=True)


def mode_auto():
    global auto_mode
    auto_mode = not auto_mode
    set_status("Jarvis : mode Auto activé." if auto_mode else "Jarvis : mode Auto désactivé.", speak=True)


def _current_manual_mode():
    if gaming_mode:
        return "gaming"
    if performance_mode:
        return "performance"
    if stealth_mode:
        return "stealth"
    return "normal"


def apply_mode_state(target):
    """Met le système dans l'état voulu — ne fait rien si on y est déjà,
    ce qui évite de re-changer le plan d'alimentation et les priorités
    des processus à chaque cycle du mode Auto."""
    current = _current_manual_mode()
    if current == target:
        return
    if gaming_mode:
        mode_gaming()
    if performance_mode:
        mode_performance()
    if stealth_mode:
        mode_stealth()
    if target == "gaming":
        mode_gaming()
    elif target == "performance":
        mode_performance()
    elif target == "stealth":
        mode_stealth()


def auto_analyze():
    while True:
        if auto_mode:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent

            if disk > 90:
                clean_temp()

            if cpu > 75 or ram > 85:
                apply_mode_state("performance")
            elif cpu < 25 and ram < 45:
                apply_mode_state("stealth")
            else:
                apply_mode_state("normal")

        time.sleep(5)


# =========================================================
# Commandes vocales
# =========================================================
voice_mode_enabled = False
voice_button = None


def process_voice_command(text):
    text = text.lower()
    set_status(f"Jarvis : commande reçue -> {text}")

    if "turbo" in text:
        mode_turbo()
    elif "performance" in text:
        mode_performance()
    elif "stealth" in text or "furtif" in text or "discret" in text:
        mode_stealth()
    elif "gaming" in text or "jeu" in text:
        mode_gaming()
    elif "auto" in text:
        mode_auto()
    elif "nettoie" in text or "nettoyage" in text:
        clean_temp()
    elif "mémoire" in text or "ram" in text:
        boost_ram()
    else:
        set_status("Jarvis : commande non reconnue.", speak=True)


def toggle_voice():
    global voice_mode_enabled
    if not _VOICE_AVAILABLE:
        set_status("Jarvis : module vocal non installé (SpeechRecognition/pyaudio).", speak=True)
        return
    voice_mode_enabled = not voice_mode_enabled
    if voice_button:
        voice_button.config(text="VOIX : ACTIVE" if voice_mode_enabled else "VOIX : COUPÉE")
    set_status("Jarvis : écoute vocale activée." if voice_mode_enabled else "Jarvis : écoute vocale désactivée.", speak=True)


def voice_listener():
    if not _VOICE_AVAILABLE:
        return
    recognizer = sr.Recognizer()
    try:
        mic = sr.Microphone()
    except Exception:
        return

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
    except Exception:
        pass

    while True:
        if not voice_mode_enabled:
            time.sleep(1)
            continue
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio, language="fr-FR")
            process_voice_command(text)
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception:
            time.sleep(2)


# --- Boutons ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip, text=self.text, justify="left",
                          bg=CARD_BG, fg=TEXT_COLOR, font=("Segoe UI", 9),
                          highlightbackground=CARD_BORDER, highlightthickness=1, padx=8, pady=4,
                          wraplength=260)
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


button_frame = tk.Frame(root, bg=BG_COLOR)
button_frame.pack(pady=10)

BTN_COLOR = ACCENT
BTN_HOVER_COLOR = "#f0c07e"

btn_style = {
    "font": ("Segoe UI Semibold", 11),
    "bg": BTN_COLOR,
    "fg": "#1c1408",
    "activebackground": "#c98f43",
    "activeforeground": "#1c1408",
    "bd": 0,
    "padx": 12,
    "pady": 6,
    "cursor": "hand2",
}

buttons = [
    ("LIBÉRER MÉMOIRE", boost_ram, "Libère la mémoire utilisée par Jarvis lui-même."),
    ("NETTOYER TEMP", clean_temp, "Supprime les fichiers temporaires de Windows pour libérer de l'espace disque."),
    ("GAMING", mode_gaming, "Performances élevées + priorité pour le jeu/programme actif au premier plan."),
    ("PERFORMANCE", mode_performance, "Performances élevées et priorité réduite pour les tâches en arrière-plan."),
    ("DISCRET", mode_stealth, "Économie d'énergie et activité réduite en arrière-plan."),
    ("TURBO", mode_turbo, "Performance + nettoyage + vidage du cache DNS."),
    ("AUTO", mode_auto, "Jarvis choisit le mode adapté selon l'usage du CPU/RAM/disque (sans le changer sans arrêt)."),
    ("VOIX : COUPÉE", toggle_voice, "Active l'écoute vocale : dis 'turbo', 'gaming', 'nettoie'…"),
    ("DÉMARRAGE AUTO : OFF", toggle_startup, "Lance Jarvis automatiquement à l'ouverture de session Windows."),
    ("GROS FICHIERS", open_large_files_window, "Cherche les fichiers de plus de 200 Mo dans Téléchargements/Documents/Bureau/Images/Vidéos/Musique."),
    ("DOUBLONS", open_duplicates_window, "Trouve les fichiers en double (même contenu) dans les mêmes dossiers."),
    ("APPS DÉMARRAGE", open_startup_manager_window, "Active/désactive les programmes qui se lancent avec Windows."),
    ("VÉRIFIER MISE À JOUR", check_for_update_button, f"Version actuelle : {JARVIS_VERSION}. Vérifie si une nouvelle version est disponible et l'installe."),
]

for i, (txt, cmd, tip_text) in enumerate(buttons):
    b = tk.Button(button_frame, text=txt, command=cmd, **btn_style)
    b.grid(row=i // 4, column=i % 4, padx=8, pady=6)
    b.bind("<Enter>", lambda e, btn=b: btn.config(bg=BTN_HOVER_COLOR))
    b.bind("<Leave>", lambda e, btn=b: btn.config(bg=BTN_COLOR))
    Tooltip(b, tip_text)
    if txt.startswith("VOIX"):
        voice_button = b
    if txt.startswith("DÉMARRAGE AUTO"):
        startup_button = b

_refresh_startup_button()

# --- GPU NVIDIA ---
_nvidia_available = True
_last_gpu_text = "GPU : lecture en cours…"
_last_gpu_power = 0.0
_last_gpu_temp = None


def get_nvidia_stats():
    global _nvidia_available
    if not _nvidia_available:
        return "GPU NVIDIA : non détecté.", 0.0, None

    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,power.limit",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.check_output(cmd, encoding="utf-8", **_SUBPROCESS_KWARGS)
        parts = [p.strip() for p in result.split(",")]
        if len(parts) >= 7:
            gpu_util, mem_util, mem_used, mem_total, temp, power_draw, power_limit = parts[:7]
            text = (
                f"Utilisation : {gpu_util} %  |  Mémoire : {mem_util} %\n"
                f"VRAM : {mem_used}/{mem_total} MiB\n"
                f"Température : {temp} °C  |  Puissance : {power_draw}/{power_limit} W"
            )
            return text, float(power_draw), float(temp)
    except FileNotFoundError:
        _nvidia_available = False
    except Exception:
        pass

    return "GPU NVIDIA : données indisponibles.", 0.0, None


def estimate_cpu_power(cpu_percent):
    tdp_cpu = 65.0
    return tdp_cpu * (cpu_percent / 100.0)


# =========================================================
# Boucle de stats — le nvidia-smi (lancement de process externe) est
# coûteux : on ne l'interroge plus que toutes les 3 secondes au lieu
# de chaque seconde.
# =========================================================
_last_energy_save = time.time()
_stats_loop_count = 0
_GPU_POLL_EVERY_N = 3


def update_stats():
    global total_energy_wh, hour_energy_wh, day_energy_wh, week_energy_wh, month_energy_wh
    global last_hour, last_day, last_week, last_month, _last_energy_save
    global _last_gpu_text, _last_gpu_power, _last_gpu_temp, _stats_loop_count

    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    while True:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        net = psutil.net_io_counters()
        net_text = f"Envoyé : {net.bytes_sent // 1024} Ko  |  Reçu : {net.bytes_recv // 1024} Ko"

        cpu_value.config(text=f"{cpu} %")
        ram_value.config(text=f"{ram} %")
        disk_value.config(text=f"{disk} %")
        net_value.config(text=net_text)

        cpu_history.append(cpu)
        ram_history.append(ram)
        root.after(0, update_history_graph)

        _stats_loop_count += 1
        if _stats_loop_count % _GPU_POLL_EVERY_N == 0 or _stats_loop_count == 1:
            _last_gpu_text, _last_gpu_power, _last_gpu_temp = get_nvidia_stats()
        gpu_value.config(text=_last_gpu_text)

        check_alerts(cpu, ram, disk, _last_gpu_temp)

        freq = psutil.cpu_freq()
        freq_text = f"{freq.current:.0f} MHz (max {freq.max:.0f} MHz)" if freq else "Fréquence : N/A"
        per_core = psutil.cpu_percent(percpu=True)
        cores_text = "Par cœur : " + " | ".join(f"{p:.0f}%" for p in per_core)

        cpu_power = estimate_cpu_power(cpu)
        cpu_adv_value.config(
            text=f"{freq_text}\n{cores_text}\nPuissance estimée CPU : {cpu_power:.1f} W"
        )

        total_power = cpu_power + _last_gpu_power
        power_value.config(
            text=f"CPU : {cpu_power:.1f} W   GPU : {_last_gpu_power:.1f} W\nTotal estimé : {total_power:.1f} W"
        )

        now_time = time.time()
        dt = now_time - prev_time
        if dt <= 0:
            dt = 1

        sent_diff = net.bytes_sent - prev_net.bytes_sent
        recv_diff = net.bytes_recv - prev_net.bytes_recv
        up_speed = sent_diff / dt / 1024
        down_speed = recv_diff / dt / 1024
        net_adv_value.config(text=f"Envoi : {up_speed:.1f} Ko/s\nRéception : {down_speed:.1f} Ko/s")

        prev_net = net
        prev_time = now_time

        # --- Energy tracking ---
        now = datetime.datetime.now()
        energy_wh = total_power / 3600.0

        total_energy_wh += energy_wh
        hour_energy_wh += energy_wh
        day_energy_wh += energy_wh
        week_energy_wh += energy_wh
        month_energy_wh += energy_wh

        if now.hour != last_hour:
            hour_energy_wh = 0.0
            last_hour = now.hour
        if now.day != last_day:
            day_energy_wh = 0.0
            last_day = now.day
        if now.isocalendar()[1] != last_week:
            week_energy_wh = 0.0
            last_week = now.isocalendar()[1]
        if now.month != last_month:
            month_energy_wh = 0.0
            last_month = now.month

        cost_total = (total_energy_wh / 1000.0) * price_per_kwh
        cost_day = (day_energy_wh / 1000.0) * price_per_kwh

        bars = int(min(total_power / 10, 20))
        graph = "█" * bars + "░" * (20 - bars)

        energy_value.config(
            text=(
                f"Puissance actuelle : {total_power:.1f} W\n"
                f"Heure : {hour_energy_wh/1000:.4f} kWh   Jour : {day_energy_wh/1000:.4f} kWh\n"
                f"Semaine : {week_energy_wh/1000:.4f} kWh   Mois : {month_energy_wh/1000:.4f} kWh\n"
                f"Coût aujourd'hui : {cost_day:.3f} €   Coût total : {cost_total:.3f} €\n"
                f"[{graph}]"
            )
        )

        if now_time - _last_energy_save > 30:
            save_energy_data()
            _last_energy_save = now_time

        time.sleep(1)


def on_close():
    if _TRAY_AVAILABLE:
        save_energy_data()
        hide_window()
    else:
        save_energy_data()
        restore_foreground_process()
        restore_lowered_processes()
        set_power_plan("balanced")
        root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

# =========================================================
# Intro — construite avec root.after (planification non-bloquante)
# plutôt qu'un thread qui boucle avec time.sleep + canvas.update(),
# ce qui évite tout appel Tkinter depuis un thread secondaire.
# =========================================================
_intro_already_shown = False


def jarvis_intro():
    global _intro_already_shown
    if _intro_already_shown:
        return
    _intro_already_shown = True

    intro = tk.Toplevel(root)
    intro.config(bg=BG_COLOR)
    intro.attributes("-fullscreen", True)
    intro.attributes("-topmost", True)

    canvas_i = tk.Canvas(intro, bg=BG_COLOR, highlightthickness=0)
    canvas_i.pack(fill="both", expand=True)

    w = intro.winfo_screenwidth()
    h = intro.winfo_screenheight()
    cx, cy = w // 2, h // 2

    # Halo de fond, dessiné une seule fois (statique, aucun coût continu).
    for i, rad in enumerate([300, 260, 220, 185]):
        canvas_i.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                              outline=_blend(ACCENT, BG_COLOR, 0.6 + i * 0.1), width=1)

    arc_outer = canvas_i.create_arc(cx - 170, cy - 170, cx + 170, cy + 170,
                                     start=0, extent=80, style="arc", outline=ACCENT, width=3)
    arc_inner = canvas_i.create_arc(cx - 120, cy - 120, cx + 120, cy + 120,
                                     start=180, extent=80, style="arc", outline=ACCENT_SOFT, width=2)
    ring_shock = canvas_i.create_oval(cx, cy, cx, cy, outline=ACCENT, width=2)

    # Particules disposées en cercle, qui convergent vers le centre.
    particles = []
    n_particles = 20
    for i in range(n_particles):
        angle = math.radians(i * (360 / n_particles))
        px, py = cx + 320 * math.cos(angle), cy + 320 * math.sin(angle)
        pid = canvas_i.create_oval(px - 2, py - 2, px + 2, py + 2, fill=ACCENT, outline="")
        particles.append((pid, px, py))

    text_title = canvas_i.create_text(cx, cy - 230, text="", font=("Segoe UI Semibold", 34), fill=TITLE_COLOR)
    text_log = canvas_i.create_text(cx, cy - 185, text="", font=("Segoe UI", 13), fill=ACCENT_SOFT)
    text_greet = canvas_i.create_text(cx, cy + 230, text="", font=("Segoe UI", 19), fill=TEXT_COLOR)

    full_text = "JARVIS"
    boot_lines = [
        "Calibrage des capteurs système…",
        "Analyse du processeur et de la mémoire…",
        "Synchronisation des modules…",
    ]
    state = {"char": 0, "spin": 0, "frame": 0, "boot_i": 0}

    def spin_step():
        state["spin"] = (state["spin"] + 7) % 360
        canvas_i.itemconfig(arc_outer, start=state["spin"])
        canvas_i.itemconfig(arc_inner, start=(360 - state["spin"] * 1.3) % 360)

    def converge_step():
        state["frame"] += 1
        t = min(state["frame"] / 45, 1.0)
        ease = 1 - (1 - t) ** 3  # décélération douce vers le centre
        for pid, px, py in particles:
            nx = px + (cx - px) * ease
            ny = py + (cy - py) * ease
            canvas_i.coords(pid, nx - 2, ny - 2, nx + 2, ny + 2)
        spin_step()
        if t < 1.0:
            intro.after(25, converge_step)
        else:
            for pid, _px, _py in particles:
                canvas_i.delete(pid)
            intro.after(100, type_step)

    def cycle_boot_log():
        if state["boot_i"] < len(boot_lines):
            canvas_i.itemconfig(text_log, text=boot_lines[state["boot_i"]])
            state["boot_i"] += 1
            intro.after(430, cycle_boot_log)

    def type_step():
        state["char"] += 1
        canvas_i.itemconfig(text_title, text=full_text[:state["char"]])
        spin_step()
        if state["char"] < len(full_text):
            intro.after(130, type_step)
        else:
            intro.after(400, settle)

    def settle():
        canvas_i.itemconfig(text_log, text="")
        canvas_i.itemconfig(text_greet, text=get_greeting())
        jarvis_say(get_greeting())
        shockwave_step()

    def shockwave_step(r=0):
        r += 26
        canvas_i.coords(ring_shock, cx - r, cy - r, cx + r, cy + r)
        fade = max(0.0, 1 - r / 260)
        canvas_i.itemconfig(ring_shock, outline=_blend(BG_COLOR, ACCENT, fade))
        if r < 260:
            intro.after(20, lambda: shockwave_step(r))
        else:
            intro.after(1300, lambda: fade_out(10))

    def fade_out(steps_left):
        t = steps_left / 10
        canvas_i.itemconfig(text_title, fill=_blend(BG_COLOR, TITLE_COLOR, t))
        canvas_i.itemconfig(text_greet, fill=_blend(BG_COLOR, TEXT_COLOR, t))
        col_accent = _blend(BG_COLOR, ACCENT, t)
        canvas_i.itemconfig(arc_outer, outline=col_accent)
        canvas_i.itemconfig(arc_inner, outline=col_accent)
        if steps_left > 0:
            intro.after(45, lambda: fade_out(steps_left - 1))
        else:
            intro.destroy()

    cycle_boot_log()
    converge_step()


# --- Démarrage des threads (uniquement pour du travail non-Tkinter) ---
threading.Thread(target=update_stats, daemon=True).start()
threading.Thread(target=auto_analyze, daemon=True).start()
threading.Thread(target=voice_listener, daemon=True).start()

animate_hud()  # animation du HUD sur le thread principal via root.after

set_status(f"Jarvis : système opérationnel, {USER_NAME}.")
root.after(500, jarvis_intro)

if _TRAY_AVAILABLE:
    start_tray_icon()

root.after(5000, lambda: check_for_update(silent=True))

root.mainloop()




















import queue
import os
import json
import shutil
import subprocess
import datetime
import math
import tempfile
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from plyer import notification as plyer_notification
    _NOTIFY_AVAILABLE = True
except ImportError:
    plyer_notification = None
    _NOTIFY_AVAILABLE = False

try:
    import speech_recognition as sr
    _VOICE_AVAILABLE = True
except ImportError:
    sr = None
    _VOICE_AVAILABLE = False

import sys
import hashlib
from tkinter import ttk, messagebox

try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_AVAILABLE = True
except ImportError:
    pystray = None
    _TRAY_AVAILABLE = False

try:
    import send2trash
    _SEND2TRASH_AVAILABLE = True
except ImportError:
    send2trash = None
    _SEND2TRASH_AVAILABLE = False

try:
    import winreg
    _WINREG_AVAILABLE = os.name == "nt"
except ImportError:
    winreg = None
    _WINREG_AVAILABLE = False

# =========================================================
# Voix naturelle : edge-tts (voix neuronale) avec repli sur pyttsx3
# =========================================================
try:
    import edge_tts
    import asyncio
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    _EDGE_TTS_AVAILABLE = False

try:
    import pygame
    pygame.mixer.init()
    _PYGAME_AVAILABLE = True
except Exception:
    _PYGAME_AVAILABLE = False

try:
    from playsound import playsound as _playsound
    _PLAYSOUND_AVAILABLE = True
except ImportError:
    _playsound = None
    _PLAYSOUND_AVAILABLE = False

import pyttsx3
_pyttsx3_engine = pyttsx3.init()
_pyttsx3_engine.setProperty('rate', 178)

# Voix masculine française neuronale, chaude et naturelle (edge-tts)
EDGE_VOICE = "fr-FR-HenriNeural"
_VOICE_TMP_PATH = os.path.join(tempfile.gettempdir(), "jarvis_voice.mp3")

# --- Variables HUD ---
hud_speed = 0.05          # vitesse de "respiration" du HUD (radians/frame)
hud_color = "#e0a85c"

# --- Energy tracking ---
total_energy_wh = 0.0
hour_energy_wh = 0.0
day_energy_wh = 0.0
week_energy_wh = 0.0
month_energy_wh = 0.0

last_hour = datetime.datetime.now().hour
last_day = datetime.datetime.now().day
last_week = datetime.datetime.now().isocalendar()[1]
last_month = datetime.datetime.now().month

price_per_kwh = 0.25  # euros par kWh

ENERGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_energy_data.json")


def load_energy_data():
    global total_energy_wh, hour_energy_wh, day_energy_wh, week_energy_wh, month_energy_wh
    global last_hour, last_day, last_week, last_month

    if not os.path.exists(ENERGY_FILE):
        return
    try:
        with open(ENERGY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    now = datetime.datetime.now()
    total_energy_wh = data.get("total_energy_wh", 0.0)
    hour_energy_wh = data.get("hour_energy_wh", 0.0) if data.get("last_hour") == now.hour else 0.0
    day_energy_wh = data.get("day_energy_wh", 0.0) if data.get("last_day") == now.day else 0.0
    week_energy_wh = data.get("week_energy_wh", 0.0) if data.get("last_week") == now.isocalendar()[1] else 0.0
    month_energy_wh = data.get("month_energy_wh", 0.0) if data.get("last_month") == now.month else 0.0


def save_energy_data():
    data = {
        "total_energy_wh": total_energy_wh,
        "hour_energy_wh": hour_energy_wh,
        "day_energy_wh": day_energy_wh,
        "week_energy_wh": week_energy_wh,
        "month_energy_wh": month_energy_wh,
        "last_hour": last_hour,
        "last_day": last_day,
        "last_week": last_week,
        "last_month": last_month,
    }
    try:
        with open(ENERGY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


load_energy_data()

# =========================================================
# Config personnalisée (prénom de l'utilisateur, demandé une seule fois)
# =========================================================
from tkinter import simpledialog

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


_config = load_config()
USER_NAME = _config.get("user_name")

# --- Fenêtre principale ---
root = tk.Tk()
root.withdraw()

if not USER_NAME:
    USER_NAME = simpledialog.askstring(
        "Bienvenue",
        "Quel est ton prénom ?",
        parent=root
    ) or "Ami"
    _config["user_name"] = USER_NAME
    save_config(_config)


def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return f"Bonjour {USER_NAME}."
    elif 12 <= hour < 18:
        return f"Bon après-midi {USER_NAME}."
    elif 18 <= hour < 23:
        return f"Bonsoir {USER_NAME}."
    else:
        return f"Bonne nuit {USER_NAME}."


root.deiconify()
root.title(f"Jarvis — {USER_NAME}")
root.geometry("1050x900")
root.minsize(900, 700)
try:
    root.state("zoomed")
except tk.TclError:
    pass

# =========================================================
# Palette : ardoise chaude + or doux, plus sobre que le style "hacker cyan"
# =========================================================
BG_COLOR = "#14161f"
CARD_BG = "#1c2030"
CARD_BORDER = "#2a2f45"
ACCENT = "#e0a85c"       # or doux
ACCENT_SOFT = "#7c8aa8"  # bleu-gris discret
TEXT_COLOR = "#c9ccd6"
TEXT_DIM = "#7f8496"
TITLE_COLOR = "#f0d9b5"

root.config(bg=BG_COLOR)

_ttk_style = ttk.Style()
try:
    _ttk_style.theme_use("clam")
except tk.TclError:
    pass
_ttk_style.configure("Jarvis.Treeview", background=CARD_BG, fieldbackground=CARD_BG,
                      foreground=TEXT_COLOR, borderwidth=0, rowheight=24)
_ttk_style.configure("Jarvis.Treeview.Heading", background=CARD_BORDER, foreground=TITLE_COLOR,
                      relief="flat")
_ttk_style.map("Jarvis.Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#1c1408")])

# =========================================================
# Voix (thread-safe via une queue + un seul worker)
# =========================================================
speech_queue = queue.Queue()


def _speak_with_pyttsx3(text):
    try:
        _pyttsx3_engine.say(text)
        _pyttsx3_engine.runAndWait()
    except Exception:
        pass


def _speak_with_edge(text):
    async def _run():
        communicate = edge_tts.Communicate(text, EDGE_VOICE)
        await communicate.save(_VOICE_TMP_PATH)

    asyncio.run(_run())
    if _PYGAME_AVAILABLE:
        pygame.mixer.music.load(_VOICE_TMP_PATH)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    elif _PLAYSOUND_AVAILABLE:
        _playsound(_VOICE_TMP_PATH)
    elif os.name == "nt":
        os.startfile(_VOICE_TMP_PATH)
    else:
        raise RuntimeError("Aucun lecteur audio disponible")


def _speech_worker():
    while True:
        text = speech_queue.get()
        if text is None:
            continue
        spoken = False
        if _EDGE_TTS_AVAILABLE:
            try:
                _speak_with_edge(text)
                spoken = True
            except Exception:
                spoken = False
        if not spoken:
            _speak_with_pyttsx3(text)
        speech_queue.task_done()


threading.Thread(target=_speech_worker, daemon=True).start()


def jarvis_say(text):
    speech_queue.put(text)


# --- Diagnostic du moteur vocal : dit clairement quelle voix est active,
# au lieu de basculer silencieusement sur pyttsx3 sans que ça se voie. ---
_voice_state = {"text": "Voix : vérification en cours…"}


def _probe_voice_engine():
    if not _EDGE_TTS_AVAILABLE:
        _voice_state["text"] = "Voix : standard (pyttsx3) — installe 'edge-tts' pour la voix naturelle"
        return
    if not (_PYGAME_AVAILABLE or _PLAYSOUND_AVAILABLE):
        _voice_state["text"] = "Voix : standard (pyttsx3) — installe 'pygame' ou 'playsound' pour lire la voix edge-tts"
        return
    try:
        async def _run():
            communicate = edge_tts.Communicate("test", EDGE_VOICE)
            await communicate.save(_VOICE_TMP_PATH)
        asyncio.run(_run())
        _voice_state["text"] = f"Voix : neuronale active ({EDGE_VOICE})"
    except Exception:
        _voice_state["text"] = "Voix : standard (pyttsx3) — edge-tts nécessite une connexion internet"


threading.Thread(target=_probe_voice_engine, daemon=True).start()


# =========================================================
# Notifications Windows
# =========================================================
def send_notification(title, message):
    if not _NOTIFY_AVAILABLE:
        return
    try:
        plyer_notification.notify(title=title, message=message, app_name="Jarvis", timeout=5)
    except Exception:
        pass


if os.name == "nt":
    _SUBPROCESS_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _SUBPROCESS_KWARGS = {}

# =========================================================
# Actions système réelles (plans d'alimentation, priorité CPU, DNS)
# =========================================================
try:
    import win32gui
    import win32process
    _WIN32_AVAILABLE = True
except ImportError:
    win32gui = None
    win32process = None
    _WIN32_AVAILABLE = False

POWER_PLANS = {
    "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
}

_current_power_plan = None  # évite de rappeler powercfg si on est déjà sur le bon plan


def set_power_plan(plan_key):
    global _current_power_plan
    if os.name != "nt":
        return False
    if _current_power_plan == plan_key:
        return True  # déjà appliqué, on ne relance pas powercfg pour rien
    guid = POWER_PLANS.get(plan_key)
    if not guid:
        return False
    try:
        subprocess.run(["powercfg", "/setactive", guid], check=True, **_SUBPROCESS_KWARGS)
        _current_power_plan = plan_key
        return True
    except Exception:
        return False


def flush_dns():
    if os.name != "nt":
        return
    try:
        subprocess.run(["ipconfig", "/flushdns"], check=True, **_SUBPROCESS_KWARGS)
    except Exception:
        pass


# =========================================================
# Démarrage automatique avec Windows (clé de registre Run,
# ne nécessite pas les droits administrateur — HKCU seulement)
# =========================================================
_STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_VALUE_NAME = "JarvisControlCenter"


def _startup_command():
    if getattr(sys, "frozen", False):
        # Empaqueté en .exe (PyInstaller) : on lance l'exécutable directement.
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pythonw if os.path.exists(pythonw) else sys.executable
    script = os.path.abspath(__file__)
    return f'"{exe}" "{script}"'


def is_startup_enabled():
    if not _WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _STARTUP_VALUE_NAME)
        return True
    except Exception:
        return False


def enable_startup():
    if not _WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _STARTUP_VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
        return True
    except Exception:
        return False


def disable_startup():
    if not _WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _STARTUP_VALUE_NAME)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


startup_button = None


def _refresh_startup_button():
    if startup_button:
        startup_button.config(
            text="DÉMARRAGE AUTO : ON" if is_startup_enabled() else "DÉMARRAGE AUTO : OFF"
        )


def toggle_startup():
    if not _WINREG_AVAILABLE:
        set_status("Jarvis : démarrage automatique disponible uniquement sur Windows.", speak=True)
        return
    if is_startup_enabled():
        disable_startup()
        set_status("Jarvis : démarrage automatique désactivé.", speak=True)
    else:
        enable_startup()
        set_status("Jarvis : démarrage automatique activé.", speak=True)
    _refresh_startup_button()


# =========================================================
# Icône dans la barre des tâches (system tray) — Jarvis continue de
# tourner en arrière-plan quand on ferme la fenêtre, comme une vraie
# appli système, au lieu de se fermer complètement.
# =========================================================
_tray_icon = None
_tray_notified_once = False


def _make_tray_image():
    size = 64
    img = Image.new("RGBA", (size, size), (20, 22, 31, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([6, 6, size - 6, size - 6], outline=(224, 168, 92, 255), width=4)
    draw.ellipse([22, 22, size - 22, size - 22], fill=(224, 168, 92, 255))
    return img


def _do_show_window():
    root.deiconify()
    try:
        root.state("zoomed")
    except tk.TclError:
        pass
    root.lift()
    root.focus_force()


def show_window(icon=None, item=None):
    root.after(0, _do_show_window)


def hide_window():
    global _tray_notified_once
    root.withdraw()
    if _TRAY_AVAILABLE:
        start_tray_icon()
        if not _tray_notified_once:
            send_notification("Jarvis", "Toujours actif dans la barre des tâches.")
            _tray_notified_once = True


def real_quit(icon=None, item=None):
    def _do():
        save_energy_data()
        restore_foreground_process()
        restore_lowered_processes()
        set_power_plan("balanced")
        if _tray_icon:
            _tray_icon.stop()
        root.destroy()
    root.after(0, _do)


def _toggle_startup_menu(icon, item):
    root.after(0, toggle_startup)


def start_tray_icon():
    global _tray_icon
    if not _TRAY_AVAILABLE or _tray_icon is not None:
        return
    menu = pystray.Menu(
        pystray.MenuItem("Afficher Jarvis", show_window, default=True),
        pystray.MenuItem("Démarrage auto avec Windows", _toggle_startup_menu,
                          checked=lambda item: is_startup_enabled()),
        pystray.MenuItem("Quitter", real_quit),
    )
    _tray_icon = pystray.Icon("jarvis", _make_tray_image(), "Jarvis Control Center", menu)
    threading.Thread(target=_tray_icon.run, daemon=True).start()


def get_foreground_pid():
    if not _WIN32_AVAILABLE:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception:
        return None


_boosted_pid = None


def boost_foreground_process():
    global _boosted_pid
    pid = get_foreground_pid()
    if pid is None:
        return None
    try:
        p = psutil.Process(pid)
        if os.name == "nt":
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            p.nice(-5)
        _boosted_pid = pid
        return p.name()
    except Exception:
        return None


def restore_foreground_process():
    global _boosted_pid
    if _boosted_pid is None:
        return
    try:
        p = psutil.Process(_boosted_pid)
        p.nice(psutil.NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
    except Exception:
        pass
    _boosted_pid = None


_CRITICAL_PROCESS_NAMES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe", "explorer.exe",
    "dwm.exe", "python.exe", "pythonw.exe",
}

_lowered_pids = []


def lower_background_processes(limit=5):
    global _lowered_pids
    restore_lowered_processes()

    foreground_pid = get_foreground_pid()
    own_pid = os.getpid()
    candidates = []

    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            name = (proc.info["name"] or "").lower()
            pid = proc.info["pid"]
            if name in _CRITICAL_PROCESS_NAMES or pid in (foreground_pid, own_pid):
                continue
            candidates.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    candidates.sort(key=lambda p: p.info.get("memory_percent") or 0, reverse=True)

    for proc in candidates[:limit]:
        try:
            proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 5)
            _lowered_pids.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def restore_lowered_processes():
    global _lowered_pids
    for pid in _lowered_pids:
        try:
            p = psutil.Process(pid)
            p.nice(psutil.NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _lowered_pids = []


# =========================================================
# Utilitaires de dessin : rectangle arrondi + interpolation de couleur.
# Tout est dessiné une seule fois (statique) — ça n'ajoute aucun coût
# en continu, seul l'aspect visuel change.
# =========================================================
def rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    c1, c2 = c1.lstrip('#'), c2.lstrip('#')
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class CanvasLabel:
    """Petit adaptateur pour garder l'API .config(text=...) des anciens
    tk.Label, mais en dessinant sur un Canvas (nécessaire pour les coins
    arrondis)."""
    def __init__(self, canvas, item_id):
        self.canvas = canvas
        self.item_id = item_id

    def config(self, **kwargs):
        if "text" in kwargs:
            self.canvas.itemconfig(self.item_id, text=kwargs["text"])


# --- Titre ---
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(fill="x", pady=(16, 0))

title = tk.Label(header_frame, text="JARVIS", font=("Segoe UI Semibold", 22), fg=TITLE_COLOR, bg=BG_COLOR)
title.pack(side="left", padx=24)

subtitle = tk.Label(header_frame, text=f"pour {USER_NAME}", font=("Segoe UI", 13), fg=TEXT_DIM, bg=BG_COLOR)
subtitle.pack(side="left", padx=(2, 0))

clock_label = tk.Label(header_frame, text="", font=("Segoe UI", 12), fg=TEXT_COLOR, bg=BG_COLOR)
clock_label.pack(side="right", padx=24)


def update_clock():
    now = datetime.datetime.now()
    clock_label.config(text=now.strftime("%A %d %B %Y — %H:%M:%S"))
    root.after(1000, update_clock)


update_clock()

# =========================================================
# HUD : un seul anneau qui "respire" doucement — animé via root.after,
# jamais via un thread qui martèle canvas.update() en continu.
# =========================================================
hud_canvas = tk.Canvas(root, width=260, height=260, bg=BG_COLOR, highlightthickness=0)
hud_canvas.pack(side="right", padx=24, pady=10)

_HUD_CX, _HUD_CY, _HUD_BASE_R = 130, 130, 88

# Halo statique : quelques cercles dessinés une seule fois avec une couleur
# qui s'estompe vers le fond, pour donner un effet de lueur sans animer quoi
# que ce soit (zéro coût CPU en continu).
for _i, _rad in enumerate([120, 108, 98]):
    hud_canvas.create_oval(
        _HUD_CX - _rad, _HUD_CY - _rad, _HUD_CX + _rad, _HUD_CY + _rad,
        outline=_blend(ACCENT, BG_COLOR, 0.55 + _i * 0.15), width=1
    )

ring_outer = hud_canvas.create_oval(0, 0, 0, 0, outline=hud_color, width=2)
ring_inner = hud_canvas.create_oval(0, 0, 0, 0, outline=ACCENT_SOFT, width=1)
hud_dot = hud_canvas.create_oval(0, 0, 0, 0, fill=hud_color, outline="")

_hud_phase = 0.0


def animate_hud():
    global _hud_phase
    _hud_phase += hud_speed
    r1 = _HUD_BASE_R + 6 * math.sin(_hud_phase)
    r2 = _HUD_BASE_R * 0.6 + 4 * math.sin(_hud_phase * 1.3 + 1.0)
    hud_canvas.coords(ring_outer, _HUD_CX - r1, _HUD_CY - r1, _HUD_CX + r1, _HUD_CY + r1)
    hud_canvas.coords(ring_inner, _HUD_CX - r2, _HUD_CY - r2, _HUD_CX + r2, _HUD_CY + r2)
    hud_canvas.coords(hud_dot, _HUD_CX - 3, _HUD_CY - 3, _HUD_CX + 3, _HUD_CY + 3)
    hud_canvas.itemconfig(ring_outer, outline=hud_color)
    hud_canvas.itemconfig(hud_dot, fill=hud_color)
    root.after(40, animate_hud)  # ~25 images/seconde, planifié proprement, pas de boucle bloquante


# --- Infos système ---
main_frame = tk.Frame(root, bg=BG_COLOR)
main_frame.pack(side="left", fill="both", expand=True, padx=24, pady=10)


def create_card(parent, title_text, width=320, height=118):
    cv = tk.Canvas(parent, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
    rounded_rect(cv, 2, 2, width - 2, height - 2, 18, fill=CARD_BG, outline=CARD_BORDER, width=1)
    cv.create_text(18, 20, text=title_text, anchor="nw", font=("Segoe UI Semibold", 11), fill=ACCENT)
    value_id = cv.create_text(18, 48, text="…", anchor="nw", font=("Segoe UI", 14),
                               fill=TEXT_COLOR, width=width - 36)
    return cv, CanvasLabel(cv, value_id)


cpu_frame, cpu_value = create_card(main_frame, "PROCESSEUR")
ram_frame, ram_value = create_card(main_frame, "MÉMOIRE")
disk_frame, disk_value = create_card(main_frame, "DISQUE")
net_frame, net_value = create_card(main_frame, "RÉSEAU")

cpu_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
ram_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
disk_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
net_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)

main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_rowconfigure(1, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_columnconfigure(1, weight=1)

# --- Tableau de bord avancé ---
advanced_frame = tk.Frame(root, bg=BG_COLOR)
advanced_frame.pack(fill="x", padx=24, pady=10)

tk.Label(advanced_frame, text="DIAGNOSTIC AVANCÉ", font=("Segoe UI Semibold", 13), fg=TITLE_COLOR, bg=BG_COLOR).grid(
    row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))


def create_adv_card(parent, title_text, width=480, height=130):
    cv = tk.Canvas(parent, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
    rounded_rect(cv, 2, 2, width - 2, height - 2, 16, fill=CARD_BG, outline=CARD_BORDER, width=1)
    cv.create_text(16, 16, text=title_text, anchor="nw", font=("Segoe UI Semibold", 10), fill=ACCENT)
    value_id = cv.create_text(16, 42, text="…", anchor="nw", font=("Segoe UI", 10),
                               fill=TEXT_COLOR, width=width - 32, justify="left")
    return cv, CanvasLabel(cv, value_id)


gpu_frame, gpu_value = create_adv_card(advanced_frame, "GPU (NVIDIA)")
cpu_adv_frame, cpu_adv_value = create_adv_card(advanced_frame, "DÉTAIL CPU")
power_frame, power_value = create_adv_card(advanced_frame, "ESTIMATION PUISSANCE")
net_adv_frame, net_adv_value = create_adv_card(advanced_frame, "DÉBIT RÉSEAU")
energy_frame, energy_value = create_adv_card(advanced_frame, "SUIVI ÉNERGÉTIQUE", width=976, height=140)

gpu_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
cpu_adv_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=6)
power_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)
net_adv_frame.grid(row=2, column=1, sticky="nsew", padx=8, pady=6)
energy_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=8, pady=6)

advanced_frame.grid_columnconfigure(0, weight=1)
advanced_frame.grid_columnconfigure(1, weight=1)

# =========================================================
# Historique graphique (CPU / RAM)
# =========================================================
HISTORY_LEN = 60
cpu_history = deque(maxlen=HISTORY_LEN)
ram_history = deque(maxlen=HISTORY_LEN)

history_frame = tk.Frame(root, bg=BG_COLOR)
history_frame.pack(fill="x", padx=24, pady=(0, 10))

tk.Label(history_frame, text="HISTORIQUE (60 dernières secondes)", font=("Segoe UI Semibold", 11),
         fg=TITLE_COLOR, bg=BG_COLOR).pack(anchor="w", padx=8)

fig = Figure(figsize=(8, 1.3), dpi=80, facecolor=CARD_BG)
ax = fig.add_subplot(111)
ax.set_facecolor(CARD_BG)
ax.tick_params(colors=TEXT_DIM, labelsize=7)
for spine in ax.spines.values():
    spine.set_color(CARD_BORDER)
line_cpu, = ax.plot([], [], color=ACCENT, label="CPU %")
line_ram, = ax.plot([], [], color=ACCENT_SOFT, label="RAM %")
ax.set_ylim(0, 100)
ax.set_xlim(0, HISTORY_LEN)
legend = ax.legend(loc="upper right", fontsize=7, facecolor=CARD_BG)
for text_ in legend.get_texts():
    text_.set_color(TEXT_DIM)
fig.tight_layout()

history_canvas = FigureCanvasTkAgg(fig, master=history_frame)
history_canvas.get_tk_widget().pack(fill="x", padx=8)


def update_history_graph():
    x = list(range(len(cpu_history)))
    line_cpu.set_data(x, list(cpu_history))
    line_ram.set_data(x, list(ram_history))
    history_canvas.draw_idle()


# --- Status ---
status_label = tk.Label(root, text=f"Jarvis prêt, {USER_NAME}.", font=("Segoe UI", 11), fg=TEXT_DIM, bg=BG_COLOR)
status_label.pack(pady=6)

voice_status_label = tk.Label(root, text=_voice_state["text"], font=("Segoe UI", 9), fg=ACCENT_SOFT, bg=BG_COLOR)
voice_status_label.pack(pady=(0, 6))


def _refresh_voice_status_label():
    voice_status_label.config(text=_voice_state["text"])
    root.after(1500, _refresh_voice_status_label)


_refresh_voice_status_label()


def set_status(text, speak=False):
    status_label.config(text=text)
    if speak:
        jarvis_say(text)


# =========================================================
# Alertes intelligentes
# =========================================================
ALERT_CPU_HIGH = 90
ALERT_RAM_HIGH = 90
ALERT_DISK_HIGH = 90
ALERT_GPU_TEMP_HIGH = 85

_alert_state = {"cpu": False, "ram": False, "disk": False, "gpu_temp": False}


def trigger_alert(key, message):
    set_status(f"Jarvis : {message}", speak=True)
    send_notification("Jarvis - Alerte", message)


def check_alerts(cpu, ram, disk, gpu_temp):
    if cpu > ALERT_CPU_HIGH and not _alert_state["cpu"]:
        _alert_state["cpu"] = True
        trigger_alert("cpu", f"attention {USER_NAME}, le processeur dépasse {ALERT_CPU_HIGH} pourcent.")
    elif cpu < ALERT_CPU_HIGH - 15:
        _alert_state["cpu"] = False

    if ram > ALERT_RAM_HIGH and not _alert_state["ram"]:
        _alert_state["ram"] = True
        trigger_alert("ram", f"attention {USER_NAME}, la mémoire vive dépasse {ALERT_RAM_HIGH} pourcent.")
    elif ram < ALERT_RAM_HIGH - 15:
        _alert_state["ram"] = False

    if disk > ALERT_DISK_HIGH and not _alert_state["disk"]:
        _alert_state["disk"] = True
        trigger_alert("disk", f"attention {USER_NAME}, le disque est presque plein, {disk:.0f} pourcent utilisé.")
    elif disk < ALERT_DISK_HIGH - 5:
        _alert_state["disk"] = False

    if gpu_temp is not None:
        if gpu_temp > ALERT_GPU_TEMP_HIGH and not _alert_state["gpu_temp"]:
            _alert_state["gpu_temp"] = True
            trigger_alert("gpu_temp", f"attention {USER_NAME}, la température du GPU atteint {gpu_temp:.0f} degrés.")
        elif gpu_temp < ALERT_GPU_TEMP_HIGH - 10:
            _alert_state["gpu_temp"] = False


# --- Actions ---
def boost_ram():
    import gc
    gc.collect()
    set_status("Jarvis : optimisation de la mémoire.", speak=True)


def clean_temp():
    set_status("Jarvis : nettoyage des fichiers temporaires…", speak=True)
    temp_dirs = [os.getenv("TEMP"), os.getenv("TMP"), r"C:\Windows\Temp"]
    for d in temp_dirs:
        if d and os.path.exists(d):
            for item in os.listdir(d):
                path = os.path.join(d, item)
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass
    set_status("Jarvis : nettoyage terminé.", speak=True)


# =========================================================
# Nettoyage avancé : gros fichiers, doublons, apps au démarrage.
# Le scan tourne toujours dans un thread séparé (jamais sur le thread
# Tkinter), et les fichiers sont envoyés à la corbeille (send2trash)
# quand c'est disponible plutôt que supprimés définitivement.
# =========================================================
def _scan_dirs():
    home = os.path.expanduser("~")
    candidates = ["Downloads", "Téléchargements", "Documents", "Desktop", "Bureau", "Pictures", "Videos", "Music"]
    seen = set()
    dirs = []
    for c in candidates:
        p = os.path.join(home, c)
        if os.path.isdir(p) and p not in seen:
            seen.add(p)
            dirs.append(p)
    return dirs


def find_large_files(threshold_mb=200, progress_cb=None):
    threshold_bytes = threshold_mb * 1024 * 1024
    results = []
    for base in _scan_dirs():
        for root_dir, _dirs, files in os.walk(base):
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size >= threshold_bytes:
                    results.append((fpath, size))
        if progress_cb:
            progress_cb(base)
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _partial_hash(path, chunk=8192):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read(chunk)).hexdigest()
    except Exception:
        return None


def _full_hash(path):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def find_duplicates(progress_cb=None):
    size_map = {}
    for base in _scan_dirs():
        for root_dir, _dirs, files in os.walk(base):
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size == 0:
                    continue
                size_map.setdefault(size, []).append(fpath)
        if progress_cb:
            progress_cb(base)

    dup_groups = []
    for _size, paths in size_map.items():
        if len(paths) < 2:
            continue
        partial_map = {}
        for p in paths:
            h = _partial_hash(p)
            if h is not None:
                partial_map.setdefault(h, []).append(p)
        for _h, plist in partial_map.items():
            if len(plist) < 2:
                continue
            full_map = {}
            for p in plist:
                fh = _full_hash(p)
                if fh is not None:
                    full_map.setdefault(fh, []).append(p)
            for _fh, flist in full_map.items():
                if len(flist) >= 2:
                    dup_groups.append(flist)
    return dup_groups


def delete_files_safely(paths):
    deleted = 0
    for p in paths:
        try:
            if _SEND2TRASH_AVAILABLE:
                send2trash.send2trash(p)
            else:
                os.remove(p)
            deleted += 1
        except Exception:
            pass
    return deleted


# --- Apps au démarrage (registre Run HKCU/HKLM + dossier Démarrage) ---
_DISABLED_STARTUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_disabled_startup.json")


def _load_disabled_startup():
    if os.path.exists(_DISABLED_STARTUP_FILE):
        try:
            with open(_DISABLED_STARTUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_disabled_startup(data):
    try:
        with open(_DISABLED_STARTUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def list_startup_registry_apps():
    apps = []
    if not _WINREG_AVAILABLE:
        return apps
    for hive, hive_name in [(winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")]:
        try:
            with winreg.OpenKey(hive, _STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _t = winreg.EnumValue(key, i)
                        if name != _STARTUP_VALUE_NAME:
                            apps.append({"source": hive_name, "name": name, "command": value, "enabled": True})
                        i += 1
                    except OSError:
                        break
        except Exception:
            continue
    disabled = _load_disabled_startup()
    for name, info in disabled.items():
        apps.append({"source": info.get("source", "HKCU"), "name": name,
                     "command": info.get("command", ""), "enabled": False})
    return apps


def disable_startup_app(hive_name, name, command):
    if not _WINREG_AVAILABLE:
        return False
    hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        with winreg.OpenKey(hive, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        disabled = _load_disabled_startup()
        disabled[name] = {"source": hive_name, "command": command}
        _save_disabled_startup(disabled)
        return True
    except Exception:
        return False


def enable_startup_app(name):
    disabled = _load_disabled_startup()
    info = disabled.get(name)
    if not info or not _WINREG_AVAILABLE:
        return False
    hive = winreg.HKEY_CURRENT_USER if info.get("source") == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        with winreg.OpenKey(hive, _STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, info.get("command", ""))
        del disabled[name]
        _save_disabled_startup(disabled)
        return True
    except Exception:
        return False


# --- Fenêtres d'affichage (Treeview stylé pour rester dans l'ambiance Jarvis) ---
def open_large_files_window():
    win = tk.Toplevel(root)
    win.title("Jarvis — Gros fichiers")
    win.configure(bg=BG_COLOR)
    win.geometry("760x480")

    info_label = tk.Label(win, text="Analyse en cours…", font=("Segoe UI", 11), fg=TEXT_COLOR, bg=BG_COLOR)
    info_label.pack(pady=8)

    tree = ttk.Treeview(win, columns=("path", "size"), show="headings", style="Jarvis.Treeview", height=16)
    tree.heading("path", text="Fichier")
    tree.heading("size", text="Taille")
    tree.column("path", width=580)
    tree.column("size", width=120, anchor="e")
    tree.pack(fill="both", expand=True, padx=12, pady=6)

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=8)

    def do_delete():
        selected = tree.selection()
        if not selected:
            return
        paths = [tree.item(iid, "values")[0] for iid in selected]
        if not messagebox.askyesno("Confirmer", f"Supprimer {len(paths)} fichier(s) ?", parent=win):
            return
        deleted = delete_files_safely(paths)
        for iid in selected:
            tree.delete(iid)
        set_status(f"Jarvis : {deleted} fichier(s) supprimé(s).", speak=True)

    label_suffix = "" if _SEND2TRASH_AVAILABLE else " (définitif — installe 'send2trash' pour la corbeille)"
    tk.Button(btn_frame, text="SUPPRIMER LA SÉLECTION" + label_suffix, command=do_delete, **btn_style).pack(side="left", padx=6)

    def scan():
        def progress(base):
            info_label.config(text=f"Analyse : {base}…")
        results = find_large_files(threshold_mb=200, progress_cb=lambda b: root.after(0, progress, b))

        def populate():
            info_label.config(text=f"{len(results)} fichier(s) de plus de 200 Mo trouvés.")
            for path, size in results:
                tree.insert("", "end", values=(path, f"{size / (1024 * 1024):.1f} Mo"))
        root.after(0, populate)

    threading.Thread(target=scan, daemon=True).start()


def open_duplicates_window():
    win = tk.Toplevel(root)
    win.title("Jarvis — Doublons")
    win.configure(bg=BG_COLOR)
    win.geometry("760x480")

    info_label = tk.Label(win, text="Analyse en cours…", font=("Segoe UI", 11), fg=TEXT_COLOR, bg=BG_COLOR)
    info_label.pack(pady=8)

    tree = ttk.Treeview(win, columns=("path", "size"), show="tree headings", style="Jarvis.Treeview", height=16)
    tree.heading("#0", text="Groupe")
    tree.heading("path", text="Fichier")
    tree.heading("size", text="Taille")
    tree.column("#0", width=90)
    tree.column("path", width=500)
    tree.column("size", width=100, anchor="e")
    tree.pack(fill="both", expand=True, padx=12, pady=6)

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=8)

    def do_delete():
        selected = [iid for iid in tree.selection() if tree.parent(iid)]
        if not selected:
            return
        paths = [tree.item(iid, "values")[0] for iid in selected]
        if not messagebox.askyesno("Confirmer", f"Supprimer {len(paths)} fichier(s) en double ?", parent=win):
            return
        deleted = delete_files_safely(paths)
        for iid in selected:
            tree.delete(iid)
        set_status(f"Jarvis : {deleted} doublon(s) supprimé(s).", speak=True)

    tk.Button(btn_frame, text="SUPPRIMER LA SÉLECTION (garde le 1er de chaque groupe)",
              command=do_delete, **btn_style).pack(side="left", padx=6)

    def scan():
        def progress(base):
            info_label.config(text=f"Analyse : {base}…")
        groups = find_duplicates(progress_cb=lambda b: root.after(0, progress, b))

        def populate():
            total_dupes = sum(len(g) - 1 for g in groups)
            info_label.config(text=f"{len(groups)} groupe(s) de doublons — {total_dupes} fichier(s) redondant(s).")
            for i, group in enumerate(groups, 1):
                parent = tree.insert("", "end", text=f"Groupe {i}", open=False)
                for p in group:
                    try:
                        size = os.path.getsize(p)
                    except OSError:
                        size = 0
                    tree.insert(parent, "end", values=(p, f"{size / (1024 * 1024):.1f} Mo"))
        root.after(0, populate)

    threading.Thread(target=scan, daemon=True).start()


def open_startup_manager_window():
    win = tk.Toplevel(root)
    win.title("Jarvis — Applications au démarrage")
    win.configure(bg=BG_COLOR)
    win.geometry("700x420")

    if not _WINREG_AVAILABLE:
        tk.Label(win, text="Fonctionnalité disponible uniquement sur Windows.",
                 font=("Segoe UI", 11), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=20)
        return

    tree = ttk.Treeview(win, columns=("source", "name", "state"), show="headings",
                         style="Jarvis.Treeview", height=14)
    tree.heading("source", text="Origine")
    tree.heading("name", text="Application")
    tree.heading("state", text="État")
    tree.column("source", width=80, anchor="center")
    tree.column("name", width=420)
    tree.column("state", width=100, anchor="center")
    tree.pack(fill="both", expand=True, padx=12, pady=10)

    apps_by_iid = {}

    def refresh():
        tree.delete(*tree.get_children())
        apps_by_iid.clear()
        for app in list_startup_registry_apps():
            iid = tree.insert("", "end", values=(app["source"], app["name"],
                                                  "Activé" if app["enabled"] else "Désactivé"))
            apps_by_iid[iid] = app

    def do_toggle():
        selected = tree.selection()
        if not selected:
            return
        for iid in selected:
            app = apps_by_iid.get(iid)
            if not app:
                continue
            if app["enabled"]:
                ok = disable_startup_app(app["source"], app["name"], app["command"])
            else:
                ok = enable_startup_app(app["name"])
            if not ok:
                messagebox.showwarning(
                    "Jarvis",
                    f"Impossible de modifier {app['name']} (droits administrateur requis pour HKLM ?)",
                    parent=win
                )
        refresh()

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=8)
    tk.Button(btn_frame, text="ACTIVER / DÉSACTIVER LA SÉLECTION", command=do_toggle, **btn_style).pack(side="left", padx=6)
    tk.Button(btn_frame, text="ACTUALISER", command=refresh, **btn_style).pack(side="left", padx=6)

    refresh()


# =========================================================
# Modes — chaque mode a maintenant une fonction "toggle" (pour les boutons,
# actionnée une fois par un clic humain) ET s'appuie sur un état explicite
# que le mode Auto peut lire/forcer sans re-déclencher sans arrêt les
# actions système (c'est ce qui faisait ramer le PC avant).
# =========================================================
gaming_mode = False
performance_mode = False
stealth_mode = False
turbo_mode = False
auto_mode = False


def _set_hud_for_mode():
    global hud_color, hud_speed
    if turbo_mode:
        hud_color, hud_speed = "#e0703c", 0.09
    elif gaming_mode:
        hud_color, hud_speed = "#c94f6d", 0.08
    elif performance_mode:
        hud_color, hud_speed = "#7cc48a", 0.06
    elif stealth_mode:
        hud_color, hud_speed = "#6b7280", 0.03
    else:
        hud_color, hud_speed = ACCENT, 0.05


def mode_gaming():
    global gaming_mode
    gaming_mode = not gaming_mode
    _set_hud_for_mode()

    if gaming_mode:
        set_power_plan("high_performance")
        lower_background_processes(limit=8)
        boosted_name = boost_foreground_process()
        if boosted_name:
            set_status(f"Jarvis : mode Gaming activé, priorité augmentée pour {boosted_name}.", speak=True)
        elif not _WIN32_AVAILABLE:
            set_status("Jarvis : mode Gaming activé (installe pywin32 pour booster le jeu actif).", speak=True)
        else:
            set_status("Jarvis : mode Gaming activé.", speak=True)
    else:
        restore_foreground_process()
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Gaming désactivé.", speak=True)


def mode_performance():
    global performance_mode
    performance_mode = not performance_mode
    _set_hud_for_mode()

    if performance_mode:
        set_power_plan("high_performance")
        lower_background_processes(limit=5)
        boost_ram()
        set_status("Jarvis : mode Performance activé.", speak=True)
    else:
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Performance désactivé.", speak=True)


def mode_stealth():
    global stealth_mode
    stealth_mode = not stealth_mode
    _set_hud_for_mode()

    if stealth_mode:
        set_power_plan("power_saver")
        lower_background_processes(limit=10)
        set_status("Jarvis : mode Discret activé, consommation réduite au minimum.", speak=True)
    else:
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Discret désactivé.", speak=True)


def mode_turbo():
    global turbo_mode
    turbo_mode = not turbo_mode
    _set_hud_for_mode()

    if turbo_mode:
        set_power_plan("high_performance")
        lower_background_processes(limit=10)
        clean_temp()
        boost_ram()
        flush_dns()
        set_status("Jarvis : mode Turbo activé.", speak=True)
    else:
        restore_lowered_processes()
        set_power_plan("balanced")
        set_status("Jarvis : mode Turbo désactivé.", speak=True)


def mode_auto():
    global auto_mode
    auto_mode = not auto_mode
    set_status("Jarvis : mode Auto activé." if auto_mode else "Jarvis : mode Auto désactivé.", speak=True)


def _current_manual_mode():
    if gaming_mode:
        return "gaming"
    if performance_mode:
        return "performance"
    if stealth_mode:
        return "stealth"
    return "normal"


def apply_mode_state(target):
    """Met le système dans l'état voulu — ne fait rien si on y est déjà,
    ce qui évite de re-changer le plan d'alimentation et les priorités
    des processus à chaque cycle du mode Auto."""
    current = _current_manual_mode()
    if current == target:
        return
    if gaming_mode:
        mode_gaming()
    if performance_mode:
        mode_performance()
    if stealth_mode:
        mode_stealth()
    if target == "gaming":
        mode_gaming()
    elif target == "performance":
        mode_performance()
    elif target == "stealth":
        mode_stealth()


def auto_analyze():
    while True:
        if auto_mode:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent

            if disk > 90:
                clean_temp()

            if cpu > 75 or ram > 85:
                apply_mode_state("performance")
            elif cpu < 25 and ram < 45:
                apply_mode_state("stealth")
            else:
                apply_mode_state("normal")

        time.sleep(5)


# =========================================================
# Commandes vocales
# =========================================================
voice_mode_enabled = False
voice_button = None


def process_voice_command(text):
    text = text.lower()
    set_status(f"Jarvis : commande reçue -> {text}")

    if "turbo" in text:
        mode_turbo()
    elif "performance" in text:
        mode_performance()
    elif "stealth" in text or "furtif" in text or "discret" in text:
        mode_stealth()
    elif "gaming" in text or "jeu" in text:
        mode_gaming()
    elif "auto" in text:
        mode_auto()
    elif "nettoie" in text or "nettoyage" in text:
        clean_temp()
    elif "mémoire" in text or "ram" in text:
        boost_ram()
    else:
        set_status("Jarvis : commande non reconnue.", speak=True)


def toggle_voice():
    global voice_mode_enabled
    if not _VOICE_AVAILABLE:
        set_status("Jarvis : module vocal non installé (SpeechRecognition/pyaudio).", speak=True)
        return
    voice_mode_enabled = not voice_mode_enabled
    if voice_button:
        voice_button.config(text="VOIX : ACTIVE" if voice_mode_enabled else "VOIX : COUPÉE")
    set_status("Jarvis : écoute vocale activée." if voice_mode_enabled else "Jarvis : écoute vocale désactivée.", speak=True)


def voice_listener():
    if not _VOICE_AVAILABLE:
        return
    recognizer = sr.Recognizer()
    try:
        mic = sr.Microphone()
    except Exception:
        return

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
    except Exception:
        pass

    while True:
        if not voice_mode_enabled:
            time.sleep(1)
            continue
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio, language="fr-FR")
            process_voice_command(text)
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception:
            time.sleep(2)


# --- Boutons ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip, text=self.text, justify="left",
                          bg=CARD_BG, fg=TEXT_COLOR, font=("Segoe UI", 9),
                          highlightbackground=CARD_BORDER, highlightthickness=1, padx=8, pady=4,
                          wraplength=260)
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


button_frame = tk.Frame(root, bg=BG_COLOR)
button_frame.pack(pady=10)

BTN_COLOR = ACCENT
BTN_HOVER_COLOR = "#f0c07e"

btn_style = {
    "font": ("Segoe UI Semibold", 11),
    "bg": BTN_COLOR,
    "fg": "#1c1408",
    "activebackground": "#c98f43",
    "activeforeground": "#1c1408",
    "bd": 0,
    "padx": 12,
    "pady": 6,
    "cursor": "hand2",
}

buttons = [
    ("LIBÉRER MÉMOIRE", boost_ram, "Libère la mémoire utilisée par Jarvis lui-même."),
    ("NETTOYER TEMP", clean_temp, "Supprime les fichiers temporaires de Windows pour libérer de l'espace disque."),
    ("GAMING", mode_gaming, "Performances élevées + priorité pour le jeu/programme actif au premier plan."),
    ("PERFORMANCE", mode_performance, "Performances élevées et priorité réduite pour les tâches en arrière-plan."),
    ("DISCRET", mode_stealth, "Économie d'énergie et activité réduite en arrière-plan."),
    ("TURBO", mode_turbo, "Performance + nettoyage + vidage du cache DNS."),
    ("AUTO", mode_auto, "Jarvis choisit le mode adapté selon l'usage du CPU/RAM/disque (sans le changer sans arrêt)."),
    ("VOIX : COUPÉE", toggle_voice, "Active l'écoute vocale : dis 'turbo', 'gaming', 'nettoie'…"),
    ("DÉMARRAGE AUTO : OFF", toggle_startup, "Lance Jarvis automatiquement à l'ouverture de session Windows."),
    ("GROS FICHIERS", open_large_files_window, "Cherche les fichiers de plus de 200 Mo dans Téléchargements/Documents/Bureau/Images/Vidéos/Musique."),
    ("DOUBLONS", open_duplicates_window, "Trouve les fichiers en double (même contenu) dans les mêmes dossiers."),
    ("APPS DÉMARRAGE", open_startup_manager_window, "Active/désactive les programmes qui se lancent avec Windows."),
]

for i, (txt, cmd, tip_text) in enumerate(buttons):
    b = tk.Button(button_frame, text=txt, command=cmd, **btn_style)
    b.grid(row=i // 4, column=i % 4, padx=8, pady=6)
    b.bind("<Enter>", lambda e, btn=b: btn.config(bg=BTN_HOVER_COLOR))
    b.bind("<Leave>", lambda e, btn=b: btn.config(bg=BTN_COLOR))
    Tooltip(b, tip_text)
    if txt.startswith("VOIX"):
        voice_button = b
    if txt.startswith("DÉMARRAGE AUTO"):
        startup_button = b

_refresh_startup_button()

# --- GPU NVIDIA ---
_nvidia_available = True
_last_gpu_text = "GPU : lecture en cours…"
_last_gpu_power = 0.0
_last_gpu_temp = None


def get_nvidia_stats():
    global _nvidia_available
    if not _nvidia_available:
        return "GPU NVIDIA : non détecté.", 0.0, None

    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,power.limit",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.check_output(cmd, encoding="utf-8", **_SUBPROCESS_KWARGS)
        parts = [p.strip() for p in result.split(",")]
        if len(parts) >= 7:
            gpu_util, mem_util, mem_used, mem_total, temp, power_draw, power_limit = parts[:7]
            text = (
                f"Utilisation : {gpu_util} %  |  Mémoire : {mem_util} %\n"
                f"VRAM : {mem_used}/{mem_total} MiB\n"
                f"Température : {temp} °C  |  Puissance : {power_draw}/{power_limit} W"
            )
            return text, float(power_draw), float(temp)
    except FileNotFoundError:
        _nvidia_available = False
    except Exception:
        pass

    return "GPU NVIDIA : données indisponibles.", 0.0, None


def estimate_cpu_power(cpu_percent):
    tdp_cpu = 65.0
    return tdp_cpu * (cpu_percent / 100.0)


# =========================================================
# Boucle de stats — le nvidia-smi (lancement de process externe) est
# coûteux : on ne l'interroge plus que toutes les 3 secondes au lieu
# de chaque seconde.
# =========================================================
_last_energy_save = time.time()
_stats_loop_count = 0
_GPU_POLL_EVERY_N = 3


def update_stats():
    global total_energy_wh, hour_energy_wh, day_energy_wh, week_energy_wh, month_energy_wh
    global last_hour, last_day, last_week, last_month, _last_energy_save
    global _last_gpu_text, _last_gpu_power, _last_gpu_temp, _stats_loop_count

    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    while True:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        net = psutil.net_io_counters()
        net_text = f"Envoyé : {net.bytes_sent // 1024} Ko  |  Reçu : {net.bytes_recv // 1024} Ko"

        cpu_value.config(text=f"{cpu} %")
        ram_value.config(text=f"{ram} %")
        disk_value.config(text=f"{disk} %")
        net_value.config(text=net_text)

        cpu_history.append(cpu)
        ram_history.append(ram)
        root.after(0, update_history_graph)

        _stats_loop_count += 1
        if _stats_loop_count % _GPU_POLL_EVERY_N == 0 or _stats_loop_count == 1:
            _last_gpu_text, _last_gpu_power, _last_gpu_temp = get_nvidia_stats()
        gpu_value.config(text=_last_gpu_text)

        check_alerts(cpu, ram, disk, _last_gpu_temp)

        freq = psutil.cpu_freq()
        freq_text = f"{freq.current:.0f} MHz (max {freq.max:.0f} MHz)" if freq else "Fréquence : N/A"
        per_core = psutil.cpu_percent(percpu=True)
        cores_text = "Par cœur : " + " | ".join(f"{p:.0f}%" for p in per_core)

        cpu_power = estimate_cpu_power(cpu)
        cpu_adv_value.config(
            text=f"{freq_text}\n{cores_text}\nPuissance estimée CPU : {cpu_power:.1f} W"
        )

        total_power = cpu_power + _last_gpu_power
        power_value.config(
            text=f"CPU : {cpu_power:.1f} W   GPU : {_last_gpu_power:.1f} W\nTotal estimé : {total_power:.1f} W"
        )

        now_time = time.time()
        dt = now_time - prev_time
        if dt <= 0:
            dt = 1

        sent_diff = net.bytes_sent - prev_net.bytes_sent
        recv_diff = net.bytes_recv - prev_net.bytes_recv
        up_speed = sent_diff / dt / 1024
        down_speed = recv_diff / dt / 1024
        net_adv_value.config(text=f"Envoi : {up_speed:.1f} Ko/s\nRéception : {down_speed:.1f} Ko/s")

        prev_net = net
        prev_time = now_time

        # --- Energy tracking ---
        now = datetime.datetime.now()
        energy_wh = total_power / 3600.0

        total_energy_wh += energy_wh
        hour_energy_wh += energy_wh
        day_energy_wh += energy_wh
        week_energy_wh += energy_wh
        month_energy_wh += energy_wh

        if now.hour != last_hour:
            hour_energy_wh = 0.0
            last_hour = now.hour
        if now.day != last_day:
            day_energy_wh = 0.0
            last_day = now.day
        if now.isocalendar()[1] != last_week:
            week_energy_wh = 0.0
            last_week = now.isocalendar()[1]
        if now.month != last_month:
            month_energy_wh = 0.0
            last_month = now.month

        cost_total = (total_energy_wh / 1000.0) * price_per_kwh
        cost_day = (day_energy_wh / 1000.0) * price_per_kwh

        bars = int(min(total_power / 10, 20))
        graph = "█" * bars + "░" * (20 - bars)

        energy_value.config(
            text=(
                f"Puissance actuelle : {total_power:.1f} W\n"
                f"Heure : {hour_energy_wh/1000:.4f} kWh   Jour : {day_energy_wh/1000:.4f} kWh\n"
                f"Semaine : {week_energy_wh/1000:.4f} kWh   Mois : {month_energy_wh/1000:.4f} kWh\n"
                f"Coût aujourd'hui : {cost_day:.3f} €   Coût total : {cost_total:.3f} €\n"
                f"[{graph}]"
            )
        )

        if now_time - _last_energy_save > 30:
            save_energy_data()
            _last_energy_save = now_time

        time.sleep(1)


def on_close():
    if _TRAY_AVAILABLE:
        save_energy_data()
        hide_window()
    else:
        save_energy_data()
        restore_foreground_process()
        restore_lowered_processes()
        set_power_plan("balanced")
        root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

# =========================================================
# Intro — construite avec root.after (planification non-bloquante)
# plutôt qu'un thread qui boucle avec time.sleep + canvas.update(),
# ce qui évite tout appel Tkinter depuis un thread secondaire.
# =========================================================
_intro_already_shown = False


def jarvis_intro():
    global _intro_already_shown
    if _intro_already_shown:
        return
    _intro_already_shown = True

    intro = tk.Toplevel(root)
    intro.config(bg=BG_COLOR)
    intro.attributes("-fullscreen", True)
    intro.attributes("-topmost", True)

    canvas_i = tk.Canvas(intro, bg=BG_COLOR, highlightthickness=0)
    canvas_i.pack(fill="both", expand=True)

    w = intro.winfo_screenwidth()
    h = intro.winfo_screenheight()
    cx, cy = w // 2, h // 2

    # Halo de fond, dessiné une seule fois (statique, aucun coût continu).
    for i, rad in enumerate([300, 260, 220, 185]):
        canvas_i.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                              outline=_blend(ACCENT, BG_COLOR, 0.6 + i * 0.1), width=1)

    arc_outer = canvas_i.create_arc(cx - 170, cy - 170, cx + 170, cy + 170,
                                     start=0, extent=80, style="arc", outline=ACCENT, width=3)
    arc_inner = canvas_i.create_arc(cx - 120, cy - 120, cx + 120, cy + 120,
                                     start=180, extent=80, style="arc", outline=ACCENT_SOFT, width=2)
    ring_shock = canvas_i.create_oval(cx, cy, cx, cy, outline=ACCENT, width=2)

    # Particules disposées en cercle, qui convergent vers le centre.
    particles = []
    n_particles = 20
    for i in range(n_particles):
        angle = math.radians(i * (360 / n_particles))
        px, py = cx + 320 * math.cos(angle), cy + 320 * math.sin(angle)
        pid = canvas_i.create_oval(px - 2, py - 2, px + 2, py + 2, fill=ACCENT, outline="")
        particles.append((pid, px, py))

    text_title = canvas_i.create_text(cx, cy - 230, text="", font=("Segoe UI Semibold", 34), fill=TITLE_COLOR)
    text_log = canvas_i.create_text(cx, cy - 185, text="", font=("Segoe UI", 13), fill=ACCENT_SOFT)
    text_greet = canvas_i.create_text(cx, cy + 230, text="", font=("Segoe UI", 19), fill=TEXT_COLOR)

    full_text = "JARVIS"
    boot_lines = [
        "Calibrage des capteurs système…",
        "Analyse du processeur et de la mémoire…",
        "Synchronisation des modules…",
    ]
    state = {"char": 0, "spin": 0, "frame": 0, "boot_i": 0}

    def spin_step():
        state["spin"] = (state["spin"] + 7) % 360
        canvas_i.itemconfig(arc_outer, start=state["spin"])
        canvas_i.itemconfig(arc_inner, start=(360 - state["spin"] * 1.3) % 360)

    def converge_step():
        state["frame"] += 1
        t = min(state["frame"] / 45, 1.0)
        ease = 1 - (1 - t) ** 3  # décélération douce vers le centre
        for pid, px, py in particles:
            nx = px + (cx - px) * ease
            ny = py + (cy - py) * ease
            canvas_i.coords(pid, nx - 2, ny - 2, nx + 2, ny + 2)
        spin_step()
        if t < 1.0:
            intro.after(25, converge_step)
        else:
            for pid, _px, _py in particles:
                canvas_i.delete(pid)
            intro.after(100, type_step)

    def cycle_boot_log():
        if state["boot_i"] < len(boot_lines):
            canvas_i.itemconfig(text_log, text=boot_lines[state["boot_i"]])
            state["boot_i"] += 1
            intro.after(430, cycle_boot_log)

    def type_step():
        state["char"] += 1
        canvas_i.itemconfig(text_title, text=full_text[:state["char"]])
        spin_step()
        if state["char"] < len(full_text):
            intro.after(130, type_step)
        else:
            intro.after(400, settle)

    def settle():
        canvas_i.itemconfig(text_log, text="")
        canvas_i.itemconfig(text_greet, text=get_greeting())
        jarvis_say(get_greeting())
        shockwave_step()

    def shockwave_step(r=0):
        r += 26
        canvas_i.coords(ring_shock, cx - r, cy - r, cx + r, cy + r)
        fade = max(0.0, 1 - r / 260)
        canvas_i.itemconfig(ring_shock, outline=_blend(BG_COLOR, ACCENT, fade))
        if r < 260:
            intro.after(20, lambda: shockwave_step(r))
        else:
            intro.after(1300, lambda: fade_out(10))

    def fade_out(steps_left):
        t = steps_left / 10
        canvas_i.itemconfig(text_title, fill=_blend(BG_COLOR, TITLE_COLOR, t))
        canvas_i.itemconfig(text_greet, fill=_blend(BG_COLOR, TEXT_COLOR, t))
        col_accent = _blend(BG_COLOR, ACCENT, t)
        canvas_i.itemconfig(arc_outer, outline=col_accent)
        canvas_i.itemconfig(arc_inner, outline=col_accent)
        if steps_left > 0:
            intro.after(45, lambda: fade_out(steps_left - 1))
        else:
            intro.destroy()

    cycle_boot_log()
    converge_step()


# --- Démarrage des threads (uniquement pour du travail non-Tkinter) ---
threading.Thread(target=update_stats, daemon=True).start()
threading.Thread(target=auto_analyze, daemon=True).start()
threading.Thread(target=voice_listener, daemon=True).start()

animate_hud()  # animation du HUD sur le thread principal via root.after

set_status(f"Jarvis : système opérationnel, {USER_NAME}.")
root.after(500, jarvis_intro)

if _TRAY_AVAILABLE:
    start_tray_icon()

root.mainloop()



















