"""
文件内容收集器 - 递归读取文件夹下所有文件，输出为带路径和内容的TXT文件
使用 pathspec 库完整支持 .gitignore 语法
"""

import os
import sys
import json
import fnmatch
from pathlib import Path
from typing import List, Tuple, Optional

# 配置文件名称
CONFIG_FILE = "collector_config.json"

# 尝试导入 pathspec，如果未安装则提示
try:
    import pathspec
    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False


def get_config_path() -> Path:
    """获取配置文件的绝对路径（与脚本同目录）"""
    return Path(sys.argv[0]).parent / CONFIG_FILE


def load_config() -> Tuple[str, List[str], bool]:
    """从配置文件读取目标文件夹路径、排除列表和gitignore开关，若不存在则生成默认配置"""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                target_dir = config.get("target_directory", "")
                exclude_list = config.get("exclude_files", [])
                use_gitignore = config.get("use_gitignore", False)
                if target_dir and Path(target_dir).exists():
                    return target_dir, exclude_list, use_gitignore
                else:
                    print(f"配置文件中路径无效或不存在: {target_dir}")
                    return "", [], False
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return "", [], False
    else:
        # 生成默认配置（当前工作目录）
        default_dir = os.getcwd()
        config = {
            "target_directory": default_dir,
            "exclude_files": [
                "collected_contents.txt",
                "collector_config.json"
            ],
            "use_gitignore": False
        }
        try:
            with open(config_path, 'w', encoding='utf-8', errors='replace') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"已生成配置文件: {config_path}")
            print(f"请编辑配置文件中的 'target_directory' 字段，指定需要处理的文件夹路径。")
            print(f"请编辑 'exclude_files' 列表，添加需要排除的文件名或模式。")
            print(f"如需遵循 .gitignore 规则，请将 'use_gitignore' 设置为 true。")
            print(f"当前默认路径: {default_dir}")
        except Exception as e:
            print(f"写入配置文件失败: {e}")
        return "", [], False


def load_gitignore_spec(base_dir: Path):
    """
    使用 pathspec 库解析 .gitignore 文件

    Args:
        base_dir: 目标文件夹路径

    Returns:
        pathspec.PathSpec 对象，如果没有 .gitignore 或 pathspec 不可用则返回 None
    """
    if not PATHSPEC_AVAILABLE:
        print("警告: 未安装 pathspec 库，.gitignore 功能将使用简化实现（可能不完整）")
        print("建议执行: pip install pathspec")
        return None

    gitignore_path = base_dir / ".gitignore"
    if not gitignore_path.exists():
        return None

    try:
        with open(gitignore_path, 'r', encoding='utf-8', errors='replace') as f:
            # 使用 gitwildmatch 模式，这是 Git 使用的通配符规则
            spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
        return spec
    except Exception as e:
        print(f"解析 .gitignore 文件失败: {e}")
        return None


def should_exclude_by_gitignore(
    rel_path: Path,
    gitignore_spec,
    is_dir: bool = False
) -> bool:
    """
    检查文件或目录是否应该根据 .gitignore 规则排除

    Args:
        rel_path: 相对于根目录的路径
        gitignore_spec: pathspec.PathSpec 对象
        is_dir: 是否为目录

    Returns:
        True 如果应该排除，否则 False
    """
    if gitignore_spec is None:
        return False

    path_str = rel_path.as_posix()

    # pathspec 的 match_file 方法会正确处理所有 .gitignore 语法
    # 包括 ** 递归通配符、目录专用模式等
    return gitignore_spec.match_file(path_str)


def should_exclude_by_config(
    file_path: Path,
    rel_path: Path,
    exclude_patterns: List[str]
) -> bool:
    """
    判断文件是否应该根据配置文件中的排除列表排除

    Args:
        file_path: 文件的绝对路径
        rel_path: 文件的相对路径
        exclude_patterns: 排除模式列表

    Returns:
        True 如果文件应该被排除，否则 False
    """
    file_name = file_path.name
    rel_path_str = rel_path.as_posix()

    for pattern in exclude_patterns:
        # 精确匹配文件名
        if pattern == file_name:
            return True
        # 精确匹配相对路径
        if pattern == rel_path_str:
            return True
        # 支持通配符匹配
        if '*' in pattern or '?' in pattern:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(rel_path_str, pattern):
                return True

    return False


def collect_files(
    base_dir: Path,
    exclude_patterns: List[str],
    use_gitignore: bool
) -> List[Tuple[Path, Path]]:
    """
    递归收集所有文件，返回列表，每个元素为 (绝对路径, 相对于base_dir的路径)
    跳过目录本身，只收集文件，根据排除列表和gitignore过滤

    Args:
        base_dir: 目标文件夹路径
        exclude_patterns: 配置文件的排除模式列表
        use_gitignore: 是否使用 .gitignore 规则
    """
    files = []
    excluded_by_config = 0
    excluded_by_gitignore = 0
    skipped_dirs_by_gitignore = 0

    # 解析 .gitignore
    gitignore_spec = None
    if use_gitignore:
        gitignore_spec = load_gitignore_spec(base_dir)
        if gitignore_spec:
            print("已加载 .gitignore 规则")
        else:
            if PATHSPEC_AVAILABLE:
                print("未找到 .gitignore 文件或文件为空")

    try:
        # os.walk 性能较好，适合大文件夹
        for root, dirs, filenames in os.walk(base_dir, topdown=True):
            root_path = Path(root)

            # 计算当前目录相对于 base_dir 的路径
            if root_path == base_dir:
                current_rel_path = Path(".")
            else:
                current_rel_path = root_path.relative_to(base_dir)

            # 过滤目录：根据 gitignore 规则跳过某些目录
            # 需要在 topdown=True 时修改 dirs 列表
            if use_gitignore and gitignore_spec:
                filtered_dirs = []
                for d in dirs:
                    dir_path = root_path / d
                    if current_rel_path == Path("."):
                        dir_rel_path = Path(d)
                    else:
                        dir_rel_path = current_rel_path / d

                    # 检查目录本身是否应该被排除
                    if should_exclude_by_gitignore(dir_rel_path, gitignore_spec, is_dir=True):
                        skipped_dirs_by_gitignore += 1
                        continue  # 跳过整个目录

                    filtered_dirs.append(d)
                dirs[:] = filtered_dirs

            # 处理文件
            for fname in filenames:
                file_path = root_path / fname

                # 只处理普通文件，跳过符号链接等
                if not file_path.is_file():
                    continue

                # 计算相对路径
                if current_rel_path == Path("."):
                    rel_path = Path(fname)
                else:
                    rel_path = current_rel_path / fname

                # 检查配置文件排除列表
                if should_exclude_by_config(file_path, rel_path, exclude_patterns):
                    excluded_by_config += 1
                    continue

                # 检查 gitignore 规则
                if use_gitignore and gitignore_spec:
                    if should_exclude_by_gitignore(rel_path, gitignore_spec, is_dir=False):
                        excluded_by_gitignore += 1
                        continue

                files.append((file_path, rel_path))

    except Exception as e:
        print(f"遍历文件夹时出错: {e}")

    if excluded_by_config > 0:
        print(f"已排除 {excluded_by_config} 个文件（根据配置文件排除列表）")
    if excluded_by_gitignore > 0:
        print(f"已排除 {excluded_by_gitignore} 个文件（根据 .gitignore 规则）")
    if skipped_dirs_by_gitignore > 0:
        print(f"已跳过 {skipped_dirs_by_gitignore} 个目录（根据 .gitignore 规则）")

    return files


def write_output(output_path: Path, base_dir: Path, files: List[Tuple[Path, Path]]) -> None:
    """
    将文件列表写入输出文件，格式：
    相对路径\n
    文件内容\n\n\n
    """
    try:
        with open(output_path, 'w', encoding='utf-8', errors='replace') as out:
            for abs_path, rel_path in files:
                # 写入相对路径（使用POSIX风格，统一用/分隔）
                out.write(rel_path.as_posix() + '\n')

                # 读取文件内容并写入
                try:
                    with open(abs_path, 'r', encoding='utf-8', errors='replace') as inf:
                        # 分块读取大文件，避免一次性加载到内存
                        while True:
                            chunk = inf.read(8192)  # 8KB块
                            if not chunk:
                                break
                            out.write(chunk)
                except Exception as e:
                    # 读取失败时记录错误信息
                    out.write(f"[读取文件失败: {e}]\n")

                # 写入三个换行符作为分隔
                out.write('\n\n\n')
    except Exception as e:
        print(f"写入输出文件失败: {e}")


def main():
    print("=== 文件内容收集器 ===")

    # 检查 pathspec 是否可用
    if not PATHSPEC_AVAILABLE:
        print("提示: 安装 pathspec 库可获得完整的 .gitignore 支持")
        print("      pip install pathspec")
        print()

    # 1. 获取目标文件夹、排除列表和gitignore设置
    target_dir_str, exclude_list, use_gitignore = load_config()
    if not target_dir_str:
        print("无法确定目标文件夹，请检查配置文件后重新运行。")
        sys.exit(1)

    target_dir = Path(target_dir_str).resolve()
    if not target_dir.is_dir():
        print(f"目标文件夹不存在或不是目录: {target_dir}")
        sys.exit(1)

    print(f"目标文件夹: {target_dir}")
    if exclude_list:
        print(f"配置文件排除模式: {', '.join(exclude_list)}")
    print(f"遵循 .gitignore: {'是' if use_gitignore else '否'}")

    # 2. 递归收集文件列表
    print("正在收集文件列表...")
    files = collect_files(target_dir, exclude_list, use_gitignore)
    print(f"共找到 {len(files)} 个文件。")

    if not files:
        print("未找到任何文件。")
        sys.exit(0)

    # 3. 确定输出文件路径（在目标文件夹内）
    output_file = target_dir / "collected_contents.txt"
    print(f"输出文件: {output_file}")

    # 4. 写入内容
    print("正在写入文件内容（可能需要一段时间）...")
    write_output(output_file, target_dir, files)

    print("完成！")


if __name__ == "__main__":
    main()