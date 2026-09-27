#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser import parse_string
from ast_nodes import (
    ProgramNode, NumberNode, StringNode, BooleanNode, NilNode,
    VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
    VarDeclarationNode, BlockNode, IfNode, WhileNode,
    FunctionDefNode, CallNode, ReturnNode, PrintNode, ExpressionStmtNode
)


def test_parser_precedence():
    ast = parse_string("x = 2 + 3 * 4 == 14 and not false;")
    assert isinstance(ast, ProgramNode)
    stmt = ast.statements[0]
    assert isinstance(stmt, AssignmentNode)
    assert stmt.variable == "x"

    # Top level of value should be 'and'
    and_op = stmt.value
    assert isinstance(and_op, BinaryOpNode)
    assert and_op.operator == "and"

    # Left of 'and' should be '=='
    eq_op = and_op.left
    assert isinstance(eq_op, BinaryOpNode)
    assert eq_op.operator == "=="

    # Left of '==' should be '+'
    add_op = eq_op.left
    assert isinstance(add_op, BinaryOpNode)
    assert add_op.operator == "+"
    assert add_op.left.value == 2

    # Right of '+' should be '*'
    mul_op = add_op.right
    assert isinstance(mul_op, BinaryOpNode)
    assert mul_op.operator == "*"


def test_parser_control_flow():
    source = """
    if (x > 0) {
        print "positive";
    } else {
        print "non-positive";
    }
    """
    ast = parse_string(source)
    stmt = ast.statements[0]
    assert isinstance(stmt, IfNode)
    assert isinstance(stmt.then_branch, BlockNode)
    assert isinstance(stmt.else_branch, BlockNode)


def test_parser_functions():
    source = """
    fn multiply(a, b) {
        return a * b;
    }
    let res = multiply(3, 4);
    """
    ast = parse_string(source)
    assert len(ast.statements) == 2
    fn_def = ast.statements[0]
    assert isinstance(fn_def, FunctionDefNode)
    assert fn_def.name == "multiply"
    assert fn_def.params == ["a", "b"]

    var_decl = ast.statements[1]
    assert isinstance(var_decl, VarDeclarationNode)
    assert isinstance(var_decl.initializer, CallNode)
    assert var_decl.initializer.callee.name == "multiply"
    assert len(var_decl.initializer.arguments) == 2


def test_parser_for_loop_desugaring():
    source = """
    for (let i = 0; i < 10; i = i + 1) {
        print i;
    }
    """
    ast = parse_string(source)
    assert isinstance(ast, ProgramNode)
    # Desugared into BlockNode([init, while_loop])
    block = ast.statements[0]
    assert isinstance(block, BlockNode)
    assert isinstance(block.statements[0], VarDeclarationNode)
    assert isinstance(block.statements[1], WhileNode)


def run_all():
    test_parser_precedence()
    test_parser_control_flow()
    test_parser_functions()
    test_parser_for_loop_desugaring()
    print("All parser tests passed!")


if __name__ == "__main__":
    run_all()
