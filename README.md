# PDF Reader

A lightweight macOS PDF viewer and editor built with Python, PyQt6 and PyMuPDF.  
Free for personal use · [mediatoring.com](https://mediatoring.com)

---

## Features / Funkce

| | EN | CZ |
|---|---|---|
| 📂 | Open, Save, Save As, Save Copy | Otevřít, Uložit, Uložit jako, Uložit kopii |
| ↩️ | Unlimited undo / redo | Neomezené zpět / znovu |
| 🔍 | Zoom in / out | Přiblížení / oddálení |
| 🖱️ | Cursor, area text selection | Kurzor, výběr textu v oblasti |
| ✏️ | Edit existing PDF text in place | Editace existujícího textu přímo v PDF |
| 🔤 | Place new text anywhere on page | Vkládání nového textu kamkoli na stránce |
| 💬 | Sticky-note comments (PDF annotations) | Komentáře jako sticky note (PDF anotace) |
| 🖌️ | Freehand drawing / pen tool | Volné kreslení / pero |
| 🎨 | Pen color picker | Výběr barvy pera |
| ✍️ | Digital e-signature via P12/PFX certificate | Digitální e-podpis přes P12/PFX certifikát |
| 🌐 | UI language follows macOS system language (EN / CZ) | Jazyk UI sleduje systémový jazyk macOS (EN / CZ) |

---

## Requirements / Požadavky

- macOS 12 Monterey or newer  
- Python 3.11+  
- Dependencies: `PyQt6`, `PyMuPDF` (fitz), `pyhanko` (for digital signing)

---

## Running from source / Spuštění ze zdrojového kódu

### EN

```bash
# 1. Clone the repo
git clone git@github.com:mediatoring/pdf-reader.git
cd pdf-reader

# 2. Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install PyQt6 PyMuPDF pyhanko

# 3. Launch
python main.py

# 4. Open a PDF from the toolbar (Cmd+O) or drag a .pdf file onto the app icon
```

### CZ

```bash
# 1. Naklonujte repozitář
git clone git@github.com:mediatoring/pdf-reader.git
cd pdf-reader

# 2. Vytvořte virtuální prostředí a nainstalujte závislosti
python3 -m venv venv
source venv/bin/activate
pip install PyQt6 PyMuPDF pyhanko

# 3. Spusťte aplikaci
python main.py

# 4. Otevřete PDF přes panel nástrojů (Cmd+O) nebo přetáhněte .pdf soubor na ikonu aplikace
```

---

## Building the macOS .app / Sestavení macOS .app

### EN

```bash
pip install py2app
python setup.py py2app
cp -r "dist/PDF Reader.app" /Applications/
```

> **Note:** Always clear the build cache before rebuilding to avoid stale bytecode:
> ```bash
> find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null
> find . -name "*.pyc" -delete 2>/dev/null
> rm -rf build dist
> ```

### CZ

```bash
pip install py2app
python setup.py py2app
cp -r "dist/PDF Reader.app" /Applications/
```

> **Poznámka:** Před každým sestavením smažte cache, aby se zabránilo zastaralému bytekódu:
> ```bash
> find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null
> find . -name "*.pyc" -delete 2>/dev/null
> rm -rf build dist
> ```

---

## Keyboard shortcuts / Klávesové zkratky

| Shortcut / Zkratka | Action EN | Akce CZ |
|---|---|---|
| `Cmd+O` | Open PDF | Otevřít PDF |
| `Cmd+S` | Save | Uložit |
| `Cmd+Z` | Undo | Zpět |
| `Cmd+Shift+Z` | Redo | Znovu |
| `Cmd++` / `Cmd+-` | Zoom in / out | Přiblížit / oddálit |
| `Cmd+A` | Select all (in active text field) | Vybrat vše (v aktivním textovém poli) |
| `Cmd+C` | Copy selected text | Kopírovat vybraný text |
| `Ctrl+Enter` | Commit text / comment to PDF | Vložit text / komentář do PDF |
| `Esc` | Cancel text / comment input | Zrušit zadávání textu / komentáře |
| `Alt+drag` | Select text area for copying | Výběr oblasti textu pro kopírování |

---

## Comments (Sticky Notes) / Komentáře (Sticky Notes)

### EN
1. Click the **comment bubble** icon in the toolbar.  
2. Click anywhere on the PDF page — a yellow draggable input panel appears.  
3. Type your comment. Drag the header to reposition.  
4. Press **Ctrl+Enter** to embed the comment as a PDF annotation.  
5. The annotation is visible in Acrobat, Preview, and all standard PDF viewers.

### CZ
1. Klikněte na ikonu **bubliny komentáře** v panelu nástrojů.  
2. Klikněte kamkoli na stránce PDF — zobrazí se žlutý panel pro zadání textu.  
3. Napište komentář. Přetažením záhlaví panel přemístěte.  
4. Stiskněte **Ctrl+Enter** pro vložení komentáře jako PDF anotace.  
5. Anotace je viditelná v Acrobatu, Preview a všech standardních čtečkách PDF.

---

## Digital Signature / Digitální podpis

### EN
1. Click the **certificate icon** in the toolbar.  
2. Go to the **E-Signature (P12 Certificate)** tab.  
3. Browse for your `.p12` / `.pfx` file and enter the password.  
4. Click **Sign PDF** — a signed copy is saved next to the original.

Export your certificate from macOS Keychain: *Keychain Access → select certificate → File → Export*.

### CZ
1. Klikněte na ikonu **certifikátu** v panelu nástrojů.  
2. Přejděte na záložku **E-podpis (P12 certifikát)**.  
3. Vyberte soubor `.p12` / `.pfx` a zadejte heslo.  
4. Klikněte na **Podepsat PDF** — podepsaná kopie se uloží vedle originálu.

Exportujte certifikát z macOS Klíčenky: *Klíčenka → vyberte certifikát → Soubor → Exportovat*.

---

## Project structure / Struktura projektu

```
pdf-reader/
├── main.py            # App entry point, macOS file-open event handler
├── viewer.py          # Main window, toolbar, tools, PDF editing logic
├── icons.py           # SVG icon definitions and rendering helpers
├── lang.py            # i18n: EN/CZ strings, auto-detected from system language
├── signature_dialog.py# Drawn + digital (P12) signature dialog
├── keychain_sign.py   # Digital signing via pyhanko
├── setup.py           # py2app build config (bundle ID: ai.kubicek.pdfreader)
└── resources/
    └── app.icns       # macOS application icon
```

---

## License / Licence

Free for personal use. For commercial use, contact [mediatoring.com](https://mediatoring.com).
