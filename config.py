#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
存放所有常量配置
"""

import os
import sys
from pathlib import Path


class Config:
    """应用配置类"""

    @classmethod
    def get_base_dir(cls):
        """获取应用基础目录（支持打包后的环境）"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的环境
            return Path(sys._MEIPASS)
        else:
            # 开发环境
            return Path(__file__).parent.resolve()

    @classmethod
    def get_data_dir(cls):
        """获取数据目录（使用用户主目录，避免权限问题）"""
        if sys.platform == 'darwin':  # macOS
            data_dir = Path.home() / "Library" / "Application Support" / "WeverseStockMonitor" / "data"
        else:  # Windows/Linux
            data_dir = Path.home() / ".weverse_stock_monitor" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @property
    def BASE_DIR(self):
        return self.get_base_dir()

    @property
    def DATA_DIR(self):
        return self.get_data_dir()

    @property
    def EXCEL_FILE(self):
        return self.get_data_dir() / "products.xlsx"

    @property
    def LOG_FILE(self):
        return self.get_data_dir() / "monitor.log"

    # 监控配置
    MONITOR_INTERVAL = 30  # 轮询间隔（秒）
    MAX_PRODUCTS = 10      # 最大商品数量
    SOUND_DURATION = 15    # 响铃时长（秒）
    DEFAULT_SOUND = "Glass"  # Mac系统音名称

    # API配置
    BASE_URL = "https://shop.weverse.io"
    ARTIST_ID = "7"
    CURRENCY = "KRW"
    LANGUAGE = "zh-tw"
    OS = "web"
    USER_COUNTRY = "CN"

    # 请求头（固定值）
    HEADERS = {
        "x-benx-artistid": ARTIST_ID,
        "x-benx-currency": CURRENCY,
        "x-benx-os": OS,
        "x-benx-language": LANGUAGE,
        "x-weverse-usercountry": USER_COUNTRY,
        "x-user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "accept": "*/*",
        "accept-language": "zh-tw",
        "accept-encoding": "gzip, deflate, br, zstd",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    # Cookie（固定值）
    COOKIES = {
        "NEXT_LOCALE": "zh-tw",
        "wes_artistId": ARTIST_ID,
        "wes_currency": CURRENCY,
        "wes_display_user_country": USER_COUNTRY,
        "wes_order_user_country": "UNSET",
    }

    # GUI配置
    WINDOW_TITLE = "Weverse Shop 库存监控"
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 600

    # Excel表头
    EXCEL_COLUMNS = [
        "sale_id",
        "product_name",
        "artist",
        "status",
        "original_price",
        "sale_price",
        "available_quantity",
        "thumbnail",
        "restock_time",
        "last_check",
    ]

    @classmethod
    def ensure_data_dir(cls):
        """确保数据目录存在"""
        data_dir = cls.get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    @classmethod
    def get_api_url(cls, sale_id: int) -> str:
        """获取商品API URL"""
        return f"{cls.BASE_URL}/api/wvs/product/api/v1/sales/{sale_id}"
