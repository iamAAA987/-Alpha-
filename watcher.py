import logging
import time

from playwright.sync_api import sync_playwright

from alpha_watcher.config_loader import setup_logging, load_config, load_stats, save_stats, log_stats, DEDUP_STATE_FILE
from alpha_watcher.fetchers import get_latest_tweet_from_api, get_latest_tweet_from_nitter
from alpha_watcher.notifier import send_email, send_wecom
from alpha_watcher.scheduler import get_sleep_duration as get_sleep_duration_with_config
from alpha_watcher.utils import normalize_tweet_id
from alpha_watcher.deduper import Deduper
from alpha_watcher.singleton import acquire_single_instance_or_exit


def main():
    setup_logging()
    # 单实例锁，避免重复运行导致重复通知
    if not acquire_single_instance_or_exit():
        return
    logging.info("程序启动，开始监控币安华语推特...")

    config = load_config()
    if not config:
        logging.error("无法加载配置，程序退出。")
        return

    # 从配置加载所有 Nitter 实例与关键词
    all_nitter_instances = [url.strip() for url in config['Scraper']['nitter_instances'].split('\n') if url.strip()]
    keywords = [kw.strip() for kw in config['Scraper']['keywords'].split(',') if kw.strip()]

    # 定义高优先级实例（可根据需要调整）
    priority_nitter_instances = [
        "https://nitter.privacyredirect.com/binancezh",
        "https://nitter.tiekoetter.com/binancezh",
    ]
    other_nitter_instances = [inst for inst in all_nitter_instances if inst not in priority_nitter_instances]

    logging.info(f"高优先级Nitter实例: {priority_nitter_instances}")
    logging.info(f"其他Nitter实例: {other_nitter_instances}")

    if not keywords:
        logging.error("配置文件中缺少关键词。")
        return

    if not all_nitter_instances and 'TWITTER' not in config:
        logging.error("配置文件中既没有 Nitter 实例，也没有配置 Twitter API。")
        return

    logging.info(f"监控关键词: {keywords}")

    stats = load_stats()

    # 初始化去重器
    deduper = Deduper(DEDUP_STATE_FILE, max_history=300, ttl_seconds=7 * 24 * 3600, min_push_interval_seconds=90)

    # 启动时获取一次最新 ID 作为基准，以避免首次重复
    last_processed_normalized_id: str | None = None
    logging.info("正在进行初始化，获取最新的推文ID作为基准...")
    with sync_playwright() as p_init:
        fetchers_init = []
        for instance in priority_nitter_instances:
            fetchers_init.append(lambda p_instance=instance: get_latest_tweet_from_nitter(p_init, [p_instance], stats))
        fetchers_init.append(lambda: get_latest_tweet_from_api(config, stats))
        if other_nitter_instances:
            fetchers_init.append(lambda: get_latest_tweet_from_nitter(p_init, other_nitter_instances, stats))

        for fetcher_init in fetchers_init:
            try:
                _, initial_id = fetcher_init()
                if initial_id:
                    normalized_id = normalize_tweet_id(initial_id)
                    if normalized_id:
                        last_processed_normalized_id = normalized_id
                        logging.info(f"初始化成功，基准推文ID为: {last_processed_normalized_id} (原始ID: {initial_id})")
                        break
            except Exception as e:
                logging.error(f"初始化获取器执行失败: {e}")
                continue

    if not last_processed_normalized_id:
        logging.warning("初始化失败，无法获取任何推文ID。程序将从头开始检查，首次运行可能产生重复通知。")

    iteration_counter = 0

    with sync_playwright() as p:
        while True:
            try:
                tweet_text, tweet_id = None, None

                # 动态调整高优先级实例顺序
                current_priority_order = priority_nitter_instances if iteration_counter % 2 == 0 else priority_nitter_instances[::-1]

                fetchers = []
                for instance in current_priority_order:
                    fetchers.append(lambda p_instance=instance: get_latest_tweet_from_nitter(p, [p_instance], stats))
                fetchers.append(lambda: get_latest_tweet_from_api(config, stats))
                if other_nitter_instances:
                    fetchers.append(lambda: get_latest_tweet_from_nitter(p, other_nitter_instances, stats))

                for fetcher in fetchers:
                    try:
                        tweet_text, tweet_id = fetcher()
                        if tweet_text and tweet_id:
                            break
                    except Exception as e:
                        logging.error(f"执行获取方法时发生错误: {e}")
                        continue

                if tweet_text and tweet_id:
                    normalized_id = normalize_tweet_id(tweet_id)
                    if not normalized_id:
                        logging.error(f"无法对获取到的推文ID进行规范化: {tweet_id}，本次跳过比较。")
                    else:
                        is_new_id = (normalized_id != last_processed_normalized_id)
                        is_new_by_deduper = deduper.should_push(normalized_id, tweet_text)

                        if is_new_id and is_new_by_deduper:
                            logging.info(f"发现新推文 (ID: {normalized_id}): {tweet_text[:80]}...")
                            last_processed_normalized_id = normalized_id

                            if all(keyword in tweet_text for keyword in keywords):
                                logging.warning(f"检测到符合所有关键词的推文！-> {tweet_text}")
                                subject = "【重要提醒】币安Alpha新动态"
                                # 若邮件配置完整，则发送邮件
                                try:
                                    email_cfg = config['Email'] if 'Email' in config else None
                                    email_ok = bool(email_cfg and email_cfg.get('sender_email') and email_cfg.get('sender_password') and email_cfg.get('receiver_email'))
                                    if email_ok:
                                        send_email(subject, tweet_text, config)
                                except Exception as e:
                                    logging.error(f"邮件发送异常: {e}")
                                # 企业微信推送（若配置了 webhook 列表）
                                try:
                                    send_wecom(f"{subject}\n{tweet_text}", config)
                                except Exception as e:
                                    logging.error(f"企业微信推送异常: {e}")
                                deduper.mark_pushed(normalized_id, tweet_text)
                            else:
                                logging.info("新推文内容不符合关键词组合，已忽略。")
                        else:
                            logging.info(f"未发现新推文或被去重策略过滤 (ID: {normalized_id})。")
                else:
                    logging.error("所有获取方法均失败，本次检查跳过。")

                log_stats(stats)
                save_stats(stats)

                sleep_duration = get_sleep_duration_with_config(config)
                time.sleep(sleep_duration)
                iteration_counter += 1

            except KeyboardInterrupt:
                logging.info("程序被手动中断，正在退出。")
                break
            except Exception as e:
                logging.error(f"主循环发生未捕获的异常: {e}")
                logging.info("将在一分钟后重试...")
                time.sleep(60)


if __name__ == '__main__':
    main() 