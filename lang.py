"""Minimal i18n: returns Czech or English strings based on macOS system language."""
import subprocess

def _detect():
    try:
        out = subprocess.run(
            ['defaults', 'read', '-g', 'AppleLanguages'],
            capture_output=True, text=True, timeout=2
        ).stdout
        first = out.strip().lstrip('(\n').split('\n')[0].strip().strip(',').strip('"')
        return 'cs' if first.startswith('cs') else 'en'
    except Exception:
        import locale
        code = (locale.getdefaultlocale()[0] or 'en').lower()
        return 'cs' if code.startswith('cs') else 'en'

LANG = _detect()

_STRINGS = {
    'en': {
        # drag header
        'drag_header':        "↕ Drag to position  ·  Ctrl+Enter = insert  ·  Esc = cancel",
        'drag_header_done':   "✓ Inserted  ·  Drag to move, then Ctrl+Enter  ·  Esc = done",
        'btn_insert':         "Insert into PDF",
        'btn_reinsert':       "Move here (reinsert)",
        # toolbar tooltips
        'open':              "Open",
        'save':              "Save",
        'save_as':           "Save As…",
        'save_copy':         "Save Copy…",
        'undo':              "Undo",
        'redo':              "Redo",
        'zoom_out':          "Zoom Out",
        'zoom_in':           "Zoom In",
        'cursor':            "Cursor",
        'select_area':       "Select Area (Alt+drag)",
        'edit_text':         "Edit Text",
        'add_text':          "Add Text",
        'add_comment':       "Add Comment",
        'draw':              "Draw",
        'esign':             "Digital Signature (Certificate)",
        'pen_color':         "Pen Color",
        # status bar
        'open_hint':         "Open a PDF file  (Cmd+O)",
        'pages':             "pages",
        'paste_hint':        "Click in PDF to paste clipboard text",
        'open_first':        "Open a PDF file first",
        'copied_chars':      "Copied to clipboard: {n} characters  (Cmd+V to paste)",
        'no_text_found':     "No text found in selected area",
        'text_outside':      "Text is outside the PDF page",
        'comment_outside':   "Comment is outside the PDF page",
        'comment_added':     "Comment added to page {n}",
        'copy_saved':        "Copy saved: {name}",
        'saved':             "Saved: {name}",
        'undo_msg':          "Undo: {desc}",
        'redo_msg':          "Redo: {desc}",
        # file dialogs
        'open_pdf_dlg':      "Open PDF",
        'pdf_filter':        "PDF files (*.pdf)",
        'save_as_dlg':       "Save PDF As",
        'save_copy_dlg':     "Save PDF Copy",
        'copy_suffix':       "_copy",
        # error titles / messages
        'err_open':          "Error",
        'err_open_msg':      "Cannot open file:\n{e}",
        'err_save':          "Error saving",
        'err_save_copy':     "Error saving copy",
        # undo stack descriptions
        'undo_draw':         "drawing",
        'undo_add_text':     "add text",
        'undo_add_comment':  "add comment",
        'undo_edit_text':    "edit text",
        'undo_sign':         "signature",
        # signature dialog
        'sig_title':         "Signature",
        'sig_draw_label':    "Draw your signature with mouse or trackpad:",
        'sig_clear':         "Clear",
        'sig_cancel':        "Cancel",
        'sig_insert':        "Insert Signature",
        'sig_tab_draw':      "Drawn Signature",
        'sig_tab_cert':      "E-Signature (P12 Certificate)",
        'sig_cert_info':     ("Select a P12/PFX certificate (file with private key).\n"
                              "Export it from Keychain or iSignum as a .p12 file."),
        'sig_p12_placeholder': "Path to .p12 / .pfx file",
        'sig_browse':        "Browse…",
        'sig_p12_label':     "P12 file:",
        'sig_pw_placeholder': "P12 password",
        'sig_pw_label':      "Password:",
        'sig_reason_ph':     "optional",
        'sig_reason_label':  "Reason:",
        'sig_location_ph':   "optional",
        'sig_location_label':"Location:",
        'sig_contact_ph':    "optional",
        'sig_contact_label': "Contact:",
        'sig_output_label':  "Output:",
        'sig_sign_btn':      "Sign PDF",
        'sig_open_p12_dlg':  "Open P12 Certificate",
        'sig_p12_filter':    "PKCS#12 files (*.p12 *.pfx);;All files (*)",
        'sig_no_pdf_label':  "(open a PDF first)",
        'sig_err_no_pdf':    "Open a PDF file first.",
        'sig_err_no_p12':    "Select a P12/PFX certificate file.",
        'sig_progress':      "Signing PDF…",
        'sig_done_title':    "Signed",
        'sig_done_msg':      "PDF signed successfully:\n{path}",
        'sig_err_sign':      "Signing error",
    },
    'cs': {
        # drag header
        'drag_header':        "↕ Přetáhni na místo  ·  Ctrl+Enter = vložit  ·  Esc = zrušit",
        'drag_header_done':   "✓ Vloženo  ·  Přetáhni pro přesun, pak Ctrl+Enter  ·  Esc = hotovo",
        'btn_insert':         "Vložit do PDF",
        'btn_reinsert':       "Přesunout sem",
        # toolbar tooltips
        'open':              "Otevřít",
        'save':              "Uložit",
        'save_as':           "Uložit jako…",
        'save_copy':         "Uložit kopii…",
        'undo':              "Zpět",
        'redo':              "Znovu",
        'zoom_out':          "Oddálit",
        'zoom_in':           "Přiblížit",
        'cursor':            "Kurzor",
        'select_area':       "Výběr oblasti (Alt+tah)",
        'edit_text':         "Editovat text",
        'add_text':          "Přidat text",
        'add_comment':       "Přidat komentář",
        'draw':              "Kreslit",
        'esign':             "E-podpis certifikátem",
        'pen_color':         "Barva pera",
        # status bar
        'open_hint':         "Otevřete PDF soubor  (Cmd+O)",
        'pages':             "stránek",
        'paste_hint':        "Klikni do PDF pro vložení textu ze schránky",
        'open_first':        "Nejprve otevřete PDF soubor",
        'copied_chars':      "Zkopírováno do schránky: {n} znaků  (Cmd+V pro vložení)",
        'no_text_found':     "Ve vybrané oblasti nebyl nalezen žádný text",
        'text_outside':      "Text je mimo stránku PDF",
        'comment_outside':   "Komentář je mimo stránku PDF",
        'comment_added':     "Komentář přidán na stránku {n}",
        'copy_saved':        "Kopie uložena: {name}",
        'saved':             "Uloženo: {name}",
        'undo_msg':          "Zpět: {desc}",
        'redo_msg':          "Znovu: {desc}",
        # file dialogs
        'open_pdf_dlg':      "Otevřít PDF",
        'pdf_filter':        "PDF soubory (*.pdf)",
        'save_as_dlg':       "Uložit PDF jako",
        'save_copy_dlg':     "Uložit kopii PDF",
        'copy_suffix':       "_kopie",
        # error titles / messages
        'err_open':          "Chyba",
        'err_open_msg':      "Nelze otevřít soubor:\n{e}",
        'err_save':          "Chyba při ukládání",
        'err_save_copy':     "Chyba při ukládání kopie",
        # undo stack descriptions
        'undo_draw':         "kresba",
        'undo_add_text':     "přidání textu",
        'undo_add_comment':  "přidání komentáře",
        'undo_edit_text':    "editace textu",
        'undo_sign':         "podpis",
        # signature dialog
        'sig_title':         "Podpis",
        'sig_draw_label':    "Nakreslete podpis myší nebo trackpadem:",
        'sig_clear':         "Vymazat",
        'sig_cancel':        "Zrušit",
        'sig_insert':        "Vložit podpis",
        'sig_tab_draw':      "Nakreslený podpis",
        'sig_tab_cert':      "E-podpis (P12 certifikát)",
        'sig_cert_info':     ("Vyberte certifikát ve formátu P12/PFX (soubor s privátním klíčem).\n"
                              "Exportujte jej z Klíčenky nebo z iSignum jako .p12 soubor."),
        'sig_p12_placeholder': "Cesta k souboru .p12 / .pfx",
        'sig_browse':        "Procházet…",
        'sig_p12_label':     "Soubor P12:",
        'sig_pw_placeholder': "heslo k P12 souboru",
        'sig_pw_label':      "Heslo:",
        'sig_reason_ph':     "volitelné",
        'sig_reason_label':  "Důvod:",
        'sig_location_ph':   "volitelné",
        'sig_location_label':"Místo:",
        'sig_contact_ph':    "volitelné",
        'sig_contact_label': "Kontakt:",
        'sig_output_label':  "Výstup:",
        'sig_sign_btn':      "Podepsat PDF",
        'sig_open_p12_dlg':  "Otevřít P12 certifikát",
        'sig_p12_filter':    "PKCS#12 soubory (*.p12 *.pfx);;Všechny soubory (*)",
        'sig_no_pdf_label':  "(nejprve otevřete PDF)",
        'sig_err_no_pdf':    "Nejprve otevřete PDF soubor.",
        'sig_err_no_p12':    "Vyberte P12/PFX soubor s certifikátem.",
        'sig_progress':      "Podepisuji PDF…",
        'sig_done_title':    "Podepsáno",
        'sig_done_msg':      "PDF bylo úspěšně podepsáno:\n{path}",
        'sig_err_sign':      "Chyba při podepisování",
    },
}


def T(key: str, **kwargs) -> str:
    """Return translated string for key, formatted with kwargs if given."""
    s = _STRINGS[LANG].get(key, _STRINGS['en'].get(key, key))
    return s.format(**kwargs) if kwargs else s
