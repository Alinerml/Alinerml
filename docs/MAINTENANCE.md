# 主页维护

这是 [Alinerml](https://github.com/Alinerml) 的 GitHub Profile README。

## 已接入模块

- 动态打字标题、深浅色插画、访客计数、技术标签与动画。
- GitHub 公开统计、语言分布、贪吃蛇与 3D 贡献城市。
- 本仓库生成的最近 30 天贡献趋势、全年与历史贡献日历。
- 公开仓库概览、关注者、评论反应、本人创建的 Issues/PR 状态、最近 Star、Star 趋势，以及精选公开项目 `minigo` 和 `tiktok`。精选卡不改变 GitHub 原生置顶。
- 公开推送时段，以及折叠区域中的最近活动与 Discussions 统计。
- WakaTime 自动更新入口；设置本人密钥后显示最近 7 天语言、编辑器与操作系统摘要。详见 [接入步骤](WAKATIME.md)。

未关联的社交、Stack Overflow、RepoBeats、Sponsors、Buy Me a Coffee 不显示占位按钮；博客保持关闭。未启用需要额外个人令牌的 Gists 和 Metrics achievements 插件。GitHub 原生成就由平台授予，不能通过 README 配置生成。

## 自动更新

| Actions 工作流 | 北京时间计划 | 更新内容 |
| --- | --- | --- |
| Reference profile metrics | 每天 08:00 | GitHub Metrics 卡片 |
| Personal profile feeds | 每天 08:00 | WakaTime 摘要与图表 |
| Update profile visuals | 每天 09:23 | 贪吃蛇、公开统计、语言分布、3D 城市 |
| Contribution calendar cards | 每天 09:35 | 30 天趋势、全年与历史贡献日历 |

GitHub 定时任务可能延迟；均可在 Actions 手动运行。工作流共用 `profile-visuals` 并发组，避免互相覆盖提交。使用 `queue: max` 保留多个等待任务，避免不同模块的待运行更新互相取消。

GitHub 模块仅使用仓库自动提供的临时 `GITHUB_TOKEN`，无需新增 PAT。未启用 Gists 插件，因为临时令牌不能读取用户 Gists。`only_base=true` 可单独重生成公开仓库概览与 Star 图。

近期活动和推送时段由 `scripts/public_activity.py` 读取公开 Events API 生成，避免上游 Metrics 旧插件依赖已移除的 `payload.commits` 字段。

公开仓库概览与 Star 图由 `scripts/public_repositories.py` 使用 GitHub REST API 生成，仅统计本人拥有的公开仓库，明确区分原创和 fork。语言分布使用 `profile/languages*.svg`。已停用 Metrics 的深度语言分析，避免旧插件吞掉仓库查询错误后输出假的零数据。

生成的统计图由本仓库托管，README 使用相对路径，避免把固定 CDN 缓存参数误当成实时更新。更改 SVG 后 GitHub 图片缓存可能需要一点时间刷新。生成失败时保留上次已提交的图片，需查看相应 Actions 日志确认更新时间。

贡献数不等同于提交数；日历使用 GitHub 贡献数据和 UTC 日期，当天数据尚未结束。推送时段按北京时间展示；一个 PushEvent 不等于一次 commit，也不代表编程时长。语言比例表示公开仓库代码分布，不代表熟练度。最近活动仅展示公开事件，活动较少或没有讨论时可能显示真实空状态。

## 修改内容

编辑根目录 `README.md` 即可调整简介、技术标签与排版。标题使用 `readme-typing-svg.demolab.com`。WakaTime 的唯一一对 `START_SECTION:waka` / `END_SECTION:waka` 标记应保留在表格外，由工作流填充；缺少密钥时不展示。

长期没有活动的公开仓库可能被 GitHub 暂停定时工作流；在 Actions 重新启用即可。

## 视觉来源

布局和装饰图参考 [sun0225SUN](https://github.com/sun0225SUN/sun0225SUN)，装饰资源固定于其提交 `6d4e976b053a33c97b5b0984516217c22af93de5`。未复制作者的个人账号、支付链接或统计数据。

- [Platane/snk](https://github.com/Platane/snk)：贡献贪吃蛇。
- [GitHub Profile 3D Contrib](https://github.com/yoshi389111/github-profile-3d-contrib)：3D 贡献城市。
- [GitHub Readme Stats Action](https://github.com/stats-organization/github-readme-stats-action)：生成公开统计和语言卡片。
- [Metrics](https://github.com/lowlighter/metrics)：公开 GitHub 活动卡片。
- [WakaTime API](https://wakatime.com/developers)：本人编程时长摘要。
- [Shields.io](https://shields.io)：技术与导航徽章。

装饰图、徽章、笑话、语录和连续贡献统计仍使用外部服务；基础统计、活动趋势与日历由仓库自动生成。
