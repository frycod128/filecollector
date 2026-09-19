"""
文件内容收集器 - 递归读取文件夹下所有文件，输出为带路径和内容的TXT文件
使用 pathspec 库完整支持 .gitignore 语法
"""

import os
import sys
import json
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import List, Tuple, Optional, Sequence

# 配置文件名称
CONFIG_FILE = "collector_config.json"

# 用于判断"整个目录都会被排除"的探针文件名
PROBE_NAME = "__file_collector_probe__"

# 尝试导入 pathspec，如果未安装则提示
try:
    import pathspec
    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False

try:
    from pathspec.util import normalize_file as _normalize_file
except Exception:  # 极老版本没有该工具函数时的兜底
    def _normalize_file(file, separators=None) -> str:
        """把路径统一成 POSIX 风格并去掉开头的 / 与 ./"""
        text = str(file).replace("\\", "/")
        while text.startswith("./"):
            text = text[2:]
        if text.startswith("/"):
            text = text[1:]
        return text


@dataclass
class Config:
    """运行配置"""
    target_directory: Path
    exclude_patterns: List[str]
    use_gitignore: bool


def get_config_path() -> Path:
    """获取配置文件的绝对路径（与脚本同目录）"""
    try:
        script_dir = Path(__file__).resolve().parent
    except NameError:  # pragma: no cover - 交互式执行等特殊情况
        script_dir = Path(sys.argv[0]).resolve().parent
    return script_dir / CONFIG_FILE


def load_config() -> Optional[Config]:
    """
    从配置文件读取配置，失败时打印具体原因并返回 None。

    配置文件不存在时会生成一份默认配置（目标目录为当前工作目录）并返回 None，
    提示用户编辑后重新运行。
    """
    config_path = get_config_path()

    if not config_path.exists():
        default_config = {
            "target_directory": str(Path.cwd()),
            "exclude_files": [
                "collected_contents.txt",
                "collector_config.json",
            ],
            "use_gitignore": False,
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            print(f"写入配置文件失败: {config_path} ({e})")
            return None

        print(f"已生成配置文件: {config_path}")
        print("请编辑其中的 target_directory（目标文件夹）后重新运行。")
        print("exclude_files 为排除模式列表，use_gitignore 决定是否遵循 .gitignore。")
        return None

    try:
        with open(config_path, "r", encoding="utf-8", errors="replace") as f:
            raw_config = json.load(f)
    except OSError as e:
        print(f"读取配置文件失败: {config_path} ({e})")
        return None
    except json.JSONDecodeError as e:
        print(f"配置文件不是合法的 JSON: {config_path} ({e})")
        return None

    if not isinstance(raw_config, dict):
        print(f"配置文件格式错误: 顶层应为 JSON 对象 ({config_path})")
        return None

    # 目标目录
    target_raw = raw_config.get("target_directory")
    if not isinstance(target_raw, str) or not target_raw.strip():
        print("配置项 target_directory 无效: 需要填写目标文件夹路径。")
        return None

    target_dir = Path(target_raw).expanduser()
    if not target_dir.exists():
        print(f"配置项 target_directory 指向的路径不存在: {target_dir}")
        return None
    if not target_dir.is_dir():
        print(f"配置项 target_directory 不是文件夹: {target_dir}")
        return None
    target_dir = target_dir.resolve()

    # 排除模式列表
    exclude_raw = raw_config.get("exclude_files")
    if exclude_raw is None:
        exclude_raw = []
    elif not isinstance(exclude_raw, list):
        print("配置项 exclude_files 应为字符串列表，已按空列表处理。")
        exclude_raw = []
    exclude_patterns = [str(p).strip() for p in exclude_raw if str(p).strip()]

    # 是否遵循 .gitignore
    gitignore_raw = raw_config.get("use_gitignore", False)
    if isinstance(gitignore_raw, bool):
        use_gitignore = gitignore_raw
    else:
        print(f"配置项 use_gitignore 应为 true/false，已按 false 处理: {gitignore_raw!r}")
        use_gitignore = False

    return Config(
        target_directory=target_dir,
        exclude_patterns=exclude_patterns,
        use_gitignore=use_gitignore,
    )


def to_git_pattern(pattern: str) -> str:
    """
    把配置文件里的排除模式转换成 Git 通配模式。

    规则:
    - 反斜杠统一成 /，便于在 Windows 上书写
    - 以 / 开头: 相对目标目录定位（与 Git 一致），如 /build 只匹配根目录下的 build
    - 其余含 / 的模式: 在任意层级匹配，如 node_modules/* 匹配任何层级的 node_modules
    - 不含 / 的模式: 本身就在任意层级匹配（Git 语义），如 *.log、temp_*
    - 以 ! 开头: 取反，重新包含此前被排除的文件
    - 以 / 结尾: 只匹配目录
    """
    text = pattern.strip().replace("\\", "/")
    if not text:
        return ""

    negation = ""
    if text.startswith("!"):
        negation, text = "!", text[1:].lstrip()
    elif text.startswith("\\!"):
        # \! 表示文件名真的以 ! 开头
        text = text[1:]

    if not text:
        return ""
    if text.startswith("/") or text.startswith("**"):
        return negation + text
    if "/" in text.rstrip("/"):
        return negation + "**/" + text
    return negation + text


def build_spec(lines: Sequence[str]):
    """把若干行 Git 模式编译成 PathSpec，失败或为空时返回 None"""
    if not lines or not PATHSPEC_AVAILABLE:
        return None

    try:
        if hasattr(pathspec, "GitIgnoreSpec"):
            # pathspec >= 0.10 的推荐用法，行为与 Git 一致
            spec = pathspec.GitIgnoreSpec.from_lines(list(lines))
        else:  # pragma: no cover - 老版本兜底
            spec = pathspec.PathSpec.from_lines("gitwildmatch", list(lines))
    except Exception as e:
        print(f"解析排除规则失败: {e}")
        return None

    return spec if spec.patterns else None


class PatternMatcher:
    """
    排除规则匹配器，封装 Git 通配匹配与"目录能否整棵跳过"的判断。

    match() 的返回值:
    - True: 命中排除规则
    - False: 命中 ! 取反规则（明确保留）
    - None: 没有规则命中
    """

    def __init__(self, spec, label: str = "排除规则"):
        self.label = label
        self.spec = spec
        # 有 ! 取反规则时不做探针剪枝，避免误剪掉被重新包含的文件
        self.can_probe_prune = spec is not None and not any(
            getattr(pattern, "include", True) is False for pattern in spec.patterns
        )

    @classmethod
    def from_patterns(cls, patterns: Sequence[str], label: str = "排除规则"):
        """用配置文件里的模式列表构建匹配器"""
        git_patterns = [to_git_pattern(p) for p in patterns]
        git_patterns = [p for p in git_patterns if p]
        return cls(build_spec(git_patterns), label)

    def match(self, rel_posix: str, is_dir: bool = False) -> Optional[bool]:
        """
        判断相对路径是否被排除。

        is_dir 为 True 时补上尾斜杠，这样才能命中 Git 的"仅目录"规则（如 build/）。
        """
        if self.spec is None or not rel_posix:
            return None

        path = rel_posix + "/" if is_dir else rel_posix
        norm_path = _normalize_file(path)

        try:
            # 逆序扫描: Git 是"最后一条匹配的规则生效"
            for pattern in reversed(self.spec.patterns):
                if getattr(pattern, "include", None) is None:
                    continue
                if pattern.match_file(norm_path) is not None:
                    return bool(pattern.include)
        except Exception as e:
            print(f"匹配规则出错（{self.label} / {rel_posix}）: {e}")
            return None

        return None

    def should_prune_dir(self, rel_posix: str) -> Optional[bool]:
        """
        判断目录能否整棵跳过。

        先看目录本身是否命中规则；若没有，再用一个假想的子文件试探
        （node_modules/* 这类模式不匹配目录本身，但会排除它下面的所有内容）。
        """
        decision = self.match(rel_posix, is_dir=True)
        if decision is not None:
            return decision
        if self.can_probe_prune:
            return self.match(f"{rel_posix}/{PROBE_NAME}", is_dir=False)
        return None


class SimplePatternMatcher:
    """
    未安装 pathspec 时的简化匹配器。

    支持 * ? [] 通配、任意层级匹配与 ! 取反，但不支持 ** 与目录专用等完整 Git 语法。
    """

    def __init__(self, patterns: Sequence[str]):
        self.rules: List[Tuple[bool, str]] = []
        for pattern in patterns:
            text = pattern.strip().replace("\\", "/")
            if not text:
                continue
            negate = text.startswith("!")
            if negate:
                text = text[1:].lstrip()
            text = text.lstrip("/")
            if text:
                self.rules.append((negate, text))
        self.can_probe_prune = bool(self.rules) and not any(negate for negate, _ in self.rules)

    @classmethod
    def from_patterns(cls, patterns: Sequence[str], label: str = "排除规则"):
        return cls(patterns)

    @staticmethod
    def _candidates(rel_posix: str) -> List[str]:
        """相对路径本身以及它的各级后缀，用于实现任意层级匹配"""
        parts = [p for p in rel_posix.split("/") if p]
        return ["/".join(parts[i:]) for i in range(len(parts))]

    def match(self, rel_posix: str, is_dir: bool = False) -> Optional[bool]:
        if not rel_posix:
            return None

        candidates = self._candidates(rel_posix)
        decision = None

        for negate, raw in self.rules:
            dir_only = raw.endswith("/")
            pattern = raw.rstrip("/")
            if not pattern:
                continue

            hit = any(fnmatchcase(c, pattern) for c in candidates)
            if not hit and dir_only:
                # 目录规则: 目录自身及其内部所有内容都算命中
                hit = any(fnmatchcase(c + "/", pattern) for c in candidates)
                hit = hit or any(f"/{pattern}/" in f"/{c}/" for c in candidates)
            if hit:
                decision = not negate

        return decision

    def should_prune_dir(self, rel_posix: str) -> Optional[bool]:
        decision = self.match(rel_posix, is_dir=True)
        if decision is not None:
            return decision
        if self.can_probe_prune and self.match(f"{rel_posix}/{PROBE_NAME}", is_dir=False):
            return True
        return None


def build_matcher(patterns: Sequence[str], label: str = "排除规则"):
    """构建排除规则匹配器（优先 pathspec，未安装时使用简化实现）"""
    if not patterns:
        return None
    if PATHSPEC_AVAILABLE:
        matcher = PatternMatcher.from_patterns(patterns, label)
        return matcher if matcher.spec is not None else None
    print(f"警告: 未安装 pathspec 库，{label} 将使用简化匹配（不支持 ** 与目录专用语法）")
    print("建议执行: pip install pathspec")
    return SimplePatternMatcher.from_patterns(patterns, label)


def load_gitignore_spec(directory: Path):
    """读取指定目录下的 .gitignore 并编译成匹配器，没有则返回 None"""
    gitignore_path = directory / ".gitignore"
    if not gitignore_path.is_file():
        return None

    try:
        with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        print(f"读取 .gitignore 失败: {gitignore_path} ({e})")
        return None

    matcher = PatternMatcher(build_spec(lines), str(gitignore_path))
    return matcher if matcher.spec is not None else None


def is_within(rel_posix: str, base_posix: str) -> bool:
    """判断相对路径是否位于某个基准目录内（含基准目录自身）"""
    if not base_posix:
        return True
    return rel_posix == base_posix or rel_posix.startswith(base_posix + "/")


def match_gitignore_stack(
    stack: Sequence[Tuple[str, PatternMatcher]],
    rel_posix: str,
    is_dir: bool = False
) -> Optional[bool]:
    """
    按 Git 的层级规则匹配: 越靠近文件的 .gitignore 优先级越高。

    stack 中的元素为 (基准目录相对路径, 匹配器)，按由浅到深排列。
    """
    for base_posix, matcher in reversed(stack):
        sub_path = rel_posix if not base_posix else rel_posix[len(base_posix) + 1:]
        if not sub_path:
            continue
        decision = (
            matcher.should_prune_dir(sub_path)
            if is_dir
            else matcher.match(sub_path, is_dir=False)
        )
        if decision is not None:
            return decision
    return None


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
    pruned_dirs_by_config = 0
    excluded_by_gitignore = 0
    skipped_dirs_by_gitignore = 0
    gitignore_files = 0
    skipped_symlinks = 0
    skipped_not_regular = 0
    matcher = build_matcher(exclude_patterns, "exclude_files")

    # .gitignore 规则栈: (基准目录相对路径, 匹配器)，随遍历深度出入栈
    gitignore_stack: List[Tuple[str, PatternMatcher]] = []

    try:
        # os.walk 性能较好，适合大文件夹
        for root, dirs, filenames in os.walk(base_dir, topdown=True, followlinks=False):
            root_path = Path(root)

            # 计算当前目录相对于 base_dir 的路径
            if root_path == base_dir:
                current_rel_path = Path(".")
            else:
                current_rel_path = root_path.relative_to(base_dir)
            current_rel_posix = "" if current_rel_path == Path(".") else current_rel_path.as_posix()

            # 排序保证输出顺序稳定（Windows 下大小写不敏感）
            dirs.sort(key=str.casefold)
            filenames.sort(key=str.casefold)

            # 先弹出已离开当前分支的规则，再压入当前目录的 .gitignore
            while gitignore_stack and not is_within(current_rel_posix, gitignore_stack[-1][0]):
                gitignore_stack.pop()
            if use_gitignore:
                gitignore_matcher = load_gitignore_spec(root_path)
                if gitignore_matcher is not None:
                    gitignore_stack.append((current_rel_posix, gitignore_matcher))
                    gitignore_files += 1

            # 过滤目录：命中排除规则时整棵跳过，可以显著减少遍历量
            # 需要在 topdown=True 时修改 dirs 列表
            filtered_dirs = []
            for d in dirs:
                dir_rel_posix = f"{current_rel_posix}/{d}" if current_rel_posix else d

                # 符号链接目录不跟随，避免循环与收集到目标目录之外
                if (root_path / d).is_symlink():
                    skipped_symlinks += 1
                    continue

                # 检查配置文件排除列表
                if matcher is not None and matcher.should_prune_dir(dir_rel_posix):
                    pruned_dirs_by_config += 1
                    continue  # 跳过整个目录

                # 检查 gitignore 规则
                if use_gitignore and gitignore_stack:
                    if match_gitignore_stack(gitignore_stack, dir_rel_posix, is_dir=True):
                        skipped_dirs_by_gitignore += 1
                        continue  # 跳过整个目录

                filtered_dirs.append(d)
            dirs[:] = filtered_dirs

            # 处理文件
            for fname in filenames:
                file_path = root_path / fname

                # 只处理普通文件: 跳过符号链接、目录、设备文件等
                if file_path.is_symlink():
                    skipped_symlinks += 1
                    continue
                if not file_path.is_file():
                    skipped_not_regular += 1
                    continue

                # 计算相对路径
                if current_rel_path == Path("."):
                    rel_path = Path(fname)
                else:
                    rel_path = current_rel_path / fname

                # 检查配置文件排除列表
                if matcher is not None and matcher.match(rel_path.as_posix(), is_dir=False):
                    excluded_by_config += 1
                    continue

                # 检查 gitignore 规则
                if use_gitignore and gitignore_stack:
                    if match_gitignore_stack(gitignore_stack, rel_path.as_posix(), is_dir=False):
                        excluded_by_gitignore += 1
                        continue

                files.append((file_path, rel_path))

    except Exception as e:
        print(f"遍历文件夹时出错: {e}")

    if excluded_by_config > 0:
        print(f"已排除 {excluded_by_config} 个文件（根据配置文件排除列表）")
    if pruned_dirs_by_config > 0:
        print(f"已跳过 {pruned_dirs_by_config} 个目录（根据配置文件排除列表）")
    if excluded_by_gitignore > 0:
        print(f"已排除 {excluded_by_gitignore} 个文件（根据 .gitignore 规则）")
    if skipped_dirs_by_gitignore > 0:
        print(f"已跳过 {skipped_dirs_by_gitignore} 个目录（根据 .gitignore 规则）")
    if use_gitignore:
        if gitignore_files > 0:
            print(f"已加载 {gitignore_files} 个 .gitignore 文件")
        elif PATHSPEC_AVAILABLE:
            print("未找到 .gitignore 文件或文件为空")
    if skipped_symlinks > 0:
        print(f"已跳过 {skipped_symlinks} 个符号链接")

    return files


def write_output(output_path: Path, base_dir: Path, files: List[Tuple[Path, Path]]) -> None:
    """
    将文件列表写入输出文件，格式：
    相对路径\n
    文件内容\n\n\n
    """
    try:
        # newline="\n" 让输出换行符与平台无关，便于 diff 与跨平台读取
        with open(output_path, "w", encoding="utf-8", errors="replace", newline="\n") as out:
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


def main() -> int:
    print("=== 文件内容收集器 ===")

    # 检查 pathspec 是否可用
    if not PATHSPEC_AVAILABLE:
        print("提示: 安装 pathspec 库可获得完整的 .gitignore 支持")
        print("      pip install pathspec")
        print()

    # 1. 获取配置（目标文件夹、排除列表、gitignore 开关）
    config = load_config()
    if config is None:
        return 1

    target_dir = config.target_directory
    print(f"目标文件夹: {target_dir}")
    if config.exclude_patterns:
        print(f"配置文件排除模式: {', '.join(config.exclude_patterns)}")
    print(f"遵循 .gitignore: {'是' if config.use_gitignore else '否'}")

    # 2. 递归收集文件列表
    print("正在收集文件列表...")
    files = collect_files(target_dir, config.exclude_patterns, config.use_gitignore)
    print(f"共找到 {len(files)} 个文件。")

    if not files:
        print("未找到任何文件。")
        return 0

    # 3. 确定输出文件路径（在目标文件夹内）
    output_file = target_dir / "collected_contents.txt"
    print(f"输出文件: {output_file}")

    # 4. 写入内容
    print("正在写入文件内容（可能需要一段时间）...")
    write_output(output_file, target_dir, files)

    print("完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
