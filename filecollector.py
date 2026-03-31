"""
文件内容收集器 - 递归读取文件夹下所有文件，输出为带路径和内容的TXT文件
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Tuple

# 配置文件名称
CONFIG_FILE = "collector_config.json"


def get_config_path() -> Path:
    """获取配置文件的绝对路径（与脚本同目录）"""
    return Path(sys.argv[0]).parent / CONFIG_FILE


def load_config() -> str:
    """从配置文件读取目标文件夹路径，若不存在则生成默认配置"""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                target_dir = config.get("target_directory", "")
                if target_dir and Path(target_dir).exists():
                    return target_dir
                else:
                    print(f"配置文件中路径无效或不存在: {target_dir}")
                    return ""
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return ""
    else:
        # 生成默认配置（当前工作目录）
        default_dir = os.getcwd()
        config = {"target_directory": default_dir}
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            print(f"已生成配置文件: {config_path}")
            print(f"请编辑配置文件中的 'target_directory' 字段，指定需要处理的文件夹路径。")
            print(f"当前默认路径: {default_dir}")
        except Exception as e:
            print(f"写入配置文件失败: {e}")
        return ""


def collect_files(base_dir: Path) -> List[Tuple[Path, Path]]:
    """
    递归收集所有文件，返回列表，每个元素为 (绝对路径, 相对于base_dir的路径)
    跳过目录本身，只收集文件
    """
    files = []
    try:
        # os.walk 性能较好，适合大文件夹
        for root, dirs, filenames in os.walk(base_dir):
            # 跳过隐藏文件夹? 默认不跳过，可根据需要修改
            root_path = Path(root)
            for fname in filenames:
                file_path = root_path / fname
                # 只处理文件，不处理链接等
                if file_path.is_file():
                    rel_path = file_path.relative_to(base_dir)
                    files.append((file_path, rel_path))
    except Exception as e:
        print(f"遍历文件夹时出错: {e}")
    return files


def write_output(output_path: Path, base_dir: Path, files: List[Tuple[Path, Path]]) -> None:
    """
    将文件列表写入输出文件，格式：
    相对路径\n
    文件内容\n\n\n
    """
    # 使用缓冲区写入，提高大文件性能
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

    # 1. 获取目标文件夹
    target_dir_str = load_config()
    if not target_dir_str:
        print("无法确定目标文件夹，请检查配置文件后重新运行。")
        sys.exit(1)

    target_dir = Path(target_dir_str).resolve()
    if not target_dir.is_dir():
        print(f"目标文件夹不存在或不是目录: {target_dir}")
        sys.exit(1)

    print(f"目标文件夹: {target_dir}")

    # 2. 递归收集文件列表
    print("正在收集文件列表...")
    files = collect_files(target_dir)
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