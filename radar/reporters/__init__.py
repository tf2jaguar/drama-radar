"""报告器：分析完成后把结果送到别处，比如写 Markdown 简报、推送到飞书或企业微信群。

每个报告器是一个函数 `fn(ctx, settings) -> list[Path]`，用 @REPORTERS.register("名字") 注册，
在 config.toml 的 [reporters.名字] 里 `enabled = true` 才会运行。
"""

from radar.reporters import feishu, markdown  # noqa: F401
