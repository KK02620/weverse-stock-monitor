#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台响铃与桌面通知模块
用于商品补货时播放系统音/自定义 MP3 并显示通知
"""

import importlib
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Product:
    """商品数据类"""
    sale_id: int
    name: str
    status: str
    status_desc: str
    price: int
    original_price: int
    currency: str = "KRW"
    artist: str = ""
    thumbnail: str = ""
    available_quantity: Optional[int] = None
    is_cart_usable: bool = False


class Notifier:
    """跨平台通知器类"""

    SYSTEM_SOUNDS = {
        "Glass": "/System/Library/Sounds/Glass.aiff",
        "Funk": "/System/Library/Sounds/Funk.aiff",
        "Hero": "/System/Library/Sounds/Hero.aiff",
        "Ping": "/System/Library/Sounds/Ping.aiff",
        "Purr": "/System/Library/Sounds/Purr.aiff",
        "Sosumi": "/System/Library/Sounds/Sosumi.aiff",
        "Submarine": "/System/Library/Sounds/Submarine.aiff",
        "Tink": "/System/Library/Sounds/Tink.aiff",
    }

    def __init__(
        self,
        sound_enabled: bool = True,
        sound_name: str = "Glass",
        sound_duration: int = 5,
        custom_sound_path: Optional[str] = None,
    ):
        self.sound_enabled = sound_enabled
        self.sound_name = sound_name
        self.sound_duration = max(1, sound_duration)
        self.custom_sound_path: Optional[str] = None
        self._sound_process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()

        if custom_sound_path:
            self.set_custom_sound(custom_sound_path)

    def enable_sound(self):
        """启用声音"""
        self.sound_enabled = True

    def disable_sound(self):
        """禁用声音"""
        self.sound_enabled = False
        self._stop_alert_sound()

    def set_sound(self, sound_name: str):
        """设置系统音"""
        if sound_name in self.SYSTEM_SOUNDS:
            self.sound_name = sound_name
            return
        raise ValueError(f"不支持的系统音: {sound_name}，可用选项: {list(self.SYSTEM_SOUNDS.keys())}")

    def set_custom_sound(self, file_path: Optional[str]):
        """设置自定义 MP3 提示音；传入 None 时恢复系统铃声"""
        if not file_path:
            self.custom_sound_path = None
            return

        path = Path(file_path).expanduser()
        if path.suffix.lower() != ".mp3":
            raise ValueError("仅支持 MP3 提示音文件")

        self.custom_sound_path = str(path)

    def _play_system_sound_once(self) -> None:
        """按平台播放一次系统提示音"""
        if sys.platform == "win32":
            winsound = importlib.import_module("winsound")
            winsound.MessageBeep(getattr(winsound, "MB_ICONEXCLAMATION", -1))
            time.sleep(1)
            return

        sound_path = self.SYSTEM_SOUNDS.get(self.sound_name, self.SYSTEM_SOUNDS["Glass"])

        if sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e", "set volume output volume 100"],
                capture_output=True,
                timeout=2,
            )
            self._sound_process = subprocess.Popen(
                ["afplay", "-v", "10", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._sound_process.wait()
            return

        print("\a", end="", flush=True)
        time.sleep(1)

    def _get_custom_sound_command(self, sound_path: str) -> Optional[list[str]]:
        """获取非 Windows 平台的 MP3 播放命令"""
        if sys.platform == "darwin":
            return ["afplay", sound_path]

        for player in (
            ["ffplay", "-nodisp", "-autoexit", sound_path],
            ["mpg123", "-q", sound_path],
            ["mpv", "--no-terminal", sound_path],
        ):
            if shutil.which(player[0]):
                return player
        return None

    def _play_custom_sound_once(self) -> bool:
        """播放一次自定义 MP3；成功返回 True"""
        if not self.custom_sound_path:
            return False

        if sys.platform == "win32":
            try:
                import ctypes
                mciSendString = ctypes.windll.WINMM.mciSendStringW
                mciSendString('close custom_mp3', None, 0, 0)
                res = mciSendString(f'open "{self.custom_sound_path}" alias custom_mp3', None, 0, 0)
                if res != 0:
                    return False
                mciSendString('play custom_mp3', None, 0, 0)
                return True
            except Exception as e:
                print(f"[警告] 播放 MP3 失败: {e}")
                return False

        command = self._get_custom_sound_command(self.custom_sound_path)
        if command is None:
            return False

        self._sound_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._sound_process.wait()
        return True

    def play_alert_sound(self, duration: int = 10) -> None:
        """后台循环播放提示音"""
        if not self.sound_enabled:
            return

        def _play_loop():
            if self.custom_sound_path:
                played = self._play_custom_sound_once()
                if played:
                    if sys.platform == "win32":
                        import ctypes
                        mciSendString = ctypes.windll.WINMM.mciSendStringW
                        status_buffer = ctypes.create_unicode_buffer(256)
                        while not self._stop_event.is_set():
                            mciSendString('status custom_mp3 mode', status_buffer, 256, 0)
                            if status_buffer.value != 'playing':
                                break
                            time.sleep(0.3)
                    # Mac 在 _play_custom_sound_once 内部已阻塞 wait()，被打断时会自动退出
                    return
                # 如果播放自定义声音失败，退回到系统音
            
            start_time = time.time()
            play_count = 0

            while not self._stop_event.is_set() and (time.time() - start_time) < duration:
                try:
                    self._play_system_sound_once()
                    play_count += 1
                    if not self._stop_event.is_set():
                        time.sleep(0.3)
                except Exception as e:
                    print(f"[警告] 播放声音失败: {e}")
                    break

            print(f"[响铃] 共播放 {play_count} 次")

        self._stop_event.clear()
        sound_thread = threading.Thread(target=_play_loop, daemon=True)
        sound_thread.start()

    def _stop_alert_sound(self) -> None:
        """停止播放声音"""
        self._stop_event.set()

        if sys.platform == "win32":
            try:
                winsound = importlib.import_module("winsound")
                winsound.PlaySound(None, 0)
            except Exception:
                pass
            try:
                import ctypes
                mciSendString = ctypes.windll.WINMM.mciSendStringW
                mciSendString('stop custom_mp3', None, 0, 0)
                mciSendString('close custom_mp3', None, 0, 0)
            except Exception:
                pass

        if self._sound_process and self._sound_process.poll() is None:
            try:
                self._sound_process.terminate()
                self._sound_process.wait(timeout=1)
            except Exception:
                pass

    def show_desktop_notification(self, title: str, message: str) -> None:
        """显示桌面通知；非 macOS 平台降级为控制台输出"""
        if sys.platform != "darwin":
            print(f"[通知] {title}: {message}")
            return

        try:
            script = f'display notification "{message}" with title "{title}"'
            if self.sound_enabled and not self.custom_sound_path:
                script += f' sound name "{self.sound_name}"'

            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[错误] 显示通知失败: {e}")
        except Exception as e:
            print(f"[错误] 显示通知时发生异常: {e}")

    def notify_restock(self, product: Product) -> None:
        """商品补货通知"""
        title = "Weverse监控 - 商品补货"
        message = f"【{product.name}】已补货！\n价格: {product.price:,} {product.currency}"
        self.play_alert_sound(duration=5)
        self.show_desktop_notification(title, message)
        print(f"[通知] {product.name} 补货提醒已发送")

    def notify_custom(self, title: str, message: str, play_sound: bool = True, duration: int = 5) -> None:
        """自定义通知"""
        if play_sound and self.sound_enabled:
            self.play_alert_sound(duration=duration)
        self.show_desktop_notification(title, message)


def create_notifier(
    sound_enabled: bool = True,
    sound_name: str = "Glass",
    custom_sound_path: Optional[str] = None,
) -> Notifier:
    """创建通知器实例的便捷函数"""
    return Notifier(
        sound_enabled=sound_enabled,
        sound_name=sound_name,
        custom_sound_path=custom_sound_path,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("通知模块测试")
    print("=" * 60)

    notifier = Notifier(sound_enabled=True, sound_name="Glass")
    test_product = Product(
        sale_id=12345,
        name="测试商品 - SEVENTEEN专辑",
        status="SALE",
        status_desc="正常销售",
        price=35000,
        original_price=40000,
        artist="SEVENTEEN",
        is_cart_usable=True,
    )

    print("\n1. 测试播放系统音（3秒）...")
    notifier.play_alert_sound(duration=3)
    time.sleep(3)

    print("\n2. 测试桌面通知...")
    notifier.show_desktop_notification(
        title="Weverse监控测试",
        message="这是一条测试通知",
    )

    print("\n3. 测试补货通知...")
    notifier.notify_restock(test_product)

    print("\n4. 测试禁用声音...")
    notifier.disable_sound()
    print(f"   声音已禁用: {not notifier.sound_enabled}")

    print("\n5. 测试启用声音...")
    notifier.enable_sound()
    print(f"   声音已启用: {notifier.sound_enabled}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
