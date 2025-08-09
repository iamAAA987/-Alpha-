import json
import os
import time
import hashlib
from typing import Optional

from .utils import normalize_tweet_id, normalize_text_for_fingerprint


class Deduper:
    """
    稳健的去重器：
    - 基于 tweet_id（规范化）和内容指纹（规范化文本 + SHA1）
    - 维护固定大小的近期窗口 + TTL 自动清理
    - 支持最小推送间隔，避免短时重复推送
    - 以 json 文件持久化，程序重启后保持上下文
    """

    def __init__(
        self,
        state_file: str,
        max_history: int = 200,
        ttl_seconds: int = 7 * 24 * 3600,
        min_push_interval_seconds: int = 60,
    ) -> None:
        self.state_file = state_file
        self.max_history = max_history
        self.ttl_seconds = ttl_seconds
        self.min_push_interval_seconds = min_push_interval_seconds

        self._ids: dict[str, float] = {}
        self._fingerprints: dict[str, float] = {}
        self._last_push_ts: float = 0.0
        self._load()
        self._cleanup()

    # ---------- public API ----------

    def seen(self, tweet_id_or_url: Optional[str], text: Optional[str]) -> bool:
        """判断是否已见。若未知则会登记到内存，但不会写盘。"""
        now = time.time()
        norm_id = normalize_tweet_id(tweet_id_or_url) if tweet_id_or_url else None
        fp = self._fingerprint(text) if text else None

        # 先做 TTL 清理（轻量）
        self._cleanup(now)

        if norm_id and norm_id in self._ids:
            return True
        if fp and fp in self._fingerprints:
            return True
        return False

    def should_push(self, tweet_id_or_url: Optional[str], text: Optional[str]) -> bool:
        """是否应该推送：未见过 且 距上次推送超过最小间隔。"""
        if self.seen(tweet_id_or_url, text):
            return False
        now = time.time()
        if now - self._last_push_ts < self.min_push_interval_seconds:
            return False
        return True

    def mark_pushed(self, tweet_id_or_url: Optional[str], text: Optional[str]) -> None:
        """将该条目标记为已推送，并持久化到文件。"""
        now = time.time()
        norm_id = normalize_tweet_id(tweet_id_or_url) if tweet_id_or_url else None
        fp = self._fingerprint(text) if text else None

        if norm_id:
            self._ids[norm_id] = now
        if fp:
            self._fingerprints[fp] = now

        self._last_push_ts = now
        self._enforce_bound()
        self._cleanup(now)
        self._save()

    # ---------- internal ----------

    def _fingerprint(self, text: str) -> str:
        base = normalize_text_for_fingerprint(text)
        return hashlib.sha1(base.encode('utf-8')).hexdigest()

    def _enforce_bound(self) -> None:
        # 如果超过窗口大小，按时间淘汰
        if len(self._ids) > self.max_history:
            sorted_ids = sorted(self._ids.items(), key=lambda kv: kv[1])
            for k, _ in sorted_ids[: len(self._ids) - self.max_history]:
                self._ids.pop(k, None)
        if len(self._fingerprints) > self.max_history:
            sorted_fp = sorted(self._fingerprints.items(), key=lambda kv: kv[1])
            for k, _ in sorted_fp[: len(self._fingerprints) - self.max_history]:
                self._fingerprints.pop(k, None)

    def _cleanup(self, now: Optional[float] = None) -> None:
        now = now or time.time()
        expire_before = now - self.ttl_seconds
        self._ids = {k: ts for k, ts in self._ids.items() if ts >= expire_before}
        self._fingerprints = {k: ts for k, ts in self._fingerprints.items() if ts >= expire_before}

    def _load(self) -> None:
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._ids = {str(k): float(v) for k, v in data.get('ids', {}).items()}
            self._fingerprints = {str(k): float(v) for k, v in data.get('fingerprints', {}).items()}
            self._last_push_ts = float(data.get('last_push_ts', 0.0))
        except Exception:
            # 读取失败时尽量不影响主流程
            self._ids = {}
            self._fingerprints = {}
            self._last_push_ts = 0.0

    def _save(self) -> None:
        data = {
            'ids': self._ids,
            'fingerprints': self._fingerprints,
            'last_push_ts': self._last_push_ts,
        }
        tmp_file = f"{self.state_file}.tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, self.state_file) 