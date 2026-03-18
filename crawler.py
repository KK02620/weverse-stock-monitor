#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weverse Shop 异步HTTP爬虫模块
使用httpx.AsyncClient实现异步商品数据获取
"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import httpx

# 导入配置
from config import Config
from cookie_manager import WeverseCookieManager


@dataclass
class Product:
    """商品数据类"""
    sale_id: int
    name: str
    artist: str
    status: str
    status_text: str
    original_price: int
    sale_price: int
    currency: str
    is_cart_usable: bool
    is_cart_button_display: bool
    max_order_quantity: int
    available_quantity: int
    partner_code: str
    thumbnail_url: str
    option_name: str
    option_stock_id: str
    is_option_sold_out: bool
    crawled_at: str

    @classmethod
    def from_api_response(cls, data: Dict[str, Any], crawled_at: str) -> "Product":
        """从API响应数据创建Product对象"""
        # 解析选项信息
        options = data.get("option", {}).get("options", [])
        if options:
            option = options[0]
            option_name = option.get("saleOptionName", "")
            option_stock_id = str(option.get("saleStockId", ""))
            is_option_sold_out = option.get("isSoldOut", False)
        else:
            option_name = ""
            option_stock_id = ""
            is_option_sold_out = False

        # 状态翻译
        status_map = {
            "SALE": "正常销售",
            "SOLD_OUT": "已售罄",
            "PRE_ORDER": "预售中",
            "OUT_OF_STOCK": "缺货",
            "COMING_SOON": "即将发售",
        }
        status = data.get("status", "")
        status_text = status_map.get(status, status)

        # 价格信息
        # 网站显示的是不含税价格 supplySalePrice/supplyPrice，不是 salePrice/originalPrice
        price_info = data.get("price", {})
        original_price = price_info.get("supplyPrice") or price_info.get("originalPrice", 0) or 0
        sale_price = price_info.get("supplySalePrice") or price_info.get("salePrice", 0) or 0

        # 库存限制
        order_limit = data.get("goodsOrderLimit", {})
        max_order_quantity = order_limit.get("maxOrderQuantity", 0) or 0
        available_quantity = order_limit.get("availableQuantity", 0) or 0

        # 缩略图
        thumbnails = data.get("thumbnailImageUrls", [])
        thumbnail_url = thumbnails[0] if thumbnails else ""

        return cls(
            sale_id=data.get("saleId", 0),
            name=data.get("name", ""),
            artist=data.get("labelArtistInfo", {}).get("name", ""),
            status=status,
            status_text=status_text,
            original_price=original_price,
            sale_price=sale_price,
            currency="KRW",
            is_cart_usable=data.get("isCartUsable", False),
            is_cart_button_display=data.get("isCartButtonDisplay", False),
            max_order_quantity=max_order_quantity,
            available_quantity=available_quantity,
            partner_code=data.get("partnerCode", ""),
            thumbnail_url=thumbnail_url,
            option_name=option_name,
            option_stock_id=option_stock_id,
            is_option_sold_out=is_option_sold_out,
            crawled_at=crawled_at,
        )


class WeverseCrawler:
    """Weverse商店异步爬虫类"""

    # 使用config.py中的配置
    BASE_URL = Config.BASE_URL
    HEADERS = Config.HEADERS

    def __init__(self, timeout: float = 30.0, max_concurrent: int = 10, auto_refresh_cookies: bool = True):
        """
        初始化爬虫

        Args:
            timeout: 请求超时时间（秒）
            max_concurrent: 最大并发数
            auto_refresh_cookies: 是否自动刷新Cookie
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.auto_refresh_cookies = auto_refresh_cookies
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cookie_manager: Optional[WeverseCookieManager] = None

    def _ensure_cookie_manager(self):
        """确保Cookie管理器已初始化"""
        if self._cookie_manager is None:
            self._cookie_manager = WeverseCookieManager()

    async def __aenter__(self) -> "WeverseCrawler":
        """异步上下文管理器入口"""
        await self._init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.close()

    async def _init_client(self) -> None:
        """初始化httpx客户端"""
        if self._client is None:
            # 如果使用自动刷新Cookie，从Cookie管理器获取
            if self.auto_refresh_cookies:
                self._ensure_cookie_manager()
                headers, cookies = self._cookie_manager.get_headers_with_cookies()
                # 创建带Cookie的客户端
                self._client = httpx.AsyncClient(
                    headers=headers,
                    timeout=httpx.Timeout(self.timeout),
                    follow_redirects=True,
                )
                # 设置Cookie
                for name, value in cookies.items():
                    self._client.cookies.set(name, value, domain=".weverse.io")
            else:
                self._client = httpx.AsyncClient(
                    headers=self.HEADERS,
                    timeout=httpx.Timeout(self.timeout),
                    follow_redirects=True,
                )
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

    async def close(self) -> None:
        """关闭客户端连接"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._semaphore = None

    async def fetch_product(self, sale_id: int) -> Optional[Product]:
        """
        获取单个商品信息

        Args:
            sale_id: 商品ID

        Returns:
            Product对象，失败返回None
        """
        if self._client is None:
            raise RuntimeError("Crawler not initialized. Use async context manager or call _init_client()")

        url = f"{self.BASE_URL}/api/wvs/product/api/v1/sales/{sale_id}"
        params = {"displayPlatform": "WEB"}

        async with self._semaphore:
            try:
                response = await self._client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                from datetime import datetime
                crawled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return Product.from_api_response(data, crawled_at)

            except httpx.HTTPStatusError as e:
                print(f"[HTTP错误] 商品 {sale_id}: {e.response.status_code}")
                return None
            except httpx.RequestError as e:
                print(f"[请求错误] 商品 {sale_id}: {e}")
                return None
            except Exception as e:
                print(f"[错误] 处理商品 {sale_id} 时出错: {e}")
                return None

    async def fetch_products(self, sale_ids: List[int]) -> List[Product]:
        """
        并发获取多个商品信息

        Args:
            sale_ids: 商品ID列表

        Returns:
            Product对象列表
        """
        if not sale_ids:
            return []

        if self._client is None:
            raise RuntimeError("Crawler not initialized. Use async context manager or call _init_client()")

        # 使用asyncio.gather并发执行
        tasks = [self.fetch_product(sale_id) for sale_id in sale_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤掉异常和None结果
        products = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[异常] 商品 {sale_ids[i]}: {result}")
            elif result is not None:
                products.append(result)

        return products

    async def fetch_products_with_limit(self, sale_ids: List[int], batch_size: int = 10) -> List[Product]:
        """
        分批并发获取多个商品信息（控制内存使用）

        Args:
            sale_ids: 商品ID列表
            batch_size: 每批处理的商品数量

        Returns:
            Product对象列表
        """
        if not sale_ids:
            return []

        all_products = []
        for i in range(0, len(sale_ids), batch_size):
            batch = sale_ids[i:i + batch_size]
            print(f"[批次] 处理第 {i//batch_size + 1} 批，共 {len(batch)} 个商品")

            products = await self.fetch_products(batch)
            all_products.extend(products)

            # 批次间短暂延迟，避免请求过快
            if i + batch_size < len(sale_ids):
                await asyncio.sleep(0.5)

        return all_products


async def main():
    """示例用法"""
    target_sale_ids = [
        53635,  # 도겸X승관 1st Mini Album '소야곡' [LP]
        54059,  # Gloves
        54067,  # Blanket
        54069,  # L/S T-Shirt (Gray)
        54071,  # L/S T-Shirt (Navy)
    ]

    async with WeverseCrawler() as crawler:
        print(f"开始爬取 {len(target_sale_ids)} 个商品...")
        products = await crawler.fetch_products(target_sale_ids)

        print(f"\n成功获取 {len(products)} 个商品:")
        for product in products:
            status_icon = "[有货]" if product.status == "SALE" else "[缺货]"
            print(f"  {status_icon} {product.name[:30]}... - {product.status_text}")


if __name__ == "__main__":
    asyncio.run(main())
