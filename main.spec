import os

dll_path = os.path.abspath(
    os.path.join('_sounddevice_data', 'portaudio-binaries', 'libportaudio64bit.dll')
)
datas = [
    ('prompt/champion_spell_prompt.txt', 'prompt'),
    ('.env', '.'),
    (dll_path, '_sounddevice_data/portaudio-binaries')  # 정확한 위치 지정
]

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('prompt/champion_spell_prompt.txt', 'prompt'), ('.env', '.'), ('_sounddevice_data/portaudio-binaries/libportaudio64bit.dll', '_sounddevice_data/portaudio-binaries')]
binaries = []
hiddenimports = ['webrtcvad', 'whisper', 'ffmpeg', 'torch', 'torchaudio', 'transformers', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto']
hiddenimports += collect_submodules('torchaudio')
hiddenimports += collect_submodules('transformers')
hiddenimports += collect_submodules('webrtcvad')
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('scipy')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('sounddevice')
tmp_ret = collect_all('whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=['./server', './worker/stt', './worker/stt/util', './worker/tts'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
