"""飞书报告器：把「今日要点」推送到飞书群机器人，每天只发一次。

内容取自 insights 分析器（看板总览的「今日要点」）。按批次日期去重：
`data/state/<source>/feishu_sent.json` 里记下已发送的日期，相同日期不再发。
GitHub 每天触发多次 cron，但只有官方刷新后产生新快照的那一次会走到这里，
所以天然满足「每天一次」；这个文件再兜底一层，避免重复部署时重发。

配置（config.toml）：
    [reporters.feishu]
    enabled = true

环境变量（GitHub Secrets）：
    FSKEY     飞书群机器人的 webhook 地址里那串 key，必填
    FSSECRET  机器人的签名校验密钥，可选

密钥通过环境变量传入，不要写进仓库。没有 FSKEY 时跳过且不记标记（等真正配好
key 之前不会误标成已发送）；发送失败只打日志，不影响站点生成。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from radar.core.registry import REPORTERS

# tools/notify.py 的 send(title, content)。模块名带哈希避免撞名。
_TOOLS = Path(__file__).resolve().parents[2] / "tools" / "notify.py"


def _load_sender():
    """加载 tools/notify.py 里的 send 函数；加载失败返回 None，不影响站点。"""
    try:
        name = "feishu_notify_" + str(abs(hash(str(_TOOLS))))
        spec = importlib.util.spec_from_file_location(name, _TOOLS)
        if spec is None or spec.loader is None:
            print("⚠️ [feishu] 无法创建 notify.py 的加载描述")
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return getattr(module, "send", None)
    except Exception as exc:
        print(f"⚠️ [feishu] 加载 tools/notify.py 失败：{exc}")
        return None


def _insight_lines(results: Dict[str, Any]) -> List[str]:
    insights = (results.get("insights") or {}).get("items") or []
    return [i.get("text", "") for i in insights if i.get("text")]


def _already_sent(ctx, day: str) -> bool:
    return bool((ctx.history and (ctx.source.store.load_state("feishu_sent") or {}).get("date") == day))


def _mark_sent(ctx, day: str) -> None:
    try:
        ctx.source.store.save_state("feishu_sent", {"date": day})
    except Exception as exc:
        print(f"⚠️ [feishu] 写入已发送标记失败：{exc}")


@REPORTERS.register("feishu")
def feishu(ctx, settings: Dict[str, Any]) -> List[Path]:
    sender = _load_sender()
    if sender is None:
        return []

    day = (ctx.results.get("metrics") or {}).get("date") or ""
    if not day:
        print("⚠️ [feishu] 没有批次日期，跳过")
        return []
    if not os.environ.get("FSKEY"):
        print("ℹ️ [feishu] 未配置 FSKEY（GitHub Secret），跳过发送且不记标记")
        return []
    if _already_sent(ctx, day):
        print(f"ℹ️ [feishu] {day} 已发送过，跳过（每天只发一次）")
        return []

    lines = _insight_lines(ctx.results)
    if not lines:
        print("ℹ️ [feishu] 今日要点为空，跳过")
        return []
    # 要点正文末尾附上看板地址（在 notify 追加的一言之前），config.toml 的 view_url 可覆盖
    view_url = settings.get("view_url") or "https://tf2jaguar.github.io/drama-radar"
    content = "\n".join(f"• {line}" for line in lines) + f"\n\n详情请查看：{view_url}"
    title = f"短剧雷达 · {day} 今日要点"

    try:
        sender(title, content)
    except Exception as exc:
        print(f"⚠️ [feishu] 发送失败：{exc}")
        return []
    _mark_sent(ctx, day)
    print(f"✅ [feishu] 已推送 {day} 今日要点（{len(lines)} 条）")
    return []
