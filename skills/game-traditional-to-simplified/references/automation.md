# 后台自动繁简转换

用户希望 skill 自动执行，不承担工具下载、命令输入、导出、导入、选 MOD 等操作。默认由 Codex 调用脚本完成；只在缺失授权、未知格式或确实没有自动接口时停在具体问题处。不能把人工教程当作默认交付。

## 新环境与首次使用

先检测 Windows x64、Python（已实测 3.10.4 x64）和 .NET Framework 4.8。入口需要现成的 Python 解释器及 .NET 编译器；它自动创建 Python 依赖环境并下载资源库，不会自动安装缺失的 Python/.NET。缺少 Python 时可检查 Codex 可用的可信运行时；缺少 .NET 或需要系统安装/提权时按用户授权处理，不能把工作目录隔离测试说成“任意新 Windows 零前置条件”。

本 skill 已做首次使用验证：只复制 skill 源文件，使用空 Python 虚拟环境和空工作目录，禁用 pip 缓存，不传旧压缩包/字体/文本，实际重新从官方来源下载依赖，再从当前游戏重新导出、转换和构建。7978 行、30 项测试、编码扩表、统一字库和 MOD 读回均通过。随后获安装及创建链接提权授权，使用已安装且核实的官方管理器自动应用 0.4.0；用户实际启动并确认简体可用、已退出。范围是当前 Windows 的新依赖/工作环境；未验证缺少 Python/.NET 的机器，应用阶段也没有模拟管理器首次安装。

需要重复此测试时使用全新目录，只传 `--game-root` 和 `--work-root`；不要传复用依赖参数。测试数据、源文件指纹、下载指纹、脚本日志和前置条件应记录到独立报告。

## 已验证的 Catalyst 自动入口

Windows x64、Steam Catalyst、Frosty profile `MirrorsEdgeCatalyst` DataVersion 20160607 / head 175205。后台入口是 [../scripts/auto_catalyst.py](../scripts/auto_catalyst.py)，调用示例供 Codex 执行：

```powershell
& '<python.exe 的绝对路径>' '<skill>/scripts/auto_catalyst.py' --game-root '<实际游戏目录>' --work-root '<独立工作目录>'
```

- 自动创建隔离 Python 环境并从官方 PyPI 安装固定依赖（现有解释器依赖齐全则复用）。缺少 Python/.NET 时先检测可信运行时，不运行未知来源安装器。
- 自动获取官方 Frosty **Editor 1.0.6.3 压缩包中的未修改资源库**，校验本实例已核实的 SHA-256；不启动 Editor，不获取或运行 Mod Manager。官方资源依赖仍然存在，不能声称完全摆脱 Frosty。
- 自动获取 Google Fonts Noto Sans SC 和 OFL。指纹不符时停止并调查来源变化，不自动接受新文件。下载和依赖安装需要当前环境允许网络；若 sandbox 阻止，由 Codex 请求所需工具权限，不能把下载任务转给用户。
- 支持 `--frosty-archive`、`--donor-font`、`--donor-license` 复用已有官方文件；字体和压缩包仍校验。工作目录和所有生成文件必须在游戏外。
- 自动编译 [../assets/catalyst/CatalystBackend.cs](../assets/catalyst/CatalystBackend.cs)，调用官方 SDK 导出文本、原始 chunk 和实际绑定字体。官方解码器获取文本，额外读取已核实 ID 表保留重复行；不复制或修改 Frosty 源码，不解析 CAS/SB/TOC。
- 对副本运行本地 OpenCC、保护格式并保留游戏专名。编码采用审查修复后的 flammenwerfer，保留其 GPL-3.0 [许可证](../assets/catalyst/vendor/flammenwerfer/LICENSE)。重复 ID 原始编码冲突、版本/资源/绑定变化均停止，不能盲用旧编号。
- 跑 30 项脚本测试，扩展编码表，并把全部汉字统一为同一个 Noto Sans SC 400 字形设计。英文/数字/图标、字宽、行距和原 UI 层级保留。
- 官方 SDK 独立读回全库，内存导入并构建标准 `.fbmod` / `.fbproject`；检查大小关联、资源类型、压缩 payload、哈希和字体资源。对照 Data/Patch/Core 文件大小及修改时间，报告其只读观察范围，不声称等价于全盘字节哈希。

脚本只输出统计、工作路径和失败日志位置，不打印整库。每次新建 `run_<随机编号>`，不覆盖之前成果；`latest_run.json` 指向最后一次成功结果。原文备份、对照 CSV、简体 JSON、术语表来源指纹、字体/编码/MOD 报告均保留。

## 自动构建与启用的边界

这个入口已实现 **自动导出→转换→编码→字体→校验→打包**。安装、生成游戏 ModData、Steam/EA 启动链不在该脚本中：用户最初要求它们先获授权，且 Frosty 的应用执行器包含游戏目录写入和可能的提权/链接操作，不能用一条 Run 调用偷偷跨越边界。

已获明确安装授权且存在经核实的自动应用接口时，由 Codex 执行应用并验证生成清单；不要再次让用户手动点管理器。没有对应接口时，先说明哪一步尚缺自动化能力，不把“已打包”描述为“已启用”。本入口不伪装成独立补丁管理器。

新构建包都标记尚未实际游戏验证。原先 0.3.0 用户确认可用的证据只属于原包；改变一条文本或重建后不能沿用为新包的运行证据。

## 已验证的后台应用路径

构建脚本仍只负责制作；以下步骤由 Codex 在确认授权后单独执行，不要求用户操作 Frosty 界面。

1. 检查游戏及管理器进程已退出。使用官方 Frosty Mod Manager 1.0.6.3；从官方发布页获取并核实来源和压缩包指纹。本实例压缩包 SHA-256 为 `c7cf94239bcfeb9203330debe7c68c8a02c07bb24df44dde8d69ace934c69b19`，实际执行前全部 50 个 EXE/DLL 与官方包逐一核对。不要复制本机工具绝对路径到其他环境。
2. 备份 `%LOCALAPPDATA%/Frosty/manager_config.json`、生成目录的普通文件及链接目标清单。读取备份时不跟随链接；任何移动/删除先核实绝对路径和 reparse point，不能递归处理链接指向的原资源。本实例没有删除原资源。
3. 将新包放入管理器的 `Mods/MirrorsEdgeCatalyst`。目标 pack 仅启用新中文/字体包。为无界面启动暂设 `UseDefaultProfile=true`、`DefaultProfile=MirrorsEdgeCatalyst`、`UpdateCheck=false`，同时保留原配置备份。
4. 以管理器所在目录为工作目录，隐藏窗口执行官方 `FrostyModManager.exe -launch Default`。这里 `Default` 是 **pack 名称**，不是游戏 profile。官方执行器可能以 `runas` 执行 `mklink`；确认用户已授权该提权，Windows UAC 必须由用户本人确认，不绕过。已经明确收到的授权不要重复索取。
5. 检查新生成 `ModData/<pack>/patch/mods.json` 的文件名和版本确为新包。EA/Steam 启动可能延迟，短时间未见进程不能直接判定应用失败。恢复无关的临时全局偏好，保留新包启用状态；不擅自持久修改 Steam 启动参数。
6. 分别记录包读回、生成清单、进程观察和用户游戏内反馈。0.4.0 本次反馈为“已经成功运行了，是简体的，我已经退出了”；证明本次启动简体可用，不等于全游戏逐句校对。用户退出后不为增加记录再次启动。

### Steam 默认启动简体

用户明确要求默认从 Steam 加载简体时，这项要求授权为该游戏保存启动选项，无需重复索取同一授权。已核实的 Catalyst 参数为 `-dataPath "ModData/Default"`，与官方管理器 Steam 启动分支相同；实际 pack 变化时重新核实路径。保存后无需每次运行管理器，仍使用已生成的 ModData 和现有官方运行时组件。

先检查 MOD 清单版本、资源路径和运行时组件。Steam 运行时优先可靠设置接口；离线编辑必须确认 Steam 及游戏已退出，备份真实账户的 localconfig.vdf，只修改 `UserLocalConfigStore/Software/Valve/Steam/apps/1233570/LaunchOptions`，保留其他参数并读回验证。不要硬编码此实例的 Steam 账户目录到新环境。已有非空自定义参数需安全合并，不能覆盖。仅保存参数不等于直接 Steam 游戏显示验证；此前同一包、同一参数经管理器启动的证据分别记录。

本实例已按用户要求将参数保存为 Steam 默认值，配置读回通过。恢复官方繁体时只撤销新增的 dataPath 参数或恢复该键旧值，不盲还原整个账户文件，也不删除原游戏资源。游戏更新、Steam 验证文件或 ModData 被清理后可能需重建；不承诺永久跨版本有效。没有持久参数时，直接 Steam 启动采用官方资源。

额外离线读取生成目录时，本实例 `Update` 为指向不存在原目录的符号链接，SDK 枚举该可选目录会报 DirectoryNotFoundException。因此此项附加检查未通过，不能把它写成资源损坏或已验证读回。不要通过新建/删除原游戏目录绕过问题；包本身的 SDK 读回与用户运行证据分别保留。

## 其他游戏

先由 Codex 自动只读检测。只有资源导出、导入、字体和启动路径有可靠接口才接入相应适配器；通用 OpenCC/字体脚本可以复用，Catalyst 编号、7978 行断言和格式不能泛用。未知格式时保留已完成成果并报告障碍，不从头猜写解析器。
