#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac 打包脚本
使用 PyInstaller 打包为 Mac .app 应用程序

使用方法:
    python build_mac.py              # 构建应用
    python build_mac.py --clean      # 清理后构建
    python build_mac.py --dmg        # 构建并创建 DMG
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent.resolve()


def clean_build():
    """清理构建目录"""
    project_root = get_project_root()
    dirs = ['build', 'dist', '__pycache__', '.pytest_cache']

    for d in dirs:
        path = project_root / d
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            print(f"Cleaned: {d}")

    # 删除 spec 文件
    for spec in project_root.glob("*.spec"):
        spec.unlink()
        print(f"Cleaned: {spec.name}")


def install_pyinstaller():
    """安装 PyInstaller"""
    print("Installing PyInstaller...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
            check=True,
            capture_output=True
        )
        print("PyInstaller installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install PyInstaller: {e}")
        return False


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return install_pyinstaller()


def build_app():
    """使用 PyInstaller 打包 Mac 应用"""
    project_root = get_project_root()
    os.chdir(project_root)

    print("=" * 60)
    print("Building Weverse Stock Monitor for Mac")
    print("=" * 60)

    app_name = "WeverseStockMonitor"

    # 确保数据目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    # 使用字符串拼接创建 spec 内容，避免转义问题
    project_root_str = str(project_root).replace("\\", "/")

    spec_lines = [
        "# -*- mode: python ; coding: utf-8 -*-",
        "",
        "import sys",
        "from pathlib import Path",
        "",
        "block_cipher = None",
        "",
        f"project_root = Path(r'{project_root_str}')",
        "",
        "added_files = [",
    ]

    # 添加 Python 文件
    py_files = [
        "config.py", "cookie_manager.py", "crawler.py", "gui.py",
        "models.py", "monitor.py", "notifier.py", "storage.py",
        "weverse_crawler.py"
    ]

    for f in py_files:
        spec_lines.append(f'    (str(project_root / "{f}"), "."),')

    spec_lines.append('    (str(project_root / "data"), "data"),')
    spec_lines.append('    (str(project_root / "mp3"), "mp3"),')
    spec_lines.append("]")
    spec_lines.append("")

    # hiddenimports
    hiddenimports = [
        "pandas", "pandas._libs.tslibs.base", "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps", "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype", "pandas._libs.tslibs.timezones",
        "pandas._libs.tslibs.conversion", "pandas._libs.tslibs.fields",
        "pandas._libs.tslibs.vectorized", "pandas._libs.ops_dispatch",
        "pandas._libs.missing", "pandas._libs.lib", "pandas._libs.hashtable",
        "pandas._libs.index", "pandas._libs.algos", "pandas._libs.interval",
        "pandas._libs.join", "pandas._libs.reduction", "pandas._libs.reshape",
        "pandas._libs.sparse", "pandas._libs.writers", "pandas._libs.parsers",
        "pandas._libs.json", "pandas._libs.testing", "pandas._libs.hashing",
        "pandas.core.methods", "pandas.core._tools", "pandas.io.formats.style",
        "pandas.io.excel._openpyxl", "openpyxl", "openpyxl.cell._writer",
        "openpyxl.cell.cell", "openpyxl.styles", "openpyxl.styles.stylesheet",
        "openpyxl.utils", "openpyxl.workbook", "openpyxl.worksheet",
        "httpx", "httpx._transports.default", "httpcore", "httpcore._backends.sync",
        "httpcore._backends.anyio", "certifi", "idna", "sniffio", "h11", "h2",
        "hpack", "hyperframe", "anyio", "anyio._backends._trio",
        "anyio._backends._asyncio", "anyio.streams", "tkinter",
        "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk",
        "tkinter.scrolledtext", "xml.etree.ElementTree", "xml.etree.cElementTree",
    ]

    spec_lines.append("hiddenimports = [")
    for imp in hiddenimports:
        spec_lines.append(f'    "{imp}",')
    spec_lines.append("]")
    spec_lines.append("")

    spec_lines.extend([
        "a = Analysis(",
        f'    [str(project_root / "main.py")],',
        "    pathex=[str(project_root)],",
        "    binaries=[],",
        "    datas=added_files,",
        "    hiddenimports=hiddenimports,",
        "    hookspath=[],",
        "    hooksconfig={},",
        "    runtime_hooks=[],",
        "    excludes=[],",
        "    win_no_prefer_redirects=False,",
        "    win_private_assemblies=False,",
        "    cipher=block_cipher,",
        "    noarchive=False,",
        ")",
        "",
        "pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)",
        "",
        "exe = EXE(",
        "    pyz,",
        "    a.scripts,",
        "    a.binaries,",
        "    a.zipfiles,",
        "    a.datas,",
        "    [],",
        f'    name="{app_name}",',
        "    debug=False,",
        "    bootloader_ignore_signals=False,",
        "    strip=False,",
        "    upx=True,",
        "    upx_exclude=[],",
        "    runtime_tmpdir=None,",
        "    console=False,",  # GUI 模式，无控制台
        "    disable_windowed_traceback=False,",
        "    argv_emulation=True,",
        "    target_arch=None,",
        "    codesign_identity=None,",
        "    entitlements_file=None,",
        ")",
        "",
        "app = BUNDLE(",
        "    exe,",
        f'    name="{app_name}.app",',
        "    icon=None,",
        '    bundle_identifier="com.weverse.stockmonitor",',
        "    info_plist={",
        '        "CFBundleShortVersionString": "1.0.0",',
        '        "CFBundleVersion": "1.0.0",',
        '        "CFBundleDisplayName": "Weverse Stock Monitor",',
        '        "CFBundleName": "WeverseStockMonitor",',
        '        "NSHighResolutionCapable": True,',
        '        "LSBackgroundOnly": False,',
        '        "NSRequiresAquaSystemAppearance": False,',
        "    },",
        ")",
    ])

    # 写入 spec 文件
    spec_file = project_root / f"{app_name}.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(spec_lines))

    print(f"Created spec file: {spec_file}")

    # 运行 PyInstaller
    try:
        print("Running PyInstaller...")
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean", "--noconfirm"],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Build failed!")
            print("STDERR:", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
            return False

        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

    except Exception as e:
        print(f"Build error: {e}")
        return False

    # 检查输出
    app_path = project_root / "dist" / f"{app_name}.app"
    if not app_path.exists():
        print(f"Error: {app_path} not found after build")
        return False

    print("\n" + "=" * 60)
    print("Build successful!")
    print("=" * 60)
    print(f"Output: {app_path}")
    print(f"\nTo run:")
    print(f"  Double-click: {app_path}")
    print(f"  Or run: open '{app_path}'")
    print("\nNote: First run may require right-click > Open")

    return True


def create_dmg():
    """创建 DMG 安装包"""
    project_root = get_project_root()
    app_name = "WeverseStockMonitor"
    dmg_name = f"{app_name}.dmg"
    dist_dir = project_root / "dist"
    app_path = dist_dir / f"{app_name}.app"

    if not app_path.exists():
        print(f"Error: {app_path} not found. Build first.")
        return False

    print(f"\nCreating DMG: {dmg_name}")

    # 创建临时目录
    temp_dir = project_root / "dmg_temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    # 复制应用
    shutil.copytree(app_path, temp_dir / f"{app_name}.app")

    # 创建 Applications 快捷方式
    try:
        os.symlink("/Applications", temp_dir / "Applications")
    except OSError:
        pass  # Windows 上可能不支持 symlink

    # 创建 DMG
    dmg_path = project_root / dmg_name
    if dmg_path.exists():
        dmg_path.unlink()

    try:
        cmd = [
            "hdiutil", "create",
            "-srcfolder", str(temp_dir),
            "-volname", app_name,
            "-fs", "HFS+",
            "-format", "UDZO",
            str(dmg_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"DMG created: {dmg_path}")
    except FileNotFoundError:
        print("Warning: hdiutil not found (not on Mac), skipping DMG creation")
        return False
    except subprocess.CalledProcessError as e:
        print(f"DMG creation failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Weverse Stock Monitor for Mac")
    parser.add_argument("--clean", action="store_true", help="Clean before build")
    parser.add_argument("--dmg", action="store_true", help="Create DMG")
    args = parser.parse_args()

    if args.clean:
        clean_build()

    if not check_pyinstaller():
        return 1

    if build_app():
        if args.dmg:
            create_dmg()
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
