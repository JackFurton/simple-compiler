#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.compiler import Compiler, CompilerError


def repl():
    print("=" * 50)
    print("Simple Bytecode Compiler & Virtual Machine REPL")
    print("Version 0.2.0")
    print("=" * 50)
    print("Enter code (e.g. let x = 5; fn inc(n) { return n + 1; } print inc(x);)")
    print("Commands:")
    print("  vars     - display current global variables")
    print("  clear    - clear all global variables")
    print("  exit/quit- exit the REPL")
    print("-" * 50)

    compiler = Compiler()

    while True:
        try:
            line = input(">>> ").strip()

            if not line:
                continue

            if line.lower() in ('quit', 'exit'):
                print("Goodbye!")
                break

            if line.lower() == 'vars':
                variables = compiler.get_variables()
                if variables:
                    for name, value in variables.items():
                        print(f"  {name} = {value}")
                else:
                    print("  No variables defined")
                continue

            if line.lower() == 'clear':
                compiler.clear_variables()
                print("  Variables cleared")
                continue

            compiler.run(line)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
        except CompilerError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


def run_file(filename: str, compiler: Compiler):
    try:
        return compiler.run_file(filename)
    except CompilerError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def show_tokens(filename: str):
    compiler = Compiler()
    try:
        with open(filename, 'r') as f:
            source = f.read()

        print(f"Tokens for {filename}:")
        print("-" * 40)
        compiler.debug_tokens(source)

    except FileNotFoundError:
        print(f"Error: File not found: {filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def show_ast(filename: str):
    compiler = Compiler()
    try:
        with open(filename, 'r') as f:
            source = f.read()

        print(f"AST for {filename}:")
        print("-" * 40)
        compiler.debug_ast(source)

    except FileNotFoundError:
        print(f"Error: File not found: {filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def show_bytecode(filename: str):
    compiler = Compiler()
    try:
        with open(filename, 'r') as f:
            source = f.read()

        print(f"Bytecode for {filename}:")
        print("-" * 40)
        compiler.debug_bytecode(source)

    except FileNotFoundError:
        print(f"Error: File not found: {filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def analyze_file(filename: str):
    compiler = Compiler()
    try:
        with open(filename, 'r') as f:
            source = f.read()

        analysis = compiler.analyze(source)

        print(f"Analysis for {filename}:")
        print("-" * 40)
        print(f"Token count: {analysis['token_count']}")
        print(f"AST depth: {analysis['ast_depth']}")
        print(f"Operations: {analysis['operations_count']}")
        print(f"Variables defined: {sorted(analysis['variables_defined'])}")
        print(f"Variables used: {sorted(analysis['variables_used'])}")

    except FileNotFoundError:
        print(f"Error: File not found: {filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Simple Bytecode Compiler & Virtual Machine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start interactive REPL
  python main.py program.lang       # Run a program file with the VM
  python main.py --disasm prog.lang # Disassemble bytecode
  python main.py --tokens prog.lang # Show tokens for file
  python main.py --ast prog.lang    # Show AST for file
  python main.py --analyze prog.lang # Analyze file
        """
    )

    parser.add_argument('file', nargs='?', help='Source file or .langc bytecode file to run')
    parser.add_argument('-c', '--compile', action='store_true', help='Compile source to .langc bytecode file')
    parser.add_argument('-o', '--output', help='Output file for compiled bytecode (.langc)')
    parser.add_argument('--no-opt', action='store_true', help='Disable constant folding and dead code elimination')
    parser.add_argument('--disasm', '--bytecode', action='store_true', help='Disassemble bytecode instead of running')
    parser.add_argument('--tokens', action='store_true', help='Show tokens instead of running')
    parser.add_argument('--ast', action='store_true', help='Show AST instead of running')
    parser.add_argument('--analyze', action='store_true', help='Analyze file instead of running')
    parser.add_argument('--version', action='version', version='Simple Compiler 0.2.0')

    args = parser.parse_args()

    if not args.file:
        repl()
        return

    compiler = Compiler()
    optimize = not args.no_opt

    if args.compile:
        try:
            out_file = compiler.compile_to_file(args.file, args.output, optimize=optimize)
            print(f"Compiled {args.file} -> {out_file}")
        except CompilerError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.tokens:
        show_tokens(args.file)
    elif args.ast:
        show_ast(args.file)
    elif args.disasm:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                source = f.read()
            print(f"Bytecode for {args.file}:")
            print("-" * 40)
            compiler.debug_bytecode(source, optimize=optimize)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.analyze:
        analyze_file(args.file)
    else:
        run_file(args.file, compiler)


if __name__ == "__main__":
    main()
