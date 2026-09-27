from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    ASSIGN = auto()

    # Comparisons
    EQUAL = auto()
    NOT_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    BANG = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COLON = auto()
    COMMA = auto()
    SEMICOLON = auto()
    DOT = auto()

    # Keywords
    PRINT = auto()
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    FN = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    CLASS = auto()
    THIS = auto()
    SUPER = auto()
    DEBUGGER = auto()

    # Special
    EOF = auto()
    NEWLINE = auto()


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int = 1
    column: int = 1

    def __str__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, {self.line}:{self.column})"
