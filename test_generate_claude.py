import os
import tempfile
import subprocess
import sys

def test_generate_claude():
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建模块目录和文件
        module_dir = os.path.join(tmpdir, 'my-plugin')
        os.makedirs(module_dir)
        # 创建相对路径文件
        rel_file = os.path.join(module_dir, 'plugin', 'AGENTS.md')
        os.makedirs(os.path.dirname(rel_file))
        with open(rel_file, 'w') as f:
            f.write('relative context')
        # 创建绝对路径文件
        abs_file = os.path.join(tmpdir, 'repo-a', 'AGENTS.md')
        os.makedirs(os.path.dirname(abs_file))
        with open(abs_file, 'w') as f:
            f.write('absolute context')

        # 运行脚本
        script_path = os.path.join(os.path.dirname(__file__), 'generate_claude.py')
        result = subprocess.run([
            sys.executable, script_path,
            '--module-dir', module_dir,
            '--append-context', 'plugin/AGENTS.md',
            '--append-context', abs_file
        ], capture_output=True, text=True, cwd=tmpdir)

        # 检查输出
        assert result.returncode == 0, f"脚本执行失败: {result.stderr}"
        # 检查生成的CLAUDE.md
        claude_path = os.path.join(tmpdir, 'CLAUDE.md')
        assert os.path.exists(claude_path), "CLAUDE.md 未生成"
        with open(claude_path, 'r') as f:
            content = f.read()
        expected_relative = f'Read the module context from .lola/modules/my-plugin/plugin/AGENTS.md'
        expected_absolute = f'Read the per-project context from {abs_file}'
        assert expected_relative in content, f"缺少相对路径引用: {content}"
        assert expected_absolute in content, f"缺少绝对路径引用: {content}"
        print("测试通过！")

if __name__ == '__main__':
    test_generate_claude()