"""
py2app setup – spusť: venv/bin/python setup.py py2app
"""
from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/app.icns",
    "plist": {
        "CFBundleName": "PDF Reader",
        "CFBundleDisplayName": "PDF Reader",
        "CFBundleIdentifier": "ai.kubicek.pdfreader",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHighResolutionCapable": True,
        # Napárování na .pdf soubory — dvojklik v Finderu otevře tuto apku
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "PDF Document",
                "CFBundleTypeExtensions": ["pdf"],
                "CFBundleTypeMIMETypes": ["application/pdf"],
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
                "CFBundleTypeIconFile": "resources/app.icns",
            }
        ],
        "UTImportedTypeDeclarations": [
            {
                "UTTypeIdentifier": "com.adobe.pdf",
                "UTTypeDescription": "PDF Document",
                "UTTypeConformsTo": ["public.data", "public.composite-content"],
                "UTTypeTagSpecification": {
                    "public.filename-extension": ["pdf"],
                    "public.mime-type": ["application/pdf"],
                },
            }
        ],
    },
    "packages": ["fitz", "PyQt6"],
    "includes": [
        "viewer", "signature_dialog", "icons", "keychain_sign",
        "PyQt6.QtPdf", "PyQt6.QtPdfWidgets", "PyQt6.QtSvg",
    ],
    "excludes": ["tkinter"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
