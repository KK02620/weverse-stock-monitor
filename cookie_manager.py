#!/usr/bin/env python3
"""
Cookie 管理模块
自动生成和维护 Weverse Shop 所需的 Cookie
"""

import requests
import json
from typing import Dict, Optional
from datetime import datetime


class WeverseCookieManager:
    """Weverse Cookie 管理器"""

    # IP 检测服务
    IP_API_SERVICES = [
        "https://ipapi.co/json/",
        "https://ipinfo.io/json",
        "http://ip-api.com/json/",
    ]

    def __init__(self):
        self._country_code: Optional[str] = None
        self._last_update: Optional[datetime] = None

    def detect_country(self) -> str:
        """
        检测当前出口 IP 的国家/地区码
        用于设置 wes_display_user_country
        """
        if self._country_code:
            return self._country_code

        for service in self.IP_API_SERVICES:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # 不同 API 返回的字段名不同
                    country = data.get("country") or data.get("country_code")
                    if country:
                        self._country_code = country.upper()
                        self._last_update = datetime.now()
                        return self._country_code
            except Exception:
                continue

        # 默认返回 HK（大多数亚洲 IP）
        return "HK"

    def generate_cookies(
        self,
        artist_id: str = "7",
        currency: str = "KRW",
        locale: str = "zh-tw",
        country: Optional[str] = None
    ) -> Dict[str, str]:
        """
        生成 Weverse Cookie

        Args:
            artist_id: 艺术家 ID，默认 7 (SEVENTEEN)
            currency: 货币代码，默认 KRW
            locale: 语言地区，默认 zh-tw
            country: 国家/地区码，默认自动检测

        Returns:
            Cookie 字典
        """
        if country is None:
            country = self.detect_country()

        return {
            "NEXT_LOCALE": locale,
            "wes_artistId": str(artist_id),
            "wes_currency": currency,
            "wes_display_user_country": country,
            "wes_order_user_country": "UNSET",
        }

    def get_headers_with_cookies(
        self,
        artist_id: str = "7",
        currency: str = "KRW",
        locale: str = "zh-tw",
        country: Optional[str] = None
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        """
        获取包含 Cookie 的完整请求头

        Returns:
            (headers, cookies) 元组
        """
        cookies = self.generate_cookies(artist_id, currency, locale, country)

        headers = {
            "x-benx-artistid": artist_id,
            "x-benx-currency": currency,
            "x-benx-os": "web",
            "x-benx-language": locale,
            "x-weverse-usercountry": country or self.detect_country(),
            "x-user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "accept": "*/*",
            "accept-language": locale,
            "accept-encoding": "gzip, deflate, br, zstd",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "referer": f"https://shop.weverse.io/{locale}/shop/{currency}/artists/{artist_id}",
            "sec-ch-ua": '"Not?A_Brand";v="99", "Chromium";v="130"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        return headers, cookies

    def test_cookie_validity(self, sale_id: int = 53635) -> bool:
        """
        测试当前生成的 Cookie 是否有效

        Returns:
            True if Cookie 有效，False otherwise
        """
        headers, cookies = self.get_headers_with_cookies()
        url = f"https://shop.weverse.io/api/wvs/product/api/v1/sales/{sale_id}"
        params = {"displayPlatform": "WEB"}

        try:
            session = requests.Session()
            session.headers.update(headers)
            session.cookies.update(cookies)

            response = session.get(url, params=params, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def refresh_if_needed(self, force: bool = False) -> Dict[str, str]:
        """
        如果需要，刷新 Cookie

        Args:
            force: 强制刷新

        Returns:
            新的 Cookie 字典
        """
        if force or not self._last_update:
            self._country_code = None
            return self.generate_cookies()

        # 检查是否需要更新（超过 1 小时）
        if self._last_update:
            elapsed = (datetime.now() - self._last_update).total_seconds()
            if elapsed > 3600:  # 1 小时
                self._country_code = None
                return self.generate_cookies()

        return self.generate_cookies()


# 便捷函数
def get_default_cookie_manager() -> WeverseCookieManager:
    """获取默认 Cookie 管理器实例"""
    return WeverseCookieManager()


def generate_weverse_cookies(
    artist_id: str = "7",
    currency: str = "KRW",
    locale: str = "zh-tw"
) -> Dict[str, str]:
    """
    便捷函数：生成 Weverse Cookie

    Example:
        >>> cookies = generate_weverse_cookies(artist_id="7")
        >>> print(cookies)
        {
            'NEXT_LOCALE': 'zh-tw',
            'wes_artistId': '7',
            'wes_currency': 'KRW',
            'wes_display_user_country': 'HK',
            'wes_order_user_country': 'UNSET'
        }
    """
    manager = WeverseCookieManager()
    return manager.generate_cookies(artist_id, currency, locale)


def test_cookies():
    """测试 Cookie 生成和有效性"""
    print("=" * 60)
    print("Weverse Cookie Manager Test")
    print("=" * 60)

    manager = WeverseCookieManager()

    # 测试国家检测
    print("\n1. Detecting country...")
    country = manager.detect_country()
    print(f"   Detected country: {country}")

    # 测试 Cookie 生成
    print("\n2. Generating cookies...")
    cookies = manager.generate_cookies()
    print(f"   Generated cookies:")
    for key, value in cookies.items():
        print(f"     {key}: {value}")

    # 测试请求头生成
    print("\n3. Generating headers...")
    headers, _ = manager.get_headers_with_cookies()
    print(f"   Generated {len(headers)} headers")

    # 测试 Cookie 有效性
    print("\n4. Testing cookie validity...")
    is_valid = manager.test_cookie_validity()
    status = "[OK] Valid" if is_valid else "[FAIL] Invalid"
    print(f"   {status}")

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)


if __name__ == "__main__":
    test_cookies()
