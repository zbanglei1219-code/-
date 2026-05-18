import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.tasks.cookie_refresh import CookieRefreshTask
from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.notification import NotificationService


def load_env_from_config(config):
    env_map = {
        "NETEASE_PHONE": "netease_phone",
        "NETEASE_PASSWORD": "netease_password",
        "NETEASE_MD5_PASSWORD": "netease_md5_password",
        "GH_TOKEN": "gh_token",
        "GH_REPO": "gh_repo",
    }

    for env_name, config_name in env_map.items():
        if not os.environ.get(env_name) and config.get(config_name):
            os.environ[env_name] = config.get(config_name)


def validate_env():
    missing = []

    if not os.environ.get("NETEASE_PHONE"):
        missing.append("NETEASE_PHONE")

    if not os.environ.get("NETEASE_PASSWORD") and not os.environ.get("NETEASE_MD5_PASSWORD"):
        missing.append("NETEASE_PASSWORD 或 NETEASE_MD5_PASSWORD")

    if not os.environ.get("GH_TOKEN"):
        missing.append("GH_TOKEN")

    if not os.environ.get("GH_REPO"):
        missing.append("GH_REPO")

    if missing:
        raise RuntimeError("缺少必要环境变量: " + ", ".join(missing))


def main():
    logger = Logger()

    try:
        config = Config()
        load_env_from_config(config)
        validate_env()

        notifier = NotificationService(config, logger)

        task = CookieRefreshTask(logger, notifier)
        success = task.execute()

        if success:
            logger.info("✅ Cookie刷新成功")
            sys.exit(0)

        logger.error("❌ Cookie刷新失败")
        notifier.send_notification(
            "网易云音乐合伙人 Cookie刷新失败",
            "Cookie刷新任务执行失败，请检查网易云登录凭据、验证码、风控或 Cookie 写入逻辑。"
        )
        sys.exit(1)

    except Exception as e:
        error_message = f"Cookie刷新程序异常: {str(e)}"
        logger.error(error_message)

        try:
            config = Config()
            notifier = NotificationService(config, logger)
            notifier.send_notification(
                "网易云音乐合伙人 Cookie刷新异常",
                error_message
            )
        except Exception as notify_error:
            logger.error(f"发送异常通知时出错: {str(notify_error)}")

        sys.exit(1)


if __name__ == "__main__":
    main()
