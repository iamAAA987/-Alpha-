import os
import sys
import re
import pytz

# 浏览器 UA 列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
]

# 北京时区
BJT = pytz.timezone('Asia/Shanghai')


def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，无论是从脚本运行还是从打包后的 exe 运行。"""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def normalize_tweet_id(tweet_id_or_url: object) -> str | None:
    """从推文 URL 或路径中提取纯数字 ID，用于统一比较。"""
    if not isinstance(tweet_id_or_url, str):
        return None

    # 优先匹配 status/ 后面的数字
    match = re.search(r'status/(\d+)', tweet_id_or_url)
    if match:
        return match.group(1)

    # 尝试 URL 或字符串末尾的纯数字
    match = re.search(r'(\d+)(?:[#?/].*)?$', tweet_id_or_url)
    if match:
        return match.group(1)

    return None


def normalize_text_for_fingerprint(text: str) -> str:
    """规范化文本用于计算去重指纹：小写化、合并空白、去掉不可见字符。"""
    simplified = re.sub(r'\s+', ' ', text or '').strip().lower()
    return simplified 