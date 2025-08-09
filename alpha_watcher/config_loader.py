import configparser
import json
import logging
import os
import sys
from typing import Any

from .utils import resource_path


def _get_persistent_config_path() -> str:
    # 打包后写入到可执行文件同目录，便于持久化与手动编辑
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath('.')
    return os.path.join(base_dir, 'config.ini')


CONFIG_FILE = _get_persistent_config_path()
LOG_FILE = 'watcher.log'
STATS_FILE = 'stats.json'
DEDUP_STATE_FILE = 'dedup_state.json'


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')]
    )


def load_config():
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(CONFIG_FILE, encoding='utf-8')
        if 'Email' not in config or 'Scraper' not in config or 'TWITTER' not in config:
            logging.error("配置文件 config.ini 格式不正确，缺少 Email、Scraper 或 TWITTER 部分。")
            return None
        return config
    except Exception as e:
        logging.error(f"读取配置文件时发生错误: {e}")
        return None


def load_stats() -> dict[str, Any]:
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"读取统计文件 {STATS_FILE} 时失败: {e}")
        return {}


def save_stats(stats: dict[str, Any]) -> None:
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logging.error(f"保存统计文件 {STATS_FILE} 时失败: {e}")


def log_stats(stats: dict[str, Any]) -> None:
    logging.info("--- 数据源访问统计 ---")
    if not stats:
        logging.info("暂无统计数据。")
        return

    sorted_stats = sorted(
        stats.items(),
        key=lambda item: (item[1].get('successes', 0) / item[1].get('attempts', 1)) if isinstance(item[1], dict) else 0,
        reverse=True,
    )

    for source, data in sorted_stats:
        if not isinstance(data, dict):
            logging.warning(f"检测到并跳过格式不正确的统计条目: key='{source}', value='{data}'")
            continue
        attempts = data.get('attempts', 0)
        successes = data.get('successes', 0)
        success_rate = (successes / attempts * 100) if attempts > 0 else 0
        logging.info(f"来源: {source} | 成功率: {success_rate:.2f}% (成功: {successes} / 尝试: {attempts})")
    logging.info("--------------------") 