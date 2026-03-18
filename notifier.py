#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac响铃通知模块
用于商品补货时播放系统音和显示桌面通知
"""

import subprocess
import threading
import time
from dataclasses import dataclass
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
    """Mac系统通知器类"""

    # Mac系统音文件路径
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

    def __init__(self, sound_enabled: bool = True, sound_name: str = "Glass", sound_duration: int = 5):
        """
        初始化通知器

        Args:
            sound_enabled: 是否启用声音
            sound_name: 系统音名称，默认Glass
            sound_duration: 响铃持续时间（秒），默认5秒
        """
        self.sound_enabled = sound_enabled
        self.sound_name = sound_name
        self.sound_duration = max(1, sound_duration)  # 至少1秒
        self._sound_process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()

    def enable_sound(self):
        """启用声音"""
        self.sound_enabled = True

    def disable_sound(self):
        """禁用声音"""
        self.sound_enabled = False
        self._stop_alert_sound()

    def set_sound(self, sound_name: str):
        """
        设置系统音

        Args:
            sound_name: 系统音名称 (Glass, Funk, Hero, Ping, Purr, Sosumi, Submarine, Tink)
        """
        if sound_name in self.SYSTEM_SOUNDS:
            self.sound_name = sound_name
        else:
            raise ValueError(f"不支持的系统音: {sound_name}，可用选项: {list(self.SYSTEM_SOUNDS.keys())}")

    def play_alert_sound(self, duration: int = 10) -> None:
        """
        播放Mac系统音（最大音量）

        Args:
            duration: 响铃持续时间（秒），默认10秒
        """
        if not self.sound_enabled:
            return

        sound_path = self.SYSTEM_SOUNDS.get(self.sound_name, "/System/Library/Sounds/Glass.aiff")

        def _play_loop():
            """在后台线程中循环播放声音（最大音量）"""
            start_time = time.time()
            play_count = 0
            while not self._stop_event.is_set() and (time.time() - start_time) < duration:
                try:
                    play_count += 1
                    # 使用afplay播放系统音，音量调至最大(-v 10)
                    # 同时调整系统音量到最大
                    subprocess.run(
                        ["osascript", "-e", "set volume output volume 100"],
                        capture_output=True,
                        timeout=2
                    )
                    self._sound_process = subprocess.Popen(
                        ["afplay", "-v", "10", sound_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    self._sound_process.wait()
                    # 短暂停顿后再次播放
                    if not self._stop_event.is_set():
                        time.sleep(0.3)
                except Exception as e:
                    print(f"[警告] 播放声音失败: {e}")
                    break
            print(f"[响铃] 共播放 {play_count} 次")

        # 重置停止事件
        self._stop_event.clear()

        # 启动后台线程播放声音
        sound_thread = threading.Thread(target=_play_loop, daemon=True)
        sound_thread.start()

    def _stop_alert_sound(self) -> None:
        """停止播放声音"""
        self._stop_event.set()
        if self._sound_process and self._sound_process.poll() is None:
            try:
                self._sound_process.terminate()
                self._sound_process.wait(timeout=1)
            except Exception:
                pass

    def show_desktop_notification(self, title: str, message: str) -> None:
        """
        显示Mac桌面通知

        Args:
            title: 通知标题
            message: 通知内容
        """
        try:
            # 使用osascript显示桌面通知
            script = f'display notification "{message}" with title "{title}"'
            if self.sound_enabled:
                script += f' sound name "{self.sound_name}"'

            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"[错误] 显示通知失败: {e}")
        except Exception as e:
            print(f"[错误] 显示通知时发生异常: {e}")

    def notify_restock(self, product: Product) -> None:
        """
        商品补货通知
        播放声音 + 显示桌面通知

        Args:
            product: 商品对象
        """
        title = "Weverse监控 - 商品补货"
        message = f"【{product.name}】已补货！\n价格: {product.price:,} {product.currency}"

        # 播放声音（5秒）
        self.play_alert_sound(duration=5)

        # 显示桌面通知
        self.show_desktop_notification(title, message)

        print(f"[通知] {product.name} 补货提醒已发送")

    def notify_custom(self, title: str, message: str, play_sound: bool = True, duration: int = 5) -> None:
        """
        自定义通知

        Args:
            title: 通知标题
            message: 通知内容
            play_sound: 是否播放声音
            duration: 声音持续时间（秒）
        """
        if play_sound and self.sound_enabled:
            self.play_alert_sound(duration=duration)

        self.show_desktop_notification(title, message)


# 便捷函数
def create_notifier(sound_enabled: bool = True, sound_name: str = "Glass") -> Notifier:
    """
    创建通知器实例的便捷函数

    Args:
        sound_enabled: 是否启用声音
        sound_name: 系统音名称

    Returns:
        Notifier实例
    """
    return Notifier(sound_enabled=sound_enabled, sound_name=sound_name)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("Mac通知模块测试")
    print("=" * 60)

    # 创建通知器
    notifier = Notifier(sound_enabled=True, sound_name="Glass")

    # 测试商品
    test_product = Product(
        sale_id=12345,
        name="测试商品 - SEVENTEEN专辑",
        status="SALE",
        status_desc="正常销售",
        price=35000,
        original_price=40000,
        artist="SEVENTEEN",
        is_cart_usable=True
    )

    print("\n1. 测试播放系统音（3秒）...")
    notifier.play_alert_sound(duration=3)
    time.sleep(3)

    print("\n2. 测试桌面通知...")
    notifier.show_desktop_notification(
        title="Weverse监控测试",
        message="这是一条测试通知"
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
