# 🎮 PS5 Discord DPI Bypass Proxy

Türkiye'deki internet servis sağlayıcılarının (Türk Telekom, Superonline, Kablonet vb.) uyguladığı **DPI (Deep Packet Inspection)** ve **DNS** engellerini aşarak **PlayStation 5** üzerinde Discord'u **ping artışı olmadan** kullanmanızı sağlayan açık kaynaklı yerel ağ (LAN) HTTP Proxy aracıdır.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-18181b?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-27272a?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-3f3f46?style=flat-square)

---

## ✨ Özellikler

- **Sıfır Ping Artışı:** VPN gibi trafiği yurt dışı sunucularına yönlendirmez; paketleri kendi internetiniz üzerinden çıkarır.
- **TLS Record & TCP Split (`ciadpi` / `ByeDPI` Mantığı):** İlk `TLS ClientHello` paketini hem TLS kayıt katmanında hem de TCP segment katmanında (`TCP_NODELAY`) parçalayarak DPI cihazlarının `discord.com` (SNI) bilgisini okumasını engeller.
- **Dahili DNS-over-HTTPS (DoH):** Alan adlarını şifreli olarak Cloudflare (`1.1.1.1`) veya Google DoH üzerinden çözer, ISS DNS zehirlemesini atlar.
- **Siyah & Gri Modern Arayüz:** *Obsidian Black*, *Carbon Gray* ve *Silver Monochrome* temalarıyla göz yormayan karanlık tasarım.
- **Tam Yazı Fontu Özelleştirme:** Ayarlar menüsünden **Comic Sans MS**, **Segoe UI**, **Consolas** dahil bilgisayarınızdaki tüm fontları ve yazı boyutunu anlık olarak değiştirebilme.
- **Tek Tıkla Test & Güvenlik Duvarı:** Arayüz içinden Discord Gateway bağlantısını test etme ve Windows Firewall port iznini otomatik tanımlama.

---

## 🚀 Kurulum ve Kullanım

### 1. Bilgisayarda Başlatma
1. `PS5-DPI-Bypass.exe` dosyasını çalıştırın (veya kaynak koddan `python ps5_dpi_proxy.py` ile açın).
2. İlk kullanımda **⚙ Ayarlar & Görünüm** sekmesinden **"🛡 Windows Güvenlik Duvarı Port İzni Ekle"** butonuna tıklayın (PS5'in bilgisayarınıza bağlanabilmesi için gereklidir).
3. Ana ekranda görünen **Proxy IP Adresi** (ör. `192.168.1.x`) ve **Proxy Portu** (`8080`) bilgilerini not edin.

### 2. PS5 Ağ Ayarlarını Yapma
1. PS5'te **Ayarlar > Ağ > Ayarlar > İnternet Bağlantısını Ayarla** menüsüne gidin.
2. Bağlı olduğunuz ağın (Wi-Fi veya LAN) üzerine gelip kumandadaki **Options** tuşuna basın ve **Gelişmiş Ayarlar**'ı seçin.
3. Aşağıdaki ayarları girin:
   - **DNS Ayarları:** `Manuel`
     - **Birincil DNS:** `1.1.1.1`
     - **İkincil DNS:** `1.0.0.1`
   - **Proxy Sunucusu:** `Kullan`
     - **Adres:** Bilgisayarınızın ekranda yazan yerel IP adresi (ör. `192.168.1.168`)
     - **Port Numarası:** `8080`
4. **Tamam**'a basarak kaydedin.
