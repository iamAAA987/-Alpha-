import logging
from datetime import datetime, timedelta

from .utils import BJT


def _parse_hhmm(value: str, default_hour: int, default_minute: int) -> tuple[int, int]:
    try:
        parts = value.strip().split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))
        return hour, minute
    except Exception:
        return default_hour, default_minute


def _in_time_range(now_hour: int, now_minute: int, start_h: int, start_m: int, end_h: int, end_m: int) -> bool:
    # 支持跨天的时间段，例如 23:02 -> 10:00
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m
    now_total = now_hour * 60 + now_minute
    if start_total <= end_total:
        return start_total <= now_total < end_total
    else:
        # 跨午夜
        return now_total >= start_total or now_total < end_total


def get_sleep_duration(config) -> int:
    """根据配置计算下一次检查的休眠秒数。
    配置项（[Schedule]）：
    - quiet_start, quiet_end (HH:MM)
    - high_start, high_end (HH:MM)
    - critical_minutes, critical_interval, high_interval, normal_interval
    默认为：
    quiet 23:02-10:00，high 15:00-23:00，critical_minutes=2，critical=30，高峰=60，普通=300
    """
    schedule = config['Schedule'] if 'Schedule' in config else {}

    quiet_start_h, quiet_start_m = _parse_hhmm(schedule.get('quiet_start', '23:02'), 23, 2)
    quiet_end_h, quiet_end_m = _parse_hhmm(schedule.get('quiet_end', '10:00'), 10, 0)

    high_start_h, high_start_m = _parse_hhmm(schedule.get('high_start', '15:00'), 15, 0)
    high_end_h, high_end_m = _parse_hhmm(schedule.get('high_end', '23:00'), 23, 0)

    try:
        critical_minutes = int(schedule.get('critical_minutes', 2))
        critical_interval = int(schedule.get('critical_interval', 30))
        high_interval = int(schedule.get('high_interval', 60))
        normal_interval = int(schedule.get('normal_interval', 300))
    except Exception:
        critical_minutes, critical_interval, high_interval, normal_interval = 2, 30, 60, 300

    now_bjt = datetime.now(BJT)
    hour = now_bjt.hour
    minute = now_bjt.minute

    # 安静时间段：暂停至 quiet_end
    if _in_time_range(hour, minute, quiet_start_h, quiet_start_m, quiet_end_h, quiet_end_m):
        pause_until = now_bjt.replace(hour=quiet_end_h, minute=quiet_end_m, second=0, microsecond=0)
        # 如果当前已过当天 quiet_end，需要顺延到次日
        quiet_end_total = quiet_end_h * 60 + quiet_end_m
        now_total = hour * 60 + minute
        if now_total >= quiet_end_total and not (quiet_start_h == quiet_end_h and quiet_start_m == quiet_end_m):
            pause_until += timedelta(days=1)
        sleep_seconds = int((pause_until - now_bjt).total_seconds())
        logging.info(f"处于休眠时间段，将暂停至北京时间 {pause_until.strftime('%Y-%m-%d %H:%M:%S')}")
        return max(30, sleep_seconds)

    # 高峰时间段
    if _in_time_range(hour, minute, high_start_h, high_start_m, high_end_h, high_end_m):
        # 整点前后 critical_minutes 分钟
        if minute >= 60 - critical_minutes or minute < critical_minutes:
            logging.info(f"处于关键时间段，{critical_interval}秒后检查。")
            return max(10, critical_interval)
        else:
            logging.info(f"处于高峰时段，{high_interval}秒后检查。")
            return max(10, high_interval)

    logging.info(f"处于普通时段，{normal_interval}秒后检查。")
    return max(10, normal_interval) 