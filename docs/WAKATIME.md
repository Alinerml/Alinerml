# WakaTime 自动更新

`Personal profile feeds` 每天北京时间 08:00 左右运行，也可以在 Actions 手动运行。使用 Python 标准库向 WakaTime 官方 API 读取当前密钥所属账号最近 7 天的统计，再使用 GitHub 自动提供的 `GITHUB_TOKEN` 提交 README 与两张 SVG；无需 `GH_TOKEN` 或个人访问令牌。

## 接入自己的数据

1. 在常用编辑器安装 [WakaTime 官方插件](https://wakatime.com/plugins)，使用自己的账号，并确认 [Dashboard](https://wakatime.com/dashboard) 已有活动。
2. 在 [WakaTime API Key 页面](https://wakatime.com/api-key) 复制自己的密钥。
3. 打开本仓库 [Actions secrets 设置](https://github.com/Alinerml/Alinerml/settings/secrets/actions)，新增 Repository secret `WAKATIME_API_KEY`，粘贴密钥。不要写入 README、代码、Issue 或聊天。
4. 在 [Personal profile feeds](https://github.com/Alinerml/Alinerml/actions/workflows/personal-feeds.yml) 点击 **Run workflow**。有真实活动数据后，隐藏的 WakaTime 插槽会自动显示语言、编辑器、操作系统和两张卡片。

没有密钥时工作流安全跳过，首次接入前不展示占位模块。最近 7 天没有活动时隐藏整个模块；API 失败或统计尚在刷新时保留上一次成功输出，并让该次运行失败，避免把接口故障当作零数据。定时任务的开始时间可能受 GitHub 排队影响。

脚本只保存三种维度的汇总名称和用时，不保存 API 原始响应，不输出项目、文件路径、分支、机器名称、账号标识或私有仓库信息。密钥只通过 HTTPS Authorization 请求头使用，不进入 URL 或日志。汇总用时可能包含在私人项目中的活动，但不会公开项目身份。

卡片保存在 `profile/wakatime-languages.svg` 和 `profile/wakatime-editors.svg`；README 必须保留唯一一对 `<!--START_SECTION:waka-->` / `<!--END_SECTION:waka-->`，标记之间由脚本管理。日期来自 API 的 UTC 时间范围；时长不是 GitHub 提交统计。

## 校验

```sh
python3 -m unittest discover -s scripts -p 'test_wakatime.py'
python3 scripts/wakatime.py
```

第一条用合成测试数据验证隐私字段过滤、空数据、SVG 转义、插槽替换和 API 错误处理；不会请求真实账号。第二条未配置密钥时不会修改文件。实际账号连通和活动采集需要配置密钥后另行验证。

## 依据

- [WakaTime API：认证与 Stats](https://wakatime.com/developers#stats)：使用官方 `users/current/stats/last_7_days`，检查 `is_up_to_date`，通过 API Key 的 HTTP Basic 请求头认证。
- [anmol098/waka-readme-stats](https://github.com/anmol098/waka-readme-stats)：参考语言、编辑器、操作系统和 `waka` 标记区间的展示方式。该工具默认涉及更多 GitHub/项目数据；本仓库用有限字段的脚本满足当前展示范围。
