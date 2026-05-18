import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.notification import NotificationService


def get_value(config, env_name, config_name=None):
    value = os.environ.get(env_name)

    if value:
        return value

    if config_name:
        return config.get(config_name)

    return None


def check_netease_cookie_valid(logger, music_u, csrf):
    if not music_u:
        logger.error("缺少 MUSIC_U")
        return False, "缺少 MUSIC_U"

    if not csrf:
        logger.error("缺少 CSRF")
        return False, "缺少 CSRF"

    cookies = {
        "MUSIC_U": music_u,
        "__csrf": csrf,
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://music.163.com/",
        "Accept": "application/json, text/plain, */*",
    }

    try:
        response = requests.get(
            "https://music.163.com/api/nuser/account/get",
            headers=headers,
            cookies=cookies,
            timeout=15,
        )

        logger.info(f"网易云账号接口状态码: {response.status_code}")

        try:
            data = response.json()
        except json.JSONDecodeError:
            text_preview = response.text[:300]
            logger.error(f"网易云返回内容不是 JSON: {text_preview}")
            return False, f"网易云返回内容不是 JSON，HTTP 状态码: {response.status_code}"

        logger.info(f"网易云账号接口返回 code: {data.get('code')}")

        if data.get("code") == 200 and data.get("account"):
            account = data.get("account") or {}
            user_id = account.get("id") or account.get("userId")
            logger.info(f"✅ Cookie 仍然有效，账号 ID: {user_id}")
            return True, "Cookie 仍然有效"

        logger.error(f"Cookie 已失效或未登录: {data}")
        return False, f"Cookie 已失效或未登录: {data}"

    except requests.exceptions.RequestException as e:
        logger.error(f"请求网易云接口失败: {str(e)}")
        return False, f"请求网易云接口失败: {str(e)}"

    except Exception as e:
        logger.error(f"Cookie 校验异常: {str(e)}")
        return False, f"Cookie 校验异常: {str(e)}"


def main():
    logger = Logger()

    try:
        config = Config()
        notifier = NotificationService(config, logger)

        logger.info("开始检查网易云 Cookie 状态")

        music_u = get_value(config, "MUSIC_U", "music_u")
        csrf = get_value(config, "CSRF", "csrf")

        valid, message = check_netease_cookie_valid(logger, music_u, csrf)

        if valid:
            logger.info("✅ Cookie 检查通过，无需通知")
            sys.exit(0)

        logger.error("❌ Cookie 检查失败，准备发送通知")

        notifier.send_notification(
            "网易云音乐合伙人 Cookie 已失效",
            (
                "当前 MUSIC_U 或 CSRF 已失效。\n\n"
                f"失败原因: {message}\n\n"
                "请在本地浏览器重新登录网易云音乐，然后复制新的 Cookie 值，"
                "更新 GitHub Secrets 中的 MUSIC_U 和 CSRF。\n\n"
                "注意: CSRF 对应浏览器 Cookie 里的 __csrf。"
            )
        )

        sys.exit(1)

    except Exception as e:
        error_message = f"Cookie 检查程序异常: {str(e)}"
        logger.error(error_message)

        try:
            config = Config()
            notifier = NotificationService(config, logger)
            notifier.send_notification(
                "网易云音乐合伙人 Cookie 检查异常",
                error_message
            )
        except Exception as notify_error:
            logger.error(f"发送异常通知时出错: {str(notify_error)}")

        sys.exit(1)


if __name__ == "__main__":
    main()
