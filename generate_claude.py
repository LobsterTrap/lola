import os
import click

@click.command()
@click.option('--module-dir', default='.', help='模块目录路径')
@click.option('--append-context', multiple=True, type=str, help='要附加的上下文文件路径，可以是相对路径（相对于模块目录）或绝对路径')
def generate_claude(module_dir, append_context):
    """生成 CLAUDE.md 文件，包含多个上下文引用。"""
    module_dir = os.path.abspath(module_dir)
    output_lines = []

    for ctx_path in append_context:
        if os.path.isabs(ctx_path):
            # 绝对路径
            abs_path = ctx_path
            if not os.path.exists(abs_path):
                click.echo(f"警告：绝对路径文件不存在: {abs_path}", err=True)
                continue
            output_lines.append(f'Read the per-project context from {abs_path}')
        else:
            # 相对路径，相对于模块目录
            rel_path = os.path.join(module_dir, ctx_path)
            abs_rel_path = os.path.abspath(rel_path)
            if not os.path.exists(abs_rel_path):
                click.echo(f"警告：相对路径文件不存在: {abs_rel_path}", err=True)
                continue
            # 输出相对路径（相对于模块目录）
            output_lines.append(f'Read the module context from .lola/modules/{os.path.basename(module_dir)}/{ctx_path}')

    if not output_lines:
        click.echo("没有有效的上下文文件，生成空的 CLAUDE.md。")

    output_content = '\n'.join(output_lines)
    with open('CLAUDE.md', 'w', encoding='utf-8') as f:
        f.write(output_content)
    click.echo(f"CLAUDE.md 已生成，包含 {len(output_lines)} 个上下文引用。")

if __name__ == '__main__':
    generate_claude()