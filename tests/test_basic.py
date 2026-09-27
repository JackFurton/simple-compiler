#!/usr/bin/env python3

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from lexer import Lexer, TokenType
from parser import parse_string
from ast_nodes import *
from interpreter import interpret_string
from compiler import Compiler


def test_lexer():
    print("Testing lexer...")
    
    source = "x = 5 + 3;"
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    expected_types = [
        TokenType.IDENTIFIER, TokenType.ASSIGN, TokenType.NUMBER,
        TokenType.PLUS, TokenType.NUMBER, TokenType.SEMICOLON, TokenType.EOF
    ]
    
    actual_types = [token.type for token in tokens]
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"
    print("Lexer test passed")


def test_parser():
    print("Testing parser...")
    
    source = "x = 5 + 3;"
    ast = parse_string(source)
    
    assert isinstance(ast, ProgramNode)
    assert len(ast.statements) == 1
    assert isinstance(ast.statements[0], AssignmentNode)
    print("Parser test passed")


def test_interpreter():
    print("Testing interpreter...")
    
    output = []
    def capture_output(value):
        output.append(value)
    
    source = """
    x = 5;
    y = 3;
    z = x + y;
    print z;
    """
    
    result = interpret_string(source, capture_output)
    assert output == [8], f"Expected [8], got {output}"
    print("Interpreter test passed")


def test_compiler():
    print("Testing compiler...")
    
    output = []
    def capture_output(value):
        output.append(value)
    
    compiler = Compiler(capture_output)
    
    compiler.run("result = 2 + 3 * 4; print result;")
    assert output[-1] == 14
    
    compiler.run("x = 10; y = x / 2; print y;")
    assert output[-1] == 5.0
    
    print("Compiler test passed")


def test_analysis():
    print("Testing analysis...")
    
    compiler = Compiler()
    source = """
    x = 5;
    y = x + 3;
    print y;
    """
    
    analysis = compiler.analyze(source)
    assert 'x' in analysis['variables_defined']
    assert 'y' in analysis['variables_defined']
    assert 'x' in analysis['variables_used']
    assert 'y' in analysis['variables_used']
    assert analysis['operations_count'] == 1
    
    print("Analysis test passed")


def run_tests():
    print("Running Simple Compiler Tests")
    print("=" * 40)
    
    try:
        test_lexer()
        test_parser()
        test_interpreter()
        test_compiler()
        test_analysis()
        
        print("=" * 40)
        print("All tests passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
