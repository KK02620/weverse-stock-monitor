"""
数据模型模块
定义库存监控系统中使用的所有数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProductStatus(Enum):
    """商品状态枚举"""
    SALE = "sale"           # 销售中
    SOLD_OUT = "sold_out"   # 售罄
    PRE_ORDER = "pre_order" # 预售


@dataclass
class Product:
    """商品数据模型"""
    sale_id: str
    name: str
    status: ProductStatus
    price: float
    available_quantity: int
    thumbnail_url: Optional[str] = None
    artist: Optional[str] = None
    last_check_time: datetime = field(default_factory=datetime.now)
    restock_time: Optional[datetime] = None

    def is_in_stock(self) -> bool:
        """
        判断商品是否有货

        Returns:
            bool: 有货返回True，无货返回False
        """
        return (
            self.status == ProductStatus.SALE
            and self.available_quantity > 0
        )

    def __post_init__(self):
        """初始化后验证数据"""
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.available_quantity < 0:
            raise ValueError("Available quantity cannot be negative")


@dataclass
class MonitorConfig:
    """监控配置数据模型"""
    interval_seconds: int = 60      # 检查间隔（秒）
    max_products: int = 100         # 最大监控商品数量
    sound_duration: int = 5         # 提示音持续时间（秒）

    def __post_init__(self):
        """初始化后验证配置"""
        if self.interval_seconds < 1:
            raise ValueError("Interval must be at least 1 second")
        if self.max_products < 1:
            raise ValueError("Max products must be at least 1")
        if self.sound_duration < 1:
            raise ValueError("Sound duration must be at least 1 second")
