#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序入口
整合所有模块，启动GUI监控程序
"""

import sys
import os

# PyInstaller 打包支持
if getattr(sys, 'frozen', False):
    # 打包后的环境
    bundle_dir = sys._MEIPASS
else:
    # 开发环境
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# 添加当前目录到路径
sys.path.insert(0, bundle_dir)

from config import Config
from models import MonitorConfig
from crawler import WeverseCrawler
from monitor import StockMonitor
from notifier import Notifier
from storage import Storage
from gui import SimpleGUI


def main():
    """主函数"""
    # 确保数据目录存在
    Config.ensure_data_dir()

    print("=" * 60)
    print("Weverse Shop Stock Monitor Starting...")
    print("=" * 60)

    # 初始化配置
    monitor_config = MonitorConfig(
        interval_seconds=Config.MONITOR_INTERVAL,
        max_products=Config.MAX_PRODUCTS,
        sound_duration=Config.SOUND_DURATION,
    )

    # 初始化组件
    storage = Storage(str(Config().EXCEL_FILE))
    notifier = Notifier(sound_duration=Config.SOUND_DURATION)

    # 创建爬虫和监控器
    crawler = WeverseCrawler()
    monitor = StockMonitor(
        poll_interval=monitor_config.interval_seconds,
        crawler=crawler,
        notifier=notifier,
        storage=storage,
    )

    # 加载已有商品
    print("Loading existing products...")
    products = storage.load_products()
    for product in products:
        monitor.add_product(int(product.sale_id))
    print(f"Loaded {len(products)} products")

    # 创建GUI，传入storage以便保存数据
    print("Starting GUI...")
    gui = SimpleGUI(monitor, storage)

    # 注册补货回调
    monitor.on_restock(gui.on_restock)

    # 运行GUI (tkinter主循环)
    print("GUI started, entering main loop...")
    gui.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
