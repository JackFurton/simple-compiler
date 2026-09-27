from .tokens import Token, TokenType
from .lexer import Lexer, LexerError
from .parser import Parser, ParseError, parse_string
from .ast_nodes import *
from .opcodes import OpCode
from .chunk import Chunk, FunctionObject
from .bytecode_compiler import BytecodeCompiler, CompileError
from .vm import VM, VMError
from .disassembler import disassemble_chunk
from .optimizer import ASTOptimizer
from .serializer import serialize_bytecode, deserialize_bytecode
from .stdlib import get_stdlib_functions, get_stdlib_constants
from .interpreter import Interpreter, RuntimeError, interpret_string
from .compiler import Compiler, CompilerError

__version__ = "0.2.0"
__author__ = "Simple Compiler Project"


def compile_and_run(source: str, output_callback=None):
    compiler = Compiler(output_callback)
    return compiler.run(source)


def tokenize(source: str):
    lexer = Lexer(source)
    return lexer.tokenize()


def parse(source: str):
    return parse_string(source)


def disassemble(source: str):
    compiler = Compiler()
    return compiler.disassemble(source)


def interpret(source: str, output_callback=None):
    return interpret_string(source, output_callback)
