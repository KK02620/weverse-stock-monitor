#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库存监控调度器模块
用于监控Weverse Shop商品库存状态，检测补货并发送通知
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import threading

# 导入项目模块
try:
    from weverse_crawler import WeverseCrawler
except ImportError:
    WeverseCrawler = None

try:
    from notifier import Notifier
except ImportError:
    Notifier = None

try:
    from storage import Storage
except ImportError:
    Storage = None

try:
    from models import Product
except ImportError:
    Product = None


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MonitoredProduct:
    """被监控商品的数据类"""
    sale_id: int
    name: str = ""
    last_status: str = ""
    current_status: str = ""
    last_check_time: Optional[datetime] = None
    restock_count: int = 0
    product_info: Dict = field(default_factory=dict)

    # GUI 兼容字段
    restock_time: Optional[datetime] = None
    sale_price: float = 0.0
    original_price: float = 0.0
    status: str = ""  # 兼容 Product.status

    # 扩展字段 - 来自 crawler
    artist: str = ""
    status_text: str = ""
    currency: str = "KRW"
    available_quantity: int = 0
    max_order_quantity: int = 0
    option_name: str = ""
    partner_code: str = ""
    thumbnail_url: str = ""
    is_cart_usable: bool = False
    is_option_sold_out: bool = False
    crawled_at: str = ""


class StockMonitor:
    """
    库存监控调度器类

    功能：
    - 添加/移除监控商品
    - 异步定时轮询检查库存状态
    - 检测补货（SOLD_OUT -> SALE）并触发回调
    - 支持GUI与asyncio集成
    """

    def __init__(
        self,
        poll_interval: int = 30,
        crawler: Optional[WeverseCrawler] = None,
        notifier: Optional[Notifier] = None,
        storage: Optional[Storage] = None
    ):
        """
        初始化监控器

        Args:
            poll_interval: 轮询间隔（秒），默认30秒
            crawler: WeverseCrawler实例，为None时自动创建
            notifier: Notifier实例，为None时自动创建
            storage: Storage实例，为None时自动创建
        """
        self.poll_interval = poll_interval

        # 依赖组件
        self._crawler = crawler
        self._notifier = notifier
        self._storage = storage

        # 监控状态
        self._monitored_products: Dict[int, MonitoredProduct] = {}
        self._is_running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._thread_stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # 回调函数
        self._restock_callbacks: List[Callable[[MonitoredProduct], None]] = []

        # 线程安全锁
        self._lock: Optional[asyncio.Lock] = None

        # GUI集成支持
        self._gui_loop: Optional[asyncio.AbstractEventLoop] = None
        self._gui_thread_id: Optional[int] = None

        logger.info(f"StockMonitor初始化完成，轮询间隔: {poll_interval}秒")

    @property
    def crawler(self) -> WeverseCrawler:
        """获取或创建爬虫实例"""
        if self._crawler is None:
            if WeverseCrawler is None:
                raise ImportError("WeverseCrawler未找到，请确保crawler.py存在")
            self._crawler = WeverseCrawler()
        return self._crawler

    @property
    def notifier(self) -> Notifier:
        """获取或创建通知器实例"""
        if self._notifier is None:
            if Notifier is None:
                raise ImportError("Notifier未找到，请确保notifier.py存在")
            self._notifier = Notifier()
        return self._notifier

    @property
    def storage(self) -> Storage:
        """获取或创建存储实例"""
        if self._storage is None:
            if Storage is None:
                raise ImportError("Storage未找到，请确保storage.py存在")
            self._storage = Storage()
        return self._storage

    @property
    def interval(self) -> int:
        """获取当前轮询间隔（秒）"""
        return self.poll_interval

    @interval.setter
    def interval(self, value: int) -> None:
        """设置轮询间隔（秒）"""
        if value < 5:
            raise ValueError("轮询间隔不能小于5秒")
        self.poll_interval = value
        logger.info(f"轮询间隔已更新为 {value} 秒")

    def add_product(self, sale_id: int, product_name: str = "") -> bool:
        """
        添加监控商品

        Args:
            sale_id: 商品ID
            product_name: 商品名称（可选）

        Returns:
            bool: 是否添加成功
        """
        if sale_id in self._monitored_products:
            logger.warning(f"商品 {sale_id} 已在监控列表中")
            return False

        product = MonitoredProduct(
            sale_id=sale_id,
            name=product_name,
            last_status="UNKNOWN",
            current_status="UNKNOWN"
        )
        self._monitored_products[sale_id] = product
        logger.info(f"添加监控商品: {sale_id} ({product_name or '未知名称'})")
        return True

    def remove_product(self, sale_id: int) -> bool:
        """
        移除监控商品

        Args:
            sale_id: 商品ID

        Returns:
            bool: 是否移除成功
        """
        if sale_id not in self._monitored_products:
            logger.warning(f"商品 {sale_id} 不在监控列表中")
            return False

        del self._monitored_products[sale_id]
        logger.info(f"移除监控商品: {sale_id}")
        return True

    def get_monitored_products(self) -> List[MonitoredProduct]:
        """
        获取所有监控商品列表

        Returns:
            List[MonitoredProduct]: 监控商品列表
        """
        return list(self._monitored_products.values())

    def on_restock(self, callback: Callable[[MonitoredProduct], None]) -> None:
        """
        注册补货回调函数

        Args:
            callback: 回调函数，接收MonitoredProduct参数
        """
        if callback not in self._restock_callbacks:
            self._restock_callbacks.append(callback)
            logger.info(f"注册补货回调函数: {callback.__name__}")

    def remove_restock_callback(self, callback: Callable[[MonitoredProduct], None]) -> bool:
        """
        移除补货回调函数

        Args:
            callback: 要移除的回调函数

        Returns:
            bool: 是否移除成功
        """
        if callback in self._restock_callbacks:
            self._restock_callbacks.remove(callback)
            logger.info(f"移除补货回调函数: {callback.__name__}")
            return True
        return False

    async def _check_single_product(self, sale_id: int) -> Optional[MonitoredProduct]:
        """
        检查单个商品的库存状态

        Args:
            sale_id: 商品ID

        Returns:
            Optional[MonitoredProduct]: 更新后的商品信息
        """
        try:
            # 使用爬虫获取商品详情
            product_info = self.crawler.get_sale_detail(sale_id)

            if product_info is None:
                logger.error(f"获取商品 {sale_id} 信息失败")
                return None

            if self._lock is None:
                self._lock = asyncio.Lock()

            async with self._lock:
                if sale_id not in self._monitored_products:
                    return None

                product = self._monitored_products[sale_id]

                # 更新商品信息
                product.last_status = product.current_status
                product.current_status = product_info.get("状态", "UNKNOWN")
                product.status = product.current_status  # 兼容字段
                product.name = product_info.get("商品名称", product.name)
                product.last_check_time = datetime.now()
                product.product_info = product_info

                # 提取价格信息
                price_str = product_info.get("折扣价") or product_info.get("原价", "0")
                try:
                    product.sale_price = float(str(price_str).replace("₩", "").replace(",", "").strip() or 0)
                except (ValueError, TypeError):
                    product.sale_price = 0

                # 提取扩展字段
                product.artist = product_info.get("艺术家", "")
                product.status_text = product_info.get("状态说明", "")
                product.currency = product_info.get("货币", "KRW")
                product.available_quantity = product_info.get("可用数量", 0) or 0
                product.max_order_quantity = product_info.get("最大购买数量", 0) or 0
                product.option_name = product_info.get("选项名称", "")
                product.partner_code = product_info.get("partner_code", "")
                product.thumbnail_url = product_info.get("缩略图", "")
                product.is_cart_usable = product_info.get("是否可加入购物车", False)
                product.is_option_sold_out = product_info.get("选项是否售罄", False)
                product.crawled_at = product_info.get("采集时间", "")

                # 检测补货：任意非 SALE 状态转为 SALE 都触发
                if product.last_status != "SALE" and product.current_status == "SALE":
                    product.restock_count += 1
                    product.restock_time = datetime.now()  # 记录补货时间
                    logger.info(f"检测到商品补货: {sale_id} ({product.name})")

                    # 播放响铃 + 桌面通知
                    try:
                        self.notifier.play_alert_sound(duration=self.notifier.sound_duration)
                        self.notifier.show_desktop_notification(
                            title="Weverse监控 - 商品补货",
                            message=f"【{product.name}】已补货！"
                        )
                    except Exception as e:
                        logger.error(f"发送补货通知失败: {e}")

                    await self._trigger_restock_callbacks(product)

                return product

        except Exception as e:
            logger.error(f"检查商品 {sale_id} 时出错: {e}")
            return None

    async def _check_all_products(self) -> None:
        """并发检查所有监控商品"""
        if not self._monitored_products:
            logger.debug("监控列表为空，跳过本次检查")
            return

        sale_ids = list(self._monitored_products.keys())
        check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 打印检查开始信息到终端
        print(f"\n[{check_time}] 开始检查 {len(sale_ids)} 个商品...")

        # 并发检查所有商品
        tasks = [self._check_single_product(sale_id) for sale_id in sale_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果并打印详细信息
        success_count = 0
        error_count = 0
        restock_items = []

        for i, result in enumerate(results):
            sale_id = sale_ids[i]
            if isinstance(result, MonitoredProduct):
                success_count += 1
                status_icon = "✓" if result.current_status == "SALE" else "✗"
                status_text = result.current_status or "UNKNOWN"
                print(f"  [{status_icon}] ID {sale_id}: {result.name[:30]:<30} | 状态: {status_text}")

                # 记录补货商品
                if result.restock_time and result.restock_time.strftime("%Y-%m-%d %H:%M") == check_time[:-3]:
                    restock_items.append(result)
            else:
                error_count += 1
                print(f"  [✗] ID {sale_id}: 检查失败")

        # 打印统计信息
        print(f"检查完成: 成功 {success_count} 个, 失败 {error_count} 个")

        # 如果有补货，打印汇总信息
        if restock_items:
            print(f"\n⚠️  检测到 {len(restock_items)} 个商品补货!")
            for item in restock_items:
                print(f"   - {item.name} (ID: {item.sale_id})")

        logger.info(f"检查完成: 成功 {success_count} 个, 失败 {error_count} 个")

    async def _trigger_restock_callbacks(self, product: MonitoredProduct) -> None:
        """
        触发所有补货回调函数

        Args:
            product: 补货的商品信息
        """
        for callback in self._restock_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(product)
                else:
                    callback(product)
            except Exception as e:
                logger.error(f"执行回调函数 {callback.__name__} 时出错: {e}")

    async def _monitoring_loop(self) -> None:
        """监控主循环"""
        logger.info("监控循环已启动")

        while self._is_running:
            try:
                # 执行检查
                await self._check_all_products()

                # 等待下一次检查或停止信号
                try:
                    if self._stop_event is None:
                        await asyncio.sleep(self.poll_interval)
                    else:
                        await asyncio.wait_for(
                            self._stop_event.wait(),
                            timeout=self.poll_interval
                        )
                    # 如果收到停止信号，退出循环
                    break
                except asyncio.TimeoutError:
                    # 正常超时，继续下一次检查
                    pass

            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(1)  # 出错后短暂等待

        logger.info("监控循环已停止")

    def _run_monitor_thread(self) -> None:
        """在后台线程中运行 asyncio 监控循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()

        try:
            self._loop.run_until_complete(self._monitoring_loop())
        except Exception as e:
            logger.error(f"后台监控线程异常: {e}")
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._loop.close()
            self._loop = None
            self._stop_event = None
            self._lock = None

    def start(self) -> bool:
        """
        开始监控（启动异步任务）

        Returns:
            bool: 是否启动成功
        """
        if self._is_running:
            logger.warning("监控器已经在运行中")
            return False

        if not self._monitored_products:
            logger.warning("监控列表为空，请先添加商品")
            return False

        self._is_running = True
        self._thread_stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._run_monitor_thread,
            daemon=True,
            name="StockMonitorThread",
        )
        self._monitor_thread.start()

        logger.info(f"监控器已启动，正在监控 {len(self._monitored_products)} 个商品")
        return True

    def stop(self) -> bool:
        """
        停止监控

        Returns:
            bool: 是否停止成功
        """
        if not self._is_running:
            logger.warning("监控器未在运行")
            return False

        self._is_running = False
        self._thread_stop_event.set()

        if self._loop and self._stop_event:
            try:
                self._loop.call_soon_threadsafe(self._stop_event.set)
            except Exception as e:
                logger.warning(f"发送停止信号失败: {e}")

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

        logger.info("监控器已停止")
        return True

    def is_running(self) -> bool:
        """
        检查监控器是否正在运行

        Returns:
            bool: 是否正在运行
        """
        return self._is_running

    def set_poll_interval(self, interval: int) -> None:
        """
        设置轮询间隔

        Args:
            interval: 新的轮询间隔（秒）
        """
        self.poll_interval = max(5, interval)  # 最小5秒
        logger.info(f"轮询间隔已设置为 {self.poll_interval} 秒")

    # ==================== GUI集成支持 ====================

    def setup_for_gui(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        为GUI环境设置监控器

        Args:
            loop: GUI主线程的事件循环
        """
        self._gui_loop = loop
        self._gui_thread_id = threading.current_thread().ident
        logger.info("监控器已配置为GUI模式")

    def start_in_gui(self) -> bool:
        """
        在GUI环境中启动监控（线程安全）

        Returns:
            bool: 是否启动成功
        """
        return self.start()

    async def force_check(self) -> List[MonitoredProduct]:
        """
        强制立即检查所有商品（用于手动刷新）

        Returns:
            List[MonitoredProduct]: 所有商品的当前状态
        """
        await self._check_all_products()
        return self.get_monitored_products()


# ==================== 便捷函数 ====================

def create_default_monitor(poll_interval: int = 30) -> StockMonitor:
    """
    创建默认配置的监控器

    Args:
        poll_interval: 轮询间隔（秒）

    Returns:
        StockMonitor: 配置好的监控器实例
    """
    return StockMonitor(poll_interval=poll_interval)


async def run_monitor_for_products(
    sale_ids: List[int],
    restock_callback: Optional[Callable[[MonitoredProduct], None]] = None,
    poll_interval: int = 30,
    duration: Optional[int] = None
) -> None:
    """
    为指定商品列表运行监控（便捷函数）

    Args:
        sale_ids: 要监控的商品ID列表
        restock_callback: 补货回调函数
        poll_interval: 轮询间隔（秒）
        duration: 监控持续时间（秒），None表示永久
    """
    monitor = StockMonitor(poll_interval=poll_interval)

    # 添加商品
    for sale_id in sale_ids:
        monitor.add_product(sale_id)

    # 注册回调
    if restock_callback:
        monitor.on_restock(restock_callback)

    # 启动监控
    monitor.start()

    try:
        if duration:
            await asyncio.sleep(duration)
        else:
            # 永久运行，等待KeyboardInterrupt
            while True:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        monitor.stop()


# ==================== 示例用法 ====================

if __name__ == "__main__":
    # 示例：基本用法

    def on_restock_example(product: MonitoredProduct):
        """补货回调示例"""
        print(f"\n{'='*60}")
        print(f"补货通知！")
        print(f"商品ID: {product.sale_id}")
        print(f"商品名称: {product.name}")
        print(f"当前状态: {product.current_status}")
        print(f"补货次数: {product.restock_count}")
        print(f"{'='*60}\n")

    async def main():
        # 创建监控器
        monitor = StockMonitor(poll_interval=30)

        # 添加监控商品
        monitor.add_product(53635, "Test Product 1")
        monitor.add_product(54059, "Test Product 2")

        # 注册补货回调
        monitor.on_restock(on_restock_example)

        # 启动监控
        if monitor.start():
            print("监控已启动，按Ctrl+C停止...")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                monitor.stop()

    # 运行示例
    # asyncio.run(main())
    pass
