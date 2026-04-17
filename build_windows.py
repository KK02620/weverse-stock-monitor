#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 打包脚本
使用 PyInstaller 打包为 Windows .exe 应用程序

使用方法:
    python build_windows.py                    # 构建 onedir GUI 版本
    python build_windows.py --clean           # 清理后构建
    python build_windows.py --onefile         # 构建单文件 exe
    python build_windows.py --console         # 构建带控制台版本
    python build_windows.py --zip             # 打包完成后额外生成 zip
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


APP_NAME = "WeverseStockMonitor"
ENTRY_SCRIPT = "main.py"
DEFAULT_ICON_NAMES = [
    "app.ico",
    "icon.ico",
    "weverse.ico",
    "WeverseStockMonitor.ico",
]
CORE_INCLUDED_DIRS = ["mp3"]
OPTIONAL_INCLUDED_DIRS = ["data"]
HIDDEN_IMPORTS = [
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.ttk",
    "tkinter.scrolledtext",
    "xml.etree.ElementTree",
    "xml.etree.cElementTree",
]
EXCLUDED_MODULES = [
    "httpx",
    "httpcore",
    "anyio",
    "sniffio",
    "h11",
    "h2",
    "hpack",
    "hyperframe",
    "crawler",
    "pytest",
    "test_cookie_simulation",
    "test_notifier",
    "test_notifier_audio",
    "manual_monitor_sound_test",
]


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.resolve()


def clean_build() -> None:
    """清理构建目录"""
    project_root = get_project_root()
    dirs = ["build", "dist", "__pycache__", ".pytest_cache"]

    for d in dirs:
        path = project_root / d
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            print(f"Cleaned: {d}")

    for spec in project_root.glob("*.spec"):
        spec.unlink()
        print(f"Cleaned: {spec.name}")


def install_pyinstaller() -> bool:
    """安装 PyInstaller"""
    print("Installing PyInstaller...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("PyInstaller installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install PyInstaller: {e}")
        return False


def check_pyinstaller() -> bool:
    """检查 PyInstaller 是否安装"""
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return install_pyinstaller()


def detect_icon(project_root: Path, icon_path: Optional[str]) -> Optional[Path]:
    """检测可用图标，未提供时尝试自动寻找。"""
    if icon_path:
        candidate = Path(icon_path).expanduser()
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate.resolve() if candidate.exists() else None

    for icon_name in DEFAULT_ICON_NAMES:
        candidate = project_root / icon_name
        if candidate.exists():
            return candidate

    return None


def resolve_included_dirs(project_root: Path, include_data: bool = False) -> list[str]:
    """根据最小打包原则解析需要带入的资源目录。"""
    included_dirs: list[str] = []

    for dir_name in CORE_INCLUDED_DIRS:
        if (project_root / dir_name).exists():
            included_dirs.append(dir_name)
        else:
            print(f"Warning: optional core resource not found, skip: {dir_name}")

    if include_data:
        for dir_name in OPTIONAL_INCLUDED_DIRS:
            if (project_root / dir_name).exists():
                included_dirs.append(dir_name)
            else:
                print(f"Warning: requested resource dir not found, skip: {dir_name}")

    return included_dirs


def ensure_build_inputs(project_root: Path) -> bool:
    """确保入口脚本存在。"""
    entry_path = project_root / ENTRY_SCRIPT
    if not entry_path.exists():
        print(f"Error: entry script not found: {entry_path}")
        return False

    return True


def build_add_data_args(project_root: Path, included_dirs: list[str]) -> list[str]:
    """构造 PyInstaller 的 --add-data 参数。"""
    args: list[str] = []
    for dir_name in included_dirs:
        source = project_root / dir_name
        args.extend(["--add-data", f"{source};{dir_name}"])
    return args


def build_pyinstaller_command(
    project_root: Path,
    onefile: bool = False,
    console: bool = False,
    icon_path: Optional[Path] = None,
    include_data: bool = False,
) -> list[str]:
    """构造 PyInstaller 命令。"""
    included_dirs = resolve_included_dirs(project_root, include_data=include_data)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(project_root / ENTRY_SCRIPT),
        "--name",
        APP_NAME,
        "--noconfirm",
        "--clean",
        "--paths",
        str(project_root),
        "--collect-submodules",
        "pandas",
        "--collect-submodules",
        "openpyxl",
    ]

    cmd.append("--console" if console else "--windowed")
    cmd.append("--onefile" if onefile else "--onedir")

    if icon_path:
        cmd.extend(["--icon", str(icon_path)])

    cmd.extend(build_add_data_args(project_root, included_dirs))

    for hidden_import in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hidden_import])

    for excluded_module in EXCLUDED_MODULES:
        cmd.extend(["--exclude-module", excluded_module])

    return cmd


def get_output_path(project_root: Path, onefile: bool) -> Path:
    """获取预期输出路径。"""
    if onefile:
        return project_root / "dist" / f"{APP_NAME}.exe"
    return project_root / "dist" / APP_NAME / f"{APP_NAME}.exe"


def create_zip_archive(project_root: Path, onefile: bool) -> Optional[Path]:
    """为打包产物创建 zip 压缩包。"""
    dist_dir = project_root / "dist"
    if not dist_dir.exists():
        return None

    archive_base = dist_dir / f"{APP_NAME}-windows"
    if onefile:
        source_base = dist_dir / APP_NAME
        source_file = dist_dir / f"{APP_NAME}.exe"
        temp_dir = dist_dir / f"{APP_NAME}_zip_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, temp_dir / f"{APP_NAME}.exe")
        archive_path = shutil.make_archive(str(archive_base), "zip", temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        source_dir = dist_dir / APP_NAME
        archive_path = shutil.make_archive(str(archive_base), "zip", source_dir)

    return Path(archive_path)


def build_exe(
    onefile: bool = False,
    console: bool = False,
    icon_path: Optional[str] = None,
    make_zip: bool = False,
    include_data: bool = False,
) -> bool:
    """使用 PyInstaller 打包 Windows exe"""
    project_root = get_project_root()
    os.chdir(project_root)

    print("=" * 60)
    print("Building Weverse Stock Monitor for Windows")
    print("=" * 60)
    print(f"Mode: {'onefile' if onefile else 'onedir'}")
    print(f"Window: {'console' if console else 'gui'}")
    print(f"Package profile: {'core + data' if include_data else 'core only'}")

    if not ensure_build_inputs(project_root):
        return False

    resolved_icon = detect_icon(project_root, icon_path)
    if icon_path and resolved_icon is None:
        print(f"Warning: icon not found, skip icon: {icon_path}")
    elif resolved_icon:
        print(f"Using icon: {resolved_icon}")
    else:
        print("No .ico file found, build will use default icon")

    cmd = build_pyinstaller_command(
        project_root=project_root,
        onefile=onefile,
        console=console,
        icon_path=resolved_icon,
        include_data=include_data,
    )

    try:
        print("Running PyInstaller...")
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Build failed!")
            if result.stdout:
                print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr[-4000:] if len(result.stderr) > 4000 else result.stderr)
            return False

        if result.stdout:
            print(result.stdout[-1200:] if len(result.stdout) > 1200 else result.stdout)
    except Exception as e:
        print(f"Build error: {e}")
        return False

    exe_path = get_output_path(project_root, onefile)
    if not exe_path.exists():
        print(f"Error: {exe_path} not found after build")
        return False

    zip_path = None
    if make_zip:
        zip_path = create_zip_archive(project_root, onefile)

    print("\n" + "=" * 60)
    print("Build successful!")
    print("=" * 60)
    print(f"Output: {exe_path}")
    print("\nTo run:")
    print(f"  Double-click: {exe_path}")

    if zip_path:
        print(f"\nZip package: {zip_path}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Weverse Stock Monitor for Windows")
    parser.add_argument("--clean", action="store_true", help="Clean before build")
    parser.add_argument("--onefile", action="store_true", help="Build a single-file exe")
    parser.add_argument("--console", action="store_true", help="Build with console window")
    parser.add_argument("--icon", help="Path to .ico file")
    parser.add_argument("--zip", action="store_true", help="Create a zip archive after build")
    parser.add_argument("--include-data", action="store_true", help="Also package local data directory")
    args = parser.parse_args()

    if sys.platform != "win32":
        print("Warning: this script is designed for Windows. Current platform may not support full packaging output.")

    if args.clean:
        clean_build()

    if not check_pyinstaller():
        return 1

    if build_exe(
        onefile=args.onefile,
        console=args.console,
        icon_path=args.icon,
        make_zip=args.zip,
        include_data=args.include_data,
    ):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
