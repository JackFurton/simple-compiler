#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tokens import TokenType
from lexer import Lexer, LexerError


def test_lexer_literals():
    source = '42 3.14 "hello world\\n" true false nil'
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    types = [t.type for t in tokens]
    assert types == [
        TokenType.NUMBER,
        TokenType.NUMBER,
        TokenType.STRING,
        TokenType.TRUE,
        TokenType.FALSE,
        TokenType.NIL,
        TokenType.EOF,
    ]
    assert tokens[2].value == "hello world\n"


def test_lexer_operators():
    source = "+ - * / % == != < <= > >= = !"
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    types = [t.type for t in tokens]
    assert types == [
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.MULTIPLY,
        TokenType.DIVIDE,
        TokenType.MODULO,
        TokenType.EQUAL,
        TokenType.NOT_EQUAL,
        TokenType.LESS,
        TokenType.LESS_EQUAL,
        TokenType.GREATER,
        TokenType.GREATER_EQUAL,
        TokenType.ASSIGN,
        TokenType.BANG,
        TokenType.EOF,
    ]


def test_lexer_keywords_and_symbols():
    source = "fn add(a, b) { let sum = a + b; return sum; }"
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    types = [t.type for t in tokens]
    assert types == [
        TokenType.FN,
        TokenType.IDENTIFIER,
        TokenType.LPAREN,
        TokenType.IDENTIFIER,
        TokenType.COMMA,
        TokenType.IDENTIFIER,
        TokenType.RPAREN,
        TokenType.LBRACE,
        TokenType.LET,
        TokenType.IDENTIFIER,
        TokenType.ASSIGN,
        TokenType.IDENTIFIER,
        TokenType.PLUS,
        TokenType.IDENTIFIER,
        TokenType.SEMICOLON,
        TokenType.RETURN,
        TokenType.IDENTIFIER,
        TokenType.SEMICOLON,
        TokenType.RBRACE,
        TokenType.EOF,
    ]


def test_lexer_comments():
    source = """
    # Python style comment
    x = 10; // C style comment
    // Another comment
    y = 20;
    """
    lexer = Lexer(source)
    tokens = [t for t in lexer.tokenize() if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    values = [t.value for t in tokens]
    assert values == ['x', '=', '10', ';', 'y', '=', '20', ';']


def run_all():
    test_lexer_literals()
    test_lexer_operators()
    test_lexer_keywords_and_symbols()
    test_lexer_comments()
    print("All lexer tests passed!")


if __name__ == "__main__":
    run_all()
