# -*- mode: python ; coding: utf-8 -*-
# One-dir build: extracted-once folder layout → instant startup.
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'PIL.JpegImagePlugin',
    'PIL.PngImagePlugin',
    'PIL.WebPImagePlugin',
    'PIL.TiffImagePlugin',
    'PIL.BmpImagePlugin',
]

# PyQt6 is handled by PyInstaller's own hook (only QtCore/QtGui/QtWidgets are used).
# collect_all('PyQt6') used to drag in all of Qt (~3.6 GB).
for pkg in ('pillow_heif', 'oxipng'):
    tmp = collect_all(pkg)
    datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'tkinterdnd2', 'numpy', 'pandas', 'pyarrow', 'pytz', 'scipy', 'matplotlib',
        'IPython', 'notebook', 'jupyter', 'sklearn', 'torch', 'tensorflow', 'cv2', 'numba',
        'sympy', 'lxml', 'fitz', 'pymupdf', 'pikepdf',
        'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets', 'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets', 'PyQt6.QtMultimedia', 'PyQt6.QtNetwork', 'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets', 'PyQt6.QtDesigner', 'PyQt6.QtSql', 'PyQt6.QtTest',
        'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets', 'PyQt6.Qt3DCore', 'PyQt6.QtCharts',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='사진압축기',
    icon=['icon.ico'],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='사진압축기',
)
