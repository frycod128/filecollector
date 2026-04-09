# 文件内容收集器 (File Content Collector)

一个Python脚本，用于递归读取指定文件夹下的所有文件，并将每个文件的相对路径和完整内容收集到一个文本文件中。

## 功能特点

- 📁 **递归遍历**：自动处理嵌套文件夹中的所有文件
- 🔧 **配置文件支持**：通过JSON配置文件指定目标文件夹路径和排除列表
- 🚫 **文件排除功能**：支持精确匹配和通配符模式排除指定文件
- 🎯 **.gitignore 支持**：可选择遵循 `.gitignore` 规则自动排除文件
- 📝 **格式清晰**：每个文件包含相对路径和完整内容，使用`\n\n\n`分隔
- 🚀 **大文件优化**：分块读取和写入，支持处理几兆甚至更大的输出文件
- 🌍 **UTF-8编码**：支持各种特殊字符和换行符，无法解码的字符会被替换
- 🛡️ **错误处理**：单个文件读取失败不影响其他文件的处理

## 使用方法

### 1. 首次运行

直接运行脚本，会自动生成配置文件 `collector_config.json`：

```bash
python file_collector.py
```

首次运行时会显示：
```
已生成配置文件: /path/to/collector_config.json
请编辑配置文件中的 'target_directory' 字段，指定需要处理的文件夹路径。
请编辑 'exclude_files' 列表，添加需要排除的文件名或模式。
如需遵循 .gitignore 规则，请将 'use_gitignore' 设置为 true。
当前默认路径: /current/working/directory
```

### 2. 配置目标文件夹和选项

编辑生成的 `collector_config.json` 文件：

```json
{
    "target_directory": "/your/target/folder/path",
    "exclude_files": [
        "collected_contents.txt",
        "collector_config.json",
        "*.log",
        "temp_*"
    ],
    "use_gitignore": true
}
```

#### 配置项说明：

- **target_directory**：目标文件夹路径
  - 支持绝对路径（推荐）
  - 支持相对路径（相对于脚本所在目录）
  - 路径中的反斜杠建议使用双反斜杠 `\\` 或正斜杠 `/`

- **exclude_files**：需要排除的文件列表（可选）
  - 支持精确文件名匹配（如 `"config.json"`）
  - 支持相对路径匹配（如 `"subfolder/file.txt"`）
  - 支持通配符模式（如 `"*.log"` 匹配所有日志文件）
  - 默认排除 `collected_contents.txt` 和 `collector_config.json` 以避免递归收集

- **use_gitignore**：是否遵循 `.gitignore` 规则（布尔值，默认 `false`）
  - 设置为 `true` 时，脚本会读取目标文件夹中的 `.gitignore` 文件
  - 自动排除匹配 `.gitignore` 规则的文件和目录
  - 与 `exclude_files` 配置项同时生效

### 3. 再次运行

配置完成后再次运行脚本：

```bash
python file_collector.py
```

脚本会显示处理进度：
```
=== 文件内容收集器 ===
目标文件夹: /your/target/folder/path
配置文件排除模式: collected_contents.txt, *.log, temp_*
遵循 .gitignore: 是
正在收集文件列表...
已加载 .gitignore 规则，共 12 条模式
已排除 8 个文件（根据配置文件排除列表）
已排除 23 个文件（根据 .gitignore 规则）
共找到 42 个文件。
输出文件: /your/target/folder/path/collected_contents.txt
正在写入文件内容（可能需要一段时间）...
完成！
```

最终会在目标文件夹内生成 `collected_contents.txt` 文件。

## 输出格式

生成的文本文件格式如下：

```
文件1的相对路径（相对于目标文件夹）
文件1的完整内容
（包含各种特殊字符、换行等）


文件2的相对路径
文件2的完整内容


...
```

## 示例

### 示例 1：基础使用

假设目标文件夹结构如下：
```
project/
├── src/
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_main.py
├── README.md
├── .gitignore
└── collected_contents.txt (输出文件)
```

配置文件：
```json
{
    "target_directory": "/path/to/project",
    "exclude_files": [
        "collected_contents.txt"
    ],
    "use_gitignore": true
}
```

`.gitignore` 文件内容：
```
*.pyc
__pycache__/
*.log
.env
```

生成的 `collected_contents.txt` 将包含 `src/main.py`、`src/utils.py`、`tests/test_main.py`、`README.md` 和 `.gitignore` 的内容，但排除所有 `.pyc` 文件和 `__pycache__` 目录。

### 示例 2：组合使用排除规则

```json
{
    "target_directory": "/path/to/project",
    "exclude_files": [
        "*.tmp",
        "backup/*",
        "secret.key"
    ],
    "use_gitignore": true
}
```

这个配置将：
1. 遵循 `.gitignore` 中的所有规则
2. 额外排除所有 `.tmp` 文件
3. 排除 `backup` 目录下的所有内容
4. 排除 `secret.key` 文件

## .gitignore 支持说明

### 支持的模式

脚本实现了 `.gitignore` 规范的大部分常用功能：

1. **基本模式匹配**
   ```
   *.log          # 所有 .log 文件
   temp/          # temp 目录及其内容
   build/         # build 目录及其内容
   ```

2. **路径匹配**
   ```
   /config.json   # 只匹配根目录的 config.json
   docs/*.txt     # docs 目录下的所有 .txt 文件
   src/**/*.test  # src 下所有 .test 文件
   ```

3. **目录专用匹配**（以 `/` 结尾）
   ```
   node_modules/  # 只匹配目录
   dist/          # 只匹配目录
   ```

### 不支持的功能

为了保持简单和性能，以下 `.gitignore` 功能暂不支持：

- **否定模式**（以 `!` 开头）
  ```
  !important.log  # 不排除 important.log（暂不支持）
  ```

- **方括号字符范围**
  ```
  *.[oa]         # 匹配 .o 或 .a 文件（暂不支持）
  ```

- **多级通配符 `**` 的完整语义**
  - 基本的 `**` 功能可用，但某些边缘情况可能不匹配

### 注意事项

1. **性能考虑**：在处理大型项目时，`.gitignore` 匹配会增加一定的处理时间
2. **编码问题**：`.gitignore` 文件必须为 UTF-8 编码
3. **嵌套 `.gitignore`**：当前版本只读取根目录的 `.gitignore` 文件
4. **规则优先级**：配置文件中的 `exclude_files` 和 `.gitignore` 规则同时生效，任一规则匹配即排除

## 排除模式说明

### 支持的匹配方式

1. **精确文件名匹配**
   ```json
   "exclude_files": ["config.json", "README.md"]
   ```

2. **相对路径匹配**
   ```json
   "exclude_files": ["subfolder/secret.txt", "docs/private.md"]
   ```

3. **通配符匹配**（使用 `*` 匹配任意字符）
   ```json
   "exclude_files": [
       "*.log",           // 所有.log文件
       "test_*.py",       // 所有test_开头的.py文件
       "*.tmp",           // 所有.tmp文件
       "__pycache__/*",   // __pycache__目录下的所有文件
       ".git/*",          // .git目录下的所有文件
       "backup/**/*.bak"  // backup目录下所有子目录中的.bak文件
   ]
   ```

### 通配符规则
- `*` 匹配任意数量的字符（不包括路径分隔符）
- `**` 匹配任意数量的字符（包括路径分隔符）
- 匹配时不区分大小写（取决于文件系统）

## 注意事项

1. **大文件处理**：
   - 输出文件可能非常大（几MB甚至更大），请确保有足够的磁盘空间
   - 脚本采用分块读写（8KB块），内存占用较低

2. **文件编码**：
   - 所有文件按UTF-8编码读取
   - 遇到无法解码的字符时，使用 `replace` 策略替换为 `�`

3. **性能考虑**：
   - 遍历大量文件时可能需要较长时间
   - 建议先在小型文件夹测试
   - 启用 `.gitignore` 支持会增加少量处理时间

4. **权限要求**：
   - 需要有目标文件夹的读取权限
   - 需要在目标文件夹内创建输出文件的写入权限

5. **符号链接**：
   - 脚本会跳过符号链接，只处理常规文件

6. **排除优先级**：
   - 配置文件中的 `exclude_files` 和 `.gitignore` 规则平等
   - 被任何规则匹配的文件都会被排除

## 配置文件说明

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| target_directory | string | 需要收集的目标文件夹路径（绝对或相对路径） | 当前工作目录 |
| exclude_files | array | 需要排除的文件名或模式列表 | `["collected_contents.txt", "collector_config.json"]` |
| use_gitignore | boolean | 是否遵循 .gitignore 规则 | `false` |

## 命令行参数

当前版本不支持命令行参数，所有配置通过配置文件完成。如需直接指定路径，可以修改脚本中的 `main()` 函数，或通过命令行参数扩展。

## 常见问题

### Q: 输出文件在哪里？
A: 输出文件 `collected_contents.txt` 保存在目标文件夹内（与配置文件中的 `target_directory` 相同）。

### Q: 如何跳过某些文件？
A: 有两种方式：
1. 在配置文件中的 `exclude_files` 列表添加需要排除的文件名或通配符模式
2. 在目标文件夹中创建或修改 `.gitignore` 文件，并将 `use_gitignore` 设为 `true`

### Q: .gitignore 和 exclude_files 有什么区别？
A: 
- `exclude_files`：在配置文件中手动指定，适合项目特定的临时排除需求
- `.gitignore`：项目版本控制的一部分，适合长期、团队共享的排除规则
- 两者可以同时使用，互不冲突

### Q: 文件读取失败怎么办？
A: 脚本会在输出文件中写入错误信息，例如 `[读取文件失败: ...]`，不会中断整个处理流程。

### Q: 可以处理二进制文件吗？
A: 脚本按文本模式读取文件，处理二进制文件可能导致输出混乱。建议：
1. 将二进制文件添加到 `exclude_files` 列表中
2. 或在 `.gitignore` 中添加相应规则

### Q: 如何只收集特定类型的文件？
A: 当前版本主要通过排除列表实现反向过滤。如果需要只收集特定类型，可以：
1. 使用通配符排除所有不需要的文件类型
2. 或修改脚本添加白名单功能

### Q: .gitignore 的否定模式（!）为什么不起作用？
A: 为了保持简单和性能，当前版本暂不支持否定模式。如有需要，可以在 `exclude_files` 中手动添加需要的文件。

### Q: 是否支持嵌套的 .gitignore 文件？
A: 当前版本只读取目标文件夹根目录的 `.gitignore` 文件，不支持子目录中的 `.gitignore` 文件。

## 系统要求

- Python 3.6 或更高版本
- 操作系统：Windows / Linux / macOS

## 更新日志

### v1.2.0 (当前版本)
- ✨ 新增 `.gitignore` 支持功能
- ✨ 添加 `use_gitignore` 配置项
- 📈 优化目录遍历性能
- 📊 改进排除统计信息显示

### v1.1.0
- ✨ 新增文件排除功能
- ✨ 支持通配符模式匹配
- 📝 改进配置文件结构

### v1.0.0
- 🎉 初始版本发布
- 基本的文件收集功能
- 配置文件支持

### 主要更新内容：

1. **代码层面**：
   - 添加了 `parse_gitignore()` 函数解析 `.gitignore` 文件
   - 添加了 `match_gitignore_pattern()` 函数实现模式匹配
   - 添加了 `should_exclude_by_gitignore()` 函数判断文件是否应排除
   - 修改了 `load_config()` 和 `collect_files()` 函数支持新配置
   - 在目录遍历时也会过滤目录，提高性能

2. **文档层面**：
   - 添加了 `.gitignore` 支持的功能说明
   - 新增 `.gitignore` 支持说明章节
   - 更新配置文件示例和说明
   - 添加了相关的常见问题解答
   - 更新了版本日志