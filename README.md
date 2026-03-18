# Weverse Shop 商品库存监控系统

## 项目说明

本项目用于监控 Weverse Shop 商品库存状态，支持自动检测商品补货并发送通知。

## API 逆向分析结果

### 逆向难度: ⭐⭐ (简单 - 中等)

| 项目 | 结论 |
|------|------|
| 加密参数 | ❌ 无加密签名 |
| 动态参数 | ⚠️ 少量动态参数（可处理） |
| 实现补货通知 | ✅ 完全可行 |

### 核心 API 接口

```
GET https://shop.weverse.io/api/wvs/product/api/v1/sales/{sale_id}?displayPlatform=WEB
```

### 固定请求头

```python
HEADERS = {
    "x-benx-artistid": "7",
    "x-benx-currency": "KRW",
    "x-benx-os": "web",
    "x-benx-language": "zh-tw",
    "x-weverse-usercountry": "CN",
    "x-user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
}
```

### 库存状态字段

| 字段 | 值 | 含义 |
|------|-----|------|
| `status` | "SALE" | 正常销售中 |
| `status` | "SOLD_OUT" | 已售罄 |
| `status` | "PRE_ORDER" | 预售中 |

## 文件说明

| 文件 | 说明 |
|------|------|
| `weverse_crawler.py` | Python 爬虫脚本 |
| `weverse_products.xlsx` | 爬取的商品库存数据 |
| `README.md` | 项目说明文档 |

## 使用方法

### 1. 运行爬虫

```bash
cd weverse-stock-monitor
python weverse_crawler.py
```

### 2. 查看数据

爬取的数据会自动保存到 `weverse_products.xlsx`

## 本次爬取结果

- **总商品数**: 10 个
- **有货 (SALE)**: 9 个
- **售罄 (SOLD_OUT)**: 1 个
- **艺术家**: SEVENTEEN

## 技术细节

### 发现的 API 端点

1. `GET /api/wvs/product/api/v1/sales/{sale_id}` - 商品详情
2. `GET /api/wvs/display/api/v1/sales/recommended-sales` - 推荐商品
3. `GET /api/wvs/display/api/v1/sales/artist-recent-sales/{artist_id}` - 艺术家最新商品

### 关键发现

- ✅ 所有请求参数均可硬编码
- ✅ 无签名机制，无需逆向
- ✅ 无加密参数
- ✅ 响应包含完整库存信息

## 实现补货监控

要监控商品补货，只需轮询商品详情 API，检查 `status` 字段：

```python
if product["status"] == "SALE":
    # 有货！发送通知
    send_notification(f"商品 {name} 已补货！")
```

## 免责声明

本项目仅供学习研究使用，请遵守 Weverse 的服务条款，合理使用 API。

---

分析时间: 2026-03-18
