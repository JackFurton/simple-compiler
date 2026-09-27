from typing import List, Optional, Any
try:
    from .tokens import Token, TokenType
    from .lexer import Lexer
    from .ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ListNode, DictNode,
        IndexNode, IndexAssignmentNode
    )
except ImportError:
    from tokens import Token, TokenType
    from lexer import Lexer
    from ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ListNode, DictNode,
        IndexNode, IndexAssignmentNode
    )


class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Parse error at {token.line}:{token.column}: {message}")


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token: Token = self.lexer.get_next_token()
        self.previous_token: Optional[Token] = None

    def _error(self, message: str) -> None:
        raise ParseError(message, self.current_token)

    def _peek(self) -> TokenType:
        return self.current_token.type

    def _check(self, token_type: TokenType) -> bool:
        return self.current_token.type == token_type

    def _advance(self) -> Token:
        self.previous_token = self.current_token
        self.current_token = self.lexer.get_next_token()
        return self.previous_token

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _eat(self, expected_type: TokenType, message: Optional[str] = None) -> Token:
        if self._check(expected_type):
            return self._advance()
        msg = message or f"Expected {expected_type.name}, got {self.current_token.type.name}"
        self._error(msg)

    def _skip_newlines(self) -> None:
        while self._check(TokenType.NEWLINE):
            self._advance()

    def parse(self) -> ProgramNode:
        statements: List[ASTNode] = []
        self._skip_newlines()

        while not self._check(TokenType.EOF):
            stmt = self._declaration()
            if stmt is not None:
                statements.append(stmt)
            self._skip_newlines()

        return ProgramNode(statements)

    def _declaration(self) -> Optional[ASTNode]:
        self._skip_newlines()
        if self._check(TokenType.EOF):
            return None

        if self._match(TokenType.FN):
            return self._function_declaration()

        if self._match(TokenType.LET):
            return self._var_declaration()

        return self._statement()

    def _function_declaration(self) -> FunctionDefNode:
        token = self.previous_token
        name_token = self._eat(TokenType.IDENTIFIER, "Expected function name")
        name = name_token.value

        self._eat(TokenType.LPAREN, "Expected '(' after function name")
        params: List[str] = []
        if not self._check(TokenType.RPAREN):
            param_token = self._eat(TokenType.IDENTIFIER, "Expected parameter name")
            params.append(param_token.value)
            while self._match(TokenType.COMMA):
                param_token = self._eat(TokenType.IDENTIFIER, "Expected parameter name")
                params.append(param_token.value)

        self._eat(TokenType.RPAREN, "Expected ')' after parameters")
        self._skip_newlines()
        self._eat(TokenType.LBRACE, "Expected '{' before function body")
        body = self._block_statement()
        return FunctionDefNode(name, params, body, line=token.line, column=token.column)

    def _var_declaration(self) -> VarDeclarationNode:
        token = self.previous_token
        name_token = self._eat(TokenType.IDENTIFIER, "Expected variable name")
        name = name_token.value
        initializer = None

        if self._match(TokenType.ASSIGN):
            initializer = self._expression()

        self._match(TokenType.SEMICOLON)
        return VarDeclarationNode(name, initializer, line=token.line, column=token.column)

    def _statement(self) -> ASTNode:
        if self._match(TokenType.PRINT):
            return self._print_statement()

        if self._match(TokenType.IF):
            return self._if_statement()

        if self._match(TokenType.WHILE):
            return self._while_statement()

        if self._match(TokenType.FOR):
            return self._for_statement()

        if self._match(TokenType.RETURN):
            return self._return_statement()

        if self._match(TokenType.LBRACE):
            return self._block_statement()

        return self._expression_statement()

    def _print_statement(self) -> PrintNode:
        token = self.previous_token
        expr = self._expression()
        self._match(TokenType.SEMICOLON)
        return PrintNode(expr, line=token.line, column=token.column)

    def _if_statement(self) -> IfNode:
        token = self.previous_token
        has_paren = self._match(TokenType.LPAREN)
        condition = self._expression()
        if has_paren:
            self._eat(TokenType.RPAREN, "Expected ')' after if condition")

        self._skip_newlines()
        then_branch = self._statement()
        else_branch = None

        self._skip_newlines()
        if self._match(TokenType.ELSE):
            self._skip_newlines()
            else_branch = self._statement()

        return IfNode(condition, then_branch, else_branch, line=token.line, column=token.column)

    def _while_statement(self) -> WhileNode:
        token = self.previous_token
        has_paren = self._match(TokenType.LPAREN)
        condition = self._expression()
        if has_paren:
            self._eat(TokenType.RPAREN, "Expected ')' after while condition")

        self._skip_newlines()
        body = self._statement()
        return WhileNode(condition, body, line=token.line, column=token.column)

    def _for_statement(self) -> ASTNode:
        # Desugar: for (init; cond; inc) body -> { init; while (cond) { body; inc; } }
        self._eat(TokenType.LPAREN, "Expected '(' after 'for'")

        init = None
        if self._match(TokenType.SEMICOLON):
            init = None
        elif self._match(TokenType.LET):
            init = self._var_declaration()
        else:
            init = self._expression_statement()

        condition = None
        if not self._check(TokenType.SEMICOLON):
            condition = self._expression()
        self._eat(TokenType.SEMICOLON, "Expected ';' after loop condition")

        increment = None
        if not self._check(TokenType.RPAREN):
            increment = self._expression()
        self._eat(TokenType.RPAREN, "Expected ')' after for clauses")

        self._skip_newlines()
        body = self._statement()

        # Build while body
        while_body_stmts = [body]
        if increment is not None:
            while_body_stmts.append(ExpressionStmtNode(increment))

        cond_node = condition if condition is not None else BooleanNode(True)
        loop_node = WhileNode(cond_node, BlockNode(while_body_stmts))

        if init is not None:
            return BlockNode([init, loop_node])
        return loop_node

    def _return_statement(self) -> ReturnNode:
        token = self.previous_token
        value = None
        if not self._check(TokenType.SEMICOLON) and not self._check(TokenType.NEWLINE) and not self._check(TokenType.EOF):
            value = self._expression()
        self._match(TokenType.SEMICOLON)
        return ReturnNode(value, line=token.line, column=token.column)

    def _block_statement(self) -> BlockNode:
        token = self.previous_token
        statements: List[ASTNode] = []
        self._skip_newlines()

        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            stmt = self._declaration()
            if stmt is not None:
                statements.append(stmt)
            self._skip_newlines()

        self._eat(TokenType.RBRACE, "Expected '}' after block")
        # Optional trailing semicolon after block
        self._match(TokenType.SEMICOLON)
        return BlockNode(statements, line=token.line, column=token.column)

    def _expression_statement(self) -> ASTNode:
        token = self.current_token
        expr = self._expression()
        self._match(TokenType.SEMICOLON)

        # Preserve AssignmentNode and IndexAssignmentNode at statement level
        if isinstance(expr, (AssignmentNode, IndexAssignmentNode)):
            return expr
        return ExpressionStmtNode(expr, line=token.line, column=token.column)

    def _expression(self) -> ASTNode:
        return self._assignment()

    def _assignment(self) -> ASTNode:
        expr = self._logical_or()

        if self._match(TokenType.ASSIGN):
            equals_token = self.previous_token
            value = self._assignment()

            if isinstance(expr, VariableNode):
                return AssignmentNode(expr.name, value, line=equals_token.line, column=equals_token.column)
            elif isinstance(expr, IndexNode):
                return IndexAssignmentNode(expr.target, expr.index, value, line=equals_token.line, column=equals_token.column)

            raise ParseError("Invalid assignment target", equals_token)

        return expr

    def _logical_or(self) -> ASTNode:
        expr = self._logical_and()

        while self._match(TokenType.OR):
            op_token = self.previous_token
            right = self._logical_and()
            expr = BinaryOpNode(expr, 'or', right, line=op_token.line, column=op_token.column)

        return expr

    def _logical_and(self) -> ASTNode:
        expr = self._equality()

        while self._match(TokenType.AND):
            op_token = self.previous_token
            right = self._equality()
            expr = BinaryOpNode(expr, 'and', right, line=op_token.line, column=op_token.column)

        return expr

    def _equality(self) -> ASTNode:
        expr = self._comparison()

        while self._match(TokenType.EQUAL, TokenType.NOT_EQUAL):
            op_token = self.previous_token
            right = self._comparison()
            expr = BinaryOpNode(expr, op_token.value, right, line=op_token.line, column=op_token.column)

        return expr

    def _comparison(self) -> ASTNode:
        expr = self._term()

        while self._match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            op_token = self.previous_token
            right = self._term()
            expr = BinaryOpNode(expr, op_token.value, right, line=op_token.line, column=op_token.column)

        return expr

    def _term(self) -> ASTNode:
        expr = self._factor()

        while self._match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.previous_token
            right = self._factor()
            expr = BinaryOpNode(expr, op_token.value, right, line=op_token.line, column=op_token.column)

        return expr

    def _factor(self) -> ASTNode:
        expr = self._unary()

        while self._match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op_token = self.previous_token
            right = self._unary()
            expr = BinaryOpNode(expr, op_token.value, right, line=op_token.line, column=op_token.column)

        return expr

    def _unary(self) -> ASTNode:
        if self._match(TokenType.BANG, TokenType.NOT, TokenType.MINUS, TokenType.PLUS):
            op_token = self.previous_token
            operand = self._unary()
            op_str = op_token.value
            if op_str in ('!', 'not'):
                op_str = 'not'
            return UnaryOpNode(op_str, operand, line=op_token.line, column=op_token.column)

        return self._call()

    def _call(self) -> ASTNode:
        expr = self._primary()

        while True:
            if self._match(TokenType.LPAREN):
                expr = self._finish_call(expr)
            elif self._match(TokenType.LBRACKET):
                bracket_token = self.previous_token
                index = self._expression()
                self._eat(TokenType.RBRACKET, "Expected ']' after index")
                expr = IndexNode(expr, index, line=bracket_token.line, column=bracket_token.column)
            else:
                break

        return expr

    def _finish_call(self, callee: ASTNode) -> CallNode:
        args: List[ASTNode] = []
        token = self.previous_token

        if not self._check(TokenType.RPAREN):
            args.append(self._expression())
            while self._match(TokenType.COMMA):
                args.append(self._expression())

        self._eat(TokenType.RPAREN, "Expected ')' after function arguments")
        return CallNode(callee, args, line=token.line, column=token.column)

    def _primary(self) -> ASTNode:
        token = self.current_token

        if self._match(TokenType.FALSE):
            return BooleanNode(False, line=token.line, column=token.column)

        if self._match(TokenType.TRUE):
            return BooleanNode(True, line=token.line, column=token.column)

        if self._match(TokenType.NIL):
            return NilNode(line=token.line, column=token.column)

        if self._match(TokenType.NUMBER):
            val = float(token.value)
            if val.is_integer():
                val = int(val)
            return NumberNode(val, line=token.line, column=token.column)

        if self._match(TokenType.STRING):
            return StringNode(token.value, line=token.line, column=token.column)

        if self._match(TokenType.LBRACKET):
            start_token = self.previous_token
            elements: List[ASTNode] = []
            self._skip_newlines()
            if not self._check(TokenType.RBRACKET):
                elements.append(self._expression())
                self._skip_newlines()
                while self._match(TokenType.COMMA):
                    self._skip_newlines()
                    if self._check(TokenType.RBRACKET):
                        break
                    elements.append(self._expression())
                    self._skip_newlines()
            self._eat(TokenType.RBRACKET, "Expected ']' after list elements")
            return ListNode(elements, line=start_token.line, column=start_token.column)

        if self._match(TokenType.LBRACE):
            start_token = self.previous_token
            entries = []
            self._skip_newlines()
            if not self._check(TokenType.RBRACE):
                key = self._expression()
                self._eat(TokenType.COLON, "Expected ':' after dictionary key")
                self._skip_newlines()
                val = self._expression()
                entries.append((key, val))
                self._skip_newlines()
                while self._match(TokenType.COMMA):
                    self._skip_newlines()
                    if self._check(TokenType.RBRACE):
                        break
                    key = self._expression()
                    self._eat(TokenType.COLON, "Expected ':' after dictionary key")
                    self._skip_newlines()
                    val = self._expression()
                    entries.append((key, val))
                    self._skip_newlines()
            self._eat(TokenType.RBRACE, "Expected '}' after dictionary entries")
            return DictNode(entries, line=start_token.line, column=start_token.column)

        if self._match(TokenType.IDENTIFIER):
            return VariableNode(token.value, line=token.line, column=token.column)

        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._eat(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        self._error(f"Unexpected token {token.type.name}")


def parse_string(source: str) -> ProgramNode:
    lexer = Lexer(source)
    parser = Parser(lexer)
    return parser.parse()
