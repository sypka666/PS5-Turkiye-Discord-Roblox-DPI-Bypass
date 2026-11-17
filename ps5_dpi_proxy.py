import asyncio
import socket
import struct
import threading
import urllib.request
import json
import os
import sys
import datetime
import subprocess
import webbrowser
import ctypes
import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont, messagebox

# Windows Yüksek DPI (Ölçekleme) Desteği
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Sürüm ve GitHub Otomatik Güncelleme Sabitleri
# ---------------------------------------------------------------------------
APP_VERSION = "v1.0.0"
GITHUB_REPO = "sypka666/PS5-Turkiye-Discord-Roblox-DPI-Bypass"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"


def parse_version_tuple(v_str: str) -> tuple:
    """'v1.2.3' gibi sürüm metinlerini karşılaştırılabilir (1, 2, 3) tuple'ına çevirir."""
    clean = v_str.strip().lstrip("vV").split("-")[0]
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


# ---------------------------------------------------------------------------
# Ayarlar (Config) Yöneticisi
# ---------------------------------------------------------------------------
def get_config_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")


DEFAULT_CONFIG = {
    "port": 8080,
    "split_pos": 2,
    "use_doh": True,
    "doh_url": "https://1.1.1.1/dns-query",
    "auto_start": True,
    "font_family": "Segoe UI",
    "font_size": 10,
    "log_font_family": "Consolas",
    "theme": "Obsidian Black",
}

THEMES = {
    "Obsidian Black": {
        "bg": "#0b0b0c",
        "panel": "#141416",
        "card": "#1c1c1f",
        "border": "#2c2c30",
        "fg": "#f0f0f2",
        "fg_muted": "#8e8e96",
        "accent": "#d4d4d8",
        "btn_bg": "#27272a",
        "btn_fg": "#fafafa",
        "btn_active": "#3f3f46",
        "status_on": "#4ade80",
        "status_off": "#f87171",
        "log_bg": "#070708",
        "log_fg": "#d4d4d8",
    },
    "Carbon Gray": {
        "bg": "#18181b",
        "panel": "#202024",
        "card": "#27272a",
        "border": "#3f3f46",
        "fg": "#f4f4f5",
        "fg_muted": "#a1a1aa",
        "accent": "#e4e4e7",
        "btn_bg": "#3f3f46",
        "btn_fg": "#ffffff",
        "btn_active": "#52525b",
        "status_on": "#22c55e",
        "status_off": "#ef4444",
        "log_bg": "#101012",
        "log_fg": "#e4e4e7",
    },
    "Silver Monochrome": {
        "bg": "#121212",
        "panel": "#1e1e1e",
        "card": "#252525",
        "border": "#383838",
        "fg": "#ffffff",
        "fg_muted": "#9e9e9e",
        "accent": "#bdbdbd",
        "btn_bg": "#333333",
        "btn_fg": "#ffffff",
        "btn_active": "#484848",
        "status_on": "#69f0ae",
        "status_off": "#ff5252",
        "log_bg": "#0a0a0a",
        "log_fg": "#e0e0e0",
    },
}

POPULAR_FONTS = [
    "Segoe UI",
    "Comic Sans MS",
    "Arial",
    "Calibri",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
    "Georgia",
    "Times New Roman",
    "Courier New",
    "Consolas",
    "Impact",
]


def load_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                cfg.update(user_cfg)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# DNS-over-HTTPS (DoH) Çözücü
# ---------------------------------------------------------------------------
dns_cache = {}


def resolve_doh(hostname: str, doh_url: str = "https://1.1.1.1/dns-query") -> str:
    """Alan adını DoH üzerinden çözer, ISS DNS engelini atlar."""
    try:
        socket.inet_aton(hostname)
        return hostname
    except OSError:
        pass

    if hostname in dns_cache:
        return dns_cache[hostname]

    try:
        url = f"{doh_url}?name={hostname}&type=A"
        req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if "Answer" in data:
                for ans in data["Answer"]:
                    if ans.get("type") == 1:
                        ip = ans.get("data")
                        dns_cache[hostname] = ip
                        return ip
    except Exception:
        pass

    ip = socket.gethostbyname(hostname)
    dns_cache[hostname] = ip
    return ip


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# DPI Bypass (ciadpi / ByeDPI Desync & Split Mantığı) + HTTP Proxy Sunucusu
# ---------------------------------------------------------------------------
class PS5DPIProxyServer:
    def __init__(
        self,
        host="0.0.0.0",
        port=8080,
        split_pos=2,
        use_doh=True,
        doh_url="https://1.1.1.1/dns-query",
        log_cb=None,
        stats_cb=None,
    ):
        self.host = host
        self.port = port
        self.split_pos = split_pos
        self.use_doh = use_doh
        self.doh_url = doh_url
        self.log_cb = log_cb
        self.stats_cb = stats_cb
        self.server = None
        self.loop = None
        self.running = False
        self.active_connections = 0
        self.total_requests = 0

    def log(self, msg: str):
        if self.log_cb:
            self.log_cb(msg)

    def _notify_stats(self):
        if self.stats_cb:
            self.stats_cb(self.active_connections, self.total_requests)

    async def pipe_data(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, is_client_to_remote=False):
        first_packet = True
        try:
            while self.running:
                data = await reader.read(16384)
                if not data:
                    break

                if is_client_to_remote and first_packet:
                    first_packet = False
                    # TLS Handshake (0x16 = Handshake, 0x03 = TLS)
                    if len(data) > 5 and data[0] == 0x16 and data[1] == 0x03:
                        await self.send_dpi_fragmented_tls(writer, data)
                        continue
                    # HTTP düz metin ise Host başlığından böl
                    elif data.startswith((b"GET ", b"POST ", b"HEAD ", b"PUT ", b"DELETE ", b"OPTIONS ")):
                        host_idx = data.find(b"Host: ")
                        if host_idx != -1 and len(data) > host_idx + 8:
                            split_at = host_idx + 7
                            writer.write(data[:split_at])
                            await writer.drain()
                            await asyncio.sleep(0.005)
                            writer.write(data[split_at:])
                            await writer.drain()
                            continue

                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def send_dpi_fragmented_tls(self, writer: asyncio.StreamWriter, data: bytes):
        """
        TLS ClientHello paketini hem TLS Record katmanında (Record Fragmentation)
        hem de TCP segment katmanında (TCP_NODELAY) küçük parçalara böler.
        """
        try:
            record_type = data[0]
            tls_ver_major = data[1]
            tls_ver_minor = data[2]
            record_len = struct.unpack("!H", data[3:5])[0]
            payload = data[5:]

            s_pos = max(1, min(self.split_pos, len(payload) - 1))

            if len(payload) == record_len and s_pos > 0:
                part1 = payload[:s_pos]
                part2 = payload[s_pos:]

                rec1 = bytes([record_type, tls_ver_major, tls_ver_minor]) + struct.pack("!H", len(part1)) + part1
                rec2 = bytes([record_type, tls_ver_major, tls_ver_minor]) + struct.pack("!H", len(part2)) + part2

                writer.write(rec1)
                await writer.drain()
                await asyncio.sleep(0.01)

                mid = min(8, len(rec2) - 1)
                writer.write(rec2[:mid])
                await writer.drain()
                await asyncio.sleep(0.01)
                writer.write(rec2[mid:])
                await writer.drain()
            else:
                writer.write(data[:2])
                await writer.drain()
                await asyncio.sleep(0.01)
                writer.write(data[2:7])
                await writer.drain()
                await asyncio.sleep(0.01)
                writer.write(data[7:])
                await writer.drain()
        except Exception:
            writer.write(data)
            await writer.drain()

    async def handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        self.active_connections += 1
        self._notify_stats()
        try:
            header_data = await asyncio.wait_for(client_reader.readuntil(b"\r\n\r\n"), timeout=10)
        except Exception:
            self.active_connections -= 1
            self._notify_stats()
            client_writer.close()
            return

        try:
            header_text = header_data.decode("latin-1")
            first_line = header_text.split("\r\n")[0]
            parts = first_line.split(" ")
            if len(parts) < 2:
                client_writer.close()
                self.active_connections -= 1
                self._notify_stats()
                return

            method = parts[0].upper()
            target = parts[1]

            if method == "CONNECT":
                if ":" in target:
                    host, port_str = target.rsplit(":", 1)
                    port = int(port_str)
                else:
                    host = target
                    port = 443

                target_ip = await asyncio.get_event_loop().run_in_executor(
                    None,
                    (lambda h: resolve_doh(h, self.doh_url)) if self.use_doh else socket.gethostbyname,
                    host,
                )

                self.total_requests += 1
                self._notify_stats()
                low_host = host.lower()
                if "discord" in low_host or "gateway" in low_host:
                    self.log(f"[DISCORD] {host}:{port} -> {target_ip} (TLS Split={self.split_pos})")
                elif "roblox" in low_host or "rbxcdn" in low_host:
                    self.log(f"[ROBLOX]  {host}:{port} -> {target_ip} (TLS Split={self.split_pos})")
                else:
                    self.log(f"[TÜNEL]   {host}:{port} -> {target_ip}")

                remote_reader, remote_writer = await asyncio.wait_for(
                    asyncio.open_connection(target_ip, port), timeout=10
                )

                sock = remote_writer.get_extra_info("socket")
                if sock:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await client_writer.drain()

                await asyncio.gather(
                    self.pipe_data(client_reader, remote_writer, is_client_to_remote=True),
                    self.pipe_data(remote_reader, client_writer, is_client_to_remote=False),
                )
            else:
                host = None
                port = 80
                for line in header_text.split("\r\n")[1:]:
                    if line.lower().startswith("host:"):
                        host_val = line.split(":", 1)[1].strip()
                        if ":" in host_val:
                            host, p = host_val.rsplit(":", 1)
                            port = int(p)
                        else:
                            host = host_val
                        break

                if not host:
                    client_writer.close()
                    self.active_connections -= 1
                    self._notify_stats()
                    return

                target_ip = await asyncio.get_event_loop().run_in_executor(
                    None,
                    (lambda h: resolve_doh(h, self.doh_url)) if self.use_doh else socket.gethostbyname,
                    host,
                )
                self.total_requests += 1
                self._notify_stats()
                self.log(f"[HTTP]    {host}:{port} -> {target_ip}")

                remote_reader, remote_writer = await asyncio.wait_for(
                    asyncio.open_connection(target_ip, port), timeout=10
                )
                sock = remote_writer.get_extra_info("socket")
                if sock:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                remote_writer.write(header_data[:12])
                await remote_writer.drain()
                await asyncio.sleep(0.005)
                remote_writer.write(header_data[12:])
                await remote_writer.drain()

                await asyncio.gather(
                    self.pipe_data(client_reader, remote_writer, is_client_to_remote=False),
                    self.pipe_data(remote_reader, client_writer, is_client_to_remote=False),
                )

        except Exception as e:
            self.log(f"[HATA]    {target if 'target' in locals() else ''}: {e}")
        finally:
            self.active_connections = max(0, self.active_connections - 1)
            self._notify_stats()
            try:
                client_writer.close()
            except Exception:
                pass

    def start_in_thread(self):
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.running = True

            async def runner():
                self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
                self.log(f"[AKTİF] Sunucu dinlemede -> {get_local_ip()}:{self.port} (TLS Split: {self.split_pos} byte)")
                async with self.server:
                    await self.server.serve_forever()

            try:
                self.loop.run_until_complete(runner())
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.log(f"[KRİTİK] Sunucu başlatılamadı: {e}")
            finally:
                self.running = False

        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        if self.loop and self.server:
            self.loop.call_soon_threadsafe(self.server.close)
            for task in asyncio.all_tasks(self.loop):
                self.loop.call_soon_threadsafe(task.cancel)
        self.log("[DURDU] Proxy sunucusu kapatıldı.")


# ---------------------------------------------------------------------------
# Siyah & Gri Özelleştirilebilir Masaüstü Arayüzü (GUI)
# ---------------------------------------------------------------------------
class AppGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PS5 Discord & Roblox DPI Bypass Proxy")

        # Ekranın ortasında geniş ve ferah bir çözünürlükle başlat (1020x720)
        win_w, win_h = 1020, 720
        scr_w = self.root.winfo_screenwidth()
        scr_h = self.root.winfo_screenheight()
        pos_x = max(0, (scr_w - win_w) // 2)
        pos_y = max(0, (scr_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(920, 650)

        # Uygulama simgesini (app_icon.ico) yükle
        try:
            if getattr(sys, "frozen", False):
                base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, "app_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.cfg = load_config()
        self.local_ip = get_local_ip()
        self.proxy_server = None
        self.current_tab = "dashboard"

        # Sistemdeki tüm fontları al ve popüler olanları en üste koy
        sys_fonts = sorted(list(set(tkfont.families())))
        self.available_fonts = []
        for pf in POPULAR_FONTS:
            if pf in sys_fonts and pf not in self.available_fonts:
                self.available_fonts.append(pf)
        for sf in sys_fonts:
            if not sf.startswith("@") and sf not in self.available_fonts:
                self.available_fonts.append(sf)

        self._build_ui()
        self.apply_styles()

        if self.cfg.get("auto_start", True):
            self.root.after(350, self.start_server)

        # Açılışta arka planda sessizce yeni GitHub sürümü var mı kontrol et
        self.root.after(1500, lambda: self.check_for_updates(silent=True))

    def get_theme(self) -> dict:
        t_name = self.cfg.get("theme", "Obsidian Black")
        return THEMES.get(t_name, THEMES["Obsidian Black"])

    def _build_ui(self):
        # Üst Navigasyon Barı (Header)
        self.header_frame = tk.Frame(self.root, pady=14, padx=22)
        self.header_frame.pack(fill="x")

        # Sağ Üst Menü Butonları (Önce pack ediliyor ki pencere daralsa bile asla kesilmesin!)
        nav_box = tk.Frame(self.header_frame)
        nav_box.pack(side="right", anchor="center")
        self.nav_box = nav_box

        self.btn_tab_main = tk.Button(
            nav_box,
            text="📡 Ana Ekran",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: self.switch_tab("dashboard"),
        )
        self.btn_tab_main.pack(side="left", padx=(0, 8))

        self.btn_tab_settings = tk.Button(
            nav_box,
            text="⚙ Ayarlar & Görünüm",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: self.switch_tab("settings"),
        )
        self.btn_tab_settings.pack(side="left", padx=(0, 8))

        self.btn_check_update = tk.Button(
            nav_box,
            text="🔄 Güncellemeleri Kontrol Et",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: self.check_for_updates(silent=False),
        )
        self.btn_check_update.pack(side="left")

        # Sol Başlık Alanı
        title_box = tk.Frame(self.header_frame)
        title_box.pack(side="left", fill="x", expand=True)
        self.title_box = title_box

        self.lbl_title = tk.Label(title_box, text=f"PS5 DISCORD & ROBLOX DPI BYPASS  ({APP_VERSION})", anchor="w")
        self.lbl_title.pack(anchor="w")

        self.lbl_subtitle = tk.Label(
            title_box,
            text="ciadpi / ByeDPI Tabanlı Yerel Ağ HTTP Proxy & DoH Çözücü",
            anchor="w",
        )
        self.lbl_subtitle.pack(anchor="w")

        # İnce Ayırıcı Çizgi
        self.sep_line = tk.Frame(self.root, height=1)
        self.sep_line.pack(fill="x")

        # Ana İçerik Konteyneri
        self.content_container = tk.Frame(self.root)
        self.content_container.pack(fill="both", expand=True, padx=18, pady=(14, 4))

        self.page_dashboard = tk.Frame(self.content_container)
        self.page_settings = tk.Frame(self.content_container)

        # Sağ Alt Köşe Küçük Credits (sypka666)
        self.footer_frame = tk.Frame(self.root, padx=18, pady=4)
        self.footer_frame.pack(fill="x", side="bottom")
        self.lbl_credits = tk.Label(self.footer_frame, text="sypka666", anchor="e")
        self.lbl_credits.pack(side="right")

        self._build_dashboard_page()
        self._build_settings_page()

        self.switch_tab("dashboard")

    # -----------------------------------------------------------------------
    # 1. ANA EKRAN (DASHBOARD)
    # -----------------------------------------------------------------------
    def _build_dashboard_page(self):
        # Üst Bilgi ve Kontrol Kartları
        top_row = tk.Frame(self.page_dashboard)
        top_row.pack(fill="x", pady=(0, 12))
        self.dash_top_row = top_row

        # Sol Kart: PS5 Bağlantı Bilgileri
        self.card_ps5 = tk.Frame(top_row, padx=16, pady=14, highlightthickness=1)
        self.card_ps5.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.lbl_card_ps5_title = tk.Label(self.card_ps5, text="PS5 AĞ AYARLARI (PROXY)", anchor="w")
        self.lbl_card_ps5_title.pack(fill="x", pady=(0, 8))

        info_grid = tk.Frame(self.card_ps5)
        info_grid.pack(fill="x")
        self.info_grid = info_grid

        self.lbl_ip_caption = tk.Label(info_grid, text="Proxy IP Adresi:", anchor="w")
        self.lbl_ip_caption.grid(row=0, column=0, sticky="w", pady=4)

        self.lbl_ip_val = tk.Label(info_grid, text=self.local_ip, padx=10, pady=2)
        self.lbl_ip_val.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        self.btn_copy_ip = tk.Button(
            info_grid,
            text="Kopyala",
            relief="flat",
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.copy_ip_port,
        )
        self.btn_copy_ip.grid(row=0, column=2, sticky="w", padx=4)

        self.lbl_port_caption = tk.Label(info_grid, text="Proxy Portu:", anchor="w")
        self.lbl_port_caption.grid(row=1, column=0, sticky="w", pady=4)

        self.lbl_port_val = tk.Label(info_grid, text=str(self.cfg["port"]), padx=10, pady=2)
        self.lbl_port_val.grid(row=1, column=1, sticky="w", padx=10, pady=4)

        self.lbl_ps5_guide = tk.Label(
            self.card_ps5,
            text="PS5 > Ayarlar > Ağ > İnternet Bağlantısını Ayarla > Ağı Seç (Options) > Gelişmiş Ayarlar\n"
            "• DNS: Manuel (1.1.1.1 / 1.0.0.1)   • Proxy Sunucusu: Kullan (Yukarıdaki IP ve Port)",
            justify="left",
            anchor="w",
        )
        self.lbl_ps5_guide.pack(fill="x", pady=(10, 0))

        # Sağ Kart: Durum ve Başlat/Durdur
        self.card_ctrl = tk.Frame(top_row, padx=16, pady=14, highlightthickness=1, width=230)
        self.card_ctrl.pack(side="right", fill="y")
        self.card_ctrl.pack_propagate(False)

        self.lbl_status_title = tk.Label(self.card_ctrl, text="SUNUCU DURUMU", anchor="w")
        self.lbl_status_title.pack(fill="x")

        self.lbl_status_badge = tk.Label(self.card_ctrl, text="● DURDURULDU", anchor="w", pady=6)
        self.lbl_status_badge.pack(fill="x")

        self.lbl_stats = tk.Label(self.card_ctrl, text="Aktif Tünel: 0  |  Toplam: 0", anchor="w")
        self.lbl_stats.pack(fill="x", pady=(0, 12))

        self.btn_toggle_srv = tk.Button(
            self.card_ctrl,
            text="▶ BAŞLAT",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self.toggle_server,
        )
        self.btn_toggle_srv.pack(fill="x", side="bottom")

        # Alt Kısım: Canlı Konsol Logları
        self.card_log = tk.Frame(self.page_dashboard, padx=12, pady=10, highlightthickness=1)
        self.card_log.pack(fill="both", expand=True)

        log_header = tk.Frame(self.card_log)
        log_header.pack(fill="x", pady=(0, 6))
        self.log_header = log_header

        self.lbl_log_title = tk.Label(log_header, text="CANLI TRAFİK VE DPI KAYITLARI (LOG)", anchor="w")
        self.lbl_log_title.pack(side="left")

        self.btn_clear_log = tk.Button(
            log_header,
            text="Temizle",
            relief="flat",
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.clear_logs,
        )
        self.btn_clear_log.pack(side="right")

        self.btn_test_discord = tk.Button(
            log_header,
            text="⚡ Discord Bağlantısını Test Et",
            relief="flat",
            padx=10,
            pady=1,
            cursor="hand2",
            command=self.test_discord_connection,
        )
        self.btn_test_discord.pack(side="right", padx=(0, 6))

        self.log_box = scrolledtext.ScrolledText(
            self.card_log,
            state="disabled",
            relief="flat",
            borderwidth=0,
            height=12,
        )
        self.log_box.pack(fill="both", expand=True)

    # -----------------------------------------------------------------------
    # 2. AYARLAR VE ÖZELLEŞTİRME SAYFASI (SETTINGS)
    # -----------------------------------------------------------------------
    def _build_settings_page(self):
        # Görünüm ve Yazı Tipi Kartı
        self.card_appearance = tk.Frame(self.page_settings, padx=18, pady=14, highlightthickness=1)
        self.card_appearance.pack(fill="x", pady=(0, 12))

        self.lbl_app_title = tk.Label(self.card_appearance, text="🎨 GÖRÜNÜM VE YAZI FONTU ÖZELLEŞTİRME", anchor="w")
        self.lbl_app_title.pack(fill="x", pady=(0, 10))

        form_app = tk.Frame(self.card_appearance)
        form_app.pack(fill="x")
        self.form_app = form_app

        # Tema Seçimi
        self.lbl_theme = tk.Label(form_app, text="Renk Teması (Siyah / Gri):", anchor="w")
        self.lbl_theme.grid(row=0, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_theme = tk.StringVar(value=self.cfg.get("theme", "Obsidian Black"))
        self.cmb_theme = ttk.Combobox(
            form_app,
            textvariable=self.var_theme,
            values=list(THEMES.keys()),
            state="readonly",
            width=24,
        )
        self.cmb_theme.grid(row=0, column=1, sticky="w", pady=6)
        self.cmb_theme.bind("<<ComboboxSelected>>", lambda e: self.on_live_preview())

        # Arayüz Font Ailesi (Comic Sans MS dahil)
        self.lbl_font = tk.Label(form_app, text="Arayüz Yazı Fontu:", anchor="w")
        self.lbl_font.grid(row=1, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_font = tk.StringVar(value=self.cfg.get("font_family", "Segoe UI"))
        self.cmb_font = ttk.Combobox(
            form_app,
            textvariable=self.var_font,
            values=self.available_fonts,
            state="readonly",
            width=24,
        )
        self.cmb_font.grid(row=1, column=1, sticky="w", pady=6)
        self.cmb_font.bind("<<ComboboxSelected>>", lambda e: self.on_live_preview())

        # Hızlı Font Butonları (Comic Sans MS, Segoe UI, Consolas)
        quick_font_frame = tk.Frame(form_app)
        quick_font_frame.grid(row=1, column=2, sticky="w", padx=12)
        self.quick_font_frame = quick_font_frame

        self.btn_comic = tk.Button(
            quick_font_frame,
            text="Comic Sans MS",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.set_quick_font("Comic Sans MS"),
        )
        self.btn_comic.pack(side="left", padx=2)

        self.btn_segoe = tk.Button(
            quick_font_frame,
            text="Segoe UI",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.set_quick_font("Segoe UI"),
        )
        self.btn_segoe.pack(side="left", padx=2)

        self.btn_consolas = tk.Button(
            quick_font_frame,
            text="Consolas",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.set_quick_font("Consolas"),
        )
        self.btn_consolas.pack(side="left", padx=2)

        # Font Boyutu
        self.lbl_fsize = tk.Label(form_app, text="Yazı Boyutu (Punto):", anchor="w")
        self.lbl_fsize.grid(row=2, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_fsize = tk.IntVar(value=int(self.cfg.get("font_size", 10)))
        self.spn_fsize = tk.Spinbox(
            form_app,
            from_=8,
            to=15,
            textvariable=self.var_fsize,
            width=8,
            relief="flat",
            command=self.on_live_preview,
        )
        self.spn_fsize.grid(row=2, column=1, sticky="w", pady=6)

        # Log Ekranı Fontu
        self.lbl_log_font = tk.Label(form_app, text="Konsol (Log) Fontu:", anchor="w")
        self.lbl_log_font.grid(row=3, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_log_font = tk.StringVar(value=self.cfg.get("log_font_family", "Consolas"))
        self.cmb_log_font = ttk.Combobox(
            form_app,
            textvariable=self.var_log_font,
            values=self.available_fonts,
            state="readonly",
            width=24,
        )
        self.cmb_log_font.grid(row=3, column=1, sticky="w", pady=6)
        self.cmb_log_font.bind("<<ComboboxSelected>>", lambda e: self.on_live_preview())

        # Ağ ve DPI Ayarları Kartı
        self.card_network = tk.Frame(self.page_settings, padx=18, pady=14, highlightthickness=1)
        self.card_network.pack(fill="x", pady=(0, 12))

        self.lbl_net_title = tk.Label(self.card_network, text="🌐 PROXY VE DPI PAKET PARÇALAMA AYARLARI", anchor="w")
        self.lbl_net_title.pack(fill="x", pady=(0, 10))

        form_net = tk.Frame(self.card_network)
        form_net.pack(fill="x")
        self.form_net = form_net

        self.lbl_set_port = tk.Label(form_net, text="Dinlenecek Proxy Portu:", anchor="w")
        self.lbl_set_port.grid(row=0, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_port = tk.IntVar(value=int(self.cfg.get("port", 8080)))
        self.ent_port = tk.Entry(form_net, textvariable=self.var_port, width=12, relief="flat")
        self.ent_port.grid(row=0, column=1, sticky="w", pady=6)

        self.lbl_split = tk.Label(form_net, text="TLS SNI Split Pozisyonu (Byte):", anchor="w")
        self.lbl_split.grid(row=1, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_split = tk.IntVar(value=int(self.cfg.get("split_pos", 2)))
        self.ent_split = tk.Entry(form_net, textvariable=self.var_split, width=12, relief="flat")
        self.ent_split.grid(row=1, column=1, sticky="w", pady=6)

        self.lbl_doh_url = tk.Label(form_net, text="DoH (DNS-over-HTTPS) Sunucusu:", anchor="w")
        self.lbl_doh_url.grid(row=2, column=0, sticky="w", pady=6, padx=(0, 16))

        self.var_doh_url = tk.StringVar(value=self.cfg.get("doh_url", "https://1.1.1.1/dns-query"))
        self.cmb_doh = ttk.Combobox(
            form_net,
            textvariable=self.var_doh_url,
            values=[
                "https://1.1.1.1/dns-query",
                "https://cloudflare-dns.com/dns-query",
                "https://dns.google/resolve",
            ],
            width=32,
        )
        self.cmb_doh.grid(row=2, column=1, columnspan=2, sticky="w", pady=6)

        self.var_use_doh = tk.BooleanVar(value=bool(self.cfg.get("use_doh", True)))
        self.chk_doh = tk.Checkbutton(
            form_net,
            text="ISP DNS Engelini Aşmak İçin DoH Kullan (Önerilen)",
            variable=self.var_use_doh,
            anchor="w",
            relief="flat",
        )
        self.chk_doh.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        self.var_autostart = tk.BooleanVar(value=bool(self.cfg.get("auto_start", True)))
        self.chk_autostart = tk.Checkbutton(
            form_net,
            text="Uygulama Açıldığında Proxy Sunucusunu Otomatik Başlat",
            variable=self.var_autostart,
            anchor="w",
            relief="flat",
        )
        self.chk_autostart.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)

        # Alt Butonlar (Kaydet, Firewall İzni, Varsayılana Dön)
        btn_bar = tk.Frame(self.page_settings)
        btn_bar.pack(fill="x", pady=(4, 0))
        self.settings_btn_bar = btn_bar

        self.btn_save_cfg = tk.Button(
            btn_bar,
            text="💾 Ayarları Kaydet ve Uygula",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.save_and_apply_settings,
        )
        self.btn_save_cfg.pack(side="left", padx=(0, 8))

        self.btn_fw = tk.Button(
            btn_bar,
            text="🛡 Windows Güvenlik Duvarı Port İzni Ekle",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.add_firewall_rule,
        )
        self.btn_fw.pack(side="left", padx=(0, 8))

        self.btn_reset_cfg = tk.Button(
            btn_bar,
            text="Varsayılanlara Sıfırla",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.reset_defaults,
        )
        self.btn_reset_cfg.pack(side="right")

    # -----------------------------------------------------------------------
    # STİL VE FONT UYGULAYICI
    # -----------------------------------------------------------------------
    def apply_styles(self):
        t = self.get_theme()
        ff = self.cfg.get("font_family", "Segoe UI")
        fs = int(self.cfg.get("font_size", 10))
        lff = self.cfg.get("log_font_family", "Consolas")

        f_title = (ff, fs + 4, "bold")
        f_sub = (ff, max(8, fs - 1))
        f_sec = (ff, fs, "bold")
        f_norm = (ff, fs)
        f_bold = (ff, fs, "bold")
        f_code = (lff, fs + 2, "bold")
        f_log = (lff, max(8, fs - 1))

        self.root.configure(bg=t["bg"])
        self.header_frame.configure(bg=t["panel"])
        self.title_box.configure(bg=t["panel"])
        self.nav_box.configure(bg=t["panel"])
        self.sep_line.configure(bg=t["border"])
        self.content_container.configure(bg=t["bg"])
        self.page_dashboard.configure(bg=t["bg"])
        self.page_settings.configure(bg=t["bg"])
        self.dash_top_row.configure(bg=t["bg"])

        self.lbl_title.configure(font=f_title, fg=t["fg"], bg=t["panel"])
        self.lbl_subtitle.configure(font=f_sub, fg=t["fg_muted"], bg=t["panel"])
        self.footer_frame.configure(bg=t["bg"])
        self.lbl_credits.configure(font=(ff, max(8, fs - 2)), fg=t["fg_muted"], bg=t["bg"])

        # Sekme butonları
        for btn, tab_name in [(self.btn_tab_main, "dashboard"), (self.btn_tab_settings, "settings")]:
            is_active = self.current_tab == tab_name
            btn.configure(
                font=f_bold if is_active else f_norm,
                bg=t["btn_active"] if is_active else t["btn_bg"],
                fg=t["btn_fg"],
                activebackground=t["btn_active"],
                activeforeground=t["btn_fg"],
            )

        # Dashboard Kartları
        for card in [self.card_ps5, self.card_ctrl, self.card_log, self.card_appearance, self.card_network]:
            card.configure(bg=t["card"], highlightbackground=t["border"], highlightcolor=t["border"])

        self.info_grid.configure(bg=t["card"])
        self.log_header.configure(bg=t["card"])

        self.lbl_card_ps5_title.configure(font=f_sec, fg=t["accent"], bg=t["card"])
        self.lbl_ip_caption.configure(font=f_norm, fg=t["fg"], bg=t["card"])
        self.lbl_port_caption.configure(font=f_norm, fg=t["fg"], bg=t["card"])
        self.lbl_ip_val.configure(font=f_code, fg=t["fg"], bg=t["panel"])
        self.lbl_port_val.configure(font=f_code, fg=t["fg"], bg=t["panel"])
        self.lbl_ps5_guide.configure(font=f_sub, fg=t["fg_muted"], bg=t["card"])

        self.lbl_status_title.configure(font=f_sec, fg=t["accent"], bg=t["card"])
        is_running = bool(self.proxy_server and self.proxy_server.running)
        self.lbl_status_badge.configure(
            font=(ff, fs + 1, "bold"),
            fg=t["status_on"] if is_running else t["status_off"],
            bg=t["card"],
            text="● AKTİF (ÇALIŞIYOR)" if is_running else "● DURDURULDU",
        )
        self.lbl_stats.configure(font=f_sub, fg=t["fg_muted"], bg=t["card"])

        self.btn_toggle_srv.configure(
            font=f_bold,
            bg=t["btn_active"] if is_running else t["btn_bg"],
            fg=t["btn_fg"],
            activebackground=t["border"],
            activeforeground=t["btn_fg"],
            text="⏹ SUNUCUYU DURDUR" if is_running else "▶ SUNUCUYU BAŞLAT",
        )

        self.lbl_log_title.configure(font=f_sec, fg=t["accent"], bg=t["card"])
        self.log_box.configure(font=f_log, bg=t["log_bg"], fg=t["log_fg"], insertbackground=t["fg"])

        # Ayarlar Sayfası
        self.form_app.configure(bg=t["card"])
        self.form_net.configure(bg=t["card"])
        self.quick_font_frame.configure(bg=t["card"])
        self.settings_btn_bar.configure(bg=t["bg"])

        self.lbl_app_title.configure(font=f_sec, fg=t["accent"], bg=t["card"])
        self.lbl_net_title.configure(font=f_sec, fg=t["accent"], bg=t["card"])

        for lbl in [
            self.lbl_theme,
            self.lbl_font,
            self.lbl_fsize,
            self.lbl_log_font,
            self.lbl_set_port,
            self.lbl_split,
            self.lbl_doh_url,
        ]:
            lbl.configure(font=f_norm, fg=t["fg"], bg=t["card"])

        for ent in [self.ent_port, self.ent_split, self.spn_fsize]:
            ent.configure(font=f_norm, bg=t["panel"], fg=t["fg"], insertbackground=t["fg"])

        for chk in [self.chk_doh, self.chk_autostart]:
            chk.configure(
                font=f_norm,
                fg=t["fg"],
                bg=t["card"],
                selectcolor=t["panel"],
                activebackground=t["card"],
                activeforeground=t["fg"],
            )

        for btn in [
            self.btn_copy_ip,
            self.btn_clear_log,
            self.btn_test_discord,
            self.btn_save_cfg,
            self.btn_fw,
            self.btn_reset_cfg,
            self.btn_comic,
            self.btn_segoe,
            self.btn_consolas,
            self.btn_check_update,
        ]:
            btn.configure(
                font=f_norm,
                bg=t["btn_bg"],
                fg=t["btn_fg"],
                activebackground=t["btn_active"],
                activeforeground=t["btn_fg"],
            )
        self.btn_comic.configure(font=("Comic Sans MS", max(8, fs - 1), "bold"))
        self.btn_save_cfg.configure(font=f_bold, bg=t["btn_active"])

    # -----------------------------------------------------------------------
    # Etkileşim & Olaylar
    # -----------------------------------------------------------------------
    def switch_tab(self, tab_name: str):
        self.current_tab = tab_name
        if tab_name == "dashboard":
            self.page_settings.pack_forget()
            self.page_dashboard.pack(fill="both", expand=True)
        else:
            self.page_dashboard.pack_forget()
            self.page_settings.pack(fill="both", expand=True)
        self.apply_styles()

    def set_quick_font(self, font_name: str):
        self.var_font.set(font_name)
        self.on_live_preview()

    def on_live_preview(self):
        self.cfg["theme"] = self.var_theme.get()
        self.cfg["font_family"] = self.var_font.get()
        try:
            self.cfg["font_size"] = int(self.var_fsize.get())
        except Exception:
            pass
        self.cfg["log_font_family"] = self.var_log_font.get()
        self.apply_styles()

    def save_and_apply_settings(self):
        try:
            port = int(self.var_port.get())
            split_pos = int(self.var_split.get())
            if not (1 <= port <= 65535):
                raise ValueError("Port 1-65535 arasında olmalıdır.")
        except ValueError as e:
            messagebox.showerror("Geçersiz Değer", f"Lütfen sayısal değerleri kontrol edin:\n{e}")
            return

        need_restart = (
            self.cfg.get("port") != port
            or self.cfg.get("split_pos") != split_pos
            or self.cfg.get("use_doh") != self.var_use_doh.get()
            or self.cfg.get("doh_url") != self.var_doh_url.get()
        )

        self.cfg["port"] = port
        self.cfg["split_pos"] = split_pos
        self.cfg["use_doh"] = self.var_use_doh.get()
        self.cfg["doh_url"] = self.var_doh_url.get().strip()
        self.cfg["auto_start"] = self.var_autostart.get()
        self.on_live_preview()
        save_config(self.cfg)

        self.lbl_port_val.configure(text=str(port))
        self.append_log(f"[AYARLAR] Yapılandırma kaydedildi (Font: {self.cfg['font_family']}, Port: {port}).")

        if need_restart and self.proxy_server and self.proxy_server.running:
            self.stop_server()
            self.root.after(300, self.start_server)

        self.switch_tab("dashboard")

    def reset_defaults(self):
        self.cfg = DEFAULT_CONFIG.copy()
        self.var_theme.set(self.cfg["theme"])
        self.var_font.set(self.cfg["font_family"])
        self.var_fsize.set(self.cfg["font_size"])
        self.var_log_font.set(self.cfg["log_font_family"])
        self.var_port.set(self.cfg["port"])
        self.var_split.set(self.cfg["split_pos"])
        self.var_doh_url.set(self.cfg["doh_url"])
        self.var_use_doh.set(self.cfg["use_doh"])
        self.var_autostart.set(self.cfg["auto_start"])
        save_config(self.cfg)
        self.lbl_port_val.configure(text=str(self.cfg["port"]))
        self.apply_styles()
        self.append_log("[AYARLAR] Varsayılan ayarlara sıfırlandı.")

    def copy_ip_port(self):
        text = f"{self.local_ip}:{self.cfg['port']}"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.append_log(f"[BİLGİ] Panoya kopyalandı: {text}")

    def clear_logs(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def append_log(self, text: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{now}] {text}\n"

        def _update():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, _update)

    def update_stats(self, active: int, total: int):
        def _upd():
            self.lbl_stats.configure(text=f"Aktif Tünel: {active}  |  Toplam İstek: {total}")

        self.root.after(0, _upd)

    def start_server(self):
        if self.proxy_server and self.proxy_server.running:
            return
        self.proxy_server = PS5DPIProxyServer(
            host="0.0.0.0",
            port=int(self.cfg["port"]),
            split_pos=int(self.cfg["split_pos"]),
            use_doh=bool(self.cfg["use_doh"]),
            doh_url=self.cfg["doh_url"],
            log_cb=self.append_log,
            stats_cb=self.update_stats,
        )
        self.proxy_server.start_in_thread()
        self.root.after(150, self.apply_styles)

    def stop_server(self):
        if self.proxy_server and self.proxy_server.running:
            self.proxy_server.stop()
            self.proxy_server = None
        self.root.after(100, self.apply_styles)

    def toggle_server(self):
        if self.proxy_server and self.proxy_server.running:
            self.stop_server()
        else:
            self.start_server()

    def test_discord_connection(self):
        if not (self.proxy_server and self.proxy_server.running):
            self.append_log("[TEST] Önce proxy sunucusunu başlatın!")
            return

        def _worker():
            port = self.cfg["port"]
            self.append_log("[TEST] Discord Gateway (https://discord.com/api/v9/gateway) test ediliyor...")
            try:
                proxy_handler = urllib.request.ProxyHandler({"https": f"http://127.0.0.1:{port}"})
                opener = urllib.request.build_opener(proxy_handler)
                req = urllib.request.Request(
                    "https://discord.com/api/v9/gateway", headers={"User-Agent": "Mozilla/5.0"}
                )
                with opener.open(req, timeout=8) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                    self.append_log(f"[TEST BAŞARILI] HTTP {resp.status} -> {body}")
            except Exception as e:
                self.append_log(f"[TEST HATASI] Bağlantı başarısız: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def add_firewall_rule(self):
        port = self.cfg["port"]
        rule_name = f"PS5_DPI_Proxy_{port}"
        cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow protocol=TCP localport={port}'
        try:
            subprocess.run(
                ["powershell", "-Command", f"Start-Process cmd -ArgumentList '/c {cmd}' -Verb RunAs"],
                check=True,
            )
            self.append_log(f"[GÜVENLİK DUVARI] TCP {port} portu için izin kuralı eklendi.")
        except Exception as e:
            self.append_log(f"[GÜVENLİK DUVARI] İşlem iptal edildi veya hata oluştu: {e}")

    # -----------------------------------------------------------------------
    # GITHUB OTOMATİK GÜNCELLEYİCİ (AUTO-UPDATER)
    # -----------------------------------------------------------------------
    def check_for_updates(self, silent: bool = True):
        def _worker():
            if not silent:
                self.append_log(f"[GÜNCELLEME] GitHub üzerinden yeni sürüm kontrol ediliyor ({GITHUB_REPO})...")
            try:
                req = urllib.request.Request(
                    GITHUB_API_LATEST,
                    headers={"User-Agent": "PS5-DPI-Bypass-Updater", "Accept": "application/vnd.github.v3+json"},
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))

                latest_tag = data.get("tag_name", "").strip()
                release_notes = data.get("body", "") or "Yeni iyileştirmeler ve hata düzeltmeleri."
                assets = data.get("assets", [])

                if not latest_tag:
                    if not silent:
                        self.append_log("[GÜNCELLEME] Henüz yayınlanmış bir sürüm bulunamadı.")
                    return

                if parse_version_tuple(latest_tag) > parse_version_tuple(APP_VERSION):
                    exe_url = None
                    for asset in assets:
                        name = asset.get("name", "")
                        if name.lower().endswith(".exe"):
                            exe_url = asset.get("browser_download_url")
                            break

                    self.append_log(f"[GÜNCELLEME] Yeni sürüm bulundu: {latest_tag} (Mevcut: {APP_VERSION})")
                    self.root.after(0, lambda: self._prompt_update(latest_tag, release_notes, exe_url))
                else:
                    if not silent:
                        self.append_log(f"[GÜNCELLEME] Uygulamanız güncel! ({APP_VERSION})")
                        self.root.after(
                            0,
                            lambda: messagebox.showinfo(
                                "Güncel", f"En güncel sürümü ({APP_VERSION}) kullanıyorsunuz."
                            ),
                        )
            except Exception as e:
                if not silent:
                    self.append_log(f"[GÜNCELLEME] Kontrol sırasında hata: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _prompt_update(self, latest_tag: str, notes: str, exe_url: str | None):
        short_notes = notes[:350] + ("..." if len(notes) > 350 else "")
        msg = (
            f"Yeni bir güncelleme mevcut: {latest_tag}  (Mevcut: {APP_VERSION})\n\n"
            f"Sürüm Notları:\n{short_notes}\n\n"
            "Şimdi otomatik olarak indirilip güncellensin mi?"
        )
        if messagebox.askyesno("Yeni Güncelleme Mevcut!", msg):
            if exe_url and getattr(sys, "frozen", False):
                self._download_and_replace_exe(exe_url, latest_tag)
            else:
                webbrowser.open(GITHUB_RELEASES_URL)

    def _download_and_replace_exe(self, exe_url: str, latest_tag: str):
        self.append_log(f"[GÜNCELLEME] {latest_tag} indiriliyor, lütfen bekleyin...")
        self.btn_check_update.configure(text="⏳ İndiriliyor...", state="disabled")

        def _dl_worker():
            try:
                current_exe = os.path.abspath(sys.executable)
                base_dir = os.path.dirname(current_exe)
                new_exe = os.path.join(base_dir, "PS5-DPI-Bypass_new.exe")
                bat_path = os.path.join(base_dir, "_update_runner.bat")

                req = urllib.request.Request(exe_url, headers={"User-Agent": "PS5-DPI-Bypass-Updater"})
                with urllib.request.urlopen(req, timeout=60) as resp, open(new_exe, "wb") as out_f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        out_f.write(chunk)

                # Eski .exe kapandıktan 2 saniye sonra yenisini üzerine yazıp tekrar başlatan script
                bat_content = (
                    "@echo off\r\n"
                    "chcp 65001 >nul\r\n"
                    "timeout /t 2 /nobreak >nul\r\n"
                    f'move /Y "{new_exe}" "{current_exe}" >nul\r\n'
                    f'start "" "{current_exe}"\r\n'
                    'del "%~f0"\r\n'
                )
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_content)

                self.append_log("[GÜNCELLEME] İndirme tamamlandı! Uygulama yeniden başlatılıyor...")
                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path],
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                self.root.after(400, self.root.destroy)
            except Exception as e:
                self.append_log(f"[GÜNCELLEME HATASI] Otomatik güncelleme başarısız: {e}")
                self.root.after(
                    0, lambda: self.btn_check_update.configure(text="🔄 Güncellemeleri Kontrol Et", state="normal")
                )

        threading.Thread(target=_dl_worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()
