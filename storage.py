"""
Excel数据存储模块
实现商品数据的持久化存储
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from models import Product, ProductStatus


class Storage:
    """Excel数据存储类"""

    @staticmethod
    def _get_default_data_dir() -> Path:
        """获取默认数据目录（支持打包后的环境）"""
        import sys
        if sys.platform == 'darwin':  # macOS
            return Path.home() / "Library" / "Application Support" / "WeverseStockMonitor" / "data"
        else:
            return Path.home() / ".weverse_stock_monitor" / "data"

    @property
    def DEFAULT_DATA_DIR(self) -> Path:
        return self._get_default_data_dir()

    @property
    def DEFAULT_EXCEL_FILE(self) -> Path:
        return self.DEFAULT_DATA_DIR / "products.xlsx"

    # 表头定义
    COLUMNS = [
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

    def __init__(self, filepath: Optional[str] = None):
        """
        初始化存储类，确保数据目录存在

        Args:
            filepath: Excel文件路径，默认使用 ./data/products.xlsx
        """
        if filepath:
            self.excel_file = Path(filepath)
            self.data_dir = self.excel_file.parent
        else:
            self.excel_file = self.DEFAULT_EXCEL_FILE
            self.data_dir = self.DEFAULT_DATA_DIR

        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_excel_path(self) -> Path:
        """获取Excel文件绝对路径"""
        return self.excel_file.resolve()

    def _file_exists(self) -> bool:
        """检查Excel文件是否存在"""
        return self.excel_file.exists()

    def _create_empty_dataframe(self) -> pd.DataFrame:
        """创建空的DataFrame"""
        return pd.DataFrame(columns=self.COLUMNS)

    def _product_to_dict(self, product: Product) -> dict:
        """将Product对象转换为字典"""
        return {
            "sale_id": product.sale_id,
            "product_name": product.name,
            "artist": product.artist or "",
            "status": product.status.value,
            "original_price": product.price,
            "sale_price": product.price,
            "available_quantity": product.available_quantity,
            "thumbnail": product.thumbnail_url or "",
            "restock_time": product.restock_time,
            "last_check": product.last_check_time,
        }

    def _dict_to_product(self, row: pd.Series) -> Product:
        """将DataFrame行转换为Product对象"""
        # 处理status字段
        status_str = row.get("status", "sale")
        try:
            status = ProductStatus(status_str)
        except ValueError:
            status = ProductStatus.SALE

        # 处理时间字段
        restock_time = row.get("restock_time")
        if pd.isna(restock_time):
            restock_time = None

        last_check = row.get("last_check")
        if pd.isna(last_check):
            last_check = datetime.now()

        return Product(
            sale_id=str(row.get("sale_id", "")),
            name=str(row.get("product_name", "")),
            status=status,
            price=float(row.get("sale_price", 0) or row.get("original_price", 0)),
            available_quantity=int(row.get("available_quantity", 0)),
            thumbnail_url=str(row.get("thumbnail", "")) if pd.notna(row.get("thumbnail")) else None,
            artist=str(row.get("artist", "")) if pd.notna(row.get("artist")) else None,
            last_check_time=last_check if isinstance(last_check, datetime) else datetime.now(),
            restock_time=restock_time if isinstance(restock_time, datetime) else None,
        )

    def load_products(self) -> List[Product]:
        """
        从Excel加载商品列表

        Returns:
            List[Product]: 商品列表
        """
        if not self._file_exists():
            return []

        try:
            df = pd.read_excel(
                self.excel_file,
                engine="openpyxl",
            )

            if df.empty:
                return []

            # 确保所有列都存在
            for col in self.COLUMNS:
                if col not in df.columns:
                    df[col] = None

            products = []
            for _, row in df.iterrows():
                try:
                    product = self._dict_to_product(row)
                    products.append(product)
                except Exception as e:
                    # 跳过无效行，记录错误
                    print(f"跳过无效商品数据: {e}")
                    continue

            return products

        except Exception as e:
            print(f"加载Excel文件失败: {e}")
            return []

    def save_products(self, products: List[Product]) -> bool:
        """
        保存商品列表到Excel

        Args:
            products: 商品列表

        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            if not products:
                # 如果没有商品，创建空文件
                df = self._create_empty_dataframe()
            else:
                # 将Product列表转换为字典列表
                data = [self._product_to_dict(p) for p in products]
                df = pd.DataFrame(data)

                # 确保列顺序正确
                df = df[self.COLUMNS]

            # 保存到Excel
            df.to_excel(
                self.excel_file,
                index=False,
                engine="openpyxl",
            )
            return True

        except Exception as e:
            print(f"保存Excel文件失败: {e}")
            return False

    def update_restock_time(self, sale_id: str, timestamp: datetime) -> bool:
        """
        更新商品补货时间

        Args:
            sale_id: 商品ID
            timestamp: 补货时间戳

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        if not self._file_exists():
            return False

        try:
            df = pd.read_excel(
                self.excel_file,
                engine="openpyxl",
            )

            if df.empty or "sale_id" not in df.columns:
                return False

            # 查找并更新指定商品
            mask = df["sale_id"] == sale_id
            if not mask.any():
                return False

            df.loc[mask, "restock_time"] = timestamp

            # 保存回文件
            df.to_excel(
                self.excel_file,
                index=False,
                engine="openpyxl",
            )
            return True

        except Exception as e:
            print(f"更新补货时间失败: {e}")
            return False

    def product_exists(self, sale_id: str) -> bool:
        """
        检查商品是否已存在

        Args:
            sale_id: 商品ID

        Returns:
            bool: 商品存在返回True，否则返回False
        """
        if not self._file_exists():
            return False

        try:
            df = pd.read_excel(
                self.excel_file,
                engine="openpyxl",
            )

            if df.empty or "sale_id" not in df.columns:
                return False

            return (df["sale_id"] == sale_id).any()

        except Exception as e:
            print(f"检查商品存在性失败: {e}")
            return False
