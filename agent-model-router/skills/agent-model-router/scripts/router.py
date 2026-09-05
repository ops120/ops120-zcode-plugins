#!/usr/bin/env python3
"""
Agent Model Router - 从 ZCode 已配置的 provider 中选择路由
"""
import os
import json
import re
import tempfile
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# 与 hooks/check-agent-type.js 约定一致：生成新定义后写入标志，
# 本会话内 hook 据此拦截 router-* 派发（定义未加载）；新会话 SessionStart 清除。
FLAG_FILE = os.path.join(tempfile.gettempdir(), "agent-model-router-new-defs.flag")

def _write_flag() -> None:
    try:
        with open(FLAG_FILE, "w", encoding="utf-8") as f:
            json.dump({"generatedAt": datetime.now().isoformat()}, f)
    except Exception:
        pass  # 标志写失败只影响同会话拦截提示，不影响定义生成

# ZCode 配置文件路径
ZCODE_CONFIG_PATH = os.path.expanduser("~/.zcode/v2/config.json")

# 插件生成的定义指纹：description 中必含此串。清理/覆盖只针对含指纹的文件，
# 用户手写的同名 router-*.md 没有指纹，一律保留、绝不触碰。
GENERATED_MARKER = "agent-model-router 生成"

def _is_plugin_generated(path: Path) -> bool:
    """判断定义文件是否由本插件生成（含指纹）"""
    try:
        return GENERATED_MARKER in path.read_text(encoding="utf-8")
    except Exception:
        return False

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

def _provider_usable(pid: str, provider: Dict[str, Any]) -> tuple:
    """判定 provider 是否真实可用，返回 (可用, 不可用原因)。

    静态检查三关：显式禁用、系统禁用原因、API key 为空。
    注意：只能拦住配置层问题，拦不住服务端认证拒绝（如 token 失效）。
    """
    if not provider.get("enabled", True):
        return False, "provider 已禁用"
    reason = provider.get("systemDisabledReason")
    if reason:
        return False, f"系统禁用 ({reason})"
    if not provider.get("options", {}).get("apiKey"):
        return False, "未配置 API key"
    return True, ""

def get_enabled_providers() -> Dict[str, Any]:
    """获取所有真实可用的 provider（已启用且配置了凭证）"""
    providers = get_providers()
    enabled = {}
    for pid, provider in providers.items():
        usable, _ = _provider_usable(pid, provider)
        if usable:
            enabled[pid] = provider
    return enabled

PROBE_QUESTION = "今天周几"

# 以官方 SDK 的标准请求签名发送探测（部分中转站的 Cloudflare 防护会拦截
# 无 SDK 特征的脚本请求 error 1010，标准 SDK UA + x-stainless 头可正常通过）
ANTHROPIC_SDK_UA = "anthropic-sdk-python/0.39.0"
OPENAI_SDK_UA = "openai-python/1.54.0"

def _extract_error_detail(raw: str) -> str:
    """从错误响应体中提取人类可读的原因"""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for k in ("msg", "message", "error"):
                v = data.get(k)
                if isinstance(v, str) and v:
                    return v
                if isinstance(v, dict):
                    for kk in ("msg", "message", "type"):
                        if isinstance(v.get(kk), str) and v[kk]:
                            return v[kk]
    except Exception:
        pass
    return (raw[:120].replace("\n", " ")) if raw else "无响应体"

def probe_model(provider_id: str, model_name: str, timeout: int = 30) -> Tuple[str, str]:
    """向 provider/model 发送一次最小真实流式请求，验证模型当前能否实际调用。

    探测问题固定为 PROBE_QUESTION（成本几乎为零）。静态检查只能拦住
    配置层问题（未配置 key、被禁用），这一步能拦住服务端拒绝
    （token 失效、captcha 验证、套餐无权益等）。

    返回 ("ok"|"fail"|"unknown", 详情)：
    - ok      2xx 且收到正常首包 → 可用
    - fail    服务端明确拒绝（4xx 业务错误 / 连接被拒）→ 不可用
    - unknown 超时（重试 1 次仍超时）→ 无法确认，不轻易判死
    """
    config = get_provider_model(provider_id, model_name)
    if not config:
        return "fail", "provider 或模型不存在"

    base = (config.get("base_url") or "").rstrip("/")
    key = config.get("api_key") or ""
    kind = config.get("provider_kind")

    if kind == "openai-compatible":
        url = base + "/chat/completions"
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer " + key,
            "user-agent": OPENAI_SDK_UA,
            "x-stainless-lang": "python",
            "x-stainless-package-version": "1.54.0",
        }
        body = {"model": model_name, "stream": True,
                "messages": [{"role": "user", "content": PROBE_QUESTION}]}
    else:  # anthropic 兼容协议
        url = base + "/v1/messages"
        headers = {
            "content-type": "application/json",
            "x-api-key": key,
            "authorization": "Bearer " + key,
            "anthropic-version": "2023-06-01",
            "user-agent": ANTHROPIC_SDK_UA,
            "x-stainless-lang": "python",
            "x-stainless-package-version": "0.39.0",
        }
        body = {"model": model_name, "max_tokens": 1024, "stream": True,
                "messages": [{"role": "user", "content": PROBE_QUESTION}]}

    data = json.dumps(body).encode("utf-8")
    last_err = ""
    for attempt in (1, 2):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                chunk = resp.read(512)
                if not chunk:
                    return "fail", f"HTTP {resp.status}: 空响应"
                text = chunk.decode(errors="replace")
                if '"error"' in text or "event: error" in text:
                    return "fail", f"HTTP {resp.status}: {_extract_error_detail(text)}"
                return "ok", f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode(errors="replace")
            except Exception:
                raw = ""
            return "fail", f"HTTP {e.code}: {_extract_error_detail(raw)}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"{type(e).__name__}: {e}"
            # 连接被拒 / DNS 解析失败是确定性故障，不重试
            if "refused" in last_err.lower() or "10061" in last_err or "getaddrinfo" in last_err:
                return "fail", last_err
            # 超时可能只是非流式链路慢，重试一次
            continue
    return "unknown", last_err

def _probe_all(targets: List[Tuple[str, str]], timeout: int = 30) -> Dict[Tuple[str, str], Tuple[str, str]]:
    """并发探测所有 (provider_id, model)，返回 {(pid, model): (status, detail)}。

    探测是纯 I/O，线程池并发把总耗时从"逐个累加"降到"最慢的一个"。
    """
    results: Dict[Tuple[str, str], Tuple[str, str]] = {}
    if not targets:
        return results
    with ThreadPoolExecutor(max_workers=min(len(targets), 16)) as pool:
        futures = {pool.submit(probe_model, pid, m, timeout): (pid, m) for pid, m in targets}
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                results[key] = fut.result()
            except Exception as e:
                results[key] = ("unknown", f"{type(e).__name__}: {e}")
    return results

def test_models(provider_id: Optional[str] = None, model_name: Optional[str] = None) -> None:
    """探测模型的真实可用性，输出逐个结果"""
    providers = get_enabled_providers()

    if provider_id:
        if provider_id not in providers:
            print(f"❌ provider '{provider_id}' 不存在或不可用")
            return
        models = providers[provider_id].get("models", {})
        if model_name:
            if model_name not in models:
                print(f"❌ 模型 '{model_name}' 在 provider '{provider_id}' 中不存在")
                return
            targets = [(provider_id, model_name)]
        else:
            targets = [(provider_id, m) for m in models]
    else:
        targets = [(pid, m) for pid, p in providers.items() for m in p.get("models", {})]

    if not targets:
        print("❌ 没有可探测的模型")
        return

    print(f"\n🧪 探测模型真实可用性（并发 {len(targets)} 个，探测问题: \"{PROBE_QUESTION}\"）:")
    print("=" * 60)
    results = _probe_all(targets)
    ok_count = 0
    for pid, m in targets:
        name = providers[pid].get("name", pid) if pid in providers else pid
        status, detail = results[(pid, m)]
        if status == "ok":
            ok_count += 1
            print(f"   ✅ {name} / {m}")
        elif status == "fail":
            print(f"   ❌ {name} / {m} —— {detail}")
        else:
            print(f"   ⚠️ {name} / {m} —— 无法确认（{detail}）")
    print("=" * 60)
    print(f"结果: {ok_count}/{len(targets)} 个模型可用")

def list_providers() -> None:
    """列出所有已配置的 provider"""
    providers = get_providers()

    print("\n📋 ZCode 已配置的 Provider:")
    print("=" * 80)

    for pid, provider in providers.items():
        name = provider.get("name", "Unknown")
        kind = provider.get("kind", "unknown")
        usable, unusable_reason = _provider_usable(pid, provider)
        models = provider.get("models", {})

        status = "✅" if usable else "❌"
        reason = f" ({unusable_reason})" if not usable else ""

        print(f"\n{status} Provider: {name}")
        print(f"   ID: {pid}")
        print(f"   类型: {kind}")
        print(f"   状态: {'可用' if usable else '不可用'}{reason}")
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
        usable, _ = _provider_usable(pid, provider)
        if not usable:
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

def _agent_slug(model_name: str) -> str:
    """模型名转子智能体定义文件名 slug（小写、非字母数字转连字符）"""
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", model_name.lower()).strip("-")
    return f"router-{slug}"


def create_agent(provider_id: str, model_name: str, custom_name: Optional[str] = None) -> None:
    """为选定的 provider/model 生成绑定模型的自定义子智能体定义文件。

    ZCode 的子智能体定义支持 frontmatter `model` 字段，主 Agent 用
    subagent_type 调用该子智能体时即真实使用该模型。
    定义写入 ~/.zcode/agents/<slug>.md，新建会话后生效。
    """
    config = get_provider_model(provider_id, model_name)
    if not config:
        return

    slug = custom_name or _agent_slug(model_name)
    agents_dir = Path(os.path.expanduser("~/.zcode/agents"))
    agents_dir.mkdir(parents=True, exist_ok=True)
    target = agents_dir / f"{slug}.md"

    model_ref = f"custom:{provider_id}:{model_name}"
    desc = (
        f"agent-model-router 生成的模型路由子智能体：绑定 {config['provider_name']} / {model_name}。"
        f"当任务需要使用 {model_name} 模型执行时，用此子智能体（subagent_type: {slug}）。"
    )
    content = (
        "---\n"
        f"name: {slug}\n"
        f'description: "{desc}"\n'
        f"model: {model_ref}\n"
        "color: purple\n"
        "---\n"
        f"你是绑定 {model_name} 模型的执行子智能体。直接完成派发的任务，保持输出简洁、结论附证据。\n"
    )

    target.write_text(content, encoding="utf-8")
    _write_flag()
    print(f"✅ 已生成子智能体定义: {target}")
    print(f"   名称(subagent_type): {slug}")
    print(f"   绑定模型: {config['provider_name']} / {model_name}")
    print("   生效时机: 新建会话后生效（已启动的会话不会热加载）。")
    print(f"   调用方式: Agent 工具 subagent_type={slug}，或聊天输入框 @ 该名称。")


def setup_agents(force: bool = False, probe: bool = True) -> None:
    """批量为所有可用 provider 的模型生成子智能体定义。

    force=True 时先清除旧的 router-* 定义再重新生成。
    probe=True 时对每个模型发送一次最小真实请求，只给探测通过的模型生成定义。
    """
    agents_dir = Path(os.path.expanduser("~/.zcode/agents"))
    agents_dir.mkdir(parents=True, exist_ok=True)

    if force:
        kept = 0
        for f in agents_dir.glob("router-*.md"):
            # 只删本插件生成的文件；无指纹的是用户自定义，绝不触碰
            if _is_plugin_generated(f):
                f.unlink()
            else:
                kept += 1
                print(f"🔒 保留用户自定义定义: {f.name}（非本插件生成，不清理）")
        if kept:
            print(f"🗑️  已清除旧的插件生成定义，保留 {kept} 个用户自定义文件。")
        else:
            print("🗑️  已清除旧的 router-* 定义文件。")

    providers = get_providers()
    usable_providers = {pid: p for pid, p in providers.items() if _provider_usable(pid, p)[0]}
    if not usable_providers:
        print("❌ 没有可用的 provider")
        return

    total = 0
    skipped = 0
    print("\n🔧 批量生成子智能体定义...")
    print("=" * 60)

    # 先并发探测所有待生成模型，再按结果生成
    probe_results: Dict[Tuple[str, str], Tuple[str, str]] = {}
    if probe:
        all_targets = [(pid, m) for pid, p in usable_providers.items() for m in p.get("models", {})]
        print(f"🧪 并发探测 {len(all_targets)} 个模型的真实可用性...")
        print(f"⏳ 预计需要 1~2 分钟（每个模型最多 2×30 秒，超时模型会重试一次），请耐心等待。")
        probe_results = _probe_all(all_targets)

    for pid, provider in providers.items():
        name = provider.get("name", "Unknown")
        usable, unusable_reason = _provider_usable(pid, provider)
        if not usable:
            model_count = len(provider.get("models", {}))
            if model_count:
                print(f"\n⏭️  {name} ({pid}): 跳过 —— {unusable_reason}（{model_count} 个模型）")
            continue

        models = provider.get("models", {})
        if not models:
            continue

        print(f"\n📦 {name} ({pid}):")
        for model_name in models.keys():
            config = get_provider_model(pid, model_name)
            if not config:
                skipped += 1
                continue

            if probe:
                status, detail = probe_results.get((pid, model_name), ("unknown", "无探测结果"))
                if status == "ok":
                    print(f"   ✅ {model_name} (探测通过)")
                elif status == "fail":
                    print(f"   ❌ {model_name} 探测不可用（{detail}）→ 跳过")
                    skipped += 1
                    continue
                else:
                    print(f"   ⚠️ {model_name} 探测无法确认（{detail}）→ 保留定义")

            slug = _agent_slug(model_name)
            target = agents_dir / f"{slug}.md"

            # 用户自定义的同名文件绝不覆盖
            if target.exists() and not _is_plugin_generated(target):
                print(f"   ⏭️  {model_name}: 已存在同名用户自定义定义 {target.name}，跳过（不覆盖）")
                skipped += 1
                continue

            model_ref = f"custom:{pid}:{model_name}"
            desc = (
                f"agent-model-router 生成的模型路由子智能体：绑定 {name} / {model_name}。"
                f"当任务需要使用 {model_name} 模型执行时，用此子智能体（subagent_type: {slug}）。"
            )
            content = (
                "---\n"
                f"name: {slug}\n"
                f'description: "{desc}"\n'
                f"model: {model_ref}\n"
                "color: purple\n"
                "---\n"
                f"你是绑定 {model_name} 模型的执行子智能体。直接完成派发的任务，保持输出简洁、结论附证据。\n"
            )
            target.write_text(content, encoding="utf-8")
            print(f"   ✅ {slug} → {name} / {model_name}")
            total += 1

    print("\n" + "=" * 60)
    print(f"✅ 生成完毕: {total} 个定义，跳过 {skipped} 个" + ("（含探测不可用）" if probe else ""))
    if total:
        _write_flag()
    print("⚠️  新建会话后生效。日常使用请执行 /agent-model-router。")

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
        print("  python router.py create-agent <provider> <model> [--name 名称]  # 生成绑定该模型的子智能体定义")
        print("  python router.py setup [--force]             # 批量为所有模型生成子智能体定义")
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
    elif command == "create-agent":
        args = sys.argv[2:]
        custom = None
        if "--name" in args:
            i = args.index("--name")
            if i + 1 >= len(args):
                print("❌ --name 缺少取值")
                sys.exit(1)
            custom = args[i + 1]
            args = args[:i] + args[i + 2:]
        if len(args) < 2:
            print("❌ 请指定 provider 和 model")
            print("用法: python router.py create-agent <provider_id> <model_name> [--name 名称]")
            sys.exit(1)
        create_agent(args[0], args[1], custom)
    elif command == "test":
        args = sys.argv[2:]
        provider_id = args[0] if args else None
        model_name = args[1] if len(args) > 1 else None
        test_models(provider_id, model_name)
    elif command == "setup":
        force = "--force" in sys.argv[2:]
        no_test = "--no-test" in sys.argv[2:]
        setup_agents(force=force, probe=not no_test)
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)
