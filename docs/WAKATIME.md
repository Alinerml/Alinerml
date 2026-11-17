# WakaTime 自动更新

`Personal profile feeds` 每天北京时间 08:00 左右运行，也可以在 Actions 手动运行。脚本使用 WakaTime OAuth 访问令牌读取最近 7 天统计，再用 GitHub Actions 自动提供的 `GITHUB_TOKEN` 提交 README 与两张 SVG；无需 GitHub 个人访问令牌。

## 接入自己的数据

1. 在常用编辑器安装 [WakaTime 官方插件](https://wakatime.com/plugins)，登录自己的账号，并确认 [Dashboard](https://wakatime.com/dashboard) 已有活动。
2. 在 [WakaTime OAuth 页面](https://wakatime.com/oauth) 获取个人 OAuth 访问令牌。只申请统计读取所需权限；脚本只展示语言、编辑器和操作系统汇总。
3. 打开本仓库 [Actions secrets 设置](https://github.com/Alinerml/Alinerml/settings/secrets/actions)，新增 Repository secret `WAKATIME_ACCESS_TOKEN`，粘贴 OAuth 访问令牌。不要写入 README、代码、Issue 或聊天。
4. 在 [Personal profile feeds](https://github.com/Alinerml/Alinerml/actions/workflows/personal-feeds.yml) 点击 **Run workflow**。有真实活动数据后，WakaTime 区域会显示语言、编辑器、操作系统汇总和两张卡片。

自 2026 年 11 月 1 日起，WakaTime API Key 仅用于插件写入活动，不能再用来读取统计。本仓库代码不再读取旧 Repository secret `WAKATIME_API_KEY`；请新增 `WAKATIME_ACCESS_TOKEN`。没有配置新 token 时工作流安全跳过。

OAuth 令牌只通过 HTTPS `Authorization: Bearer` 请求头发送，不进入 URL 或日志。API 失败或统计仍在刷新时，脚本保留上一次成功输出，避免把接口故障当作零数据。

脚本仅保存三种维度的汇总名称和用时，不保存 API 原始响应，也不输出项目、文件路径、分支、机器名称、账号标识或私有仓库信息。汇总用时可能包含私人项目中的活动，但不会公开项目身份。

卡片保存在 `profile/wakatime-languages.svg` 和 `profile/wakatime-editors.svg`；README 必须保留唯一一对 `<!--START_SECTION:waka-->` / `<!--END_SECTION:waka-->`，标记之间由脚本管理。日期来自 API 的 UTC 时间范围；时长不是 GitHub 提交统计。

## 校验

```sh
python3 -m unittest discover -s scripts -p 'test_wakatime.py'
python3 scripts/wakatime.py
```

第一条使用合成数据验证隐私字段过滤、空数据状态、SVG 转义、插槽替换和 API 错误处理，不请求真实账号。第二条未配置 OAuth token 时不会修改文件。实际账号连通需要配置 `WAKATIME_ACCESS_TOKEN` 后运行工作流。

## 依据

- [WakaTime API：OAuth 认证和 Stats](https://wakatime.com/developers)：读取统计使用 OAuth 2.0 access token；认证头为 `Authorization: Bearer ...`。API Key 自 2026-11-01 起仅供插件写入活动。
- [WakaTime OAuth](https://wakatime.com/oauth)：个人账号的 OAuth token 页面。
