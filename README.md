# YT Grabber

Helyi, egyszemélyes használatra szánt YouTube videó/hang letöltő, modern felülettel. [yt-dlp](https://github.com/yt-dlp/yt-dlp) motorral, Flask backenddel — futtatható böngészőből (`python app.py`) vagy natív desktop ablakként (`python desktop.py`, illetve a lenti kész csomagok). Csak `127.0.0.1`-en fut, nem elérhető a hálózaton keresztül.

## Letöltés (kész csomagok)

A [Releases](../../releases) oldalon minden verzióhoz automatikusan épül:
- **macOS**: `YT-Grabber-macOS.dmg`
- **Windows**: `YT-Grabber-Windows.exe`
- **Linux**: `YT-Grabber-Linux` (futtatható bináris)

Ezek önmagukban működnek — a szükséges ffmpeg és a "legjobb minőség" mechanizmus (lásd lent) be van csomagolva, semmit nem kell külön telepíteni.

> **Linux megjegyzés:** a desktop ablak (`pywebview`) a rendszer WebKitGTK-jét használja. Ha az App nem indul, telepítsd: `sudo apt install gir1.2-webkit2-4.1` (Debian/Ubuntu) vagy a disztród megfelelő csomagját.

## Legjobb minőség: PO-token szerver

A YouTube egyre több formátumot köt egy ún. PO Tokenhez (proof-of-origin), aminek hiányában a yt-dlp gyakran csak alacsony (~360p) minőséget tud elérni, vagy hibát dob ("The page needs to be reloaded"). Ennek megkerülésére az app egy helyi [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) szervert indít háttérben (Node.js-en), ami tokent generál a yt-dlp számára.

- A kész csomagokban (DMG/EXE/Linux) ez **be van építve**, automatikusan elindul, nincs teendő.
- Forrásból futtatva (lásd lent) **egyszeri setup script** kell hozzá.
- Ha valamiért nem elérhető (pl. nincs Node.js fejlesztői módban), az app attól még működik, csak a minőség YouTube-oldali korlátozás alá eshet — a minőség-választó mindig csak azt kínálja, ami ténylegesen elérhető.
- Mivel ez a YouTube és a yt-dlp közötti folyamatosan változó "versenyfutás", időnként érdemes frissíteni: `pip install -U yt-dlp`.

## Fejlesztői futtatás forrásból

### Előfeltételek

- Python 3.10+ (a repo CI-ja 3.11-et használ)
- Node.js 20+ (a PO-token szerver buildeléséhez és futtatásához)
- ffmpeg a PATH-on (`brew install ffmpeg` / `apt install ffmpeg` / `choco install ffmpeg`)

### Telepítés

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# PO-token szerver egyszeri build (jobb minőségű letöltéshez):
./scripts/setup_pot_server.sh      # Windows: scripts\setup_pot_server.ps1
```

### Futtatás böngészőben

```bash
python app.py
```

Nyisd meg: [http://127.0.0.1:5000](http://127.0.0.1:5000)

### Futtatás natív ablakként (desktop mód)

```bash
python desktop.py
```

Ugyanaz a felület, csak egy saját ablakban nyílik meg böngésző helyett.

## Használat

1. Illessz be egy YouTube videó URL-t, kattints a **Lekérdezés**-re (vagy a vágólap-ikonra).
2. Válassz minőséget a chipek közül (a lista mindig a ténylegesen elérhető formátumokhoz igazodik).
3. Kattints a **Letöltés**-re — a folyamatjelző mutatja az állapotot.
4. Amint elkészült, kattints a megjelenő linkre. A fájl a letöltési mappában is megtalálható (forrásból futtatva: `downloads/`; csomagolt appban: `~/Downloads/YT Grabber/`).

**Megjegyzés:** playlist linkek esetén az app csak az adott (egy) videót tölti le, a teljes playlistet nem.

## Saját csomag építése (PyInstaller)

```bash
pip install -r requirements-build.txt
./scripts/setup_pot_server.sh
python packaging/build.py
```

Az eredmény a `dist/` mappában lesz (macOS: `.app`, Windows/Linux: egyetlen futtatható fájl). A GitHub Actions workflow (`.github/workflows/release.yml`) ugyanezt futtatja le mindhárom platformon egy `v*` tag push-ra, és feltölti az eredményt a Release-hez.

## Felelősség

Csak olyan tartalmat tölts le, amihez jogod van (saját videók, Creative Commons, vagy a jogtulajdonos engedélyével). A YouTube Szolgáltatási Feltételei korlátozzák a letöltést — a felelősség a felhasználót terheli.

## Hibaelhárítás

- **"ffmpeg not found" figyelmeztetés indításkor** (forrásból futtatva): telepítsd az ffmpeg-et, majd indítsd újra az appot.
- **Videó lekérdezési/letöltési hiba**: a YouTube gyakran változtat, ami elavulttá teheti a yt-dlp-t. Frissítsd: `pip install -U yt-dlp`.
- **Alacsony minőség minden videónál**: ellenőrizd, hogy a PO-token szerver elindult-e (a konzolban "PO-token szerver elindult" üzenet jelenik meg indításkor).
