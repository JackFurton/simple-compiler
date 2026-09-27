from typing import Optional, Iterator, List
try:
    from .tokens import Token, TokenType
except ImportError:
    from tokens import Token, TokenType


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Lexer error at {line}:{column}: {message}")


class Lexer:
    KEYWORDS = {
        'print': TokenType.PRINT,
        'let': TokenType.LET,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'fn': TokenType.FN,
        'return': TokenType.RETURN,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'nil': TokenType.NIL,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
        'class': TokenType.CLASS,
        'this': TokenType.THIS,
        'super': TokenType.SUPER,
        'debugger': TokenType.DEBUGGER,
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self._get_current_char()

    def _get_current_char(self) -> Optional[str]:
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]

    def _advance(self) -> None:
        if self.current_char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.pos += 1
        self.current_char = self._get_current_char()

    def _peek(self, offset: int = 1) -> Optional[str]:
        peek_pos = self.pos + offset
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]

    def _match(self, expected: str) -> bool:
        if self.current_char == expected:
            self._advance()
            return True
        return False

    def _skip_whitespace(self) -> None:
        while self.current_char and self.current_char in ' \t\r':
            self._advance()

    def _skip_line_comment(self) -> None:
        while self.current_char and self.current_char != '\n':
            self._advance()

    def _read_string(self) -> str:
        start_line = self.line
        start_col = self.column
        self._advance()  # Skip opening quote

        result = []
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == '\\':
                self._advance()
                if self.current_char is None:
                    raise LexerError("Unterminated escape sequence in string", self.line, self.column)
                escape_chars = {
                    'n': '\n',
                    't': '\t',
                    'r': '\r',
                    '\\': '\\',
                    '"': '"',
                    "'": "'",
                }
                result.append(escape_chars.get(self.current_char, self.current_char))
            elif self.current_char == '\n':
                result.append('\n')
            else:
                result.append(self.current_char)
            self._advance()

        if self.current_char is None:
            raise LexerError("Unterminated string literal", start_line, start_col)

        self._advance()  # Skip closing quote
        return "".join(result)

    def _read_number(self) -> str:
        result = ""
        has_dot = False

        while self.current_char and (self.current_char.isdigit() or self.current_char == '.'):
            if self.current_char == '.':
                if has_dot:
                    break
                # Only treat as decimal if followed by a digit
                peek_char = self._peek(1)
                if peek_char is None or not peek_char.isdigit():
                    break
                has_dot = True
            result += self.current_char
            self._advance()

        return result

    def _read_identifier(self) -> str:
        result = ""
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self._advance()
        return result

    def _make_token(self, token_type: TokenType, value: str, line: Optional[int] = None, col: Optional[int] = None) -> Token:
        return Token(token_type, value, line or self.line, col or self.column)

    def get_next_token(self) -> Token:
        while self.current_char is not None:
            # Skip spaces and tabs
            if self.current_char in ' \t\r':
                self._skip_whitespace()
                continue

            # Python-style comment
            if self.current_char == '#':
                self._skip_line_comment()
                continue

            # C-style comments //
            if self.current_char == '/' and self._peek(1) == '/':
                self._skip_line_comment()
                continue

            # Newline
            if self.current_char == '\n':
                token = self._make_token(TokenType.NEWLINE, '\n')
                self._advance()
                return token

            # String literals
            if self.current_char == '"':
                start_line = self.line
                start_col = self.column
                value = self._read_string()
                return self._make_token(TokenType.STRING, value, start_line, start_col)

            # Number literals
            if self.current_char.isdigit():
                start_line = self.line
                start_col = self.column
                number_str = self._read_number()
                return self._make_token(TokenType.NUMBER, number_str, start_line, start_col)

            # Identifiers and keywords
            if self.current_char.isalpha() or self.current_char == '_':
                start_line = self.line
                start_col = self.column
                identifier = self._read_identifier()
                token_type = self.KEYWORDS.get(identifier, TokenType.IDENTIFIER)
                return self._make_token(token_type, identifier, start_line, start_col)

            start_line = self.line
            start_col = self.column

            # Two-character tokens
            if self.current_char == '=':
                self._advance()
                if self.current_char == '=':
                    self._advance()
                    return self._make_token(TokenType.EQUAL, '==', start_line, start_col)
                return self._make_token(TokenType.ASSIGN, '=', start_line, start_col)

            if self.current_char == '!':
                self._advance()
                if self.current_char == '=':
                    self._advance()
                    return self._make_token(TokenType.NOT_EQUAL, '!=', start_line, start_col)
                return self._make_token(TokenType.BANG, '!', start_line, start_col)

            if self.current_char == '<':
                self._advance()
                if self.current_char == '=':
                    self._advance()
                    return self._make_token(TokenType.LESS_EQUAL, '<=', start_line, start_col)
                return self._make_token(TokenType.LESS, '<', start_line, start_col)

            if self.current_char == '>':
                self._advance()
                if self.current_char == '=':
                    self._advance()
                    return self._make_token(TokenType.GREATER_EQUAL, '>=', start_line, start_col)
                return self._make_token(TokenType.GREATER, '>', start_line, start_col)

            # Single-character tokens
            char_map = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.MULTIPLY,
                '/': TokenType.DIVIDE,
                '%': TokenType.MODULO,
                ';': TokenType.SEMICOLON,
                ',': TokenType.COMMA,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                ':': TokenType.COLON,
                '.': TokenType.DOT,
            }

            if self.current_char in char_map:
                char = self.current_char
                token_type = char_map[char]
                self._advance()
                return self._make_token(token_type, char, start_line, start_col)

            raise LexerError(
                f"Unexpected character '{self.current_char}'",
                self.line,
                self.column
            )

        return self._make_token(TokenType.EOF, '')

    def __iter__(self) -> Iterator[Token]:
        while True:
            token = self.get_next_token()
            yield token
            if token.type == TokenType.EOF:
                break

    def tokenize(self) -> List[Token]:
        return list(self)
