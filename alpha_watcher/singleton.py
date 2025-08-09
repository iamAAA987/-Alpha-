import os
import sys
import logging
from typing import Optional

from .config_loader import CONFIG_FILE

try:
    import msvcrt  # type: ignore
except ImportError:  # non-Windows
    msvcrt = None  # type: ignore

try:
    import fcntl  # type: ignore
except ImportError:
    fcntl = None  # type: ignore


_LOCK_FILE_PATH = os.path.join(os.path.dirname(CONFIG_FILE), 'watcher.lock')
_SINGLETON_LOCK_HANDLE: Optional[object] = None


def acquire_single_instance_or_exit() -> bool:
    """
    尝试获取单实例锁。若已在运行，则记录日志并返回 False。
    - Windows 使用 msvcrt.locking 实现强制文件锁
    - 类 Unix 使用 fcntl.flock
    锁文件位于 config.ini 同目录，名为 watcher.lock。
    """
    global _SINGLETON_LOCK_HANDLE

    try:
        # 保持文件句柄为全局，防止 gc 提前释放导致锁失效
        lock_file = open(_LOCK_FILE_PATH, 'a+b')
        _SINGLETON_LOCK_HANDLE = lock_file

        if msvcrt is not None and sys.platform.startswith('win'):
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                logging.info(f"单实例锁获取成功: {_LOCK_FILE_PATH}")
                return True
            except OSError:
                logging.error("检测到另一个实例正在运行（Windows 文件锁冲突）——本进程将退出。")
                return False

        if fcntl is not None:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
                logging.info(f"单实例锁获取成功: {_LOCK_FILE_PATH}")
                return True
            except OSError:
                logging.error("检测到另一个实例正在运行（Unix 文件锁冲突）——本进程将退出。")
                return False

        # 兜底：无法锁时退化为创建独占文件
        try:
            fd = os.open(_LOCK_FILE_PATH + '.pid', os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(str(os.getpid()))
            logging.info(f"单实例锁(兜底)获取成功: {_LOCK_FILE_PATH}.pid")
            return True
        except FileExistsError:
            logging.error("检测到另一个实例正在运行（兜底独占文件存在）——本进程将退出。")
            return False

    except Exception as e:
        logging.error(f"获取单实例锁时发生异常: {e}")
        # 容错选择退出，避免重复通知
        return False 