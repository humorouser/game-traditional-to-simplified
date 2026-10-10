# 游戏官方繁体转简体 · Codex Skill

将游戏已经提供的官方繁体中文，在本地使用 OpenCC 转为简体中文，再通过对应游戏的资源工具制作独立补丁。保留字符串 ID、顺序、占位符、英文、数字和控制字符，不逐句调用 AI 翻译 API，不重新翻译剧情。

**当前已实现并实测：Steam 版《镜之边缘：催化剂》的自动构建流程。** 通用的是转换、验证和适配方法；其他游戏或平台必须先核实资源格式、字体和加载方式。本项目不是能够自动处理所有游戏的通用二进制补丁程序。

## 功能

- 只读检测游戏与官方繁体资源，导出原文备份和资源关联。
- OpenCC tw2sp 批量转换，生成简体 JSON、CSV 对照、t2s 比较和统计报告。
- 保留重复 ID 条目与合法空文本，保护实际引擎的变量、标签和转义序列。
- 分开验证文本、引擎编码表、字体覆盖和 MOD 加载。
- 检查缺字和同一句汉字粗细不一致，保留原 UI 的字号层级。
- 使用游戏对应的可靠 SDK/导入器生成独立 MOD；安装、启动参数和管理员操作按用户授权执行。
- 可由 Codex 为已适配的游戏另外制作一键启用/恢复工具。

## 实际效果

《镜之边缘：催化剂》的操作设置页面：左侧官方繁体，右侧转换后的简体。截图由使用者实际运行游戏提供。

| 官方繁体 | 简体补丁 |
|---|---|
| ![官方繁体操作设置](docs/images/controls-traditional.png) | ![简体操作设置](docs/images/controls-simplified.png) |

主菜单、进度页面及故障修复经过见 [完整案例](docs/catalyst-case.md)。

## 安装 Skill

将仓库中的 skills/game-traditional-to-simplified 整个文件夹放到本机的 Codex skills 目录，例如 Windows 的 %USERPROFILE%\\.codex\\skills\\。入口是 [SKILL.md](skills/game-traditional-to-simplified/SKILL.md)。

随后向 Codex 提供游戏名称和实际安装目录，例如：

> 使用 game-traditional-to-simplified skill，将《镜之边缘：催化剂》的官方繁体转为简体。游戏目录为我提供的本地路径。先只读检查，在独立工作目录构建，安装前说明实际需要的修改。

Skill 是给 Codex 使用的指令、脚本和参考资料，不是双击运行的安装程序。

## 自动流程

检测游戏与版本 → 确认适配器 → 结构化导出与备份 → 样本测试 → OpenCC 批量转换 → 编码与字体检查 → 资源读回及 MOD 打包 → 已授权应用 → 实际游戏验证。

Catalyst 的 [auto_catalyst.py](skills/game-traditional-to-simplified/scripts/auto_catalyst.py) 已自动完成到 MOD 打包；应用、生成游戏 ModData、持久启动配置和一键 EXE 制作属于后续单独执行的工作，不在该入口中。

## 环境与支持范围

| 项目 | 当前状态 |
|---|---|
| 文本转换 | 可复用；接受规范化 JSON，不能直接读取任意游戏容器 |
| 字体工具 | 适用于支持的标准 TrueType 结构；其他字体封装另行适配 |
| Catalyst 构建 | Windows x64、现有 Python x64、.NET Framework 4.8/C# 编译器；自动准备隔离依赖及可信 SDK/字体 |
| Steam Catalyst 实测 | 已有真实游戏反馈和截图；未逐句审阅完整剧情 |
| Epic、EA App、GOG 或其他游戏 | 转换原理可用，尚无本仓库验证的完整适配器 |
| 全新 Windows | 已验证当前电脑上的空依赖/工作目录；未验证缺少 Python/.NET 的另一台电脑 |

首次构建需要下载官方依赖；游戏文本转换在本地完成。构建使用 Frosty 官方资源库，不能说完全无 Frosty 依赖。游戏更新或工具下载指纹变化时停止核实，不盲用旧补丁。

## 一键工具的关系

本地案例工具名称为 GameChineseConverter.exe，用于安装已经转换并验证的资源、启用简体和恢复官方繁体。它不是运行时翻译器。

已制作的案例 EXE 的后端仅适配指定 Steam Catalyst 版本。Steam 账户用于选择要修改的本地启动配置，启动按钮调用对应游戏；这些不是 OpenCC 的转换条件。其他平台需要自己的加载适配。**本仓库不包含案例 EXE、完整游戏文本、MOD、游戏字体或运行库**；一键工具的源码模板及构建入口也尚未纳入本 skill。

更多说明见 [功能与平台范围](docs/features.md)。

## 测试

在准备好依赖的 Python 环境中，可运行不访问游戏的合成测试：

~~~powershell
python -m pip install -r skills/game-traditional-to-simplified/scripts/requirements.txt
python -m unittest discover -s skills/game-traditional-to-simplified/scripts -p "test_*.py"
~~~

合成测试验证脚本行为，不等于 MOD 已在游戏中成功加载。真实游戏流程必须另行执行资源读回和实际启动检查。

## 参与适配与许可

新游戏适配要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。项目代码与文字按 GPL-3.0 发布，第三方文件保持原许可，见 [LICENSE](LICENSE) 和 [THIRD_PARTY.md](THIRD_PARTY.md)。案例截图中的游戏画面、商标和游戏内容归其权利人，截图用于展示转换效果，不授予对游戏资产的再许可。
