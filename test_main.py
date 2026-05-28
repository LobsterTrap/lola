#!/usr/bin/env python3
"""
测试脚本：测试多个 --append-context 值和绝对路径的功能。
"""
import subprocess
import tempfile
import os
from pathlib import Path

def test_multiple_contexts():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        file1 = Path(tmpdir) / "file1.txt"
        file1.write_text("Content of file1")
        file2 = Path(tmpdir) / "subdir" / "file2.txt"
        file2.parent.mkdir(parents=True, exist_ok=True)
        file2.write_text("Content of file2")
        # 绝对路径文件
        abs_file = Path(tempfile.gettempdir()) / "abs_file.txt"
        abs_file.write_text("Absolute content")

        # 运行脚本
        cmd = [
            "python", "main.py",
            "--append-context", str(file1),
            "--append-context", "subdir/file2.txt",
            "--append-context", str(abs_file),
            "--module-dir", tmpdir,
            "--output", os.path.join(tmpdir, "CLAUDE.md")
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"脚本运行失败: {result.stderr}")
            return False

        # 验证输出
        output_path = Path(tmpdir) / "CLAUDE.md"
        if not output_path.exists():
            print("CLAUDE.md 未生成")
            return False

        content = output_path.read_text()
        # 检查是否包含所有文件
        if "file1.txt" not in content or "file2.txt" not in content or "abs_file.txt" not in content:
            print("缺少某些文件内容")
            return False
        if "Content of file1" not in content or "Content of file2" not in content or "Absolute content" not in content:
            print("文件内容不正确")
            return False

        print("测试通过！")
        return True

if __name__ == '__main__':
    test_multiple_contexts()