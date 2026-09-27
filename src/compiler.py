import os
from typing import Any, Optional, Callable, List, Dict
from pathlib import Path

try:
    from .tokens import Token, TokenType
    from .lexer import Lexer
    from .parser import Parser, ProgramNode
    from .interpreter import Interpreter
    from .ast_nodes import ASTNode
    from .bytecode_compiler import BytecodeCompiler, CompileError
    from .vm import VM, VMError
    from .chunk import FunctionObject
    from .disassembler import disassemble_chunk
    from .optimizer import ASTOptimizer
    from .serializer import serialize_bytecode, deserialize_bytecode
except ImportError:
    from tokens import Token, TokenType
    from lexer import Lexer
    from parser import Parser, ProgramNode
    from interpreter import Interpreter
    from ast_nodes import ASTNode
    from bytecode_compiler import BytecodeCompiler, CompileError
    from vm import VM, VMError
    from chunk import FunctionObject
    from disassembler import disassemble_chunk
    from optimizer import ASTOptimizer
    from serializer import serialize_bytecode, deserialize_bytecode


class CompilerError(Exception):
    pass


class Compiler:
    def __init__(self, output_callback: Optional[Callable] = None):
        self.output_callback = output_callback or print
        self.vm = VM(self.output_callback)
        self.interpreter = Interpreter(self.output_callback)

    def tokenize(self, source: str) -> List[Token]:
        try:
            lexer = Lexer(source)
            return lexer.tokenize()
        except Exception as e:
            raise CompilerError(f"Tokenization failed: {e}")

    def parse(self, source: str) -> ProgramNode:
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            return parser.parse()
        except Exception as e:
            raise CompilerError(f"Parsing failed: {e}")

    def compile(self, source: str, optimize: bool = True) -> FunctionObject:
        ast = self.parse(source)
        if optimize:
            optimizer = ASTOptimizer()
            ast = optimizer.optimize(ast)
        try:
            bc_compiler = BytecodeCompiler()
            return bc_compiler.visit(ast)
        except Exception as e:
            raise CompilerError(f"Compilation failed: {e}")

    def disassemble(self, source: str, name: str = "main", optimize: bool = True) -> str:
        fn = self.compile(source, optimize=optimize)
        return disassemble_chunk(fn.chunk, name)

    def interpret(self, ast: ASTNode) -> Any:
        try:
            return self.interpreter.interpret(ast)
        except Exception as e:
            raise CompilerError(f"Execution failed: {e}")

    def run(self, source: str, optimize: bool = True) -> Any:
        fn = self.compile(source, optimize=optimize)
        try:
            return self.vm.interpret(fn)
        except Exception as e:
            raise CompilerError(f"Execution failed: {e}")

    def compile_to_file(self, source_filename: str, output_filename: Optional[str] = None, optimize: bool = True) -> str:
        try:
            with open(source_filename, 'r', encoding='utf-8') as f:
                source = f.read()

            fn = self.compile(source, optimize=optimize)
            binary_data = serialize_bytecode(fn)

            if output_filename is None:
                p = Path(source_filename)
                output_filename = str(p.with_suffix('.langc'))

            with open(output_filename, 'wb') as f:
                f.write(binary_data)

            return output_filename
        except FileNotFoundError:
            raise CompilerError(f"File not found: {source_filename}")
        except Exception as e:
            raise CompilerError(f"Bytecode compilation to file failed: {e}")

    def run_bytecode_file(self, filename: str) -> Any:
        try:
            with open(filename, 'rb') as f:
                data = f.read()
            fn = deserialize_bytecode(data)
            return self.vm.interpret(fn)
        except FileNotFoundError:
            raise CompilerError(f"File not found: {filename}")
        except Exception as e:
            raise CompilerError(f"Bytecode execution failed: {e}")

    def run_file(self, filename: str) -> Any:
        if filename.endswith('.langc'):
            return self.run_bytecode_file(filename)

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read()
            return self.run(source)
        except FileNotFoundError:
            raise CompilerError(f"File not found: {filename}")
        except IOError as e:
            raise CompilerError(f"Error reading file {filename}: {e}")

    def get_variables(self) -> Dict[str, Any]:
        return self.vm.globals.copy()

    def set_variable(self, name: str, value: Any) -> None:
        self.vm.globals[name] = value
        self.interpreter.set_variable(name, value)

    def clear_variables(self) -> None:
        self.vm.globals.clear()
        self.vm.globals.update(self.vm._setup_globals())
        self.interpreter.clear_variables()

    def debug_tokens(self, source: str) -> None:
        tokens = self.tokenize(source)
        for token in tokens:
            print(token)

    def debug_ast(self, source: str) -> None:
        ast = self.parse(source)
        print(ast)

    def debug_bytecode(self, source: str, optimize: bool = True) -> None:
        print(self.disassemble(source, optimize=optimize))

    def analyze(self, source: str) -> dict:
        tokens = self.tokenize(source)
        ast = self.parse(source)

        token_count = len([t for t in tokens if t.type.name != 'EOF'])
        analyzer = ASTAnalyzer()
        analysis = analyzer.analyze(ast)

        return {
            'token_count': token_count,
            'ast_depth': analysis['depth'],
            'variables_used': analysis['variables_used'],
            'variables_defined': analysis['variables_defined'],
            'operations_count': analysis['operations_count']
        }


class ASTAnalyzer:
    def analyze(self, node: ASTNode) -> dict:
        self.variables_used = set()
        self.variables_defined = set()
        self.operations_count = 0
        self.max_depth = 0

        self._analyze_node(node, depth=0)

        return {
            'depth': self.max_depth,
            'variables_used': self.variables_used,
            'variables_defined': self.variables_defined,
            'operations_count': self.operations_count
        }

    def _analyze_node(self, node: Optional[ASTNode], depth: int = 0):
        if node is None:
            return

        self.max_depth = max(self.max_depth, depth)

        if hasattr(node, 'statements'):
            for stmt in node.statements:
                self._analyze_node(stmt, depth + 1)

        elif hasattr(node, 'variable') and hasattr(node, 'value'):
            self.variables_defined.add(node.variable)
            self._analyze_node(node.value, depth + 1)

        elif hasattr(node, 'name') and hasattr(node, 'initializer'):
            self.variables_defined.add(node.name)
            if node.initializer:
                self._analyze_node(node.initializer, depth + 1)

        elif hasattr(node, 'name') and hasattr(node, 'params') and hasattr(node, 'body'):
            self.variables_defined.add(node.name)
            for p in node.params:
                self.variables_defined.add(p)
            self._analyze_node(node.body, depth + 1)

        elif hasattr(node, 'name') and not hasattr(node, 'statements'):
            self.variables_used.add(node.name)

        elif hasattr(node, 'left') and hasattr(node, 'right'):
            self.operations_count += 1
            self._analyze_node(node.left, depth + 1)
            self._analyze_node(node.right, depth + 1)

        elif hasattr(node, 'operand'):
            self.operations_count += 1
            self._analyze_node(node.operand, depth + 1)

        elif hasattr(node, 'expression'):
            self._analyze_node(node.expression, depth + 1)

        elif hasattr(node, 'callee') and hasattr(node, 'arguments'):
            self._analyze_node(node.callee, depth + 1)
            for arg in node.arguments:
                self._analyze_node(arg, depth + 1)

        elif hasattr(node, 'condition'):
            self._analyze_node(node.condition, depth + 1)
            if hasattr(node, 'then_branch'):
                self._analyze_node(node.then_branch, depth + 1)
            if hasattr(node, 'else_branch') and node.else_branch:
                self._analyze_node(node.else_branch, depth + 1)
            if hasattr(node, 'body'):
                self._analyze_node(node.body, depth + 1)

        elif hasattr(node, 'elements'):
            for elem in node.elements:
                self._analyze_node(elem, depth + 1)

        elif hasattr(node, 'entries'):
            for k, v in node.entries:
                self._analyze_node(k, depth + 1)
                self._analyze_node(v, depth + 1)

        elif hasattr(node, 'target') and hasattr(node, 'index'):
            self._analyze_node(node.target, depth + 1)
            self._analyze_node(node.index, depth + 1)
            if hasattr(node, 'value'):
                self._analyze_node(node.value, depth + 1)
