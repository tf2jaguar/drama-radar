# 短剧雷达 drama-radar

每天自动采集红果短剧官网公开的 4 个热播榜（综合 / 真人 / AI / 漫剧，各前 100 名），以及每部在榜剧的详情，
算出**热门剧、飙升剧、潜力新剧、题材冷热**，发布成 GitHub Pages 上的分析看板，并导出 CSV 方便自己再分析。

看板地址：**https://tf2jaguar.github.io/drama-radar/**

参考了 [hongguo-radar](https://github.com/2252399314-cyber/hongguo-radar) 的思路，代码重新写过。2026-10-13 至 10-16 的历史数据迁移自 hongguo-radar（转换脚本见 [`scripts/import_hongguo_radar.py`](scripts/import_hongguo_radar.py)，快照里带 `imported_from` 标记），10-17 起为本项目自己采集。主要改进：

| | hongguo-radar | drama-radar |
|---|---|---|
| 访问方式 | 冒充百度爬虫的 User-Agent 拿榜单 | 普通访客请求，User-Agent 如实标明身份；榜单页本来就对普通访客输出完整数据 |
| 题材分析 | 无 | 题材热度占比、升温/降温动量、新剧扎堆的题材（超配倍数）、题材组合、题材 × 类型、题材吸粉能力 |
| 潜力新剧 | 无 | 收藏日增、热度增速、名次上升、评分的百分位加权，列出理由，权重可配 |
| 其他分析 | 名次变化、增速 | 另有新剧热度占比走势、剧龄/集数分布、小说改编来源、上线到上榜用时、自动生成「今日要点」 |
| 数据出口 | 看板 | 看板 + 4 份 CSV + 每日 Markdown 简报 |
| 扩展方式 | 改主流程 | 数据源、分析器、报告器、看板页面都是插件，注册即可 |

## 看板有什么

- **总览**：今日要点（自动生成的几句话）、关键数字、收藏涨得最多的剧、潜力新剧、新剧热度占比走势。
- **榜单**：4 个官方榜的完整排名，名次变化、NEW/回榜、热度和收藏日增、连续在榜、上线天数、题材；可搜索、按题材筛选、只看新剧。
- **飙升**：按收藏日增、热度日增、热度增长率、名次上升、新上榜、评论日增、7 日增量等口径排序，也能看下滑。
- **潜力新剧**：上线 7 天内（可配置）或第一次上榜的剧，按潜力分排序。
- **题材**：哪些题材正热、哪些在升温、新剧往哪些题材挤、常见组合。
- **内容结构**：剧龄、集数、改编来源分布。
- **剧集库**：采集以来出现过的所有剧，可搜索；点任何剧名都能看单剧的热度、收藏、名次走势。
- **数据下载**：CSV、每日简报、口径说明、采集状态。

## 部署到自己的 GitHub

1. 新建一个仓库（公开仓库可以免费用 GitHub Pages），把这个目录推上去，默认分支叫 `main`。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
3. 把 `config.toml` 里 `user_agent` 的地址换成你的仓库地址，提交。
4. 打开 **Actions → radar → Run workflow** 手动跑一次（勾选「先采集一次」）。完成后看板地址是
   `https://<你的用户名>.github.io/<仓库名>/`。
5. 之后每天会自动检查 5 次，官方刷新后采集一次、提交数据、重新部署。官方没刷新时什么都不做。

> 历史数据只能从第一次采集那天开始积累：名次变化、增量和题材动量从第二天起才有，7 日指标要满一周。

## 本地运行

需要 Python 3.11 及以上。采集与分析本身只用标准库；只有启用了飞书通知报告器才需要
`requests`（`pip install -r requirements.txt`，不配飞书时可不装）。

```bash
python3 -m unittest discover -s tests -t .   # 测试
python3 -m radar collect                     # 采集今天的批次
python3 -m radar build                       # 分析并生成 _site/
python3 -m radar serve                       # 本地预览 http://127.0.0.1:8765/
python3 -m radar plugins                     # 列出已注册的数据源、分析器、报告器
```

`collect` 的参数：`--date YYYY-MM-DD` 指定批次日期；`--force` 覆盖当天已有快照；`--allow-stale` 官方没刷新也写（会标记为 stale，不计入名次变化）。

## 配置

都在 [`config.toml`](config.toml)：要抓哪些榜、请求间隔、观察列表（不在榜上也每天追踪的剧）、新剧的天数界限、
题材动量对比天数、潜力分权重、是否生成每日简报等。改完提交即可。

## 飞书通知（可选）

把看板总览的「今日要点」每天推送到飞书群机器人，**一天只发一次**。

1. 在飞书群里添加一个**自定义机器人**，拿到 webhook 地址里那串 key，在 GitHub 仓库的
   **Settings → Secrets and variables → Actions → New repository secret** 里加：
   - `FSKEY`：必填，机器人 webhook 里的 key；
   - `FSSECRET`：可选，机器人的签名校验密钥（配了才做签名）。
2. 提交即可。每次官方刷新后采集成功并重新部署的那一次，会把当日要点发到群里；
   其余几次定时任务因官方未刷新而跳过，所以天然一天一次（`data/state/hongguo/feishu_sent.json`
   再兜底，避免同一天重复部署时重发）。没配 `FSKEY` 时不发送，也不影响站点生成。

发送失败只打日志、不影响采集与部署结果。内容格式为「短剧雷达 · 日期 今日要点」加若干条要点。

## 目录

```
radar/
  core/        配置、HTTP、存储、时间、插件注册表（与平台无关）
  sources/     数据源插件（hongguo/）
  analysis/    分析器插件（metrics、boards、movers、potential、tags、lifecycle、dramas、exports、insights、status）
  reporters/   报告器插件（markdown、feishu）
  site.py      组装 _site/
tools/         第三方工具（tools/notify.py 飞书推送，来自 cron-job 的通用通知模块）
web/           看板（原生 JS + ECharts，无需构建）
data/          采集到的数据：snapshots/ 每天一份原始快照，catalog/ 剧集目录，state/ 采集缓存
reports/       每日 Markdown 简报
docs/          数据格式说明、扩展指南
```

- 数据格式与口径：[docs/DATA.md](docs/DATA.md)
- 加数据源、分析器、报告器、看板页面：[docs/EXTENDING.md](docs/EXTENDING.md)

## 采集规范

- 只读取官网公开的榜单、详情和搜索页面；`robots.txt` 允许这些路径。
- 相邻请求至少间隔 1 秒，一天只在官方刷新后完整采集一次（约 20 个榜单页 + 几百个详情页）。
- 不下载视频，不保存评论内容和评论者信息。
- 数据仅用于研究和内部分析，转载或商用前请自行确认平台条款。
