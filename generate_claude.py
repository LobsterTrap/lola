import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description='Generate CLAUDE.md with context references.')
    parser.add_argument('--append-context', action='append', default=[],
                        help='Path to context file. Can be absolute or relative to module directory.')
    args = parser.parse_args()

    # Get the module directory (directory where the script is located)
    module_dir = os.path.dirname(os.path.abspath(__file__))

    # Process each provided path
    context_paths = []
    for path in args.append_context:
        if path.startswith('/'):
            # Absolute path
            context_paths.append(path)
        else:
            # Relative to module directory
            abs_path = os.path.join(module_dir, path)
            context_paths.append(abs_path)

    # Generate CLAUDE.md content
    lines = []
    lines.append('# Context References\n')
    for i, cp in enumerate(context_paths, 1):
        lines.append(f'{i}. {cp}\n')

    # Write to CLAUDE.md
    output_path = os.path.join(module_dir, 'CLAUDE.md')
    try:
        with open(output_path, 'w') as f:
            f.writelines(lines)
        print(f'Successfully generated {output_path}')
    except IOError as e:
        print(f'Error writing to {output_path}: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()