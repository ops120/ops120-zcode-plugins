#!/usr/bin/env python3
"""
Agent Model Router - 从 ZCode 已配置的 provider 中选择路由
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

# ZCode 配置文件路径
ZCODE_CONFIG_PATH = os.path.expanduser("~/.zcode/v2/config.json")

def load_zcode_config() -> Dict[str, Any]:
    """加载 ZCode 配置文件"""
    if not os.path.exists(ZCODE_CONFIG_PATH):
        print(f"❌ ZCode 配置文件不存在: {ZCODE_CONFIG_PATH}")
        return {}

    with open(ZCODE_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_providers() -> Dict[str, Any]:
    """获取所有已配置的 provider"""
    config = load_zcode_config()
    return config.get("provider", {})

def get_enabled_providers() -> Dict[str, Any]:
    """获取所有已启用的 provider"""
    providers = get_providers()
    enabled = {}
    for pid, provider in providers.items():
        # 检查是否启用（默认启用，除非明确设置 enabled: false）
        if provider.get("enabled", True) and not provider.get("systemDisabledReason"):
            enabled[pid] = provider
    return enabled

def list_providers() -> None:
    """列出所有已配置的 provider"""
    providers = get_providers()

    print("\n📋 ZCode 已配置的 Provider:")
    print("=" * 80)

    for pid, provider in providers.items():
        name = provider.get("name", "Unknown")
        kind = provider.get("kind", "unknown")
        enabled = provider.get("enabled", True)
        disabled_reason = provider.get("systemDisabledReason", "")
        models = provider.get("models", {})

        status = "✅" if enabled and not disabled_reason else "❌"
        reason = f" ({disabled_reason})" if disabled_reason else ""

        print(f"\n{status} Provider: {name}")
        print(f"   ID: {pid}")
        print(f"   类型: {kind}")
        print(f"   状态: {'已启用' if enabled and not disabled_reason else '已禁用'}{reason}")
        print(f"   可用模型:")
        for model_name, model_info in models.items():
            reasoning = "🧠" if model_info.get("reasoning", {}).get("enabled") else "  "
            modalities = model_info.get("modalities", {}).get("input", [])
            mods = ",".join(modalities) if modalities else "text"
            rank_tag = format_rank_tag(model_name)
            print(f"     {reasoning} {model_name} (输入: {mods}){rank_tag}")

    print("\n" + "=" * 80)

def list_models(provider_id: Optional[str] = None) -> None:
    """列出指定 provider 或所有 provider 的模型"""
    providers = get_enabled_providers() if provider_id is None else {provider_id: get_providers().get(provider_id, {})}

    if not providers:
        print("❌ 没有找到可用的 provider")
        return

    print("\n📋 可用模型:")
    print("=" * 60)

    for pid, provider in providers.items():
        name = provider.get("name", "Unknown")
        models = provider.get("models", {})

        print(f"\n📦 {name} ({pid}):")
        for model_name, model_info in models.items():
            reasoning = model_info.get("reasoning", {})
            has_reasoning = reasoning.get("enabled", False)
            variants = reasoning.get("variants", [])
            limit = model_info.get("limit", {})
            context = limit.get("context", 0)
            output = limit.get("output", 0)
            modalities = model_info.get("modalities", {}).get("input", [])

            print(f"   📄 {model_name}")
            if has_reasoning:
                print(f"      🧠 推理模式: {', '.join(variants)}")
            print(f"      📏 上下文: {context:,} tokens, 输出: {output:,} tokens")
            print(f"      📥 输入: {', '.join(modalities) if modalities else 'text'}")

    print("\n" + "=" * 60)

def get_provider_model(provider_id: str, model_name: str) -> Optional[Dict[str, Any]]:
    """获取指定 provider 和 model 的配置"""
    providers = get_providers()

    if provider_id not in providers:
        print(f"❌ Provider '{provider_id}' 不存在")
        return None

    provider = providers[provider_id]
    models = provider.get("models", {})

    if model_name not in models:
        print(f"❌ 模型 '{model_name}' 在 provider '{provider.get('name')}' 中不存在")
        print(f"   可用模型: {', '.join(models.keys())}")
        return None

    model = models[model_name]
    options = provider.get("options", {})

    return {
        "provider_id": provider_id,
        "provider_name": provider.get("name"),
        "provider_kind": provider.get("kind"),
        "base_url": options.get("baseURL"),
        "api_key": options.get("apiKey"),
        "model_name": model_name,
        "model_config": model
    }

def search_models(keyword: str) -> None:
    """根据关键词搜索模型"""
    providers = get_providers()
    results = []

    for pid, provider in providers.items():
        if not provider.get("enabled", True) or provider.get("systemDisabledReason"):
            continue

        name = provider.get("name", "Unknown")
        models = provider.get("models", {})

        for model_name, model_info in models.items():
            if keyword.lower() in model_name.lower() or keyword.lower() in name.lower():
                results.append({
                    "provider": name,
                    "provider_id": pid,
                    "model": model_name,
                    "model_info": model_info
                })

    if not results:
        print(f"❌ 没有找到匹配 '{keyword}' 的模型")
        return

    print(f"\n🔍 搜索结果 (关键词: {keyword}):")
    print("-" * 60)
    for r in results:
        print(f"   {r['provider']} / {r['model']}")
        print(f"   Provider ID: {r['provider_id']}")
    print("-" * 60)

def format_for_agent(provider_id: str, model_name: str) -> None:
    """格式化输出供 Agent 调用使用的配置"""
    config = get_provider_model(provider_id, model_name)
    if not config:
        return

    print(f"\n🔧 Agent 路由配置:")
    print("-" * 40)
    print(f"Provider: {config['provider_name']}")
    print(f"Model: {config['model_name']}")
    print(f"Base URL: {config['base_url']}")
    print("-" * 40)
    print(f"\n💡 使用方式:")
    print(f'   调用 Agent，使用 {config["provider_name"]}/{config["model_name"]}，完成...')

def _normalize_model_name(name: str) -> str:
    """统一模型名格式：小写、空格/下划线→连字符、去多余符号"""
    return name.lower().replace(" ", "-").replace("_", "-").strip()

def _get_live_rankings() -> Dict[str, Any]:
    """获取排行榜数据：优先缓存 → 远程获取 → 兜底内置"""
    try:
        script_dir = Path(__file__).parent
        import importlib.util
        spec = importlib.util.spec_from_file_location("rankings", script_dir / "rankings.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        live = mod.get_rankings()
        if live:
            # 把远程数据转成和 RANKINGS_SNAPSHOT 一样的格式
            return _convert_live_to_snapshot(live)
    except Exception:
        pass
    return {}

def _convert_live_to_snapshot(live: Dict[str, Any]) -> Dict[str, Any]:
    """将远程抓取的数据转为内部快照格式"""
    result = {}
    board_map = {"text": "文本榜 (Arena Text)", "code": "代码榜 (Arena WebDev)", "document": "文档榜 (Arena Document)"}
    for key, board_name in board_map.items():
        entries = live.get(key, [])
        if entries:
            result[board_name] = [(m, v, s) for m, v, s in entries]
    # 用量榜无法自动抓取，保留内置数据
    if "用量榜 (OpenRouter)" in RANKINGS_SNAPSHOT:
        result["用量榜 (OpenRouter)"] = RANKINGS_SNAPSHOT["用量榜 (OpenRouter)"]
    if result:
        result["任务推荐"] = RANKINGS_SNAPSHOT.get("任务推荐", {})
    return result

def _build_rank_index() -> Dict[str, Dict[str, Any]]:
    """从排行榜快照构建模型名→排名信息的索引（优先用缓存/远程数据）"""
    # 尝试获取最新数据（优先缓存 → 远程 → 兜底内置）
    live = _get_live_rankings()
    source = live if live else RANKINGS_SNAPSHOT

    index: Dict[str, Dict[str, Any]] = {}
    board_map = {
        "文本榜 (Arena Text, Elo)": "文本",
        "文本榜 (Arena Text)": "文本",
        "代码榜 (Arena WebDev)": "代码",
        "文档榜 (Arena Document)": "文档",
        "用量榜 (OpenRouter)": "用量",
    }
    for board_name, entries in source.items():
        short = board_map.get(board_name, board_name)
        if isinstance(entries, list):
            for i, item in enumerate(entries, 1):
                model_key = _normalize_model_name(item[0])
                if model_key not in index:
                    index[model_key] = {}
                index[model_key][short] = i
    return index


_RANK_INDEX = None

def _get_rank_index() -> Dict[str, Dict[str, Any]]:
    global _RANK_INDEX
    if _RANK_INDEX is None:
        _RANK_INDEX = _build_rank_index()
    return _RANK_INDEX


def format_rank_tag(model_name: str) -> str:
    """根据模型名查找排行榜排名，返回标注字符串"""
    idx = _get_rank_index()
    key = _normalize_model_name(model_name)

    # 精确匹配
    ranks = idx.get(key)

    # 模糊匹配：模型名包含索引 key，或索引 key 包含模型名（用 base name 匹配）
    if not ranks:
        # 尝试去掉后缀变体（-high/-max/-free 等）后再匹配
        for suffix in ["-high", "-max", "-free", "-low", "-medium", "-xhigh"]:
            stripped = key.replace(suffix, "")
            if stripped != key and stripped in idx:
                ranks = idx[stripped]
                break

    if not ranks:
        # 最后尝试子串匹配
        for k, v in idx.items():
            if k in key or key in k:
                ranks = v
                break

    if not ranks:
        return ""

    tags = []
    for board, pos in ranks.items():
        tags.append(f"{board}第{pos}")
    return f"  🏅 {' | '.join(tags)}"


# 本地模型排名快照（定期更新，来源见 references/model-rankings.md）
RANKINGS_SNAPSHOT = {
    "文本榜 (Arena Text, Elo)": [
        ("claude-fable-5", "Anthropic", 1507),
        ("claude-opus-4-6-high", "Anthropic", 1505),
        ("claude-fable-5.1-max", "Anthropic", 1504),
        ("muse-spark-1.2", "Meta", 1499),
        ("gemini-3.8-flash-high", "Google", 1494),
        ("kimi-k3-max", "Moonshot", 1489),
        ("glm-5.3-max", "智谱", 1482),
    ],
    "代码榜 (Arena WebDev)": [
        ("claude-fable-5.1-max", "Anthropic", 1765),
        ("qwen3.8-max-0902", "Alibaba", 1688),
        ("claude-opus-5-max", "Anthropic", 1687),
        ("kimi-k3-max", "Moonshot", 1674),
        ("claude-fable-5", "Anthropic", 1628),
        ("hy4-preview", "腾讯", 1626),
        ("glm-5.3-flash", "智谱", 1604),
        ("deepseek-v4-flash-high", "DeepSeek", 1581),
    ],
    "文档榜 (Arena Document)": [
        ("claude-opus-5-high", "Anthropic", 1520),
        ("claude-opus-4-6", "Anthropic", 1510),
        ("claude-fable-5", "Anthropic", 1504),
        ("gpt-5.5-high", "OpenAI", 1485),
        ("gpt-5.5", "OpenAI", 1480),
        ("gpt-5.4", "OpenAI", 1470),
        ("gemini-3.5-flash-high", "Google", 1465),
    ],
    "用量榜 (OpenRouter)": [
        ("GLM 5.3 Flash", "智谱", "11.9T"),
        ("GPT-5.6 Luna", "OpenAI", "11.6T"),
        ("DeepSeek V4 Flash", "DeepSeek", "11.3T"),
        ("Hy4 Preview", "腾讯", "11T"),
        ("MiMo-V2.5", "小米", "4.5T"),
    ],
    "任务推荐": {
        "代码生成": "claude-fable-5.1-max / qwen3.8-max / kimi-k3-max",
        "文档处理": "claude-opus-5 / claude-fable-5 / gpt-5.4",
        "复杂推理": "claude-opus-5 / deepseek-v4-flash",
        "快速低成本": "glm-5.3-flash / gpt-5.6-luna",
        "Agent调用": "kimi-k3-max / claude-opus-5",
    },
}

def show_rankings() -> None:
    """显示模型排行榜"""
    print("\n🏆 模型排行榜（快照，详见 references/model-rankings.md）")
    print("=" * 60)
    for board, entries in RANKINGS_SNAPSHOT.items():
        print(f"\n📊 {board}:")
        if isinstance(entries, list):
            for i, item in enumerate(entries, 1):
                if isinstance(item, tuple):
                    if len(item) == 3 and isinstance(item[2], int):
                        print(f"   {i}. {item[0]} ({item[1]}) — Elo {item[2]}")
                    else:
                        print(f"   {i}. {item[0]} ({item[1]}) — {item[2]}")
        else:
            for task, rec in entries.items():
                print(f"   {task}: {rec}")
    print("\n" + "=" * 60)
    print("💡 数据来源: arena.ai / openrouter.ai / artificialanalysis.ai")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python router.py list              # 列出所有 provider")
        print("  python router.py models [provider]  # 列出模型")
        print("  python router.py search <keyword>   # 搜索模型")
        print("  python router.py rankings           # 查看模型排行榜")
        print("  python router.py get <provider> <model>  # 获取路由配置")
        print("  python router.py format <provider> <model>  # 格式化输出")
        sys.exit(1)

    command = sys.argv[1]

    if command == "rankings":
        show_rankings()
    elif command == "list":
        list_providers()
    elif command == "models":
        provider_id = sys.argv[2] if len(sys.argv) > 2 else None
        list_models(provider_id)
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ 请指定搜索关键词")
            sys.exit(1)
        search_models(sys.argv[2])
    elif command == "get":
        if len(sys.argv) < 4:
            print("❌ 请指定 provider 和 model")
            print("用法: python router.py get <provider_id> <model_name>")
            sys.exit(1)
        config = get_provider_model(sys.argv[2], sys.argv[3])
        if config:
            print(json.dumps(config, indent=2, ensure_ascii=False, default=str))
    elif command == "format":
        if len(sys.argv) < 4:
            print("❌ 请指定 provider 和 model")
            print("用法: python router.py format <provider_id> <model_name>")
            sys.exit(1)
        format_for_agent(sys.argv[2], sys.argv[3])
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)
