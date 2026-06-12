# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    [str(root / 'app' / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'app' / 'server' / 'static_dashboard.py'), 'app' / 'server'),
        (str(root / 'app' / 'server' / 'schemas.py'), 'app' / 'server'),
    ],
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
    excludes=[],
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
