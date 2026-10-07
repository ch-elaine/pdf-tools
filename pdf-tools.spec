# PyInstaller recipe for a single self-contained executable (pdf-tools.exe on
# Windows). From the project folder:
#
#     pip install -r requirements.txt waitress pyinstaller
#     pyinstaller pdf-tools.spec
#
# The result lands in dist/. PyInstaller cannot cross-compile, so the Windows
# build runs on a Windows machine - .github/workflows/release.yml does that.

from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    # Flask finds these beside app.py, which in the bundle is the unpack folder.
    datas=[
        (str(ROOT / "templates"), "templates"),
        (str(ROOT / "static"), "static"),
    ],
    # PyMuPDF only imports this when a font is first asked for, so the
    # analysis cannot see it. Without it, Greek/Cyrillic/... text becomes "?".
    hiddenimports=["pymupdf_fonts"],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pdf-tools",
    # Keep the console: it shows the address, and closing it stops the server.
    console=True,
    # UPX-packed executables trip antivirus heuristics far more often.
    upx=False,
)
