# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['auto_sub_pipe_PACKAGE.py'],
             pathex=['C:\\Users\\imago\\Documents\\GitHub\\omesis_sub'],
             binaries=[],
             datas=[],
             hiddenimports=['pkg_resources.py2_warn'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='auto_sub_pipe_PACKAGE',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True ,
		  icon='C:\\Users\\imago\\Documents\\GitHub\\omesis_sub\\unchan_pink.ico'		  )
