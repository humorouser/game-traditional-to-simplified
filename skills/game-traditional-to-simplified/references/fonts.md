# 字体覆盖与汉字外观

编码表映射字节到 Unicode，字体映射 Unicode 到字形。扩大 histogram 不会给字体添“继、续、戏、线”等字形。用对应 SDK 提取当前语言绑定的实际字体副本，包含菜单、字幕、提示和回退链；用 fontTools cmap 核对目标字符，报告缺字和受影响行。

仅给缺字补另一字体会留下两种设计、两种粗细。优先统一汉字字体/字重，保留英文、数字、图标及非汉字。标题与正文原本不同字号是正常层级，不强行统一。

`font_tools.py unify` 仅支持原字体和 donor 均为标准 TrueType glyf：

```powershell
python SKILL_DIR\scripts\font_tools.py audit --font work\original.ttf --text-json outputs\converted\simplified.json --report outputs\font-audit.json
python SKILL_DIR\scripts\font_tools.py unify --font work\original.ttf --donor work\licensed-font.ttf --text-json outputs\converted\simplified.json --weight 400 --output outputs\uniform.ttf --report outputs\font-validation.json
```

脚本不安装字体、不写容器。将原字体及目标文本的所有汉字映射到同一个 donor，补齐其他目标缺字。保留原非汉字映射、原 glyph 数值编号/轮廓/字宽、字体家族及行距。post 格式 3 不存 glyph name，读回名称会重建：用数值 ID、metrics、轮廓比较，不按名字判错。汉字字宽不兼容时停止，另选合适字体或明确适配策略。

变量字体固定字重；静态 donor 使用已有字重，不谎称已改。CFF、位图、距离场图集用相应工具。原字体没有支持补充平面的 cmap 时脚本停止，不猜引擎支持新增表。

本次使用 [Google Fonts 官方 Noto Sans SC](https://github.com/google/fonts/tree/main/ofl/notosanssc) 的变量 TTF，在 0.3.0 固定到 400 Regular；不是每个游戏都必须用此字体。保留许可和下载 SHA-256，不执行不明字体安装程序。

检查 UPEM、advance width、ascent/descent/lineGap、bbox、基线、标点、截断。同尺寸渲染原/结果的**真实导出文本**，避免手打样本引入语料外缺字。竖排、变体选择符、连字和复杂 shaping 另在原引擎检查。

导入保持字体 RID、类型、metadata、语言绑定和必要大小字段；压缩打包后解压读回。离线字体可显示仍需游戏内验证。
