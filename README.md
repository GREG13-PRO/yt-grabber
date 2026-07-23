# YT Grabber

Helyi, egyszemélyes használatra szánt YouTube videó/hang letöltő, modern felülettel. [yt-dlp](https://github.com/yt-dlp/yt-dlp) motorral, Flask backenddel — futtatható böngészőből (`python app.py`) vagy natív desktop ablakként (`python desktop.py`, illetve a lenti kész csomagok). Csak `127.0.0.1`-en fut, nem elérhető a hálózaton keresztül.

## Letöltés (kész csomagok)

A [Releases](../../releases) oldalon minden verzióhoz automatikusan épül:
- **macOS**: `YT-Grabber-macOS.dmg`
- **Windows**: `YT-Grabber-Windows.exe`
- **Linux**: `YT-Grabber-Linux` (futtatható bináris)

Ezek önmagukban működnek — a szükséges ffmpeg be van csomagolva, semmit nem kell külön telepíteni.

> **Linux megjegyzés:** a desktop ablak (`pywebview`) a rendszer WebKitGTK-jét használja. Ha az App nem indul, telepítsd: `sudo apt install gir1.2-webkit2-4.1` (Debian/Ubuntu) vagy a disztród megfelelő csomagját.

> **macOS/Windows megjegyzés:** a csomagok nincsenek Apple/Microsoft által aláírva (ez fizetős fejlesztői előfizetést igényelne), ezért első futtatáskor figyelmeztetést kaphatsz ("unidentified developer" / "Windows protected your PC"). macOS-en: jobb klikk a `.app`-on → **Megnyitás**, vagy `xattr -d com.apple.quarantine "YT Grabber.app"` terminálban. Windows-on: **More info** → **Run anyway**.

## Elérhető minőség

A YouTube időnként szerveroldali változtatásokat vezet be, amik átmenetileg megzavarhatják a yt-dlp-t. Ez egy **friss yt-dlp-vel** (ami Python 3.10+-at igényel) jellemzően nem probléma — teljes formátumlistát ad, akár 1080p+ is elérhető. A minőség-választó mindig csak azt kínálja fel, ami az adott videónál ténylegesen elérhető.

**Ha csak alacsony (pl. 360p) minőséget kapsz:**
1. Ellenőrizd a Python verziót: `python3 --version` — ha 3.9 vagy régebbi, a `pip` egy régi, korlátozott yt-dlp verziót fog telepíteni. Telepíts Python 3.10+-at (pl. `brew install python@3.12` macOS-en), és azzal hozd létre a venv-et.
2. Frissítsd a yt-dlp-t a venv-ben: `pip install -U yt-dlp`.

A kész csomagok (fenti Releases) már eleve friss Python-nal épülnek, ott ez nem szokott gondot okozni.

## Fejlesztői futtatás forrásból

### Előfeltételek

- **Python 3.10+** (fontos: régebbi Python csak régi yt-dlp-t kap a pip-től, lásd fent)
- ffmpeg a PATH-on (`brew install ffmpeg` / `apt install ffmpeg` / `choco install ffmpeg`)

### Telepítés

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
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
python packaging/build.py
```

Az eredmény a `dist/` mappában lesz (macOS: `.app`, Windows/Linux: egyetlen futtatható fájl). A GitHub Actions workflow (`.github/workflows/release.yml`) ugyanezt futtatja le mindhárom platformon egy `v*` tag push-ra, és feltölti az eredményt a Release-hez.

## Felelősség

Csak olyan tartalmat tölts le, amihez jogod van (saját videók, Creative Commons, vagy a jogtulajdonos engedélyével). A YouTube Szolgáltatási Feltételei korlátozzák a letöltést — a felelősség a felhasználót terheli.

## Hibaelhárítás

- **"ffmpeg not found" figyelmeztetés indításkor** (forrásból futtatva): telepítsd az ffmpeg-et, majd indítsd újra az appot.
- **Csak alacsony minőség érhető el**: lásd fent az "Elérhető minőség" szakaszt — ez szinte mindig a Python/yt-dlp verzió kérdése.
- **Videó lekérdezési/letöltési hiba**: a YouTube gyakran változtat, ami elavulttá teheti a yt-dlp-t. Frissítsd: `pip install -U yt-dlp`.
