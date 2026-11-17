# WakaTime 与开发统计

主页使用与 [sun0225SUN](https://github.com/sun0225SUN) 相同的 `anmol098/waka-readme-stats` Action 生成统计。它会更新 README 中唯一一对 `<!--START_SECTION:waka-->` / `<!--END_SECTION:waka-->` 标记，包含提交时段、最活跃星期、WakaTime 语言/编辑器/系统统计，以及 WakaTime 支持时的 AI 编码统计。

## 配置

1. 在 [WakaTime OAuth 页面](https://wakatime.com/oauth) 获取个人 OAuth Access Token。2026-11-01 起，普通 WakaTime API Key 不能用于读取统计。
2. 在仓库 [Actions secrets 设置](https://github.com/Alinerml/Alinerml/settings/secrets/actions) 添加或更新 `WAKATIME_ACCESS_TOKEN`，值为 OAuth Access Token。此 Secret 只在工作流中作为上游 Action 的 `WAKATIME_API_KEY` 输入传递；不要把令牌放进代码或聊天。
3. 若要启用截图中的 GitHub 提交时段和星期统计，请再添加 `GH_TOKEN`。按上游 Action 当前文档，该 token 需要 `repo` 和 `user` scopes；工作流用它读取提交指标，提交 README 则仍使用权限受限的临时 `github.token`。
4. 在 [Personal profile feeds](https://github.com/Alinerml/Alinerml/actions/workflows/personal-feeds.yml) 手动运行。后续每天北京时间 08:00 左右自动更新。

未设置 `GH_TOKEN` 时，工作流会退回到内置 `github.token`；WakaTime 数据仍可更新，但提交统计可能不完整。AI 编码数据只会在 WakaTime/上游 Action 能读取到真实数据时显示，不会使用示例截图数值。

## 上游

- [sun0225SUN 的 Waka 工作流](https://github.com/sun0225SUN/sun0225SUN/blob/main/.github/workflows/waka.yml)
- [waka-readme-stats](https://github.com/anmol098/waka-readme-stats)
- [WakaTime OAuth](https://wakatime.com/oauth)
