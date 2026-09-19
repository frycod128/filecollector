# 文件内容收集器

递归读取文件夹下所有文件，将路径和内容整合到一个文本文件中。

典型用途：把整个项目源码打包成单个 txt，方便喂给大模型或做代码审阅。

## 安装

```bash
pip install pathspec
```

未安装 `pathspec` 时脚本仍可运行，但排除规则会退化为简化匹配（不支持 `**` 与目录专用语法）。

## 使用方法

### 1. 首次运行

```bash
python filecollector.py
```

脚本同目录下不存在配置文件时，会自动生成 `collector_config.json`（目标目录默认是当前工作目录）并退出，等待你编辑。

### 2. 编辑配置

```json
{
    "target_directory": "D:\\你的\\目标\\文件夹",
    "exclude_files": [
        "collected_contents.txt",
        "collector_config.json",
        ".git/*",
        "__pycache__/*",
        "node_modules/*",
        "target/*",
        "*.log"
    ],
    "use_gitignore": false,
    "newlines_between_files": 2
}
```

| 配置项 | 说明 |
|--------|------|
| `target_directory` | 目标文件夹路径 |
| `exclude_files` | 排除模式列表，支持通配符与 `!` 取反，写法见下节 |
| `use_gitignore` | 是否遵循 `.gitignore` 规则（`true`/`false`） |
| `newlines_between_files` | 每个文件之间的空行数量，取值 `0~1000`，默认 `2`；配置缺失或非法时使用默认值并给出提示 |

### 3. 运行收集

```bash
python filecollector.py
```

输出文件 `collected_contents.txt` 保存在目标文件夹中。

## 排除规则写法

`exclude_files` 使用 Git 的通配语法，并且**默认在任意层级生效**：

| 写法 | 含义 |
|------|------|
| `*.log`、`temp_*` | 匹配任意层级下同名的文件 |
| `node_modules/*`、`target/*` | 匹配任意层级下的该目录及其全部内容（`node_modules`、`src/node_modules` 都会被排除） |
| `build/` | 以 `/` 结尾表示只匹配目录，并排除其全部内容 |
| `/build` | 以 `/` 开头表示只匹配目标目录根部的 `build`，不匹配 `src/build` |
| `!keep.log` | 取反：重新包含此前被排除的文件（放在排除规则之后才有效） |

命中规则的目录会被整棵跳过，因此 `node_modules` 这类目录不会拖慢收集速度。

`use_gitignore` 为 `true` 时，除了根目录，**各级子目录中的 `.gitignore` 同样生效**，并且遵循 Git 的优先级（越靠近文件的 `.gitignore` 越优先）。`exclude_files` 的排除结果不会被 `.gitignore` 的取反规则推翻。

## 输出格式

```
相对路径/文件名.后缀
文件内容


另一个文件.另一个文件的后缀
文件内容
```

即：一行相对路径（统一用 `/` 分隔），紧接文件内容，之后是 `newlines_between_files` 个空行。

文件顺序是稳定的：先输出当前目录下的文件（按名称排序），再依次进入各子目录（深度优先），同一目录每次运行结果一致，便于 diff。换行符统一为 `\n`。

## 健壮性

- 输出文件自身永远不会被收集，避免自我引用。
- 符号链接一律跳过（不跟随、不读取），避免循环与收集到目标目录之外的文件。
- 二进制文件（前 8KB 含 NUL 字节）只写入路径占位 `[已跳过二进制文件]`，不会产出乱码。
- 单个文件读取失败时写入 `[读取文件失败: ...]`，不影响其它文件。
- 运行结束会打印统计信息（收集数量、输出体积、各类排除/跳过计数），便于确认规则是否按预期生效。

## 常见问题

**Q: 如何排除特定文件？**

A: 在 `exclude_files` 中添加文件名或通配符，或在 `.gitignore` 中添加规则并将 `use_gitignore` 设为 `true`。（如果没有额外排除 `.gitignore`，它的内容也会出现在输出中。）

**Q: 输出里的文件顺序为什么不是全局按路径排序？**

A: 顺序是"先本目录文件、再子目录"，这样同一目录的文件在输出中连续出现，便于阅读。它是确定性的，不会因文件系统顺序而变化。

**Q: 配置文件有错时会怎样？**

A: 会打印具体原因（路径不存在、JSON 非法、`target_directory` 为空等）并以退出码 1 结束；只有 `newlines_between_files` 非法时会回退到默认值 2 继续运行。
