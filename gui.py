#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI界面模块 - tkinter 简约白色主题
使用Python内置组件，无外部依赖
"""

import sys
from datetime import datetime
from typing import List, Optional

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    HAS_TK = True
except ImportError:
    HAS_TK = False

from models import Product, ProductStatus

try:
    from monitor import MonitoredProduct
except ImportError:
    MonitoredProduct = Product


class SimpleGUI:
    """简约GUI主窗口"""

    def __init__(self, monitor, storage=None):
        self.monitor = monitor
        self.storage = storage  # 用于保存数据
        self.root = tk.Tk()
        self.root.title("Weverse Stock Monitor")
        self.root.geometry("900x700")
        self.root.configure(bg="white")
        self.root.minsize(800, 600)

        # 商品卡片字典
        self.cards = {}

        self._setup_ui()
        self._start_refresh()

    def _setup_ui(self):
        """设置界面"""
        # 标题区域
        header = tk.Frame(self.root, bg="white", padx=20, pady=15)
        header.pack(fill=tk.X)

        title = tk.Label(
            header,
            text="库存监控",
            font=("Helvetica", 26, "bold"),
            bg="white",
            fg="#000000"
        )
        title.pack(anchor=tk.W)

        subtitle = tk.Label(
            header,
            text="Weverse Shop 商品库存实时追踪",
            font=("Helvetica", 11),
            bg="white",
            fg="#555555"
        )
        subtitle.pack(anchor=tk.W, pady=(3, 0))

        # 分隔线
        line = tk.Frame(self.root, bg="#bbbbbb", height=1)
        line.pack(fill=tk.X, padx=20)

        # 工具栏
        self.toolbar = tk.Frame(self.root, bg="white", padx=20, pady=12)
        self.toolbar.pack(fill=tk.X)

        self.add_btn = tk.Button(
            self.toolbar,
            text="+ 添加商品",
            font=("Helvetica", 11, "bold"),
            bg="#000000",
            fg="white",
            activebackground="#333333",
            activeforeground="white",
            bd=0,
            padx=18,
            pady=7,
            cursor="hand2",
            command=self._show_add_dialog
        )
        self.add_btn.pack(side=tk.LEFT)

        # 间隔设置
        tk.Label(
            self.toolbar,
            text="监控间隔:",
            font=("Helvetica", 11),
            bg="white",
            fg="#333333"
        ).pack(side=tk.LEFT, padx=(25, 8))

        self.interval_var = tk.StringVar(value="30")
        interval_spin = tk.Spinbox(
            self.toolbar,
            from_=5,
            to=3600,
            textvariable=self.interval_var,
            width=6,
            font=("Helvetica", 11),
            bg="white",
            fg="black",
            buttonbackground="white"
        )
        interval_spin.pack(side=tk.LEFT)

        tk.Label(
            self.toolbar,
            text="秒",
            font=("Helvetica", 11),
            bg="white",
            fg="#333"
        ).pack(side=tk.LEFT, padx=(5, 20))

        self.monitor_btn = tk.Button(
            self.toolbar,
            text="开始监控",
            font=("Helvetica", 11),
            bg="white",
            fg="black",
            activebackground="#f0f0f0",
            activeforeground="black",
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self._toggle_monitor
        )
        self.monitor_btn.pack(side=tk.LEFT)

        self.test_sound_btn = tk.Button(
            self.toolbar,
            text="测试声音",
            font=("Helvetica", 11),
            bg="white",
            fg="black",
            activebackground="#f0f0f0",
            activeforeground="black",
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self._test_sound
        )
        self.test_sound_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.settings_btn = tk.Button(
            self.toolbar,
            text="音频设置 ▼",
            font=("Helvetica", 11),
            bg="white",
            fg="black",
            activebackground="#f0f0f0",
            activeforeground="black",
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self._toggle_settings_panel
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.counter_label = tk.Label(
            self.toolbar,
            text="0 / 10",
            font=("Helvetica", 11, "bold"),
            bg="#f5f5f5",
            fg="#333",
            padx=12,
            pady=5
        )
        self.counter_label.pack(side=tk.RIGHT)

        # 音频设置面板（默认隐藏）
        self.settings_panel = tk.Frame(self.root, bg="#f5f5f5", padx=20, pady=10)
        
        # 初始化读取现有设置
        initial_mp3 = bool(self.monitor.notifier.custom_sound_path)
        self.mp3_var = tk.BooleanVar(value=initial_mp3)
        
        self.mp3_check = tk.Checkbutton(
            self.settings_panel,
            text="启用 MP3 响铃 (替代系统音)",
            variable=self.mp3_var,
            font=("Helvetica", 11),
            bg="#f5f5f5",
            command=self._on_mp3_toggle
        )
        self.mp3_check.pack(side=tk.LEFT)

        self.play_mp3_btn = tk.Button(
            self.settings_panel,
            text="试听 MP3",
            font=("Helvetica", 10),
            bg="white",
            cursor="hand2",
            command=self._play_mp3_test
        )
        self.play_mp3_btn.pack(side=tk.LEFT, padx=(15, 0))

        self.stop_mp3_btn = tk.Button(
            self.settings_panel,
            text="停止试听",
            font=("Helvetica", 10),
            bg="white",
            cursor="hand2",
            command=self._stop_mp3_test
        )
        self.stop_mp3_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 商品列表区域
        list_frame = tk.Frame(self.root, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 画布 + 滚动条
        self.canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="white")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 空白提示
        self.empty_label = tk.Label(
            self.scrollable_frame,
            text="暂无商品，点击添加按钮开始监控",
            font=("Helvetica", 13),
            bg="white",
            fg="#cccccc"
        )
        self.empty_label.pack(pady=80)

        # 状态栏
        self.status_bar = tk.Label(
            self.root,
            text="就绪",
            font=("Helvetica", 10),
            bg="#f8f8f8",
            fg="#666666",
            anchor=tk.W,
            padx=20,
            pady=10
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # 窗口大小调整处理
        self.root.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        """处理窗口大小调整"""
        if event and event.widget == self.root:
            width = event.width - 60
            self.canvas.itemconfig(self.canvas_window, width=width)

    def _test_sound(self):
        """测试声音"""
        try:
            self.monitor.notifier.play_alert_sound(duration=5)
            self._update_status("正在测试声音（5秒）")
        except Exception as e:
            messagebox.showerror("错误", f"测试声音失败: {e}")

    def _toggle_settings_panel(self):
        if self.settings_panel.winfo_ismapped():
            self.settings_panel.pack_forget()
            self.settings_btn.config(text="音频设置 ▼")
        else:
            self.settings_panel.pack(fill=tk.X, after=self.toolbar)
            self.settings_btn.config(text="音频设置 ▲")

    def _on_mp3_toggle(self):
        is_enabled = self.mp3_var.get()
        import os
        mp3_path = os.path.join(os.path.dirname(__file__), "mp3", "7095273652496665352.mp3")
        
        if is_enabled:
            self.monitor.notifier.set_custom_sound(mp3_path)
            if self.storage:
                self.storage.save_notification_settings({"custom_sound_path": mp3_path})
            self._play_mp3_test()
        else:
            self.monitor.notifier.set_custom_sound(None)
            if self.storage:
                self.storage.save_notification_settings({"custom_sound_path": None})
            self._stop_mp3_test()

    def _play_mp3_test(self):
        self.monitor.notifier._stop_alert_sound()
        import os
        import threading
        mp3_path = os.path.join(os.path.dirname(__file__), "mp3", "7095273652496665352.mp3")
        
        self.monitor.notifier._stop_event.clear()
        def _test_loop():
            old_path = self.monitor.notifier.custom_sound_path
            self.monitor.notifier.custom_sound_path = mp3_path
            self.monitor.notifier._play_custom_sound_once()
            
            if sys.platform == "win32":
                import ctypes
                mciSendString = ctypes.windll.WINMM.mciSendStringW
                status_buffer = ctypes.create_unicode_buffer(256)
                while not self.monitor.notifier._stop_event.is_set():
                    mciSendString('status custom_mp3 mode', status_buffer, 256, 0)
                    if status_buffer.value != 'playing':
                        break
                    import time
                    time.sleep(0.3)
                    
            if not self.mp3_var.get():
                self.monitor.notifier.custom_sound_path = old_path

        threading.Thread(target=_test_loop, daemon=True).start()
        self._update_status("正在试听 MP3音频...")

    def _stop_mp3_test(self):
        self.monitor.notifier._stop_alert_sound()
        if not self.mp3_var.get():
            self.monitor.notifier.set_custom_sound(None)
        self._update_status("已停止试听")

    def _show_add_dialog(self):
        if len(self.cards) >= 10:
            messagebox.showinfo("提示", "最多监控 10 个商品")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("添加商品")
        dialog.geometry("500x400")
        dialog.configure(bg="white")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # 标题
        tk.Label(
            dialog,
            text="添加商品",
            font=("Helvetica", 16, "bold"),
            bg="white",
            fg="black"
        ).pack(anchor=tk.W, padx=20, pady=(20, 5))

        # 提示文字
        tk.Label(
            dialog,
            text="粘贴商品链接，每行一个",
            font=("Helvetica", 10),
            bg="white",
            fg="#888888"
        ).pack(anchor=tk.W, padx=20, pady=(0, 10))

        # 输入框
        text_input = tk.Text(
            dialog,
            font=("Helvetica", 11),
            bg="#fafafa",
            fg="black",
            bd=1,
            relief=tk.SOLID,
            height=10,
            padx=10,
            pady=10
        )
        text_input.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        text_input.insert("1.0", "https://shop.weverse.io/zh-tw/shop/KRW/artists/7/sales/53635")

        # 结果提示
        result_label = tk.Label(
            dialog,
            text="",
            font=("Helvetica", 10),
            bg="white",
            fg="#e74c3c"
        )
        result_label.pack(pady=(0, 10))

        # 按钮区域
        btn_frame = tk.Frame(dialog, bg="white")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        def on_cancel():
            dialog.destroy()

        def on_add():
            text = text_input.get("1.0", tk.END).strip()
            if not text:
                result_label.config(text="请输入至少一个链接")
                return

            sale_ids = self._parse_urls(text)
            if sale_ids:
                self._add_products(sale_ids)
                dialog.destroy()
            else:
                result_label.config(text="未能解析到有效的商品链接")

        cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            font=("Helvetica", 11),
            bg="white",
            fg="#333",
            bd=1,
            relief=tk.SOLID,
            padx=20,
            pady=6,
            command=on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

        add_btn = tk.Button(
            btn_frame,
            text="添加",
            font=("Helvetica", 11, "bold"),
            bg="black",
            fg="white",
            bd=0,
            padx=25,
            pady=6,
            command=on_add
        )
        add_btn.pack(side=tk.RIGHT)

        text_input.focus_set()

    def _parse_urls(self, text: str) -> List[int]:
        """解析URL提取sale_id"""
        import re
        ids = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            match = re.search(r'/sales/(\d+)', line)
            if match:
                ids.append(int(match.group(1)))
            elif line.isdigit():
                ids.append(int(line))
        return ids

    def _add_products(self, sale_ids: List[int]):
        """批量添加商品 - 立即获取详情"""
        added = 0
        skipped = 0

        # 导入爬虫
        from weverse_crawler import WeverseCrawler
        crawler = WeverseCrawler()

        for sale_id in sale_ids:
            if sale_id in self.cards:
                skipped += 1
                continue

            if len(self.cards) >= 10:
                messagebox.showinfo("提示", f"已添加 {added} 个商品，达到上限")
                break

            # 先添加到监控器
            if self.monitor.add_product(sale_id):
                added += 1

                # 立即获取商品详情
                try:
                    product_info = crawler.get_sale_detail(sale_id)
                    if product_info:
                        # 更新监控器中的商品信息
                        product = self.monitor._monitored_products.get(sale_id)
                        if product:
                            product.name = product_info.get("商品名称", "")
                            product.current_status = product_info.get("状态", "UNKNOWN")
                            product.status = product.current_status
                            product.sale_price = product_info.get("售价", 0) or product_info.get("原价", 0)
                            product.original_price = product_info.get("原价", 0)
                            product.artist = product_info.get("艺术家", "")
                            product.status_text = product_info.get("状态说明", "")
                            product.available_quantity = product_info.get("可用数量", 0) or 0
                            product.max_order_quantity = product_info.get("最大购买数量", 0) or 0
                            product.option_name = product_info.get("选项名称", "")
                            product.partner_code = product_info.get("partner_code", "")
                            product.thumbnail_url = product_info.get("缩略图", "")
                            product.is_cart_usable = product_info.get("是否可加入购物车", False)
                            product.is_option_sold_out = product_info.get("选项是否售罄", False)
                            product.crawled_at = product_info.get("采集时间", "")
                            product.product_info = product_info
                except Exception as e:
                    print(f"获取商品 {sale_id} 详情失败: {e}")

        self._update_status(f"已添加 {added} 个商品" + (f"，跳过 {skipped} 个重复" if skipped > 0 else ""))
        self._refresh()

    def _remove_product(self, sale_id: int):
        """删除商品"""
        if messagebox.askyesno("确认", f"删除商品 {sale_id}?"):
            if self.monitor.remove_product(sale_id):
                if sale_id in self.cards:
                    self.cards[sale_id].destroy()
                    del self.cards[sale_id]
                self._update_view()
                self._update_status("已删除")

    def _toggle_monitor(self):
        """切换监控状态"""
        if self.monitor_btn.cget("text") == "开始监控":
            try:
                interval = int(self.interval_var.get())
                self.monitor.interval = interval
            except ValueError:
                pass

            if self.monitor.start():
                self.monitor_btn.config(text="停止监控", fg="#e74c3c")
                self._update_status(f"监控中 ({self.interval_var.get()}秒)", active=True)
            else:
                messagebox.showwarning("提示", "请先添加商品")
        else:
            self.monitor.stop()
            self.monitor_btn.config(text="开始监控", fg="black")
            self._update_status("已停止")

    def _start_refresh(self):
        """启动定时刷新"""
        self._refresh()
        self.root.after(1000, self._start_refresh)

    def _refresh(self):
        """刷新商品列表"""
        products = self.monitor.get_monitored_products()
        self._update_list(products)
        self._update_view()

    def _update_list(self, products: List):
        """更新商品列表显示"""
        current_ids = set(self.cards.keys())
        new_ids = set(p.sale_id for p in products)

        for sid in current_ids - new_ids:
            if sid in self.cards:
                self.cards[sid].destroy()
                del self.cards[sid]

        for product in products:
            if product.sale_id not in self.cards:
                card = self._create_product_card(product)
                self.cards[product.sale_id] = card
            else:
                self._update_product_card(self.cards[product.sale_id], product)

    def _create_product_card(self, product) -> tk.Frame:
        """创建商品卡片 - 详细版"""
        card = tk.Frame(
            self.scrollable_frame,
            bg="white",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#cccccc",
            highlightthickness=1
        )
        card.pack(fill=tk.X, pady=6, ipady=15)
        card.product = product

        # 主内容区
        main_frame = tk.Frame(card, bg="white")
        main_frame.pack(fill=tk.X, padx=15, pady=12)

        # 左侧：商品基本信息
        left = tk.Frame(main_frame, bg="white")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 商品名称（大）
        name_text = product.name or "Unknown Product"
        name = tk.Label(
            left,
            text=name_text,
            font=("Helvetica", 14, "bold"),
            bg="white",
            fg="#000000",
            wraplength=350,
            justify=tk.LEFT
        )
        name.pack(anchor=tk.W)
        card.name_label = name

        # 艺术家
        artist_text = f"艺术家: {product.artist}" if hasattr(product, 'artist') and product.artist else ""
        if artist_text:
            artist = tk.Label(
                left,
                text=artist_text,
                font=("Helvetica", 10),
                bg="white",
                fg="#444444"
            )
            artist.pack(anchor=tk.W, pady=(4, 0))
            card.artist_label = artist

        # ID和代码
        meta_text = f"ID: {product.sale_id}"
        if hasattr(product, 'partner_code') and product.partner_code:
            meta_text += f"  |  Code: {product.partner_code}"

        meta = tk.Label(
            left,
            text=meta_text,
            font=("Helvetica", 9),
            bg="white",
            fg="#666666"
        )
        meta.pack(anchor=tk.W, pady=(6, 0))
        card.meta_label = meta

        # 选项信息
        if hasattr(product, 'option_name') and product.option_name:
            option = tk.Label(
                left,
                text=f"选项: {product.option_name}",
                font=("Helvetica", 9),
                bg="white",
                fg="#444444"
            )
            option.pack(anchor=tk.W, pady=(3, 0))
            card.option_label = option

        # 中间：价格区域
        price_frame = tk.Frame(main_frame, bg="white", padx=20)
        price_frame.pack(side=tk.LEFT, fill=tk.Y)

        # 原价（划线）
        orig_price = getattr(product, 'original_price', 0) or getattr(product, 'sale_price', 0)
        if orig_price and orig_price > 0:
            orig_label = tk.Label(
                price_frame,
                text=f"₩{orig_price:,.0f}",
                font=("Helvetica", 10),
                bg="white",
                fg="#888888"
            )
            orig_label.pack(anchor=tk.CENTER)
            card.orig_price_label = orig_label

        # 售价
        sale_price = getattr(product, 'sale_price', 0)
        if sale_price and sale_price > 0:
            price = tk.Label(
                price_frame,
                text=f"₩{sale_price:,.0f}",
                font=("Helvetica", 20, "bold"),
                bg="white",
                fg="#000000"
            )
        else:
            price = tk.Label(
                price_frame,
                text="-",
                font=("Helvetica", 20, "bold"),
                bg="white",
                fg="#000000"
            )
        price.pack(anchor=tk.CENTER)
        card.price_label = price

        # 库存信息
        stock_frame = tk.Frame(card, bg="#eeeeee", padx=15, pady=8)
        stock_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        # 库存数量
        avail = getattr(product, 'available_quantity', 0) or 0
        max_qty = getattr(product, 'max_order_quantity', 0) or 0

        stock_text = f"库存: {avail}"
        if max_qty > 0:
            stock_text += f"  |  限购: {max_qty}"

        stock_label = tk.Label(
            stock_frame,
            text=stock_text,
            font=("Helvetica", 10, "bold"),
            bg="#eeeeee",
            fg="#000000"
        )
        stock_label.pack(side=tk.LEFT)
        card.stock_label = stock_label

        # 购物车状态 - 基于 status 和 is_cart_usable 共同判断
        # 只有当 status 为 SALE 且 is_cart_usable 为 True 时才显示"可购买"
        status = getattr(product, 'current_status', '') or getattr(product, 'status', '')
        is_cart_usable = getattr(product, 'is_cart_usable', False)
        is_cart = (status == "SALE") and is_cart_usable
        cart_text = "可购买" if is_cart else "不可购买"
        cart_color = "#008800" if is_cart else "#cc0000"

        cart_label = tk.Label(
            stock_frame,
            text=cart_text,
            font=("Helvetica", 9, "bold"),
            bg="#eeeeee",
            fg=cart_color
        )
        cart_label.pack(side=tk.RIGHT)
        card.cart_label = cart_label

        # 右侧：状态和操作
        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态标签
        status_text, status_bg, status_fg = self._get_status_style(product)

        status = tk.Label(
            right,
            text=status_text,
            font=("Helvetica", 10, "bold"),
            bg=status_bg,
            fg=status_fg,
            padx=15,
            pady=5
        )
        status.pack()
        card.status_label = status

        # 更新时间
        crawled = getattr(product, 'crawled_at', "")
        if crawled:
            time_text = f"更新: {crawled}"
        else:
            time_text = ""

        time_label = tk.Label(
            right,
            text=time_text,
            font=("Helvetica", 8),
            bg="white",
            fg="#666666"
        )
        time_label.pack(pady=(5, 0))
        card.time_label = time_label

        # 删除按钮
        delete_btn = tk.Label(
            right,
            text="删除",
            font=("Helvetica", 9, "underline"),
            bg="white",
            fg="#cc0000",
            cursor="hand2"
        )
        delete_btn.pack(pady=(15, 0))
        delete_btn.bind("<Button-1>", lambda e, sid=product.sale_id: self._remove_product(sid))

        return card

    def _update_product_card(self, card, product):
        """更新现有卡片"""
        # 更新名称
        if hasattr(card, 'name_label'):
            name = product.name or "Unknown Product"
            if name == "Unknown Product" and hasattr(product, 'current_status') and product.current_status != "UNKNOWN":
                name = "获取中..."
            card.name_label.config(text=name)

        # 更新价格
        if hasattr(card, 'price_label'):
            sale_price = getattr(product, 'sale_price', 0)
            if sale_price and sale_price > 0:
                card.price_label.config(text=f"₩{sale_price:,.0f}", fg="#000000")
            else:
                card.price_label.config(text="-", fg="#888888")

        # 更新原价
        if hasattr(card, 'orig_price_label'):
            orig_price = getattr(product, 'original_price', 0)
            if orig_price and orig_price > 0 and orig_price != getattr(product, 'sale_price', 0):
                card.orig_price_label.config(text=f"₩{orig_price:,.0f}")

        # 更新库存
        if hasattr(card, 'stock_label'):
            avail = getattr(product, 'available_quantity', 0) or 0
            max_qty = getattr(product, 'max_order_quantity', 0) or 0
            stock_text = f"库存: {avail}"
            if max_qty > 0:
                stock_text += f"  |  限购: {max_qty}"
            card.stock_label.config(text=stock_text)

        # 更新购物车状态 - 基于 status 和 is_cart_usable 共同判断
        if hasattr(card, 'cart_label'):
            status = getattr(product, 'current_status', '') or getattr(product, 'status', '')
            is_cart_usable = getattr(product, 'is_cart_usable', False)
            is_cart = (status == "SALE") and is_cart_usable
            cart_text = "可购买" if is_cart else "不可购买"
            cart_color = "#008800" if is_cart else "#cc0000"
            card.cart_label.config(text=cart_text, fg=cart_color)

        # 更新状态
        if hasattr(card, 'status_label'):
            status_text, status_bg, status_fg = self._get_status_style(product)
            card.status_label.config(text=status_text, bg=status_bg, fg=status_fg)

        # 更新时间
        if hasattr(card, 'time_label'):
            crawled = getattr(product, 'crawled_at', "")
            if crawled:
                card.time_label.config(text=f"更新: {crawled}")

    def _get_status_style(self, product):
        """获取状态样式"""
        status = getattr(product, 'current_status', '') or getattr(product, 'status', '')

        if status == "SALE":
            return ("有货", "#006600", "white")
        elif status == "PRE_ORDER":
            return ("预售", "#004488", "white")
        elif getattr(product, 'restock_time', None):
            return ("已补货", "#660088", "white")
        elif status == "SOLD_OUT":
            return ("售罄", "#444444", "white")
        elif status == "COMING_SOON":
            return ("即将发售", "#cc6600", "white")
        else:
            return (status or "未知", "#888888", "white")

    def _update_view(self):
        """更新视图状态"""
        count = len(self.cards)
        self.counter_label.config(text=f"{count} / 10")

        if count == 0:
            self.empty_label.pack(pady=80)
        else:
            self.empty_label.pack_forget()

        if count >= 10:
            self.add_btn.config(state=tk.DISABLED, bg="#cccccc")
        else:
            self.add_btn.config(state=tk.NORMAL, bg="black")

    def _update_status(self, text: str, active: bool = False):
        """更新状态栏"""
        self.status_bar.config(
            text=text,
            fg="#27ae60" if active else "#666666"
        )

    def on_restock(self, product):
        """补货回调 - 显示通知并保存到Excel"""
        # 显示弹窗通知
        messagebox.showinfo(
            "补货提醒",
            f"{product.name}\n\n该商品已补货！"
        )

        # 保存到Excel
        if self.storage:
            try:
                from models import Product, ProductStatus
                # 转换MonitoredProduct为Product以便保存
                save_product = Product(
                    sale_id=str(product.sale_id),
                    name=product.name,
                    artist=product.artist,
                    status=ProductStatus(product.current_status.lower()) if hasattr(ProductStatus, product.current_status) else ProductStatus.UNKNOWN,
                    original_price=product.original_price,
                    sale_price=product.sale_price,
                    available_quantity=product.available_quantity,
                    thumbnail=product.thumbnail_url,
                    restock_time=product.restock_time,
                    last_check=product.crawled_at
                )
                # 加载现有数据并追加
                existing = self.storage.load_products()
                # 查找是否已存在
                found = False
                for i, p in enumerate(existing):
                    if p.sale_id == str(product.sale_id):
                        existing[i] = save_product
                        found = True
                        break
                if not found:
                    existing.append(save_product)

                # 保存
                if self.storage.save_products(existing):
                    print(f"  [保存成功] 商品 {product.name} 已保存到 Excel")
                else:
                    print(f"  [保存失败] 商品 {product.name} 保存失败")
            except Exception as e:
                print(f"  [保存错误] {e}")

    def run(self):
        """运行GUI"""
        self.root.mainloop()


# 兼容层
if not HAS_TK:
    class SimpleGUI:
        def __init__(self, monitor, storage=None):
            self.monitor = monitor
            self.storage = storage
        def run(self):
            print("tkinter is required but not available")
        def on_restock(self, product):
            pass
