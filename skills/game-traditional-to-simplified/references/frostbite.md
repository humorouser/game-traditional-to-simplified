# Frostbite / Frosty 专项

以下在 Frosty 1.0.6.3 Catalyst profile 核实。其他游戏/版本查实际 profile 和源码，不能套 GUID、magic、字段和路径。

来源：[官方发布](https://github.com/CadeEvs/FrostyToolsuite/releases/tag/v1.0.6.3)、[读取器](https://github.com/CadeEvs/FrostyToolsuite/blob/v1.0.6.3/Plugins/FsLocalizationPlugin/FsLocalizationStringDatabase.cs)、[写入处理器](https://github.com/CadeEvs/FrostyToolsuite/blob/v1.0.6.3/Plugins/FsLocalizationPlugin/FsLocalizationCustomActionHandler.cs)、[旧插件源码](https://github.com/zhpete/Frosty-LocalizedStringPlugin)、[flammenwerfer](https://github.com/BF1CHS/flammenwerfer)。

## 无损提取

从安装清单、FileSystem 布局和 AssetManager 找语言；小 SB 可能索引 CAS 内容，不等于没有文本。用 ResourceManager/AssetManager，不重写容器解析器。

FsLocalizationStringDatabase 将解码结果放 ID 字典，会丢重复行。将现有解码逻辑改为逐行收集 ID/偏移表，并对照原读取器；不去重。

1.0.6.3 CSV 导出删除 CR、把 LF 改空格；导入位置切片不能可靠恢复双引号/多行。CSV 存在不等于无损导入已确认。旧 zhpete 插件只有 CSV/SID 导出，不猜它支持导入。

FsLocalizationCustomActionHandler.ModifyHistogram 不扩表；ModifyChunk 对不能表示的字警告并跳过，不可直接用于完整简体后宣称无损。

## 扩表与重建

复用经过审查的字符串编码工具，先用原资源比对 Frosty，完整一致才扩展。本次 flammenwerfer commit `fe2bb16163e63dd6249cf5dbe47f990845cbf2d0` 需检查这些历史问题：

- 第二字节边界应为 `>= 0x80`，不是 `> 0x80`。
- 前缀是合法单字节，不能把大于 0xFF 的索引编码为一个字节。
- 保留原 ID 表顺序/重复行，不能按字典重写去重。
- 新字符固定 Unicode 排序，避免 set 顺序不确定。
- ASCII 直接编码，不占新增 histogram 槽。

扩展后分别用 Python 工具和 Frosty 原解码逻辑读回全库，ID/文本/次序/重复行一致。对应 profile 若有 BinaryChunkSize/HistogramChunkSize，更新 EBX 这两个大小，不只改 chunk。

## 构建与字体

独立进程用 AssetManager.ModifyChunk/ModifyRes/ModifyEbx 暂存，不调用 Apply/Launch；内存暂存不写游戏。标准 FrostyModWriter 输出，避免再经过丢字的 custom handler；需要控制 writer 时隔离配置，不改用户全局设置或安装未知插件。

字体查 UITtfAsset、UITtfFontFile RES 和语言字体配置；仅搜类型里的“font”会漏掉 UITtfAsset。保持 RES RID、类型、metadata 和 EBX 关联，用 fontTools 处理标准 TTF。

FrostyModReader 读回 profile/head、资源数/类型、SHA-1、解压 payload。EBX 读回检查语言/GUID/大小；RES 检查 RID/类型/metadata/字体数据。构建有效不是加载已成功。

## 实际应用

- Available Mods 仅导入；选中 → Apply Mod(s) → Applied Mods 存在且启用 → 管理器 Launch。
- 新版标题/版本核实，停旧中文/字体包。
- 只读核对 `ModData/<pack>/<actual patch path>/mods.json`。Catalyst 示例是 `ModData/Default/patch/mods.json`，空数组意味着该次生成没包含 MOD；缓存也可能过时，结合当前 UI 和时间。
- 基础语言仍与修改资源一致，本次为繁体中文；Steam/EA 启动链按实际日志确认，不擅改启动参数、全局环境变量或装启动插件。
- 分别排查未应用、参数丢失、资源未覆盖、编码缺字、字体缺字和混合字形。
