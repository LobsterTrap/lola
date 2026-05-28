#!/usr/bin/env python3
"""
支持多个 --append-context 值和绝对路径的脚本。
"""
import argparse
from pathlib import Path
import sys

def read_file(path: Path) -> str:
    """读取文件内容，如果文件不存在则报错。"""
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"路径不是文件: {path}")
    try:
        return path.read_text(encoding='utf-8')
    except Exception as e:
        raise IOError(f"读取文件失败: {path}, 错误: {e}")

def resolve_path(path_str: str, module_dir: Path) -> Path:
    """解析路径，如果是绝对路径则直接返回，否则相对于 module_dir 解析。"""
    p = Path(path_str)
    if p.is_absolute():
        return p
    else:
        # 相对于模块目录解析
        return (module_dir / p).resolve()

def generate_claude_md(context_files: list, module_dir: Path) -> str:
    """生成 CLAUDE.md 内容。"""
    lines = []
    lines.append("# Context Files")
    lines.append("")
    for file_path in context_files:
        # 读取内容
        content = read_file(file_path)
        # 写入路径和内容
        lines.append(f"## {file_path}")
        lines.append("```")
        lines.append(content)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="生成 CLAUDE.md 包含多个上下文文件")
    parser.add_argument(
        '--append-context',
        action='append',
        dest='context_files',
        default=[],
        help='要包含的上下文文件路径（可多次使用，支持绝对路径或相对路径）'
    )
    parser.add_argument(
        '--module-dir',
        type=str,
        default='.',
        help='模块目录，用于解析相对路径（默认为当前目录）'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='CLAUDE.md',
        help='输出文件名（默认为 CLAUDE.md）'
    )
    args = parser.parse_args()

    # 解析模块目录
    module_dir = Path(args.module_dir).resolve()
    if not module_dir.is_dir():
        print(f"错误: 模块目录不存在或不是目录: {module_dir}", file=sys.stderr)
        sys.exit(1)

    # 解析所有上下文文件路径
    resolved_files = []
    for path_str in args.context_files:
        try:
            resolved = resolve_path(path_str, module_dir)
            resolved_files.append(resolved)
        except Exception as e:
            print(f"错误: 解析路径失败 '{path_str}': {e}", file=sys.stderr)
            sys.exit(1)

    # 生成内容
    try:
        content = generate_claude_md(resolved_files, module_dir)
    except Exception as e:
        print(f"错误: 生成内容失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 写入文件
    output_path = Path(args.output)
    try:
        output_path.write_text(content, encoding='utf-8')
        print(f"成功生成 {output_path}")
    except Exception as e:
        print(f"错误: 写入文件失败: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()