"""
GELİŞMİŞ UZAY SAVAŞI 🚀 — v4 (PREMIUM+ SÜRÜM)
--------------------------------------------------------
v3'e göre yapılan değişiklikler:

DÜZELTİLEN HATALAR:
  - BUG FIX: Yeni oyun başlatıldığında boss HUD öğeleri (hp bar/label) global
    referanslar temizlenmeden kalabiliyordu; artık start_game() içinde
    garantili sıfırlanıyor.
  - BUG FIX: Zigzag düşmanların sınır kontrolü artık gerçek bbox genişliğine
    göre yapılıyor, önceden merkez tabanlıydı ve düşmanlar ekran kenarından
    görünür şekilde taşabiliyordu.
  - BUG FIX: Kalkan (shield) aurası, gemi parçalarından biri silinmişse
    (ör. oyun yeniden başlatılırken yarım kalan bir kare) hataya yol
    açabiliyordu; artık tüm hareket çağrıları None-güvenli.
  - BUG FIX: Combo artık aniden kesilmek yerine son 0.6 saniyede HUD'da
    görsel bir "azalıyor" efektiyle (renk soluklaşması) biter.
  - BUG FIX: Power-up'lar üst üste gelip aynı anda ekranda çakışabiliyordu;
    artık spawn sırasında minimum mesafe kontrolü var.
  - BUG FIX: Skor tablosu artık hangi zorlukta yapıldığını da saklıyor.
  - DENGE: Boss'un hız/ateş artışı (enrage) artık tek seferlik zıplama değil,
    can azaldıkça kademeli olarak şiddetleniyor (%50 altı ve %20 altı için
    ek eşikler eklendi).

YENİ ÖZELLİKLER:
  - SİLAH ÇEŞİTLİLİĞİ: Üçlü atışın yanında yeni geçici güçlendirmeler:
    Lazer Işını (delici, düşmanları arka arkaya vurur) ve Roket (alan hasarı).
  - 3 FARKLI BOSS: Her biri kendi saldırı desenine sahip (Klasik/Mermi Yağmuru,
    Işın Bossu/lazer süpürme, Sürü Bossu/mini drone çağırma).
  - DASH (KAÇIŞ) HAREKETİ: Kısa mesafe hızlı kayma + kısa dokunulmazlık,
    bilinçli risk-ödül mekaniği katıyor (bekleme süresi var, spam edilemez).
  - GERÇEK "NEAR-MISS" BONUSU: Düşman mermisi gemiye çok yakından geçerse
    küçük bonus puan + görsel kıvılcım (cesur oynamayı ödüllendirir).
  - ZORLUĞA GÖRE AYRI SKOR TABLOLARI: Kolay/Orta/Zor için ayrı top-5.
  - SEVİYE BAŞINA YENİ DÜŞMAN TÜRÜ AÇILIMI (kademeli tanıtım, ilk saniyelerden
    itibaren "her şeyi birden" göstermek yerine öğretici bir eğri).
  - HAREKET AKICILIĞI: İvme tabanlı gemi hareketi (anlık zıplama yerine
    yumuşak hızlanma/yavaşlama).
"""

import subprocess
import sys
import os
import json
import random
import time
import math
import datetime

# --- OTOMATİK KÜTÜPHANE YÜKLEYİCİ ---
def auto_install_packages():
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("'pygame' kütüphanesi eksik, otomatik yükleniyor (pygame-ce)...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
            print("'pygame-ce' başarıyla yüklendi!")
        except Exception as e:
            print(f"Uyarı: pygame otomatik yüklenemedi ({e}). Oyun sessiz modda çalışacak.")

auto_install_packages()

import tkinter as tk

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# --- DOSYA YOLLARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(name):
    return os.path.join(BASE_DIR, name)


HIGHSCORE_FILE = asset_path("highscore.json")
SETTINGS_FILE = asset_path("settings.json")
PROGRESS_FILE = asset_path("progress.json")

REQUIRED_SOUND_FILES = ["ates.wav", "patlama.wav", "hasar.wav", "powerup.wav", "muzik.wav"]


def ensure_sound_assets():
    missing = [f for f in REQUIRED_SOUND_FILES if not os.path.exists(asset_path(f))]
    if not missing:
        return
    maker_path = asset_path("make_sounds.py")
    if not os.path.exists(maker_path):
        return
    try:
        subprocess.check_call([sys.executable, maker_path], cwd=BASE_DIR)
    except Exception as e:
        print(f"Uyarı: Ses dosyaları otomatik üretilemedi ({e}).")


ensure_sound_assets()

# --- AYARLAR (KALICI) ---
DEFAULT_SETTINGS = {"sound_on": True, "control_mode": None, "music_volume": 0.25}


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f)
    except Exception as e:
        print("Uyarı: Ayarlar kaydedilemedi:", e)


SETTINGS = load_settings()

# --- KALICI İLERLEME ---
DEFAULT_PROGRESS = {
    "stardust": 0,
    "upgrades": {"fire_rate": 0, "damage": 0, "triple": 0, "dash": 0},
    "unlocked_skins": ["classic"],
    "equipped_skin": "classic",
    "achievements": [],
    "last_login": "",
    "total_games_played": 0,
    "total_kills": 0,
}

SKINS = {
    "classic": {"name": "Klasik", "hull": "#444455", "cockpit": "cyan", "engine": "#FF6D00", "cost": 0},
    "crimson": {"name": "Kızıl Şahin", "hull": "#5a1616", "cockpit": "#ff5252", "engine": "#ff8a65", "cost": 300},
    "emerald": {"name": "Zümrüt Yılan", "hull": "#0f3d2e", "cockpit": "#00e676", "engine": "#69f0ae", "cost": 300},
    "royal":   {"name": "Kraliyet Moru", "hull": "#2a1250", "cockpit": "#b388ff", "engine": "#7c4dff", "cost": 500},
}

UPGRADE_INFO = {
    "fire_rate": {"name": "🔥 Ateş Hızı", "max": 5, "base_cost": 120, "cost_growth": 1.5,
                  "desc": "Ateş etme aralığını kısaltır."},
    "damage": {"name": "💥 Mermi Gücü", "max": 5, "base_cost": 150, "cost_growth": 1.6,
               "desc": "Mermi başına verilen hasarı artırır."},
    "triple": {"name": "🔫 Üçlü Atış Süresi", "max": 5, "base_cost": 100, "cost_growth": 1.4,
               "desc": "Üçlü atış güçlendirmesinin süresini uzatır."},
    "dash": {"name": "💨 Kaçış Bekleme Süresi", "max": 5, "base_cost": 130, "cost_growth": 1.5,
             "desc": "Dash (kaçış) hareketinin bekleme süresini kısaltır."},
}

ACHIEVEMENTS = [
    {"id": "first_blood", "name": "İlk Kan", "desc": "İlk düşmanını yok et.", "reward": 20,
     "check": lambda p: p["total_kills"] >= 1},
    {"id": "kills_100", "name": "Yıkım Ustası", "desc": "Toplam 100 düşman yok et.", "reward": 100,
     "check": lambda p: p["total_kills"] >= 100},
    {"id": "kills_500", "name": "Galaksi Kırıcı", "desc": "Toplam 500 düşman yok et.", "reward": 300,
     "check": lambda p: p["total_kills"] >= 500},
    {"id": "games_10", "name": "Azimli Pilot", "desc": "10 oyun oyna.", "reward": 50,
     "check": lambda p: p["total_games_played"] >= 10},
    {"id": "near_miss_master", "name": "Sinir Harbi Ustası", "desc": "Tek oyunda 15 'ucuz kurtuluş' yaşa.", "reward": 80,
     "check": lambda p: p.get("best_near_miss_run", 0) >= 15},
    {"id": "boss_slayer", "name": "Boss Avcısı", "desc": "10 boss yok et.", "reward": 150,
     "check": lambda p: p.get("total_bosses_killed", 0) >= 10},
]


def load_progress():
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = json.loads(json.dumps(DEFAULT_PROGRESS))
            merged.update({k: v for k, v in data.items() if k in merged})
            if "upgrades" in data:
                merged["upgrades"].update(data["upgrades"])
            # eski kayıtlarda olmayabilecek alanları güvenle ekle
            merged.setdefault("best_near_miss_run", data.get("best_near_miss_run", 0))
            merged.setdefault("total_bosses_killed", data.get("total_bosses_killed", 0))
            return merged
    except Exception:
        return json.loads(json.dumps(DEFAULT_PROGRESS))


def save_progress():
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(PROGRESS, f, ensure_ascii=False)
    except Exception as e:
        print("Uyarı: İlerleme kaydedilemedi:", e)


PROGRESS = load_progress()
PROGRESS.setdefault("best_near_miss_run", 0)
PROGRESS.setdefault("total_bosses_killed", 0)

_daily_bonus_awarded = 0
def check_daily_bonus():
    global _daily_bonus_awarded
    today = datetime.date.today().isoformat()
    if PROGRESS.get("last_login") != today:
        PROGRESS["last_login"] = today
        _daily_bonus_awarded = 50
        PROGRESS["stardust"] = PROGRESS.get("stardust", 0) + _daily_bonus_awarded
        save_progress()

check_daily_bonus()


def upgrade_cost(key):
    info = UPGRADE_INFO[key]
    lvl = PROGRESS["upgrades"].get(key, 0)
    if lvl >= info["max"]:
        return None
    return int(info["base_cost"] * (info["cost_growth"] ** lvl))


def try_buy_upgrade(key):
    cost = upgrade_cost(key)
    if cost is None or PROGRESS["stardust"] < cost:
        return False
    PROGRESS["stardust"] -= cost
    PROGRESS["upgrades"][key] = PROGRESS["upgrades"].get(key, 0) + 1
    save_progress()
    return True


def try_buy_skin(key):
    skin = SKINS[key]
    if key in PROGRESS["unlocked_skins"]:
        PROGRESS["equipped_skin"] = key
        save_progress()
        return True
    if PROGRESS["stardust"] >= skin["cost"]:
        PROGRESS["stardust"] -= skin["cost"]
        PROGRESS["unlocked_skins"].append(key)
        PROGRESS["equipped_skin"] = key
        save_progress()
        return True
    return False


def check_achievements():
    newly_done = []
    for ach in ACHIEVEMENTS:
        if ach["id"] not in PROGRESS["achievements"] and ach["check"](PROGRESS):
            PROGRESS["achievements"].append(ach["id"])
            PROGRESS["stardust"] += ach["reward"]
            newly_done.append(ach)
    if newly_done:
        save_progress()
    return newly_done


# --- SES MOTORU ---
SOUND_ENABLED = False
sound_shoot = sound_explosion = sound_damage = sound_powerup = None

if PYGAME_AVAILABLE:
    try:
        pygame.mixer.init()
        try:
            sound_shoot = pygame.mixer.Sound(asset_path("ates.wav"))
            sound_explosion = pygame.mixer.Sound(asset_path("patlama.wav"))
            sound_damage = pygame.mixer.Sound(asset_path("hasar.wav"))
            sound_powerup = pygame.mixer.Sound(asset_path("powerup.wav"))

            sound_shoot.set_volume(0.3)
            sound_explosion.set_volume(0.5)
            sound_damage.set_volume(0.7)
            sound_powerup.set_volume(0.6)

            pygame.mixer.music.load(asset_path("muzik.wav"))
            pygame.mixer.music.set_volume(SETTINGS.get("music_volume", 0.25))
            SOUND_ENABLED = True
        except Exception as e:
            print("Uyarı: Ses dosyalarından bazıları bulunamadı, oyun sessiz modda çalışacak:", e)
            SOUND_ENABLED = False
    except Exception as e:
        print("Uyarı: Ses sistemi başlatılamadı, oyun sessiz modda çalışacak:", e)
        SOUND_ENABLED = False
else:
    print("Uyarı: pygame kurulamadı, oyun sessiz modda çalışacak.")


def sound_master_enabled():
    return SOUND_ENABLED and SETTINGS.get("sound_on", True)


def play_sound(snd):
    if sound_master_enabled() and snd is not None:
        try:
            snd.play()
        except Exception:
            pass


def play_music():
    if sound_master_enabled():
        try:
            pygame.mixer.music.play(-1)
        except Exception:
            pass


def stop_music():
    if SOUND_ENABLED:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


def refresh_music_state():
    if not SOUND_ENABLED:
        return
    try:
        if sound_master_enabled() and game_started and not game_over:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.stop()
    except Exception:
        pass


# --- ZORLUĞA GÖRE AYRI SKOR TABLOLARI (YENİ / BUG FIX) ---
def _empty_boards():
    return {"easy": [], "medium": [], "hard": []}


def load_scoreboards():
    """
    BUG FIX: v3'te tüm zorluklar aynı tek listede tutuluyordu; bu da 'Kolay'da
    yapılan yüksek bir skorun 'Zor' modun rekoruymuş gibi görünmesine yol
    açıyordu. Artık her zorluk kendi top-5 listesine sahip. Eski (düz liste)
    formatındaki kayıtlar 'medium' zorluğuna geçmişten devralınmış kabul
    edilerek geri uyumlu şekilde okunuyor.
    """
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        boards = data.get("boards")
        if isinstance(boards, dict):
            result = _empty_boards()
            for k in result:
                lst = boards.get(k, [])
                if isinstance(lst, list):
                    result[k] = sorted([int(s) for s in lst], reverse=True)[:5]
            return result
        old_scores = data.get("scores")
        if isinstance(old_scores, list):
            result = _empty_boards()
            result["medium"] = sorted([int(s) for s in old_scores], reverse=True)[:5]
            return result
        old_single = data.get("highscore")
        if old_single:
            result = _empty_boards()
            result["medium"] = [int(old_single)]
            return result
        return _empty_boards()
    except Exception:
        return _empty_boards()


def save_scoreboards(boards):
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump({"boards": {k: v[:5] for k, v in boards.items()}}, f)
    except Exception as e:
        print("Uyarı: Skor tablosu kaydedilemedi:", e)


def submit_score(difficulty, new_score):
    boards = load_scoreboards()
    lst = boards.get(difficulty, [])
    is_new_record = (new_score > 0) and (len(lst) == 0 or new_score > lst[0])
    lst.append(new_score)
    lst = sorted(lst, reverse=True)[:5]
    boards[difficulty] = lst
    save_scoreboards(boards)
    return boards, is_new_record


scoreboards = load_scoreboards()


def top_score_all_difficulties():
    best = 0
    for lst in scoreboards.values():
        if lst:
            best = max(best, lst[0])
    return best


high_score = top_score_all_difficulties()

# --- PENCERE ---
WIDTH = 1000
HEIGHT = 800

root = tk.Tk()
root.title("Gelişmiş Uzay Savaşı 🚀")
root.resizable(False, False)
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#050510", highlightthickness=0)
canvas.pack()

TITLE_FONT = ("Impact", 54)
HEADER_FONT = ("Impact", 42)

# ------------------ OYUN DEĞİŞKENLERİ ------------------
bullets = []
enemy_bullets = []
enemies = []
stars = []
nebulas = []
powerups = []
particles = []
engine_trail = []
score_popups = []
near_miss_flashes = []

score = 0
lives = 3
invincible_until = 0
triple_shot_until = 0
laser_until = 0
combo_count = 0
last_kill_time = 0
run_kills = 0
run_near_misses = 0
run_bosses_killed = 0

level = 1

ship_vx = 0.0
SHIP_ACCEL = 1.3
SHIP_MAX_SPEED = 9.5
SHIP_FRICTION = 0.82

dash_ready_at = 0.0
DASH_BASE_COOLDOWN = 3.0
dash_active_until = 0.0
DASH_DURATION = 0.18
dash_direction = 0

game_started = False
game_over = False
paused = False
current_state = "SPLASH"

difficulty_settings = {
    "easy":   {"enemy_delay": 1600, "min_delay": 700,  "hp": 1, "pts_mult": 1.0, "powerup_chance": 0.20, "label": "Kolay 🌱"},
    "medium": {"enemy_delay": 1150, "min_delay": 520,  "hp": 1, "pts_mult": 1.5, "powerup_chance": 0.22, "label": "Orta ⚖️"},
    "hard":   {"enemy_delay": 850,  "min_delay": 380,  "hp": 2, "pts_mult": 2.5, "powerup_chance": 0.28, "label": "Zor 🔥"},
}
current_difficulty = "medium"

BOSS_SCORE_INTERVAL = 400
LEVEL_SCORE_INTERVAL = 150
next_boss_score = BOSS_SCORE_INTERVAL
boss_active = False
boss_hp_bg = None
boss_hp_fg = None
boss_label = None
boss_enrage_stage = 0
boss_kind = None

last_shot_time = 0
score_text = None
life_text = None
combo_text = None
level_text = None
sound_indicator_text = None
stardust_text = None
low_hp_vignette = None
dash_indicator_text = None
ship = None
cockpit = None
engine = None
shield_aura = None

move_left_active = False
move_right_active = False
shoot_active = False
control_mode = SETTINGS.get("control_mode")

current_menu_widgets = []
touch_widgets = []

loop_after_ids = {}


# ------------------ TEMİZLİK ------------------
class _DummyDestroyable:
    def destroy(self):
        pass


def add_menu_widget(widget, x, y):
    win_id = canvas.create_window(x, y, window=widget)
    current_menu_widgets.append((win_id, widget))
    return win_id


def add_menu_canvas_item(item_id):
    current_menu_widgets.append((item_id, _DummyDestroyable()))
    return item_id


def cleanup_menu():
    for win_id, widget in current_menu_widgets:
        try:
            canvas.delete(win_id)
        except Exception:
            pass
        try:
            widget.destroy()
        except Exception:
            pass
    current_menu_widgets.clear()


def cleanup_touch_controls():
    for w in touch_widgets:
        try:
            w.destroy()
        except Exception:
            pass
    touch_widgets.clear()


def cancel_loop(*keys):
    for key in keys:
        if key in loop_after_ids:
            try:
                root.after_cancel(loop_after_ids[key])
            except Exception:
                pass
            del loop_after_ids[key]


# ------------------ EKRAN SALLANTISI ------------------
def trigger_screen_shake(intensity=8, duration=8):
    def shake(count):
        if count > 0 and game_started:
            dx = random.randint(-intensity, intensity)
            dy = random.randint(-intensity, intensity)
            canvas.move("all", dx, dy)
            root.after(20, lambda: [canvas.move("all", -dx, -dy), shake(count - 1)])

    shake(duration)


# ------------------ ARKA PLAN ------------------
def create_stars():
    for s in stars:
        try:
            canvas.delete(s["id"])
        except Exception:
            pass
    stars.clear()
    for n in nebulas:
        try:
            canvas.delete(n["id"])
        except Exception:
            pass
    nebulas.clear()

    nebula_colors = ["#151032", "#1a1440", "#0f1a35", "#160f28"]
    for _ in range(6):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        r = random.randint(80, 180)
        color = random.choice(nebula_colors)
        cloud = canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="", stipple="gray25")
        canvas.tag_lower(cloud)
        nebulas.append({"id": cloud, "speed": random.uniform(0.15, 0.4)})

    for _ in range(60):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        speed = random.uniform(0.8, 1.8)
        star = canvas.create_oval(x, y, x + 1, y + 1, fill="#555588", outline="")
        stars.append({"id": star, "speed": speed})

    for _ in range(30):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        speed = random.uniform(3.0, 5.5)
        star = canvas.create_oval(x, y, x + 2, y + 2, fill="#FFFFFF", outline="")
        stars.append({"id": star, "speed": speed})


def update_stars():
    for n in nebulas:
        canvas.move(n["id"], 0, n["speed"])
        pos = canvas.coords(n["id"])
        if pos and pos[1] > HEIGHT + 200:
            r = (pos[2] - pos[0]) / 2
            canvas.coords(n["id"], pos[0], -r * 2 - 50, pos[2], -50)

    for s in stars:
        canvas.move(s["id"], 0, s["speed"])
        pos = canvas.coords(s["id"])
        if pos and pos[1] > HEIGHT:
            size = pos[2] - pos[0]
            canvas.coords(s["id"], random.randint(0, WIDTH), 0, random.randint(0, WIDTH) + size, size)
    loop_after_ids["stars"] = root.after(30, update_stars)


# ------------------ MENÜLER ------------------
def format_scoreboard_lines(scores, limit=5):
    if not scores:
        return ["Henüz skor yok — ilk rekoru sen kır!"]
    medals = ["🥇", "🥈", "🥉", "4.", "5."]
    lines = []
    for i, s in enumerate(scores[:limit]):
        prefix = medals[i] if i < len(medals) else f"{i+1}."
        lines.append(f"{prefix}  {s} puan")
    return lines


def draw_splash_screen():
    global current_state
    current_state = "SPLASH"
    cleanup_touch_controls()
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 250, text="UZAY SAVAŞI", fill="#00FFFF", font=TITLE_FONT)
    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 190, text="Galaksiyi Savunmaya Hazır Mısın?",
                        fill="#AAAAAA", font=("Arial", 18, "italic"))

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 145, text=f"✨ Yıldız Tozu: {PROGRESS['stardust']}",
                        fill="#FFD700", font=("Arial", 16, "bold"))

    if _daily_bonus_awarded:
        canvas.create_text(WIDTH // 2, HEIGHT // 2 - 118,
                            text=f"🎁 Günlük bonus: +{_daily_bonus_awarded} yıldız tozu!",
                            fill="#00FF7F", font=("Arial", 12, "bold"))

    best_medium = scoreboards.get("medium", [])
    lines = format_scoreboard_lines(best_medium, limit=3)
    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 85, text="   ".join(lines),
                        fill="#DDDDDD", font=("Arial", 13))

    play_btn = tk.Button(
        root, text="🚀 OYNA", font=("Impact", 24),
        bg="#00E676", fg="black", activebackground="#00C853", activeforeground="white",
        bd=0, cursor="hand2", padx=20, pady=10,
        command=draw_difficulty_menu
    )
    add_menu_widget(play_btn, WIDTH // 2, HEIGHT // 2 - 25)

    hangar_btn = tk.Button(
        root, text="🛠️ Hangar (Yükseltmeler)", font=("Arial", 14, "bold"),
        bg="#7c4dff", fg="white", activebackground="#9575cd",
        bd=0, cursor="hand2", padx=15, pady=8,
        command=draw_hangar_menu
    )
    add_menu_widget(hangar_btn, WIDTH // 2, HEIGHT // 2 + 35)

    row_y = HEIGHT // 2 + 90
    settings_btn = tk.Button(
        root, text="⚙️ Ayarlar", font=("Arial", 12, "bold"),
        bg="#333355", fg="white", activebackground="#4a4a70",
        bd=0, cursor="hand2", padx=12, pady=6,
        command=lambda: draw_settings_menu("SPLASH")
    )
    add_menu_widget(settings_btn, WIDTH // 2 - 160, row_y)

    scores_btn = tk.Button(
        root, text="📜 Skorlar", font=("Arial", 12, "bold"),
        bg="#222", fg="#DDDDDD", bd=0, cursor="hand2", padx=12, pady=6,
        command=draw_full_scoreboard
    )
    add_menu_widget(scores_btn, WIDTH // 2, row_y)

    ach_btn = tk.Button(
        root, text="🏅 Başarımlar", font=("Arial", 12, "bold"),
        bg="#222", fg="#FFD700", bd=0, cursor="hand2", padx=12, pady=6,
        command=draw_achievements_menu
    )
    add_menu_widget(ach_btn, WIDTH // 2 + 160, row_y)

    how_btn = tk.Button(
        root, text="❓ Nasıl Oynanır", font=("Arial", 11, "bold"),
        bg="#111", fg="#888", bd=0, cursor="hand2", padx=10, pady=4,
        command=draw_how_to_play
    )
    add_menu_widget(how_btn, WIDTH // 2, row_y + 45)


def draw_how_to_play():
    """YENİ: Yeni oyuncular için kısa, net kontrol rehberi."""
    global current_state
    current_state = "HOWTO"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, 90, text="NASIL OYNANIR ❓", fill="#00FFFF", font=HEADER_FONT)

    lines = [
        ("💻 Klavye", "◀ ▶ Hareket   |   SPACE Ateş   |   SHIFT Dash (Kaçış)   |   ESC Duraklat"),
        ("📱 Dokunmatik", "Ekrandaki SOL / SAĞ / ATEŞ / DASH butonlarını kullan"),
        ("🛡️ Kalkan", "Bir süre tüm hasara karşı korunursun"),
        ("🔫 Üçlü Atış", "3 mermi birden fırlatırsın"),
        ("⚡ Lazer", "Kısa süreliğine düşmanları delip geçen sürekli ışın"),
        ("💣 Bomba", "Ekrandaki tüm düşmanları anında yok eder"),
        ("❤️ Can", "Ekstra bir can kazandırır (maks 5)"),
        ("💨 Dash", "Kısa anlık dokunulmazlıkla hızlıca yana kayarsın (bekleme süresi var)"),
        ("✨ Near-Miss", "Bir mermi seni kıl payı ıskalarsa bonus puan kazanırsın"),
    ]
    y = 160
    for title, desc in lines:
        canvas.create_text(WIDTH // 2 - 320, y, anchor="w", text=title, fill="#FFD700", font=("Arial", 14, "bold"))
        canvas.create_text(WIDTH // 2 - 150, y, anchor="w", text=desc, fill="#DDDDDD", font=("Arial", 12))
        y += 45

    back_btn = tk.Button(
        root, text="◀ Ana Menü", font=("Arial", 14, "bold"),
        bg="#333", fg="white", bd=0, cursor="hand2", padx=15, pady=8,
        command=draw_splash_screen
    )
    add_menu_widget(back_btn, WIDTH // 2, HEIGHT - 50)


def draw_full_scoreboard():
    global current_state
    current_state = "SCOREBOARD"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, 80, text="EN İYİ SKORLAR 🏆", fill="#FFD700", font=HEADER_FONT)

    col_w = 300
    diffs = [("easy", "🟢 Kolay"), ("medium", "🟡 Orta"), ("hard", "🔴 Zor")]
    start_x = WIDTH // 2 - col_w
    for i, (key, label) in enumerate(diffs):
        cx = start_x + i * col_w
        canvas.create_text(cx, 150, text=label, fill="white", font=("Arial", 18, "bold"))
        lines = format_scoreboard_lines(scoreboards.get(key, []), limit=5)
        for j, line in enumerate(lines):
            canvas.create_text(cx, 200 + j * 36, text=line, fill="#DDDDDD", font=("Arial", 13))

    back_btn = tk.Button(
        root, text="◀ Ana Menü", font=("Arial", 14, "bold"),
        bg="#333", fg="white", bd=0, cursor="hand2", padx=15, pady=8,
        command=draw_splash_screen
    )
    add_menu_widget(back_btn, WIDTH // 2, HEIGHT - 60)


def draw_achievements_menu():
    global current_state
    current_state = "ACHIEVEMENTS"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, 70, text="BAŞARIMLAR 🏅", fill="#FFD700", font=HEADER_FONT)

    y = 140
    for ach in ACHIEVEMENTS:
        done = ach["id"] in PROGRESS["achievements"]
        color = "#00FF7F" if done else "#666677"
        icon = "✅" if done else "🔒"
        canvas.create_text(WIDTH // 2 - 300, y, anchor="w", text=f"{icon} {ach['name']}",
                            fill=color, font=("Arial", 15, "bold"))
        canvas.create_text(WIDTH // 2 - 300, y + 22, anchor="w", text=ach["desc"],
                            fill="#999999", font=("Arial", 11))
        canvas.create_text(WIDTH // 2 + 300, y, anchor="e", text=f"+{ach['reward']} ✨",
                            fill="#FFD700", font=("Arial", 13, "bold"))
        y += 58

    back_btn = tk.Button(
        root, text="◀ Ana Menü", font=("Arial", 14, "bold"),
        bg="#333", fg="white", bd=0, cursor="hand2", padx=15, pady=8,
        command=draw_splash_screen
    )
    add_menu_widget(back_btn, WIDTH // 2, HEIGHT - 45)


def draw_hangar_menu():
    global current_state
    current_state = "HANGAR"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, 50, text="HANGAR 🛠️", fill="#00FFFF", font=HEADER_FONT)
    canvas.create_text(WIDTH // 2, 90, text=f"✨ Yıldız Tozu: {PROGRESS['stardust']}",
                        fill="#FFD700", font=("Arial", 15, "bold"))

    canvas.create_text(WIDTH // 2 - 250, 130, anchor="w", text="Kalıcı Yükseltmeler",
                        fill="white", font=("Arial", 15, "bold"))
    y = 165
    for key, info in UPGRADE_INFO.items():
        lvl = PROGRESS["upgrades"].get(key, 0)
        cost = upgrade_cost(key)
        canvas.create_text(WIDTH // 2 - 250, y, anchor="w",
                            text=f"{info['name']}  (Seviye {lvl}/{info['max']})",
                            fill="white", font=("Arial", 13, "bold"))
        canvas.create_text(WIDTH // 2 - 250, y + 18, anchor="w", text=info["desc"],
                            fill="#999999", font=("Arial", 10))

        if cost is None:
            btn = tk.Button(root, text="MAKS", font=("Arial", 11, "bold"),
                             bg="#333", fg="#777", bd=0, state="disabled", padx=10, pady=5)
        else:
            afford = PROGRESS["stardust"] >= cost
            btn = tk.Button(
                root, text=f"Yükselt ({cost} ✨)", font=("Arial", 11, "bold"),
                bg="#00C853" if afford else "#444", fg="white" if afford else "#888",
                bd=0, cursor="hand2" if afford else "arrow", padx=10, pady=5,
                command=(lambda k=key: (try_buy_upgrade(k), draw_hangar_menu())) if afford else None
            )
        add_menu_widget(btn, WIDTH // 2 + 220, y + 6)
        y += 48

    canvas.create_text(WIDTH // 2 - 250, y + 10, anchor="w", text="Gemi Görünümleri",
                        fill="white", font=("Arial", 15, "bold"))
    y += 45
    for key, skin in SKINS.items():
        owned = key in PROGRESS["unlocked_skins"]
        equipped = PROGRESS["equipped_skin"] == key
        swatch = canvas.create_oval(WIDTH // 2 - 260, y - 12, WIDTH // 2 - 236, y + 12,
                                     fill=skin["hull"], outline=skin["cockpit"], width=2)
        add_menu_canvas_item(swatch)
        label = f"{skin['name']}" + (" (Kuşanılmış)" if equipped else "")
        canvas.create_text(WIDTH // 2 - 220, y, anchor="w", text=label,
                            fill="#00FF7F" if equipped else "white", font=("Arial", 12, "bold"))

        if equipped:
            btn = tk.Button(root, text="Kuşanılmış ✓", font=("Arial", 10, "bold"),
                             bg="#333", fg="#00FF7F", bd=0, state="disabled", padx=10, pady=5)
        elif owned:
            btn = tk.Button(root, text="Kuşan", font=("Arial", 10, "bold"),
                             bg="#303f9f", fg="white", bd=0, cursor="hand2", padx=10, pady=5,
                             command=lambda k=key: (try_buy_skin(k), draw_hangar_menu()))
        else:
            afford = PROGRESS["stardust"] >= skin["cost"]
            btn = tk.Button(
                root, text=f"Aç ({skin['cost']} ✨)", font=("Arial", 10, "bold"),
                bg="#00C853" if afford else "#444", fg="white" if afford else "#888",
                bd=0, cursor="hand2" if afford else "arrow", padx=10, pady=5,
                command=(lambda k=key: (try_buy_skin(k), draw_hangar_menu())) if afford else None
            )
        add_menu_widget(btn, WIDTH // 2 + 220, y)
        y += 38

    back_btn = tk.Button(
        root, text="◀ Ana Menü", font=("Arial", 13, "bold"),
        bg="#333", fg="white", bd=0, cursor="hand2", padx=15, pady=6,
        command=draw_splash_screen
    )
    add_menu_widget(back_btn, WIDTH // 2, HEIGHT - 25)


def draw_settings_menu(return_to):
    global current_state
    current_state = "SETTINGS"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 200, text="AYARLAR ⚙️", fill="#00FFFF", font=HEADER_FONT)

    sound_label_var = tk.StringVar()

    def sound_label():
        return f"🔊 Ses: {'AÇIK' if SETTINGS.get('sound_on', True) else 'KAPALI'}"

    sound_label_var.set(sound_label())

    def toggle_sound():
        SETTINGS["sound_on"] = not SETTINGS.get("sound_on", True)
        save_settings()
        sound_label_var.set(sound_label())
        refresh_music_state()
        update_sound_indicator()

    sound_btn = tk.Button(
        root, textvariable=sound_label_var, font=("Arial", 16, "bold"),
        bg="#303f9f", fg="white", activebackground="#7986cb",
        bd=0, cursor="hand2", padx=20, pady=12,
        command=toggle_sound
    )
    add_menu_widget(sound_btn, WIDTH // 2, HEIGHT // 2 - 110)

    if not SOUND_ENABLED:
        canvas.create_text(WIDTH // 2, HEIGHT // 2 - 70,
                            text="(pygame/ses dosyaları yüklenemedi, sessiz mod)",
                            fill="#888888", font=("Arial", 11, "italic"))

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 20, text="Kontrol Modu (varsayılan):",
                        fill="white", font=("Arial", 16, "bold"))

    def set_default_control(mode):
        SETTINGS["control_mode"] = mode
        save_settings()
        draw_settings_menu(return_to)

    kb_btn = tk.Button(
        root, text="💻 Klavye", font=("Arial", 14, "bold"),
        bg="#455a64" if SETTINGS.get("control_mode") != "keyboard" else "#00C853",
        fg="white", bd=0, cursor="hand2", padx=15, pady=10,
        command=lambda: set_default_control("keyboard")
    )
    add_menu_widget(kb_btn, WIDTH // 2 - 100, HEIGHT // 2 + 30)

    touch_btn = tk.Button(
        root, text="📱 Dokunmatik", font=("Arial", 14, "bold"),
        bg="#455a64" if SETTINGS.get("control_mode") != "touch" else "#00C853",
        fg="white", bd=0, cursor="hand2", padx=15, pady=10,
        command=lambda: set_default_control("touch")
    )
    add_menu_widget(touch_btn, WIDTH // 2 + 100, HEIGHT // 2 + 30)

    def go_back():
        if return_to == "PAUSE":
            draw_pause_overlay()
        else:
            draw_splash_screen()

    back_btn = tk.Button(
        root, text="◀ Geri", font=("Arial", 14, "bold"),
        bg="#333", fg="white", bd=0, cursor="hand2", padx=15, pady=8,
        command=go_back
    )
    add_menu_widget(back_btn, WIDTH // 2, HEIGHT // 2 + 100)


def set_difficulty(level_choice):
    global current_difficulty
    current_difficulty = level_choice
    draw_device_menu()


def draw_difficulty_menu():
    global current_state
    current_state = "DIFFICULTY_MENU"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 160, text="ZORLUK SEÇİMİ ⚙️", fill="#00FFFF", font=HEADER_FONT)
    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 90, text="Galaksi Hangi Seviyede?", fill="white", font=("Arial", 22, "bold"))

    easy_btn = tk.Button(
        root, text="🟢 KOLAY\n(Düşük Hız)", font=("Arial", 16, "bold"),
        bg="#00C853", fg="white", activebackground="#a5d6a7",
        bd=0, cursor="hand2", padx=20, pady=15,
        command=lambda: set_difficulty("easy")
    )
    add_menu_widget(easy_btn, WIDTH // 2 - 250, HEIGHT // 2 + 40)

    medium_btn = tk.Button(
        root, text="🟡 ORTA\n(Dengeli)", font=("Arial", 16, "bold"),
        bg="#FFD700", fg="black", activebackground="#fff59d",
        bd=0, cursor="hand2", padx=20, pady=15,
        command=lambda: set_difficulty("medium")
    )
    add_menu_widget(medium_btn, WIDTH // 2, HEIGHT // 2 + 40)

    hard_btn = tk.Button(
        root, text="🔴 ZOR\n(Hızlı & Tanklar)", font=("Arial", 16, "bold"),
        bg="#d32f2f", fg="white", activebackground="#ef9a9a",
        bd=0, cursor="hand2", padx=20, pady=15,
        command=lambda: set_difficulty("hard")
    )
    add_menu_widget(hard_btn, WIDTH // 2 + 250, HEIGHT // 2 + 40)

    back_btn = tk.Button(
        root, text="◀ Geri", font=("Arial", 12),
        bg="#333", fg="white", bd=0, cursor="hand2",
        command=draw_splash_screen
    )
    add_menu_widget(back_btn, 60, HEIGHT - 40)


# ------------------ EFEKTLER ------------------
def create_explosion(x, y, color="orange", count=12):
    for _ in range(count):
        dx = random.uniform(-5, 5)
        dy = random.uniform(-5, 5)
        size = random.randint(3, 6)
        p = canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline="")
        particles.append({"id": p, "dx": dx, "dy": dy, "life": 15, "max_life": 15})


def spawn_engine_trail(x, y):
    if random.random() < 0.6:
        size = random.randint(2, 4)
        color = random.choice(["#FF6D00", "#FFAB40", "#FFD180"])
        p = canvas.create_oval(x - size, y, x + size, y + size * 2, fill=color, outline="")
        engine_trail.append({"id": p, "life": 12, "max_life": 12})


def spawn_score_popup(x, y, text, color="#FFD700"):
    item = canvas.create_text(x, y, text=text, fill=color, font=("Arial", 13, "bold"))
    score_popups.append({"id": item, "life": 24, "max_life": 24})


def spawn_near_miss_flash(x, y):
    item = canvas.create_text(x, y, text="✨", font=("Arial", 16, "bold"))
    near_miss_flashes.append({"id": item, "life": 18, "max_life": 18})


def update_particles():
    if game_started and not paused:
        for p in particles[:]:
            canvas.move(p["id"], p["dx"], p["dy"])
            p["life"] -= 1
            if p["life"] <= 0:
                canvas.delete(p["id"])
                particles.remove(p)

        for p in engine_trail[:]:
            canvas.move(p["id"], random.uniform(-0.5, 0.5), 4)
            p["life"] -= 1
            if p["life"] <= 0:
                canvas.delete(p["id"])
                engine_trail.remove(p)

        for p in score_popups[:]:
            canvas.move(p["id"], 0, -1.6)
            p["life"] -= 1
            if p["life"] <= 0:
                canvas.delete(p["id"])
                score_popups.remove(p)

        for p in near_miss_flashes[:]:
            canvas.move(p["id"], 0, -1.0)
            p["life"] -= 1
            if p["life"] <= 0:
                canvas.delete(p["id"])
                near_miss_flashes.remove(p)
    loop_after_ids["particles"] = root.after(30, update_particles)


def get_dash_cooldown():
    lvl = PROGRESS["upgrades"].get("dash", 0)
    return DASH_BASE_COOLDOWN * (0.88 ** lvl)


def try_dash(direction):
    global dash_active_until, dash_ready_at, dash_direction, invincible_until
    now = time.time()
    if now < dash_ready_at:
        return
    dash_direction = direction
    dash_active_until = now + DASH_DURATION
    dash_ready_at = now + get_dash_cooldown()
    invincible_until = max(invincible_until, now + DASH_DURATION + 0.05)
    trigger_screen_shake(intensity=4, duration=3)


def move_ship():
    global ship_vx
    if game_started and not game_over and not paused and ship:
        now = time.time()

        if now < dash_active_until:
            ship_vx = dash_direction * (SHIP_MAX_SPEED * 2.4)
        else:
            if move_left_active and not move_right_active:
                ship_vx -= SHIP_ACCEL
            elif move_right_active and not move_left_active:
                ship_vx += SHIP_ACCEL
            else:
                ship_vx *= SHIP_FRICTION
                if abs(ship_vx) < 0.05:
                    ship_vx = 0.0
            ship_vx = max(-SHIP_MAX_SPEED, min(SHIP_MAX_SPEED, ship_vx))

        dx = ship_vx
        if dx != 0:
            canvas.move(ship, dx, 0)
            canvas.move(cockpit, dx, 0)
            canvas.move(engine, dx, 0)
            if shield_aura:
                canvas.move(shield_aura, dx, 0)

        bbox = canvas.bbox(ship)
        if bbox:
            x1, _, x2, _ = bbox
            shift = -x1 if x1 < 0 else (WIDTH - x2 if x2 > WIDTH else 0)
            if shift != 0:
                ship_vx = 0.0
                for part in [ship, cockpit, engine, shield_aura]:
                    if part:
                        canvas.move(part, shift, 0)

        ebbox = canvas.bbox(engine)
        if ebbox:
            ex = (ebbox[0] + ebbox[2]) / 2
            ey = ebbox[3]
            spawn_engine_trail(ex, ey)

        if time.time() < invincible_until:
            canvas.itemconfig(shield_aura, state="normal")
        else:
            canvas.itemconfig(shield_aura, state="hidden")

        update_dash_indicator()

    if game_started:
        loop_after_ids["ship"] = root.after(16, move_ship)


def update_dash_indicator():
    if not dash_indicator_text:
        return
    now = time.time()
    remaining = dash_ready_at - now
    if remaining <= 0:
        canvas.itemconfig(dash_indicator_text, text="💨 DASH HAZIR", fill="#00E5FF")
    else:
        canvas.itemconfig(dash_indicator_text, text=f"💨 {remaining:0.1f}s", fill="#666677")


# ------------------ OYUNCU YÜKSELTME YARDIMCILARI ------------------
def get_fire_cooldown():
    lvl = PROGRESS["upgrades"].get("fire_rate", 0)
    return 0.20 * (0.92 ** lvl)


def get_bullet_damage():
    return 1 + PROGRESS["upgrades"].get("damage", 0)


def get_triple_shot_bonus_duration():
    return PROGRESS["upgrades"].get("triple", 0) * 1.5


# ------------------ OYUN MEKANİZMALARI: ATEŞ ------------------
def shoot():
    global last_shot_time
    if game_started and not game_over and not paused:
        now = time.time()
        cooldown = get_fire_cooldown()
        if now < laser_until:
            cooldown *= 0.4
        if now - last_shot_time >= cooldown:
            play_sound(sound_shoot)

            bbox = canvas.bbox(cockpit)
            if not bbox:
                return
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) / 2
            dmg = get_bullet_damage()

            if now < laser_until:
                b = canvas.create_rectangle(cx - 4, 0, cx + 4, y1, fill="#FF1744", outline="#FFCDD2")
                bullets.append({"id": b, "dx": 0, "dmg": dmg * 0.5, "piercing": True})
            elif now < triple_shot_until:
                b1 = canvas.create_rectangle(cx - 15, y1 - 15, cx - 9, y1, fill="cyan", outline="white")
                b2 = canvas.create_rectangle(cx - 3, y1 - 20, cx + 3, y1 - 5, fill="lime", outline="white")
                b3 = canvas.create_rectangle(cx + 9, y1 - 15, cx + 15, y1, fill="cyan", outline="white")
                bullets.extend([
                    {"id": b1, "dx": -2, "dmg": dmg},
                    {"id": b2, "dx": 0, "dmg": dmg},
                    {"id": b3, "dx": 2, "dmg": dmg},
                ])
            else:
                b = canvas.create_rectangle(cx - 3, y1 - 18, cx + 3, y1 - 3, fill="lime", outline="white")
                bullets.append({"id": b, "dx": 0, "dmg": dmg})
            last_shot_time = now


def auto_shoot():
    if shoot_active and game_started and not game_over and not paused:
        shoot()
    if game_started:
        loop_after_ids["auto_shoot"] = root.after(16, auto_shoot)


def current_level_for_score(s):
    return 1 + s // LEVEL_SCORE_INTERVAL


def maybe_level_up():
    global level
    new_level = current_level_for_score(score)
    if new_level > level:
        level = new_level
        if level_text:
            canvas.itemconfig(level_text, text=f"Seviye {level}")
        show_level_banner(level)


LEVEL_UNLOCK_MESSAGES = {
    2: "⚠ Yeni düşman: Hızlı Avcı!",
    3: "⚠ Yeni düşman: Zigzag Kayıkçı!",
    4: "⚠ Yeni düşman: Ateşli Nişancı!",
    5: "⚠ Yeni düşman: Zırhlı Tank!",
}


def show_level_banner(lvl):
    banner = canvas.create_text(WIDTH // 2, HEIGHT // 2 - 200, text=f"SEVİYE {lvl}! 🚀",
                                 fill="#00FFAA", font=("Impact", 46))
    unlock_msg = LEVEL_UNLOCK_MESSAGES.get(lvl)
    sub_text = unlock_msg if unlock_msg else "Düşmanlar güçleniyor..."
    sub = canvas.create_text(WIDTH // 2, HEIGHT // 2 - 150, text=sub_text,
                              fill="#FFD700" if unlock_msg else "#AAAAAA",
                              font=("Arial", 14, "italic"))
    root.after(1600, lambda: canvas.delete(banner))
    root.after(1600, lambda: canvas.delete(sub))


def enemy_types_unlocked_for_level(lvl):
    pool = ["basic"]
    if lvl >= 2:
        pool.append("fast")
    if lvl >= 3:
        pool.append("zigzag")
    if lvl >= 4:
        pool.append("shooter")
    if lvl >= 5:
        pool.append("tank")
    return pool


def get_enemy_spawn_delay():
    cfg = difficulty_settings[current_difficulty]
    base = cfg["enemy_delay"]
    floor = cfg["min_delay"]
    intensity = min(1.0, (score / 1200.0) + (level - 1) * 0.05)
    delay = base - (base - floor) * intensity
    return max(floor, int(delay))


def spawn_enemy():
    if game_started and not game_over:
        if not paused:
            diff_cfg = difficulty_settings[current_difficulty]

            global boss_active, next_boss_score
            if score >= next_boss_score and not boss_active:
                spawn_boss()
                next_boss_score += BOSS_SCORE_INTERVAL
            elif not boss_active:
                x = random.randint(40, WIDTH - 40)
                level_hp_bonus = (level - 1) // 3
                level_speed_bonus = (level - 1) * 0.15

                unlocked = enemy_types_unlocked_for_level(level)
                weight_table = {"basic": 45, "fast": 20, "zigzag": 15, "shooter": 12, "tank": 8}
                if current_difficulty == "hard":
                    weight_table = {"basic": 28, "fast": 22, "zigzag": 15, "shooter": 17, "tank": 18}
                elif current_difficulty == "easy":
                    weight_table = {"basic": 60, "fast": 18, "zigzag": 12, "shooter": 6, "tank": 4}

                choices = [(t, weight_table[t]) for t in unlocked]
                types_list, weights_list = zip(*choices)
                e_type = random.choices(types_list, weights=weights_list)[0]

                if e_type == "basic":
                    e = canvas.create_oval(x - 20, -40, x + 20, -5, fill="#FF4444", outline="white", width=2)
                    hp, speed, pts = 1, 4, 10
                elif e_type == "fast":
                    e = canvas.create_polygon(x, -35, x - 15, -5, x + 15, -5, fill="orange", outline="yellow")
                    hp, speed, pts = 1, 7, 20
                elif e_type == "zigzag":
                    e = canvas.create_polygon(x - 16, -30, x + 16, -30, x, -5, fill="#00E5FF", outline="white")
                    hp, speed, pts = 1, 3.5, 25
                elif e_type == "shooter":
                    e = canvas.create_rectangle(x - 18, -40, x + 18, -8, fill="#AA00FF", outline="#E0B0FF", width=2)
                    hp, speed, pts = 2, 2.2, 35
                else:  # tank
                    e = canvas.create_rectangle(x - 30, -50, x + 30, -5, fill="purple", outline="cyan", width=2)
                    hp, speed, pts = 3, 2, 50

                hp += level_hp_bonus
                speed += level_speed_bonus
                pts = int(pts * diff_cfg["pts_mult"])
                bbox_e = canvas.bbox(e)
                half_w = (bbox_e[2] - bbox_e[0]) / 2 if bbox_e else 20
                enemy_data = {
                    "id": e, "type": e_type, "hp": hp, "max_hp": hp, "speed": speed, "pts": pts,
                    "half_w": half_w,
                    "zig_dir": random.choice([-1, 1]), "last_shot": time.time() + random.uniform(0, 1.5)
                }
                enemies.append(enemy_data)

        delay = get_enemy_spawn_delay()
        loop_after_ids["spawn"] = root.after(delay, spawn_enemy)


def select_control_mode(mode):
    global control_mode
    control_mode = mode
    start_game()


def draw_device_menu():
    global current_state
    current_state = "DEVICE_MENU"
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 160, text="CİHAZ SEÇİMİ 🎮", fill="#00FFFF", font=HEADER_FONT)
    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 90, text="Oynayacağınız Cihazı Seçin:", fill="white", font=("Arial", 22, "bold"))

    pc_btn = tk.Button(
        root, text="💻 BİLGİSAYAR\n(Klavye Kontrolü)", font=("Arial", 16, "bold"),
        bg="#303f9f", fg="white", activebackground="#7986cb",
        bd=0, cursor="hand2", padx=15, pady=15,
        command=lambda: select_control_mode("keyboard")
    )
    add_menu_widget(pc_btn, WIDTH // 2 - 180, HEIGHT // 2 + 40)

    mobile_btn = tk.Button(
        root, text="📱 DOKUNMATİK\n(Ekran Butonları)", font=("Arial", 16, "bold"),
        bg="#f57c00", fg="black", activebackground="#ffb74d",
        bd=0, cursor="hand2", padx=15, pady=15,
        command=lambda: select_control_mode("touch")
    )
    add_menu_widget(mobile_btn, WIDTH // 2 + 180, HEIGHT // 2 + 40)

    back_btn = tk.Button(
        root, text="◀ Geri", font=("Arial", 12),
        bg="#333", fg="white", bd=0, cursor="hand2",
        command=draw_difficulty_menu
    )
    add_menu_widget(back_btn, 60, HEIGHT - 40)


# ------------------ 3 FARKLI BOSS SİSTEMİ (YENİ) ------------------
BOSS_KINDS = ["classic", "beam", "swarm"]


def spawn_boss():
    global boss_active, boss_hp_bg, boss_hp_fg, boss_label, boss_enrage_stage, boss_kind
    boss_active = True
    boss_enrage_stage = 0
    boss_kind = random.choice(BOSS_KINDS)
    x = WIDTH // 2
    diff_cfg = difficulty_settings[current_difficulty]
    hp = int(15 * diff_cfg["pts_mult"]) + (level - 1) * 3

    if boss_kind == "classic":
        e = canvas.create_polygon(
            x - 60, -60, x + 60, -60, x + 80, 0, x, 40, x - 80, 0,
            fill="#8E24AA", outline="#FF00FF", width=3
        )
        color_name, title = "#FF00FF", "⚠ BOSS ⚠"
        shot_interval = 1.6
    elif boss_kind == "beam":
        e = canvas.create_polygon(
            x - 70, -50, x + 70, -50, x + 50, 20, x - 50, 20,
            fill="#01579B", outline="#00E5FF", width=3
        )
        color_name, title = "#00E5FF", "⚠ IŞIN BOSSU ⚠"
        shot_interval = 2.4
    else:
        e = canvas.create_oval(x - 65, -65, x + 65, 5, fill="#33691E", outline="#AEEA00", width=3)
        color_name, title = "#AEEA00", "⚠ SÜRÜ BOSSU ⚠"
        shot_interval = 3.0

    enemies.append({
        "id": e, "type": "boss", "kind": boss_kind, "hp": hp, "speed": 1.5, "base_speed": 1.5,
        "pts": int(300 * diff_cfg["pts_mult"]), "dx": 3, "max_hp": hp,
        "last_shot": time.time() + 1.0, "shot_interval": shot_interval,
        "beam_phase": 0,
    })

    boss_hp_bg = canvas.create_rectangle(WIDTH // 2 - 150, 70, WIDTH // 2 + 150, 88, fill="#220022", outline=color_name)
    boss_hp_fg = canvas.create_rectangle(WIDTH // 2 - 148, 72, WIDTH // 2 + 148, 86, fill=color_name, outline="")
    boss_label = canvas.create_text(WIDTH // 2, 58, text=title, fill=color_name, font=("Impact", 20))
    show_level_banner_boss(title)


def show_level_banner_boss(title):
    clean_title = title.replace("⚠", "").strip()
    banner = canvas.create_text(WIDTH // 2, HEIGHT // 2 - 180, text=f"{clean_title} YAKLAŞIYOR!",
                                 fill="#FF00FF", font=("Impact", 36))
    root.after(1300, lambda: canvas.delete(banner))


def update_boss_hp_bar(enemy):
    global boss_enrage_stage
    if boss_hp_fg is None:
        return
    ratio = max(0, enemy["hp"]) / max(1, enemy["max_hp"])
    x1 = WIDTH // 2 - 148
    x2 = WIDTH // 2 - 148 + 296 * ratio
    canvas.coords(boss_hp_fg, x1, 72, x2, 86)

    if ratio < 0.5 and boss_enrage_stage < 1:
        boss_enrage_stage = 1
        enemy["speed"] = enemy.get("base_speed", 1.5) * 1.35
        enemy["shot_interval"] = max(0.8, enemy["shot_interval"] * 0.75)
        canvas.itemconfig(boss_hp_fg, fill="#FF6D00")
        if boss_label:
            canvas.itemconfig(boss_label, fill="#FF6D00")

    if ratio < 0.2 and boss_enrage_stage < 2:
        boss_enrage_stage = 2
        enemy["speed"] = enemy.get("base_speed", 1.5) * 1.9
        enemy["shot_interval"] = max(0.5, enemy["shot_interval"] * 0.7)
        canvas.itemconfig(boss_hp_fg, fill="#FF1744")
        if boss_label:
            canvas.itemconfig(boss_label, text="⚠ ÖFKELİ! ⚠", fill="#FF1744")


def cleanup_boss_ui():
    global boss_hp_bg, boss_hp_fg, boss_label
    for item in (boss_hp_bg, boss_hp_fg, boss_label):
        if item is not None:
            try:
                canvas.delete(item)
            except Exception:
                pass
    boss_hp_bg = boss_hp_fg = boss_label = None


def boss_fire(enemy, pos):
    xs = pos[0::2]
    ys = pos[1::2]
    ex, ey = sum(xs) / len(xs), max(ys)
    kind = enemy.get("kind", "classic")

    if kind == "classic":
        eb = canvas.create_oval(ex - 4, ey, ex + 4, ey + 8, fill="#E040FB", outline="white")
        enemy_bullets.append({"id": eb, "vx": 0, "vy": 6})
    elif kind == "beam":
        for i in range(-2, 3):
            eb = canvas.create_oval(ex - 4, ey, ex + 4, ey + 8, fill="#18FFFF", outline="white")
            enemy_bullets.append({"id": eb, "vx": i * 1.6, "vy": 5.5})
    else:
        dx_spawn = random.randint(-120, 120)
        dxp = max(30, min(WIDTH - 30, ex + dx_spawn))
        d = canvas.create_oval(dxp - 12, ey - 10, dxp + 12, ey + 14, fill="#76FF03", outline="white", width=1)
        bbox_d = canvas.bbox(d)
        half_w = (bbox_d[2] - bbox_d[0]) / 2 if bbox_d else 12
        enemies.append({
            "id": d, "type": "drone", "hp": 1, "max_hp": 1, "speed": 4.5, "pts": 15,
            "half_w": half_w, "zig_dir": random.choice([-1, 1]), "last_shot": time.time() + 999,
        })


# ------------------ POWER-UP'LAR ------------------
def spawn_powerup(x, y):
    chance = difficulty_settings[current_difficulty]["powerup_chance"]
    if random.random() < chance:
        for p in powerups:
            ppos = canvas.coords(p["id"])
            if ppos and abs(ppos[0] - x) < 40 and abs(ppos[1] - y) < 40:
                return
        p_type = random.choice(["shield", "triple", "laser", "life", "bomb"])
        symbols = {"shield": "🛡️", "triple": "🔫", "laser": "⚡", "life": "❤️", "bomb": "💣"}
        item = canvas.create_text(x, y, text=symbols[p_type], font=("Arial", 19))
        powerups.append({"id": item, "type": p_type})


def take_damage():
    global lives, invincible_until
    if time.time() < invincible_until:
        return

    play_sound(sound_damage)

    lives -= 1
    canvas.itemconfig(life_text, text=f"Can: {'❤️' * max(0,lives)}{'🖤' * max(0, 3 - lives)}")
    invincible_until = time.time() + 2.0
    update_low_hp_vignette()

    flash = canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="red")
    root.after(50, lambda: canvas.delete(flash))

    trigger_screen_shake(intensity=12, duration=10)

    if lives <= 0:
        end_game()


def update_low_hp_vignette():
    global low_hp_vignette
    if low_hp_vignette:
        try:
            canvas.delete(low_hp_vignette)
        except Exception:
            pass
        low_hp_vignette = None
    if lives == 1:
        low_hp_vignette = canvas.create_rectangle(4, 4, WIDTH - 4, HEIGHT - 4, outline="#FF1744", width=6)
        canvas.tag_lower(low_hp_vignette)


def trigger_bomb():
    for enemy in enemies[:]:
        pos = canvas.coords(enemy["id"])
        if pos:
            n = len(pos) // 2
            cx = sum(pos[0::2]) / n
            cy = sum(pos[1::2]) / n
            create_explosion(cx, cy, "yellow", count=14)
        canvas.delete(enemy["id"])
    enemies.clear()

    for eb in enemy_bullets[:]:
        canvas.delete(eb["id"])
    enemy_bullets.clear()

    trigger_screen_shake(intensity=15, duration=12)
    global boss_active
    if boss_active:
        cleanup_boss_ui()
    boss_active = False


def collision(a, b):
    try:
        bbox_a = canvas.bbox(a)
        bbox_b = canvas.bbox(b)
        if not bbox_a or not bbox_b:
            return False
        x1, y1, x2, y2 = bbox_a
        a1, b1, a2, b2 = bbox_b
        return not (x2 < a1 or x1 > a2 or y2 < b1 or y1 > b2)
    except Exception:
        return False


def near_miss_check(bullet_pos, ship_bbox):
    if not bullet_pos or not ship_bbox:
        return False
    bx1, by1, bx2, by2 = bullet_pos
    sx1, sy1, sx2, sy2 = ship_bbox
    margin = 14
    expanded = (sx1 - margin, sy1 - margin, sx2 + margin, sy2 + margin)
    close_horiz = not (bx2 < expanded[0] or bx1 > expanded[2])
    close_vert = not (by2 < expanded[1] or by1 > expanded[3])
    actually_hit = not (bx2 < sx1 or bx1 > sx2 or by2 < sy1 or by1 > sy2)
    return close_horiz and close_vert and not actually_hit


def update_sound_indicator():
    if sound_indicator_text:
        icon = "🔊" if sound_master_enabled() else "🔇"
        canvas.itemconfig(sound_indicator_text, text=icon)


def award_run_stardust(final_score, final_kills):
    earned = int(final_score * 0.12) + final_kills * 2
    PROGRESS["stardust"] += earned
    PROGRESS["total_games_played"] += 1
    PROGRESS["total_kills"] += final_kills
    PROGRESS["best_near_miss_run"] = max(PROGRESS.get("best_near_miss_run", 0), run_near_misses)
    PROGRESS["total_bosses_killed"] = PROGRESS.get("total_bosses_killed", 0) + run_bosses_killed
    save_progress()
    return earned


# ------------------ ANA GÜNCELLEME DÖNGÜSÜ ------------------
def update():
    global score, invincible_until, triple_shot_until, laser_until, lives, boss_active
    global combo_count, last_kill_time, run_kills, run_near_misses, run_bosses_killed

    if not game_started or game_over:
        return
    if paused:
        loop_after_ids["update"] = root.after(30, update)
        return

    # 1. Oyuncu mermileri
    for bullet in bullets[:]:
        canvas.move(bullet["id"], bullet["dx"], -15)
        pos = canvas.coords(bullet["id"])
        if pos and pos[1] < 0:
            canvas.delete(bullet["id"])
            bullets.remove(bullet)

    # 1b. Düşman mermileri (+ near-miss kontrolü)
    ship_bbox = canvas.bbox(ship) if ship else None
    for eb in enemy_bullets[:]:
        vx = eb.get("vx", 0)
        vy = eb.get("vy", 6)
        canvas.move(eb["id"], vx, vy)
        pos = canvas.coords(eb["id"])
        if not pos:
            continue
        if pos[1] > HEIGHT or pos[0] < -20 or pos[0] > WIDTH + 20:
            canvas.delete(eb["id"])
            enemy_bullets.remove(eb)
            continue
        if collision(eb["id"], ship):
            canvas.delete(eb["id"])
            enemy_bullets.remove(eb)
            take_damage()
            continue
        # YENİ: Near-miss — kıl payı kurtuluşları ödüllendir
        if not eb.get("near_miss_awarded") and near_miss_check(pos, ship_bbox):
            eb["near_miss_awarded"] = True
            run_near_misses += 1
            gained = 5
            score += gained
            spawn_near_miss_flash(pos[0], pos[1])
            spawn_score_popup(pos[0], pos[1] - 12, f"+{gained}", "#00E5FF")
            if score_text:
                canvas.itemconfig(score_text, text=f"Skor: {score}")

    # 2. Power-up'lar
    for p in powerups[:]:
        canvas.move(p["id"], 0, 3.5)
        pos = canvas.coords(p["id"])
        if pos and collision(p["id"], ship):
            play_sound(sound_powerup)

            if p["type"] == "shield":
                invincible_until = max(invincible_until, time.time()) + 6.0
            elif p["type"] == "triple":
                bonus = get_triple_shot_bonus_duration()
                base_dur = 8.0 + bonus
                triple_shot_until = max(triple_shot_until, time.time()) + base_dur
            elif p["type"] == "laser":
                bonus = get_triple_shot_bonus_duration()
                laser_until = max(laser_until, time.time()) + 5.0 + bonus * 0.5
            elif p["type"] == "life":
                lives = min(5, lives + 1)
                canvas.itemconfig(life_text, text=f"Can: {'❤️' * lives}")
                update_low_hp_vignette()
            elif p["type"] == "bomb":
                trigger_bomb()
            label = {"shield": "KALKAN!", "triple": "ÜÇLÜ ATIŞ!", "laser": "LAZER!",
                     "life": "EKSTRA CAN!", "bomb": "BOMBA!"}[p["type"]]
            spawn_score_popup(pos[0], pos[1] - 10, label, "#00E5FF")
            canvas.delete(p["id"])
            powerups.remove(p)
        elif pos and pos[1] > HEIGHT:
            canvas.delete(p["id"])
            powerups.remove(p)

    # Combo süresi doldu mu? (BUG FIX: artık aniden değil, HUD'da soluklaşarak biter)
    if combo_count > 0 and combo_text:
        elapsed = time.time() - last_kill_time
        if elapsed > 2.0:
            combo_count = 0
            canvas.itemconfig(combo_text, text="")
        elif elapsed > 1.4:
            # son 0.6 saniyede metni soluklaştır (görsel geri sayım hissi)
            canvas.itemconfig(combo_text, fill="#8a7a2a")
        else:
            canvas.itemconfig(combo_text, fill="#FFD700")

    # 3. Düşmanlar
    for enemy in enemies[:]:
        if enemy["type"] == "boss":
            canvas.move(enemy["id"], enemy["dx"], enemy["speed"] * 0.15)
            pos = canvas.coords(enemy["id"])
            if pos:
                xs = pos[0::2]
                if min(xs) < 20 or max(xs) > WIDTH - 20:
                    enemy["dx"] *= -1
            update_boss_hp_bar(enemy)
        elif enemy["type"] == "zigzag" or enemy["type"] == "drone":
            canvas.move(enemy["id"], enemy["zig_dir"] * 3, enemy["speed"])
            pos = canvas.coords(enemy["id"])
            # BUG FIX: Sınır kontrolü artık gerçek yarı-genişliğe (half_w) göre
            # yapılıyor; önceden merkez tabanlıydı ve düşmanlar kenardan
            # görünür şekilde taşabiliyordu.
            if pos:
                half_w = enemy.get("half_w", 16)
                xs = pos[0::2]
                cx = sum(xs) / len(xs)
                if cx - half_w < 0 or cx + half_w > WIDTH:
                    enemy["zig_dir"] *= -1
        else:
            canvas.move(enemy["id"], 0, enemy["speed"])
            pos = canvas.coords(enemy["id"])

        pos = canvas.coords(enemy["id"])
        if not pos:
            continue

        if enemy["type"] in ("shooter", "boss"):
            now = time.time()
            interval = enemy.get("shot_interval", 1.8)
            if now - enemy.get("last_shot", 0) > interval:
                enemy["last_shot"] = now
                if enemy["type"] == "boss":
                    boss_fire(enemy, pos)
                else:
                    xs = pos[0::2]
                    ys = pos[1::2]
                    ex, ey = sum(xs) / len(xs), max(ys)
                    eb = canvas.create_oval(ex - 4, ey, ex + 4, ey + 8, fill="#E040FB", outline="white")
                    enemy_bullets.append({"id": eb, "vx": 0, "vy": 6})

        if collision(enemy["id"], ship):
            ys = pos[1::2]
            xs = pos[0::2]
            ex, ey = sum(xs) / len(xs), sum(ys) / len(ys)
            create_explosion(ex, ey, "red")
            if enemy["type"] != "boss":
                canvas.delete(enemy["id"])
                enemies.remove(enemy)
            take_damage()
            continue

        if pos[1] > HEIGHT + 60:
            canvas.delete(enemy["id"])
            enemies.remove(enemy)
            if enemy["type"] == "boss":
                boss_active = False
                cleanup_boss_ui()
            continue

        for bullet in bullets[:]:
            if collision(enemy["id"], bullet["id"]):
                is_piercing = bullet.get("piercing", False)
                if not is_piercing:
                    canvas.delete(bullet["id"])
                    bullets.remove(bullet)
                enemy["hp"] -= bullet.get("dmg", 1)
                if enemy["type"] == "boss":
                    update_boss_hp_bar(enemy)
                if enemy["hp"] <= 0:
                    play_sound(sound_explosion)
                    xs = pos[0::2]
                    ys = pos[1::2]
                    ex, ey = sum(xs) / len(xs), sum(ys) / len(ys)

                    if enemy["type"] == "boss":
                        trigger_screen_shake(intensity=18, duration=16)
                        create_explosion(ex, ey, "magenta", count=40)
                        boss_active = False
                        cleanup_boss_ui()
                        run_bosses_killed += 1
                        spawn_powerup(ex - 20, ey)
                        spawn_powerup(ex + 20, ey)
                    elif enemy["type"] == "tank":
                        trigger_screen_shake(intensity=6, duration=6)
                        create_explosion(ex, ey, "purple", count=20)
                        spawn_powerup(ex, ey)
                    elif enemy["type"] == "shooter":
                        create_explosion(ex, ey, "#E040FB", count=16)
                        spawn_powerup(ex, ey)
                    elif enemy["type"] == "drone":
                        create_explosion(ex, ey, "#AEEA00", count=10)
                    else:
                        create_explosion(ex, ey, "orange", count=12)
                        spawn_powerup(ex, ey)

                    canvas.delete(enemy["id"])
                    enemies.remove(enemy)

                    run_kills += 1
                    combo_count += 1
                    last_kill_time = time.time()
                    combo_bonus = 1 + min(combo_count, 10) * 0.1
                    gained = int(enemy["pts"] * combo_bonus)
                    score += gained
                    spawn_score_popup(ex, ey, f"+{gained}")
                    canvas.itemconfig(score_text, text=f"Skor: {score}")
                    maybe_level_up()
                    if combo_text:
                        if combo_count >= 2:
                            canvas.itemconfig(combo_text, text=f"Kombo x{combo_count}!", fill="#FFD700")
                        else:
                            canvas.itemconfig(combo_text, text="")
                if is_piercing:
                    continue
                break

    loop_after_ids["update"] = root.after(30, update)


# ------------------ BAŞLATMA, DURAKLATMA VE BİTİŞ ------------------
def start_game():
    global game_started, game_over, paused, current_state, score, lives
    global score_text, life_text, combo_text, level_text, sound_indicator_text, dash_indicator_text
    global ship, cockpit, engine, shield_aura
    global move_left_active, move_right_active, shoot_active
    global next_boss_score, boss_active, combo_count, level, run_kills, run_near_misses, run_bosses_killed
    global low_hp_vignette, ship_vx, dash_ready_at, dash_active_until
    global laser_until, triple_shot_until, invincible_until, last_shot_time
    global boss_hp_bg, boss_hp_fg, boss_label, boss_enrage_stage, boss_kind

    cleanup_menu()
    cleanup_touch_controls()
    # BUG FIX: Yeni oyun başlarken önceki boss HUD referansları garantili
    # sıfırlanıyor (v3'te bazı senaryolarda None olmayan eski canvas id'leri
    # yeni oyun ekranında hataya yol açabiliyordu).
    cleanup_boss_ui()
    canvas.delete("all")

    current_state = "GAME"
    game_started = True
    game_over = False
    paused = False
    score = 0
    lives = 3
    level = 1
    run_kills = 0
    run_near_misses = 0
    run_bosses_killed = 0
    next_boss_score = BOSS_SCORE_INTERVAL
    boss_active = False
    boss_enrage_stage = 0
    boss_kind = None
    combo_count = 0
    low_hp_vignette = None
    ship_vx = 0.0
    dash_ready_at = 0.0
    dash_active_until = 0.0
    laser_until = 0
    triple_shot_until = 0
    invincible_until = 0
    last_shot_time = 0

    move_left_active = False
    move_right_active = False
    shoot_active = False

    bullets.clear()
    enemy_bullets.clear()
    enemies.clear()
    powerups.clear()
    particles.clear()
    engine_trail.clear()
    score_popups.clear()
    near_miss_flashes.clear()

    play_music()
    create_stars()

    # HUD
    score_text = canvas.create_text(20, 20, anchor="nw", fill="cyan", font=("Arial", 19, "bold"), text="Skor: 0")
    life_text = canvas.create_text(WIDTH - 55, 20, anchor="ne", fill="#FF5252", font=("Arial", 19, "bold"),
                                    text=f"Can: {'❤️' * lives}")
    combo_text = canvas.create_text(WIDTH // 2, 105, fill="#FFD700", font=("Arial", 16, "bold"), text="")
    level_text = canvas.create_text(20, 50, anchor="nw", fill="#00FFAA", font=("Arial", 14, "bold"), text=f"Seviye {level}")
    sound_indicator_text = canvas.create_text(WIDTH - 20, 45, anchor="ne", fill="white", font=("Arial", 14))
    dash_indicator_text = canvas.create_text(20, 75, anchor="nw", fill="#00E5FF", font=("Arial", 12, "bold"), text="💨 DASH HAZIR")
    update_sound_indicator()

    diff_label = difficulty_settings[current_difficulty]["label"]
    canvas.create_text(WIDTH // 2, 20, fill="#AAAAAA", font=("Arial", 16, "italic"), text=diff_label)
    canvas.create_text(WIDTH // 2, HEIGHT - 15, fill="#555577", font=("Arial", 11),
                        text="ESC: Duraklat   |   SHIFT: Dash")

    # Gemi (kuşanılmış skin ile)
    skin = SKINS[PROGRESS.get("equipped_skin", "classic")]
    sx, sy = WIDTH // 2, HEIGHT - 80
    ship = canvas.create_polygon(sx - 25, sy + 20, sx + 25, sy + 20, sx, sy - 30,
                                  fill=skin["hull"], outline=skin["cockpit"], width=2)
    cockpit = canvas.create_oval(sx - 8, sy - 10, sx + 8, sy + 10, fill=skin["cockpit"])
    engine = canvas.create_polygon(sx - 10, sy + 20, sx + 10, sy + 20, sx, sy + 40, fill=skin["engine"])
    shield_aura = canvas.create_oval(sx - 40, sy - 45, sx + 40, sy + 45, outline="cyan", width=3, state="hidden")

    if control_mode == "touch":
        setup_touch_controls()

    move_ship()
    spawn_enemy()
    update()
    auto_shoot()


def setup_touch_controls():
    bw, bh = 100, 55

    left_btn = tk.Button(root, text="◀ SOL", font=("Arial", 14, "bold"), bg="#333", fg="white")
    left_btn.place(x=30, y=HEIGHT - 80, width=bw, height=bh)
    left_btn.bind("<ButtonPress>", lambda e: set_move("left", True))
    left_btn.bind("<ButtonRelease>", lambda e: set_move("left", False))
    touch_widgets.append(left_btn)

    right_btn = tk.Button(root, text="SAĞ ▶", font=("Arial", 14, "bold"), bg="#333", fg="white")
    right_btn.place(x=140, y=HEIGHT - 80, width=bw, height=bh)
    right_btn.bind("<ButtonPress>", lambda e: set_move("right", True))
    right_btn.bind("<ButtonRelease>", lambda e: set_move("right", False))
    touch_widgets.append(right_btn)

    dash_btn = tk.Button(root, text="💨 DASH", font=("Arial", 13, "bold"), bg="#01579B", fg="white")
    dash_btn.place(x=WIDTH - 260, y=HEIGHT - 80, width=bw, height=bh)
    dash_btn.bind("<ButtonPress>", lambda e: try_dash(-1 if move_left_active else (1 if move_right_active else -1)))
    touch_widgets.append(dash_btn)

    shoot_btn = tk.Button(root, text="🔥 ATEŞ", font=("Arial", 14, "bold"), bg="#bf360c", fg="white")
    shoot_btn.place(x=WIDTH - 140, y=HEIGHT - 80, width=bw, height=bh)
    shoot_btn.bind("<ButtonPress>", lambda e: set_move("shoot", True))
    shoot_btn.bind("<ButtonRelease>", lambda e: set_move("shoot", False))
    touch_widgets.append(shoot_btn)


def toggle_pause(event=None):
    global paused, current_state
    if current_state == "GAME" and not game_over:
        paused = True
        current_state = "PAUSED"
        draw_pause_overlay()
    elif current_state == "PAUSED":
        resume_game()


def draw_pause_overlay():
    overlay = canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000000", stipple="gray50")
    title = canvas.create_text(WIDTH // 2, HEIGHT // 2 - 150, text="DURAKLATILDI ⏸", fill="#00FFFF", font=("Impact", 40))
    add_menu_canvas_item(overlay)
    add_menu_canvas_item(title)

    resume_btn = tk.Button(
        root, text="▶ Devam Et", font=("Arial", 16, "bold"),
        bg="#00E676", fg="black", bd=0, cursor="hand2", padx=15, pady=10,
        command=resume_game
    )
    add_menu_widget(resume_btn, WIDTH // 2, HEIGHT // 2 - 60)

    settings_btn = tk.Button(
        root, text="⚙️ Ayarlar", font=("Arial", 16, "bold"),
        bg="#455a64", fg="white", bd=0, cursor="hand2", padx=15, pady=10,
        command=lambda: draw_settings_menu("PAUSE")
    )
    add_menu_widget(settings_btn, WIDTH // 2, HEIGHT // 2 + 5)

    restart_btn = tk.Button(
        root, text="🔁 Yeniden Başla", font=("Arial", 16, "bold"),
        bg="#FFD700", fg="black", bd=0, cursor="hand2", padx=15, pady=10,
        command=start_game
    )
    add_menu_widget(restart_btn, WIDTH // 2, HEIGHT // 2 + 70)

    menu_btn = tk.Button(
        root, text="🏠 Ana Menü", font=("Arial", 16, "bold"),
        bg="#d32f2f", fg="white", bd=0, cursor="hand2", padx=15, pady=10,
        command=go_to_main_menu
    )
    add_menu_widget(menu_btn, WIDTH // 2, HEIGHT // 2 + 135)


def resume_game():
    global paused, current_state
    cleanup_menu()
    paused = False
    current_state = "GAME"


def go_to_main_menu():
    global game_started, game_over, paused
    cleanup_menu()
    cancel_loop("spawn", "update", "ship", "auto_shoot")
    cleanup_touch_controls()
    cleanup_boss_ui()
    stop_music()
    game_started = False
    game_over = True
    paused = False
    draw_splash_screen()


def end_game():
    global game_started, game_over, high_score, scoreboards
    game_started = False
    game_over = True

    stop_music()
    cancel_loop("spawn", "update", "ship", "auto_shoot")
    cleanup_touch_controls()
    cleanup_boss_ui()

    scoreboards, new_record = submit_score(current_difficulty, score)
    high_score = top_score_all_difficulties()

    earned = award_run_stardust(score, run_kills)
    new_achievements = check_achievements()

    draw_game_over_screen(new_record, earned, new_achievements)


def draw_game_over_screen(new_record, earned_stardust, new_achievements):
    cleanup_menu()
    canvas.delete("all")
    create_stars()

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 250, text="OYUN BİTTİ 💥", fill="#FF5252", font=("Impact", 50))
    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 185, text=f"Skor: {score}", fill="yellow", font=("Arial", 26, "bold"))
    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 150,
                        text=f"Ulaştığın Seviye: {level}   |   Yok Edilen: {run_kills}   |   Ucuz Kurtuluş: {run_near_misses}",
                        fill="#00FFAA", font=("Arial", 12))

    canvas.create_text(WIDTH // 2, HEIGHT // 2 - 115, text=f"✨ +{earned_stardust} Yıldız Tozu kazandın!",
                        fill="#FFD700", font=("Arial", 15, "bold"))

    diff_label = difficulty_settings[current_difficulty]["label"]
    if new_record:
        canvas.create_text(WIDTH // 2, HEIGHT // 2 - 85, text=f"🏆 YENİ REKOR! ({diff_label}) 🏆",
                            fill="#00FF7F", font=("Arial", 17, "bold"))
    else:
        best_this_diff = scoreboards.get(current_difficulty, [])
        best_val = best_this_diff[0] if best_this_diff else 0
        canvas.create_text(WIDTH // 2, HEIGHT // 2 - 85, text=f"{diff_label} Yüksek Skoru: {best_val}",
                            fill="#AAAAAA", font=("Arial", 14))

    y_ach = HEIGHT // 2 - 55
    if new_achievements:
        names = ", ".join(a["name"] for a in new_achievements)
        canvas.create_text(WIDTH // 2, y_ach, text=f"🏅 Yeni başarım: {names}", fill="#00E5FF", font=("Arial", 12, "bold"))
        y_ach += 25

    canvas.create_text(WIDTH // 2, y_ach + 5, text=f"🏆 En İyi 5 Skor ({diff_label}) 🏆", fill="#FFD700", font=("Arial", 13, "bold"))
    lines = format_scoreboard_lines(scoreboards.get(current_difficulty, []), limit=5)
    canvas.create_text(WIDTH // 2, y_ach + 32, text="   ".join(lines), fill="#DDDDDD", font=("Arial", 11))

    retry_btn = tk.Button(
        root, text="🔁 Tekrar Oyna", font=("Arial", 17, "bold"),
        bg="#00E676", fg="black", bd=0, cursor="hand2", padx=18, pady=11,
        command=start_game
    )
    add_menu_widget(retry_btn, WIDTH // 2 - 170, HEIGHT // 2 + 90)

    hangar_btn = tk.Button(
        root, text="🛠️ Hangar", font=("Arial", 17, "bold"),
        bg="#7c4dff", fg="white", bd=0, cursor="hand2", padx=18, pady=11,
        command=draw_hangar_menu
    )
    add_menu_widget(hangar_btn, WIDTH // 2, HEIGHT // 2 + 90)

    menu_btn = tk.Button(
        root, text="🏠 Ana Menü", font=("Arial", 17, "bold"),
        bg="#303f9f", fg="white", bd=0, cursor="hand2", padx=18, pady=11,
        command=draw_splash_screen
    )
    add_menu_widget(menu_btn, WIDTH // 2 + 170, HEIGHT // 2 + 90)


# ------------------ KONTROLLER ------------------
def set_move(direction, state):
    global move_left_active, move_right_active, shoot_active
    if direction == "left":
        move_left_active = state
    elif direction == "right":
        move_right_active = state
    elif direction == "shoot":
        shoot_active = state


def handle_key_press(event):
    if current_state == "GAME" and control_mode == "keyboard":
        if event.keysym == "Left":
            set_move("left", True)
        elif event.keysym == "Right":
            set_move("right", True)
        elif event.keysym == "space":
            set_move("shoot", True)
        elif event.keysym in ("Shift_L", "Shift_R"):
            # YENİ: Dash — mevcut hareket yönüne, yoksa son yöne doğru
            direction = -1 if move_left_active else (1 if move_right_active else (1 if ship_vx >= 0 else -1))
            try_dash(direction)
    if event.keysym == "Escape":
        toggle_pause()


def handle_key_release(event):
    if event.keysym == "Left":
        set_move("left", False)
    elif event.keysym == "Right":
        set_move("right", False)
    elif event.keysym == "space":
        set_move("shoot", False)


root.bind("<KeyPress>", handle_key_press)
root.bind("<KeyRelease>", handle_key_release)

# ------------------ BAŞLANGIÇ ------------------
create_stars()
update_stars()
update_particles()
draw_splash_screen()

root.mainloop()