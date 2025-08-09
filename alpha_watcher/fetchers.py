import logging
import random
from typing import cast, Tuple

import tweepy
from bs4 import BeautifulSoup
from bs4.element import Tag, ResultSet
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .utils import USER_AGENTS


def get_latest_tweet_from_api(config, stats) -> Tuple[str | None, str | None]:
    source = "Twitter API"
    stats.setdefault(source, {'attempts': 0, 'successes': 0})
    stats[source]['attempts'] += 1

    try:
        cfg_twitter = config['TWITTER']
        client = tweepy.Client(bearer_token=cfg_twitter['bearer_token'])
        user_id = cfg_twitter['user_id']
        username = cfg_twitter['target_username']

        logging.info(f"正在尝试从 {source} 获取 @{username} 的推文...")
        response = client.get_users_tweets(user_id, exclude=['retweets', 'replies'], max_results=5)
        if not response.data:  # type: ignore[attr-defined]
            logging.warning(f"通过API未能获取到 @{username} 的任何推文。")
            return None, None

        latest_tweet = response.data[0]  # type: ignore[index]
        tweet_text = latest_tweet.text
        tweet_id = f"https://twitter.com/{username}/status/{latest_tweet.id}"
        logging.info(f"成功通过 API 获取到最新推文 ID: {latest_tweet.id}")
        stats[source]['successes'] += 1
        return tweet_text, tweet_id
    except Exception as e:
        logging.error(f"使用 Twitter API 时发生错误: {e}")
        return None, None


def get_latest_tweet_from_nitter(p, nitter_instances, stats) -> Tuple[str | None, str | None]:
    random.shuffle(nitter_instances)
    browser = None
    try:
        browser = p.chromium.launch(headless=True)
        for instance in nitter_instances:
            stats.setdefault(instance, {'attempts': 0, 'successes': 0})
            stats[instance]['attempts'] += 1

            page = None
            try:
                page = browser.new_page(user_agent=random.choice(USER_AGENTS))
                logging.info(f"正在尝试从 {instance} 获取推文 (使用Playwright)...")
                page.goto(instance, timeout=30000)
                page.wait_for_selector('div.timeline-item', timeout=30000)

                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                tweet_divs = cast(ResultSet[Tag], soup.find_all('div', class_='timeline-item', limit=5))
                if not tweet_divs:
                    logging.warning(f"在 {instance} 上未找到任何推文。")
                    continue

                latest_tweet_div: Tag | None = None
                for tweet_div in tweet_divs:
                    if not tweet_div.find('div', class_='pinned'):
                        latest_tweet_div = tweet_div
                        break
                    logging.info(f"在 {instance} 检测到并跳过一条置顶推文。")

                if not latest_tweet_div:
                    logging.warning(f"在 {instance} 上找到的推文均为置顶或无法解析，本次跳过。")
                    continue

                content_div = latest_tweet_div.find('div', class_='tweet-content')
                tweet_text = content_div.text.strip() if content_div else ""
                link_tag = cast(Tag | None, latest_tweet_div.find('a', class_='tweet-link'))
                tweet_id = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""

                if tweet_text and tweet_id:
                    logging.info(f"成功从 {instance} 获取到最新推文 ID: {tweet_id}")
                    stats[instance]['successes'] += 1
                    return tweet_text, tweet_id
                else:
                    logging.warning(f"在 {instance} 上解析推文内容或ID失败。")
            except PlaywrightTimeoutError:
                logging.error(f"访问 {instance} 超时，可能被验证码卡住或网络问题。")
            except Exception as e:
                logging.error(f"使用Playwright处理 {instance} 时发生未知错误: {e}")
            finally:
                if page:
                    page.close()
    except Exception as e:
        logging.error(f"Playwright 浏览器启动失败或发生严重错误: {e}")
    finally:
        if browser and browser.is_connected():
            browser.close()

    logging.error(f"尝试了 {len(nitter_instances)} 个Nitter实例，均无法访问。")
    return None, None 