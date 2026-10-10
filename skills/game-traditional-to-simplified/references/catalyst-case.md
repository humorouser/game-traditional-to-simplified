# Catalyst 已验证实例

用户在本对话确认 **0.3.0 统一字体版成功**；证据来自用户实际游戏反馈，不是代理自行运行。此前菜单/提示截图出现简体，未声称全剧情逐句审阅。以下编号/路径仅用于同款游戏，其他安装仍需检测。

- Windows 10 x64；Steam App ID 1233570、buildid 10351434；Frosty 1.0.6.3 `MirrorsEdgeCatalyst`，DataVersion 20160607，game head 175205。
- 路径实例 `<实际游戏安装目录>`。
- EBX `Localization/fs_zh_loc`，类型 FsUITextDatabase，LanguageFormat_TraditionalChinese。
- BinaryChunk `b33bd00e-3c9a-e427-e1b3-e10bcaf3b73d`，HistogramChunk `97ed5d4a-0e91-042b-b41c-2ce4f59fefc3`。
- 7978 行/7977 唯一 ID；`C3678BFD` 两行相同，保留；6161 行转换，9 行原空文本保留。
- tw2sp 把专名“塑膠怪”错转为“塑料怪”，本实例术语表用“塑胶怪”，不全局泛用。
- 编码表补 783 字符；新 BinaryChunk 356579、HistogramChunk 270142 字节，更新 EBX 大小。
- 字体 EBX `UI/Fonts/FontSources/ARHeitiMediumB5_TC`，家族 ARHeitiMediumB5；RES RID `9AA46CCB815CD1C5`，UITtfFontFile，标准 TTF。

| 现象 | 实际原因 | 修复 |
|---|---|---|
| 导入后仍繁体 | 应用列表为空，生成记录 `[]` | Apply、勾选再启动 |
| 0.1.0 空白/方框 | 编码表已扩，字体缺 710 字符，涉及 6043 行 | 检查实际 cmap，处理字体 |
| 0.2.0 同句粗细不同 | 原字体与 Noto Sans SC 500 补字混用 | 所有汉字统一 Noto Sans SC 400 |
| 字体名字校验失败 | post 格式 3 名称读回重建 | 校验数值 glyph ID、字宽和轮廓 |

0.3.0 统一 13780 个汉字码点，含语料 2135 不同汉字，缺字 0、FreeType 栅格化非空；英文/数字/图标和汉字字宽/字体行距保留。离线验证 + 用户运行反馈可记录本版可用，不保证其他游戏。

技能通用脚本复测时进一步发现，旧脚本把普通方括号可见文字 `[ 未尋獲 ]` 也保护了。通用脚本仅默认保护双中括号，单层标记按引擎语法定制；此可见文案可正确转为 `[ 未寻获 ]`，本次真实语料复测因此为 6162 条变化。技能创建过程仅用工作副本复测，没有改动用户已确认可用的 0.3.0 游戏安装。

当次 Google Fonts `ofl/notosanssc/NotoSansSC[wght].ttf` SHA-256：`a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`，这是下载指纹而非独立签名。附 OFL，原游戏字体和文本不放入 skill 包。

后续首次使用测试重新从原游戏导出，空依赖环境下载官方资源库及字体，构建 0.4.0 自动包（7978 行、6162 行变化、30 项测试通过）。用户授权自动应用与创建链接提权后，官方管理器后台 `-launch Default` 生成清单仅启用 0.4.0；用户确认“已经成功运行了，是简体的，我已经退出了”。本包 SHA-256 为 `8451acb3290fc821ac2373cf65b2a16e6d7404babe84471514df301a230ae7f6`。这是当前机器首次依赖/工作环境及实际游戏测试，未覆盖缺少 Python/.NET 的全新 Windows 或全剧情校对。具体应用步骤见 [automation.md](automation.md)。
