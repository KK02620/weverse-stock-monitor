#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weverse Shop 商品库存爬虫
用于监控商品库存状态
"""

import requests
import json
import pandas as pd
from datetime import datetime
import time

from cookie_manager import WeverseCookieManager


class WeverseCrawler:
    """Weverse商店爬虫类"""

    BASE_URL = "https://shop.weverse.io"

    # 固定请求头 - 所有参数都可以硬编码
    HEADERS = {
        "x-benx-artistid": "7",
        "x-benx-currency": "KRW",
        "x-benx-os": "web",
        "x-benx-language": "zh-tw",
        "x-weverse-usercountry": "CN",
        "x-user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "accept": "*/*",
        "accept-language": "zh-tw",
        "accept-encoding": "gzip, deflate, br, zstd",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    COOKIES = {
        "NEXT_LOCALE": "zh-tw",
        "wes_artistId": "7",
        "wes_currency": "KRW",
        "wes_display_user_country": "CN",
        "wes_order_user_country": "UNSET",
    }

    def __init__(self, auto_refresh_cookies: bool = True):
        """
        初始化爬虫

        Args:
            auto_refresh_cookies: 是否自动刷新Cookie
        """
        self.auto_refresh_cookies = auto_refresh_cookies
        self.session = requests.Session()

        if auto_refresh_cookies:
            # 使用Cookie管理器生成
            self.cookie_manager = WeverseCookieManager()
            headers, cookies = self.cookie_manager.get_headers_with_cookies()
            self.session.headers.update(headers)
            self.session.cookies.update(cookies)
        else:
            # 使用固定的HEADERS和COOKIES
            self.session.headers.update(self.HEADERS)
            self.session.cookies.update(self.COOKIES)

    def refresh_cookies(self):
        """刷新Cookie（当请求失败时调用）"""
        if self.auto_refresh_cookies and hasattr(self, 'cookie_manager'):
            headers, cookies = self.cookie_manager.get_headers_with_cookies()
            self.session.headers.update(headers)
            self.session.cookies.clear()
            self.session.cookies.update(cookies)
            return True
        return False

    def get_sale_detail(self, sale_id):
        """
        获取商品详情和库存状态

        Args:
            sale_id: 商品ID

        Returns:
            dict: 商品信息字典
        """
        url = f"{self.BASE_URL}/api/wvs/product/api/v1/sales/{sale_id}"
        params = {"displayPlatform": "WEB"}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 解析关键字段
            price_info = data.get("price", {})
            # 网站显示的是不含税价格 supplySalePrice，不是 salePrice
            display_price = price_info.get("supplySalePrice") or price_info.get("salePrice")
            original_display_price = price_info.get("supplyPrice") or price_info.get("originalPrice")

            result = {
                "sale_id": data.get("saleId"),
                "商品名称": data.get("name"),
                "艺术家": data.get("labelArtistInfo", {}).get("name"),
                "状态": data.get("status"),
                "状态说明": self._translate_status(data.get("status")),
                "原价": original_display_price,
                "售价": display_price,
                "货币": "KRW",
                "是否可加入购物车": data.get("isCartUsable"),
                "是否显示购物车按钮": data.get("isCartButtonDisplay"),
                "最大购买数量": data.get("goodsOrderLimit", {}).get("maxOrderQuantity"),
                "可用数量": data.get("goodsOrderLimit", {}).get("availableQuantity"),
                "partner_code": data.get("partnerCode"),
                "缩略图": data.get("thumbnailImageUrls", [""])[0] if data.get("thumbnailImageUrls") else "",
                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 解析选项库存
            options = data.get("option", {}).get("options", [])
            if options:
                option = options[0]
                result["选项名称"] = option.get("saleOptionName")
                result["选项库存ID"] = option.get("saleStockId")
                result["选项是否售罄"] = option.get("isSoldOut")
            else:
                result["选项名称"] = ""
                result["选项库存ID"] = ""
                result["选项是否售罄"] = ""

            return result

        except requests.exceptions.RequestException as e:
            print(f"[错误] 请求商品 {sale_id} 失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[错误] 解析商品 {sale_id} 数据失败: {e}")
            return None

    def _translate_status(self, status):
        """翻译状态码"""
        status_map = {
            "SALE": "正常销售",
            "SOLD_OUT": "已售罄",
            "PRE_ORDER": "预售中",
            "OUT_OF_STOCK": "缺货",
            "COMING_SOON": "即将发售",
        }
        return status_map.get(status, status)

    def get_artist_recent_sales(self, artist_id=7, limit=10):
        """
        获取艺术家最新商品列表

        Args:
            artist_id: 艺术家ID
            limit: 获取数量

        Returns:
            list: 商品列表
        """
        url = f"{self.BASE_URL}/api/wvs/display/api/v1/sales/artist-recent-sales/{artist_id}"
        params = {"displayPlatform": "WEB"}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            sales = data.get("sales", [])
            return sales[:limit]

        except Exception as e:
            print(f"[错误] 获取艺术家商品列表失败: {e}")
            return []

    def crawl_multiple_products(self, sale_ids):
        """
        爬取多个商品信息

        Args:
            sale_ids: 商品ID列表

        Returns:
            list: 商品信息列表
        """
        results = []
        try:
            print(f"开始爬取 {len(sale_ids)} 个商品...")
        except:
            pass

        for i, sale_id in enumerate(sale_ids, 1):
            try:
                print(f"[{i}/{len(sale_ids)}] Crawling product ID: {sale_id}...")
            except:
                pass
            product = self.get_sale_detail(sale_id)
            if product:
                results.append(product)
                try:
                    status_icon = "[IN_STOCK]" if product["状态"] == "SALE" else "[SOLD_OUT]"
                    name = product['商品名称'][:30] if product['商品名称'] else 'Unknown'
                    status = product['状态说明']
                    print(f"   {status_icon} {name}... - {status}")
                except:
                    pass
            time.sleep(0.5)

        try:
            print(f"\nSuccessfully crawled {len(results)} products")
        except:
            pass
        return results

    def save_to_excel(self, products, filename="weverse_products.xlsx"):
        """
        保存商品数据到Excel

        Args:
            products: 商品信息列表
            filename: 文件名
        """
        if not products:
            print("[错误] 没有数据可保存")
            return

        df = pd.DataFrame(products)

        # 调整列顺序
        columns_order = [
            "sale_id",
            "商品名称",
            "艺术家",
            "状态",
            "状态说明",
            "原价",
            "售价",
            "货币",
            "是否可加入购物车",
            "是否显示购物车按钮",
            "最大购买数量",
            "可用数量",
            "选项名称",
            "选项库存ID",
            "选项是否售罄",
            "partner_code",
            "缩略图",
            "采集时间",
        ]

        # 只保留存在的列
        df = df[[col for col in columns_order if col in df.columns]]

        # 保存到Excel（使用当前工作目录或用户桌面）
        from pathlib import Path
        import platform

        if platform.system() == 'Darwin':  # macOS
            save_dir = Path.home() / "Desktop"
        else:  # Windows
            save_dir = Path.home() / "Desktop"

        save_dir.mkdir(exist_ok=True)
        filepath = save_dir / filename
        df.to_excel(filepath, index=False, engine='openpyxl')
        print(f"\n[保存] 数据已保存到: {filepath}")
        print(f"[统计] 共 {len(products)} 条记录")

        return df


def main():
    """主函数"""
    print("=" * 60)
    print("Weverse Shop Stock Monitor")
    print("=" * 60)

    # 创建爬虫实例
    crawler = WeverseCrawler()

    # 方法1: 使用预定义的商品ID列表
    # 这些ID来自SEVENTEEN商店的实际商品
    target_sale_ids = [
        53635,  # 도겸X승관 1st Mini Album '소야곡' [LP] - SOLD_OUT
        54059,  # Gloves
        54067,  # Blanket
        54069,  # L/S T-Shirt (Gray)
        54071,  # L/S T-Shirt (Navy)
        53154,  # 도겸X승관 1st Mini Album '소야곡' (Set)
        53165,  # 도겸X승관 1st Mini Album '소야곡' KiT Ver.
        55715,  # HOSHI PHOTOBOOK
        31653,  # [DINO] Dinosoul Wine Glass Set
        31652,  # [VERNON] Hansol's Cup
    ]

    # 爬取商品数据
    products = crawler.crawl_multiple_products(target_sale_ids)

    if products:
        # 保存到Excel
        df = crawler.save_to_excel(products)

        # 打印统计信息
        print("\n" + "=" * 60)
        print("库存统计")
        print("=" * 60)

        status_counts = df['状态说明'].value_counts()
        for status, count in status_counts.items():
            print(f"  {status}: {count} 个")

        print(f"\n总价: KRW {df['售价'].sum():,}")
    else:
        print("[错误] 未获取到任何商品数据")


if __name__ == "__main__":
    main()
