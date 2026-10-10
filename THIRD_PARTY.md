# 第三方来源与发布内容

- flammenwerfer：skills/game-traditional-to-simplified/assets/catalyst/vendor/flammenwerfer 为来自 https://github.com/BF1CHS/flammenwerfer 的选取源码，保留 GPL-3.0 许可。本地修订处理编码及边界检查，审查说明见 references/frostbite.md，不等同于未修改的上游。
- OpenCC：https://github.com/BYVoid/OpenCC ，运行时依赖通过官方 PyPI 获取，未把依赖包放入仓库。
- FrostyToolsuite：https://github.com/CadeEvs/FrostyToolsuite ，构建时获取官方版本资源库；仓库只含调用接口的自有 C# 胶水源码，不分发 Frosty EXE/DLL 或修改其源码。
- Google Fonts / Noto Sans SC：https://github.com/google/fonts/tree/main/ofl/notosanssc ，脚本获取官方字体和 SIL OFL，保存下载指纹；仓库不含字体或生成的游戏字体资源。
- fontTools 和 Pillow 是构建/验证依赖，按 requirements.txt 安装，未内置包。

本仓库自己的代码及说明按 GPL-3.0 发布，完整条款见根目录 LICENSE。第三方许可不因该说明而变更。六张案例截图中的游戏内容、角色及商标归相关权利人，仅作为繁简转换效果的展示，不属于本项目授予 GPL 的代码资产。

不含完整官方文本、转换后文本库、原字体、CAS/SB/TOC、MOD、补丁安装 EXE、运行库、个人账户配置或凭据。用户在自己的正版安装中本地生成的产物不自动成为本仓库的公开发布附件。
