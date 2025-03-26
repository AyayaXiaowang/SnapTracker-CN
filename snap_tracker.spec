# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 添加所有资源文件
added_files = [
    ('ui/icon.ico', 'ui'),
    ('ui/styles.qss', 'ui'),
    ('cards.json', '.'),
    ('卡面/*.png', '卡面'),  # 确保包含所有PNG文件
    ('screen_match/*', 'screen_match'),  # 包含所有识别文件
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'win32gui',
        'win32api',
        'win32com',
        'win32com.client',
        'json',
        'numpy',
        'cv2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 
        'tkinter',
        'PyQt5',
        'scipy',
        'pandas',
        'notebook',
        'IPython',
        'pytest',
        'docutils',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='小王记牌器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # 启用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='file_version_info.txt',
    icon='ui/icon.ico'
)