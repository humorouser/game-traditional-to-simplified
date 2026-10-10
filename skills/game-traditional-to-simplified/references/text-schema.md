# 无损文本输入和转换

脚本用 UTF-8 JSON（可带 BOM）保存 Unicode，不直接解析游戏资源。每个资源独立导出：

```json
{
  "schema_version": 1,
  "metadata": {
    "language": "TraditionalChinese",
    "lossless": true,
    "resource": "actual/resource/name",
    "source_encoding": "record real encoding/container",
    "id_format": "hex32"
  },
  "entries": [
    {"id": "00000001", "text": "繼續遊戲", "resource_index": 0},
    {"id": "00000002", "text": "任務 {0:d}\n記憶體", "resource_index": 0}
  ]
}
```

`id_format: hex32` 只用于实际 32 位十六进制 ID；其他游戏省略，ID 可为非空字符串或整数，不转浮点数。附加字段原样保留。`lossless: true` 来自导出路径核实，不能随便补字段将有损 CSV 标成无损。相同重复行保留，有冲突的同 ID 文本拒绝并调查资源/上下文。

从 `scripts/glossary.json` 复制术语表到工作目录，按游戏定制。默认只提供“遊戲設定 → 游戏设置”示例，不泛用 Catalyst 专名。

```json
{
  "replacements": {"遊戲設定": "游戏设置"},
  "protected_terms": [],
  "additional_protected_regex": []
}
```

替换只含汉字。默认保护标签、花括号占位符、双中括号、printf、反斜杠转义、URL 和控制字符。单层方括号默认是可见文字；引擎使用 `[BUTTON_ID]` 时补针对性规则。检查颜色代码、变量等真实语法，默认不覆盖所有游戏。

```powershell
python -m venv work\venv
work\venv\Scripts\python.exe -m pip install -r SKILL_DIR\scripts\requirements.txt
work\venv\Scripts\python.exe SKILL_DIR\scripts\test_conversion.py
work\venv\Scripts\python.exe SKILL_DIR\scripts\convert_localization.py work\original.json --output outputs\converted --glossary work\glossary.json --game-root "ACTUAL_GAME_DIRECTORY"
```

以实际值代换示例路径，输出必须在工作目录。`--histogram path.json` 对照编码表，格式为 resource 和 codepoints 数组；不是字体检查。默认 tw2sp；对照表含无术语替换的 t2s，差异不全是错误。requirements 固定本次 OpenCC 1.4.2；升级先测样本。

校验数量、ID 类型和值、排序、重复行、附加字段、metadata、token、非汉字、换行、空文本、UTF-8。保护变量中的繁体可能合法；NUL 要确认存储支持，不静默移除。
