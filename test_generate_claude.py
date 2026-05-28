import unittest
import os
import tempfile
import sys
from unittest.mock import patch

# 假设主脚本文件名为 generate_claude.py
# 测试时模拟命令行参数
class TestGenerateClaude(unittest.TestCase):
    def setUp(self):
        # 创建临时目录作为模块目录
        self.test_dir = tempfile.mkdtemp()
        # 保存当前工作目录
        self.orig_cwd = os.getcwd()
        os.chdir(self.test_dir)
        # 创建模拟的脚本文件
        self.script_path = os.path.join(self.test_dir, 'generate_claude.py')
        with open(self.script_path, 'w') as f:
            f.write('')

    def tearDown(self):
        os.chdir(self.orig_cwd)
        # 清理临时目录
        import shutil
        shutil.rmtree(self.test_dir)

    @patch('sys.argv', ['generate_claude.py', '--append-context', 'relative/path.txt', '--append-context', '/absolute/path.txt'])
    def test_append_context(self):
        # 执行主函数
        from generate_claude import main
        main()
        # 检查CLAUDE.md是否存在
        claude_path = os.path.join(self.test_dir, 'CLAUDE.md')
        self.assertTrue(os.path.exists(claude_path))
        # 读取内容
        with open(claude_path, 'r') as f:
            content = f.read()
        # 检查是否包含两个路径
        expected_relative = os.path.join(self.test_dir, 'relative/path.txt')
        self.assertIn(expected_relative, content)
        self.assertIn('/absolute/path.txt', content)

if __name__ == '__main__':
    unittest.main()