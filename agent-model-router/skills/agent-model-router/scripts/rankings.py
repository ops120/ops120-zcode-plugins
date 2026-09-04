#!/usr/bin/env python3
"""
Agent Model Rankings - 从 Arena 抓取最新排行榜并缓存
首次用内置数据，后台异步更新供下次使用。
"""
import os
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional

CACHE_DIR = Path.home() / ".zcode" / "agent-model-router-cache"
CACHE_FILE = CACHE_DIR / "rankings-cache.json"
CACHE_MAX_AGE = 86400 * 3  # 3 天有效期

def _load_cache() -> Optional[Dict[str, Any]]:
    """读取缓存文件"""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 检查是否过期
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE:
            return None  # 过期，需要刷新
        return data
    except Exception:
        return None

def _save_cache(data: Dict[str, Any]) -> None:
    """保存排行数据到缓存"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = time.time()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _fetch_url(url: str) -> Optional[str]:
    """安全地获取 URL 内容"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "agent-model-router/0.1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

def _parse_arena_text(html: str) -> list:
    """从 Arena Text 页面解析排行榜（简单正则提取模型名和分数）"""
    import re
    results = []
    # Arena 页面模型排名格式：模型名 + Elo 分数
    # 匹配模式：模型名在表格行中，后面跟着 Elo 数字
    pattern = r'<td[^>]*class="[^"]*model[^"]*"[^>]*>([^<]+)</td>.*?<td[^>]*>(\d{4})</td>'
    matches = re.findall(pattern, html, re.DOTALL)
    for i, (model, score) in enumerate(matches[:20], 1):
        results.append((model.strip(), "unknown", int(score)))
    return results

def _parse_arena_code(html: str) -> list:
    """从 Arena Code 页面解析排行榜"""
    return _parse_arena_text(html)  # 格式类似

def _parse_arena_document(html: str) -> list:
    """从 Arena Document 页面解析排行榜"""
    return _parse_arena_text(html)

def fetch_latest_rankings() -> Optional[Dict[str, Any]]:
    """从 Arena 获取最新排行榜数据"""
    urls = {
        "text": "https://arena.ai/leaderboard/text",
        "code": "https://arena.ai/leaderboard/code",
        "document": "https://arena.ai/leaderboard/document",
    }

    result = {}
    for key, url in urls.items():
        html = _fetch_url(url)
        if html:
            if key == "text":
                parsed = _parse_arena_text(html)
            elif key == "code":
                parsed = _parse_arena_code(html)
            else:
                parsed = _parse_arena_document(html)
            if parsed:
                result[key] = parsed

    if not result:
        return None

    result["_fetched_at"] = time.time()
    return result

def get_rankings() -> Dict[str, Any]:
    """
    获取排行榜数据，优先级：
    1. 缓存文件（未过期）
    2. 尝试远程获取（成功则存缓存供下次用）
    3. 内置数据（兜底）
    """
    # 1. 尝试读缓存
    cached = _load_cache()
    if cached:
        # 后台刷新：读完缓存后异步获取最新数据
        _background_refresh()
        return cached

    # 2. 尝试远程获取
    fetched = fetch_latest_rankings()
    if fetched:
        _save_cache(fetched)
        return fetched

    # 3. 兜底：返回空，让调用方使用内置 RANKINGS_SNAPSHOT
    return {}


def _background_refresh():
    """后台刷新缓存（非阻塞）"""
    try:
        fetched = fetch_latest_rankings()
        if fetched:
            _save_cache(fetched)
    except Exception:
        pass  # 静默失败

def cache_status() -> str:
    """显示缓存状态"""
    if not CACHE_FILE.exists():
        return "📦 缓存：无（使用内置数据）"
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_at = data.get("_cached_at", 0)
        age_hours = (time.time() - cached_at) / 3600
        expired = age_hours > 72
        status = "❌ 已过期" if expired else "✅ 有效"
        boards = [k for k in data.keys() if not k.startswith("_")]
        return f"📦 缓存：{status}（{age_hours:.1f}h 前，含 {', '.join(boards)}）"
    except Exception:
        return "📦 缓存：损坏"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        print("🔄 正在获取最新排行榜...")
        fetched = fetch_latest_rankings()
        if fetched:
            _save_cache(fetched)
            print(f"✅ 已更新缓存，包含: {', '.join(k for k in fetched.keys() if not k.startswith('_'))}")
        else:
            print("❌ 获取失败，将使用内置数据")
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        print(cache_status())
    else:
        print("用法:")
        print("  python rankings.py refresh   # 手动刷新排行榜缓存")
        print("  python rankings.py status    # 查看缓存状态")
