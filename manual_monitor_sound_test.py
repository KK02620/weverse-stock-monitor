#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import time
from statistics import mean

from monitor import StockMonitor
from notifier import Notifier
from weverse_crawler import WeverseCrawler


def _product_payload(status: str, sale_id: int, index: int) -> dict:
    return {
        "sale_id": sale_id,
        "商品名称": f"测试商品-{sale_id}",
        "艺术家": "TEST",
        "状态": status,
        "状态说明": status,
        "原价": 10000,
        "售价": 10000,
        "货币": "KRW",
        "是否可加入购物车": status == "SALE",
        "是否显示购物车按钮": True,
        "最大购买数量": 1,
        "可用数量": 1 if status == "SALE" else 0,
        "partner_code": f"TEST-{index}",
        "缩略图": "",
        "采集时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "选项名称": "默认",
        "选项库存ID": str(index),
        "选项是否售罄": status != "SALE",
    }


class SequenceCrawler:
    def __init__(self, sale_id: int, sequence: list[str]):
        self.sale_id = sale_id
        self.sequence = sequence
        self.calls: list[float] = []
        self._index = 0

    def get_sale_detail(self, sale_id: int):
        self.calls.append(time.time())
        status = self.sequence[min(self._index, len(self.sequence) - 1)]
        self._index += 1
        return _product_payload(status, self.sale_id, self._index)


class TimedCrawler:
    def __init__(self, base_crawler):
        self.base_crawler = base_crawler
        self.calls: list[float] = []

    def get_sale_detail(self, sale_id: int):
        self.calls.append(time.time())
        return self.base_crawler.get_sale_detail(sale_id)


def _format_intervals(call_times: list[float]) -> tuple[list[float], float]:
    if len(call_times) < 2:
        return [], 0.0
    intervals = [round(call_times[i] - call_times[i - 1], 2) for i in range(1, len(call_times))]
    return intervals, round(mean(intervals), 2)


def run_sound_test(notifier: Notifier, duration: int):
    print("\n=== 声音测试 ===")
    print(f"将播放 {duration} 秒提示音，请你主观判断是否听到声音。")
    notifier.play_alert_sound(duration=duration)
    time.sleep(duration + 1)
    print("声音播放结束。")


def run_mock_monitor_test(interval: int, notifier: Notifier):
    print("\n=== 模拟监控测试（必触发响铃）===")
    sale_id = 999001
    crawler = SequenceCrawler(sale_id=sale_id, sequence=["SOLD_OUT", "SALE", "SALE"])
    monitor = StockMonitor(poll_interval=interval, crawler=crawler, notifier=notifier)
    trigger = {"count": 0}

    def on_restock(product):
        trigger["count"] += 1
        print(f"[补货回调] sale_id={product.sale_id} status={product.current_status} restock_count={product.restock_count}")

    monitor.on_restock(on_restock)
    monitor.add_product(sale_id)
    started = monitor.start()
    print(f"监控启动: {started}")
    wait_seconds = interval * 3 + 2
    time.sleep(wait_seconds)
    monitor.stop()

    products = monitor.get_monitored_products()
    product = products[0] if products else None
    intervals, avg_interval = _format_intervals(crawler.calls)
    print(f"采样次数: {len(crawler.calls)}")
    print(f"采样间隔: {intervals}")
    print(f"平均间隔: {avg_interval} 秒")
    if product:
        print(f"最终状态: {product.current_status}")
        print(f"补货计数: {product.restock_count}")
    print(f"回调触发次数: {trigger['count']}")


def run_real_monitor_test(interval: int, duration: int, sale_id: int, notifier: Notifier):
    print("\n=== 真实商品监控测试（是否响铃取决于测试窗口内是否发生补货）===")
    base_crawler = WeverseCrawler()
    crawler = TimedCrawler(base_crawler)
    monitor = StockMonitor(poll_interval=interval, crawler=crawler, notifier=notifier)
    trigger = {"count": 0}

    def on_restock(product):
        trigger["count"] += 1
        print(f"[真实补货回调] sale_id={product.sale_id} name={product.name} status={product.current_status}")

    monitor.on_restock(on_restock)
    monitor.add_product(sale_id)
    started = monitor.start()
    print(f"监控启动: {started}")
    time.sleep(duration)
    monitor.stop()

    products = monitor.get_monitored_products()
    product = products[0] if products else None
    intervals, avg_interval = _format_intervals(crawler.calls)
    print(f"采样次数: {len(crawler.calls)}")
    print(f"采样间隔: {intervals}")
    print(f"平均间隔: {avg_interval} 秒")
    if product:
        print(f"当前状态: {product.current_status}")
        print(f"商品名称: {product.name}")
        print(f"最近采集: {product.crawled_at}")
        print(f"补货计数: {product.restock_count}")
    print(f"回调触发次数: {trigger['count']}")


def build_notifier(use_mp3: bool, mp3_path: str, sound_duration: int) -> Notifier:
    notifier = Notifier(sound_enabled=True, sound_duration=sound_duration)
    if use_mp3:
        notifier.set_custom_sound(mp3_path)
    return notifier


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--sale-id", type=int, default=53635)
    parser.add_argument("--sound-duration", type=int, default=5)
    parser.add_argument("--mp3-path", type=str, default=r"c:\Users\Administrator\Desktop\项目归档\项目归档\05-自动化工具\weverse-stock-monitor\mp3\7095273652496665352.mp3")
    parser.add_argument("--use-mp3", action="store_true")
    parser.add_argument("--skip-sound", action="store_true")
    parser.add_argument("--skip-real", action="store_true")
    args = parser.parse_args()

    if args.interval < 5:
        raise ValueError("interval 不能小于 5 秒")

    notifier = build_notifier(args.use_mp3, args.mp3_path, args.sound_duration)

    if not args.skip_sound:
        run_sound_test(notifier, args.sound_duration)

    run_mock_monitor_test(args.interval, notifier)

    if not args.skip_real:
        run_real_monitor_test(args.interval, args.duration, args.sale_id, notifier)

    print("\n测试结束。")
    print("请你确认两件事：")
    print("1) 声音测试阶段是否听到了响铃")
    print("2) 模拟监控阶段是否在状态从 SOLD_OUT 变 SALE 时立即响铃")
    print("3) 真实监控阶段是否按你设置的 interval 周期抓取，并在真实补货时响铃")


if __name__ == "__main__":
    main()
