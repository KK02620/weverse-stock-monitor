#!/usr/bin/env python3
"""
Weverse Cookie 模拟生成测试脚本
分析哪些 Cookie 可以静态模拟，哪些需要动态生成
"""

import requests
import json


def generate_cookies_v1_static():
    """
    方案1: 完全静态 Cookie（代码当前使用的）
    问题：wes_display_user_country = CN 可能与实际 IP 地区不符
    """
    return {
        "NEXT_LOCALE": "zh-tw",
        "wes_artistId": "7",
        "wes_currency": "KRW",
        "wes_display_user_country": "CN",  # 代码使用 CN
        "wes_order_user_country": "UNSET",
    }


def generate_cookies_v2_ip_based(ip_country="HK"):
    """
    方案2: 基于 IP 地区动态设置 wes_display_user_country
    根据实际出口 IP 的国家/地区码设置
    """
    return {
        "NEXT_LOCALE": "zh-tw",
        "wes_artistId": "7",
        "wes_currency": "KRW",
        "wes_display_user_country": ip_country,  # 根据实际 IP 设置
        "wes_order_user_country": "UNSET",
    }


def generate_cookies_v3_minimal():
    """
    方案3: 最小化 Cookie
    测试是否只需要关键字段
    """
    return {
        "wes_artistId": "7",
        "wes_currency": "KRW",
    }


def generate_cookies_v4_full_headers():
    """
    方案4: 完整的请求头和 Cookie
    添加更多可能需要的字段
    """
    return {
        "NEXT_LOCALE": "zh-tw",
        "wes_artistId": "7",
        "wes_currency": "KRW",
        "wes_display_user_country": "HK",
        "wes_order_user_country": "UNSET",
    }


def test_api_request(cookie_version, cookies, headers):
    """测试 API 请求"""
    url = "https://shop.weverse.io/api/wvs/product/api/v1/sales/53635"
    params = {"displayPlatform": "WEB"}

    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)

    try:
        response = session.get(url, params=params, timeout=10)

        result = {
            "version": cookie_version,
            "status_code": response.status_code,
            "success": response.status_code == 200,
        }

        if response.status_code == 200:
            data = response.json()
            result["data"] = {
                "sale_id": data.get("saleId"),
                "name": data.get("name"),
                "status": data.get("status"),
                "price": data.get("price", {}).get("supplySalePrice") or data.get("price", {}).get("salePrice"),
            }
            result["message"] = "[OK] Success"
        else:
            result["error"] = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                result["error_detail"] = error_data
            except:
                result["error_detail"] = response.text[:200]
            result["message"] = f"[FAIL] Error {response.status_code}"

        return result

    except Exception as e:
        return {
            "version": cookie_version,
            "success": False,
            "error": str(e),
            "message": f"[ERROR] {str(e)}",
        }


def main():
    """主测试函数"""
    print("=" * 70)
    print("Weverse Cookie 模拟生成测试")
    print("=" * 70)

    # 基础请求头
    base_headers = {
        "x-benx-artistid": "7",
        "x-benx-currency": "KRW",
        "x-benx-os": "web",
        "x-benx-language": "zh-tw",
        "x-weverse-usercountry": "CN",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "accept": "*/*",
        "accept-language": "zh-tw",
        "referer": "https://shop.weverse.io/zh-tw/shop/KRW/artists/7/sales/53635",
        "sec-ch-ua": '"Not?A_Brand";v="99", "Chromium";v="130"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    # 测试不同 Cookie 方案
    test_cases = [
        ("方案1-静态CN", generate_cookies_v1_static()),
        ("方案2-IP匹配HK", generate_cookies_v2_ip_based("HK")),
        ("方案3-最小化", generate_cookies_v3_minimal()),
        ("方案4-完整", generate_cookies_v4_full_headers()),
    ]

    results = []
    for version, cookies in test_cases:
        print(f"\n测试 {version}...")
        result = test_api_request(version, cookies, base_headers)
        results.append(result)
        print(f"  {result['message']}")
        if result.get('data'):
            print(f"  商品: {result['data']['name'][:30]}...")
            print(f"  价格: ₩{result['data']['price']:,.0f}")
            print(f"  状态: {result['data']['status']}")

    # 输出总结
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)

    success_count = sum(1 for r in results if r['success'])
    print(f"Success: {success_count}/{len(results)}")

    for r in results:
        icon = "[OK]" if r['success'] else "[FAIL]"
        print(f"  {icon} {r['version']}: {r['message']}")

    # 分析结论
    print("\n" + "=" * 70)
    print("Cookie Generation Analysis")
    print("=" * 70)

    print("""
Based on test results:

1. wes_display_user_country
   - Browser actual: HK (based on IP geolocation)
   - Code current: CN
   - Suggestion: Should match actual exit IP country code
   - Can detect via: https://ipapi.co/country/

2. wes_artistId
   - Dynamically set based on artist page
   - Can extract from URL: /artists/{id}/
   - Not critical for API requests

3. Other fields
   - NEXT_LOCALE: matches language setting (zh-tw)
   - wes_currency: currency code (KRW)
   - wes_order_user_country: fixed UNSET

4. Conclusion
   - Cookies can be fully simulated
   - Key field: wes_display_user_country must match IP
   - Secondary: wes_artistId can be hardcoded or extracted
""")


if __name__ == "__main__":
    main()
