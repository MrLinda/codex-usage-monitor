# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

# conda 环境把 tcl/tk/sqlite/lzma/bz2/ffi 等 DLL 放在 Library/bin，
# 不在系统 PATH 里，PyInstaller 默认搜不到。把这个目录追加进 PATH
# 让依赖分析阶段能解析到这些 DLL 并打包进发布产物。
_conda_bin = Path(sys.executable).parent / 'Library' / 'bin'
if _conda_bin.is_dir():
    os.environ['PATH'] = str(_conda_bin) + os.pathsep + os.environ.get('PATH', '')

_datas = [
    (str(root / 'app' / 'server' / 'static_dashboard.py'), 'app/server'),
]
# 本地 Chart.js（离线仪表盘用），存在才打包；缺失时后端会回退 CDN
_static_dir = root / 'app' / 'server' / 'static'
if _static_dir.is_dir():
    _datas.append((str(_static_dir), 'app/server/static'))

a = Analysis(
    [str(root / 'app' / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'pydantic',
        'tomli_w',
        'requests',
        'pystray',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'app',
        'app.server',
        'app.server.api',
        'app.storage',
        'app.storage.db',
        'app.storage.migrations',
        'app.storage.repository',
        'app.collectors',
        'app.collectors.log_collector',
        'app.collectors.quota_collector',
        'app.scheduler',
        'app.scheduler.poller',
        'app.analytics',
        'app.analytics.burn_rate',
        'app.analytics.forecast',
        'app.analytics.events',
        'app.gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide6', 'PyQt6', 'PySide2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='codex-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='codex-backend',
)
