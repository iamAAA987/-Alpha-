import configparser
import os
import sys
import random
import tweepy
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- 复用 watcher.py 中的辅助函数和常量 ---

def resource_path(relative_path):
    """ 获取资源的绝对路径，无论是从脚本运行还是从打包后的exe运行 """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
]

CONFIG_FILE = resource_path('config.ini')

def load_config():
    """加载配置文件，并禁用插值以处理特殊字符"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ 错误: 配置文件 'config.ini' 未找到。")
        return None
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(CONFIG_FILE, encoding='utf-8')
        return config
    except Exception as e:
        print(f"❌ 错误: 读取配置文件时出错 - {e}")
        return None

# --- 测试函数 ---

def test_twitter_api(config):
    """测试Twitter官方API的连通性"""
    print("\n--- 正在测试 Twitter API ---")
    if 'TWITTER' not in config:
        print("🟡 跳过: 配置文件中缺少 [TWITTER] 部分。")
        return

    try:
        cfg_twitter = config['TWITTER']
        client = tweepy.Client(bearer_token=cfg_twitter.get('bearer_token'))
        user_id = cfg_twitter.get('user_id')
        
        if not user_id:
            print("❌ 失败: 配置文件中缺少 'user_id'。")
            return
            
        # 使用一个简单的API调用来验证
        client.get_user(id=user_id)
        print("✅ 成功: Twitter API 连接正常，凭据有效。")

    except Exception as e:
        print(f"❌ 失败: 连接或验证时发生错误 - {e}")

def test_nitter_instance(p, instance_url):
    """测试单个Nitter实例的连通性"""
    print(f"--- 正在测试 Nitter 实例: {instance_url} ---")
    browser = None
    try:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=random.choice(USER_AGENTS))
        
        page.goto(instance_url, timeout=20000) # 20秒超时
        page.wait_for_selector('div.timeline-item', timeout=15000)
        
        print(f"✅ 成功: 实例 {instance_url} 看起来工作正常。")
    
    except PlaywrightTimeoutError:
        print(f"❌ 失败: 访问 {instance_url} 超时，可能无法访问或被验证码卡住。")
    except Exception as e:
        print(f"❌ 失败: 处理 {instance_url} 时发生未知错误: {e}")
    finally:
        if browser:
            browser.close()

def main():
    """主函数，执行所有测试"""
    print("===================================")
    print("=     数据源可用性测试脚本      =")
    print("===================================")

    config = load_config()
    if not config:
        return

    # 1. 测试Twitter API
    test_twitter_api(config)

    # 2. 测试所有Nitter实例
    print("\n--- 正在测试所有 Nitter 实例 ---")
    if 'Scraper' not in config or not config['Scraper'].get('nitter_instances'):
        print("🟡 跳过: 配置文件中缺少 Nitter 实例。")
    else:
        nitter_instances = [url.strip() for url in config['Scraper']['nitter_instances'].split('\n') if url.strip()]
        if not nitter_instances:
            print("🟡 跳过: Nitter 实例列表为空。")
        else:
            with sync_playwright() as p:
                for instance in nitter_instances:
                    test_nitter_instance(p, instance)
    
    print("\n===================================")
    print("=           测试完成            =")
    print("===================================")


if __name__ == '__main__':
    main() 