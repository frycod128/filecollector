# 文件内容收集器

递归读取文件夹下所有文件，将路径和内容整合到一个文本文件中。

## 安装

```bash
pip install pathspec
```

## 使用方法

### 1. 首次运行

```bash
python file_collector.py
```

自动生成配置文件 `collector_config.json`。

### 2. 编辑配置

```json
{
    "target_directory": "/你的/目标/文件夹/路径",
    "exclude_files": [
        "collected_contents.txt",
        "collector_config.json"
    ],
    "use_gitignore": true
}
```

| 配置项 | 说明 |
|--------|------|
| `target_directory` | 目标文件夹路径 |
| `exclude_files` | 排除的文件名或通配符（如 `*.log`） |
| `use_gitignore` | 是否遵循 `.gitignore` 规则（`true`/`false`） |

### 3. 运行收集

```bash
python file_collector.py
```

输出文件 `collected_contents.txt` 将保存在目标文件夹中。

## 输出格式

```
相对路径/文件名.后缀
文件内容...


另一个文件.另一个文件的后缀
文件内容...
```

## 常见问题

**Q: 如何排除特定文件？**  
A: 在 `exclude_files` 中添加文件名或通配符，或在 `.gitignore` 中添加规则并将 `use_gitignore` 设为 `true`。
    （如果你没有额外排除 `.gitignore` 文件那么它的内容也将是输出的一部分）

**Q: 可以处理二进制文件吗？**  
A: 会被当作纯文本处理，建议在 `exclude_files` 中排除图片、压缩包等二进制文件。

**Q: 文件读取失败怎么办？**  
A: 输出中会显示 `[读取文件失败: ...]`，不影响其他文件处理。
