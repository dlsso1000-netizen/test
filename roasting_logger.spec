# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Pro Roasting Logger
실행: pyinstaller roasting_logger.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Streamlit 관련 파일 수집
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')

# Plotly 관련 파일 수집
plotly_datas, plotly_binaries, plotly_hiddenimports = collect_all('plotly')

# Pandas 관련 파일 수집
pandas_datas = collect_data_files('pandas')

# pywebview 관련 파일 수집
try:
    webview_datas, webview_binaries, webview_hiddenimports = collect_all('webview')
except:
    webview_datas, webview_binaries, webview_hiddenimports = [], [], []

# 추가 hidden imports
additional_hiddenimports = [
    'streamlit',
    'streamlit.web',
    'streamlit.web.cli',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'streamlit.runtime.caching',
    'streamlit.runtime.legacy_caching',
    'streamlit.components.v1',
    'plotly',
    'plotly.graph_objects',
    'plotly.subplots',
    'plotly.express',
    'pandas',
    'pandas.plotting',
    'pandas.io.formats.style',
    'numpy',
    'pyarrow',
    'PIL',
    'PIL.Image',
    'altair',
    'pydeck',
    'watchdog',
    'watchdog.observers',
    'watchdog.events',
    'tornado',
    'tornado.web',
    'tornado.websocket',
    'click',
    'toml',
    'validators',
    'gitpython',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements',
    'importlib_metadata',
    'typing_extensions',
    'drivers',  # 우리가 만든 드라이버 모듈
    'webview',  # pywebview
    'webview.platforms',
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
    'clr',
    'clr_loader',
    'pythonnet',
]

# 모든 hidden imports 합치기
all_hiddenimports = list(set(
    streamlit_hiddenimports +
    plotly_hiddenimports +
    webview_hiddenimports +
    additional_hiddenimports
))

# 모든 datas 합치기
all_datas = streamlit_datas + plotly_datas + pandas_datas + webview_datas + [
    ('roasting_log.py', '.'),
    ('drivers.py', '.'),
]

# 모든 binaries 합치기
all_binaries = streamlit_binaries + plotly_binaries + webview_binaries

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # 용량 줄이기 위해 제외 (필요시 제거)
        'scipy',
        'tkinter',
    ],
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
    name='RoastingLogger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 콘솔 창 숨김 (앱 창만 표시)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있으면 'icon.ico' 지정
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RoastingLogger',
)
