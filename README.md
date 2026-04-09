# 文件内容收集器 (File Content Collector)

一个Python脚本，用于递归读取指定文件夹下的所有文件，并将每个文件的相对路径和完整内容收集到一个文本文件中。

## 功能特点

- 📁 **递归遍历**：自动处理嵌套文件夹中的所有文件
- 🔧 **配置文件支持**：通过JSON配置文件指定目标文件夹路径和排除列表
- 🚫 **文件排除功能**：支持精确匹配和通配符模式排除指定文件
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
当前默认路径: /current/working/directory
```

### 2. 配置目标文件夹和排除列表

编辑生成的 `collector_config.json` 文件：

```json
{
    "target_directory": "/your/target/folder/path",
    "exclude_files": [
        "collected_contents.txt",
        "collector_config.json",
        "*.log",
        "temp_*",
        "__pycache__/*",
        ".git/*"
    ]
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

### 3. 再次运行

配置完成后再次运行脚本：

```bash
python file_collector.py
```

脚本会显示处理进度：
```
=== 文件内容收集器 ===
目标文件夹: /your/target/folder/path
排除模式: collected_contents.txt, *.log, temp_*
正在收集文件列表...
已排除 15 个文件（根据排除列表）
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

假设目标文件夹结构如下：
```
target_folder/
├── file1.txt
├── app.log
├── temp_data.tmp
├── subfolder/
│   ├── file2.py
│   └── debug.log
├── config.json
└── collected_contents.txt (输出文件)
```

配置文件：
```json
{
    "target_directory": "/path/to/target_folder",
    "exclude_files": [
        "*.log",
        "*.tmp",
        "collected_contents.txt"
    ]
}
```

生成的 `collected_contents.txt` 内容可能为：
```
file1.txt
这是file1的内容
第一行
第二行


subfolder/file2.py
def hello():
    print("Hello, World!")


config.json
{"name": "example", "version": "1.0"}
```

注意：所有 `.log` 和 `.tmp` 文件以及输出文件本身都被排除了。

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
- `**` 匹配任意数量的字符（包括路径分隔符，需要代码支持）
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

4. **权限要求**：
   - 需要有目标文件夹的读取权限
   - 需要在目标文件夹内创建输出文件的写入权限

5. **符号链接**：
   - 脚本会跳过符号链接，只处理常规文件

6. **排除列表优先级**：
   - 排除列表中的模式优先于其他所有规则
   - 被排除的文件不会被读取和处理

## 配置文件说明

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
| target_directory | string | 需要收集的目标文件夹路径（绝对或相对路径） | 是 |
| exclude_files | array | 需要排除的文件名或模式列表 | 否 |

## 命令行参数

当前版本不支持命令行参数，所有配置通过配置文件完成。如需直接指定路径，可以修改脚本中的 `main()` 函数，或通过命令行参数扩展。

## 常见问题

### Q: 输出文件在哪里？
A: 输出文件 `collected_contents.txt` 保存在目标文件夹内（与配置文件中的 `target_directory` 相同）。

### Q: 如何跳过某些文件？
A: 在配置文件中的 `exclude_files` 列表添加需要排除的文件名或通配符模式。例如：
- 跳过所有日志文件：添加 `"*.log"`
- 跳过特定文件：添加 `"secret.txt"`
- 跳过整个目录：添加 `"temp/*"`

### Q: 文件读取失败怎么办？
A: 脚本会在输出文件中写入错误信息，例如 `[读取文件失败: ...]`，不会中断整个处理流程。

### Q: 可以处理二进制文件吗？
A: 脚本按文本模式读取文件，处理二进制文件可能导致输出混乱。建议将二进制文件添加到排除列表中。

### Q: 如何只收集特定类型的文件？
A: 当前版本主要通过排除列表实现反向过滤。如果需要只收集特定类型，可以：
1. 使用通配符排除所有不需要的文件类型
2. 或修改脚本添加白名单功能

### Q: 排除列表中的通配符支持哪些？
A: 支持使用 `*` 匹配任意字符。如果需要更复杂的模式匹配，可以修改脚本中的 `should_exclude()` 函数。

## 系统要求

- Python 3.6 或更高版本
- 操作系统：Windows / Linux / macOS

## 更新日志

### v1.1.0 (当前版本)
- ✨ 新增文件排除功能
- ✨ 支持通配符模式匹配
- 📝 改进配置文件结构
- 🐛 修复可能出现的路径问题

### v1.0.0
- 🎉 初始版本发布
- 基本的文件收集功能
- 配置文件支持

### 主要更新内容：

1. **功能特点**：添加了文件排除功能的说明
2. **配置文件**：更新了JSON示例，包含 `exclude_files` 字段
3. **排除模式说明**：新增专门章节详细解释排除功能的各种用法
4. **示例更新**：展示了实际使用排除功能的场景
5. **配置文件说明表格**：添加了 `exclude_files` 字段的说明
6. **常见问题**：更新了关于文件排除的问答
7. **更新日志**：添加了版本历史记录