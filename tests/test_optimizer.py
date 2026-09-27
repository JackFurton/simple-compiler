#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser import parse_string
from optimizer import ASTOptimizer
from ast_nodes import NumberNode, StringNode, BooleanNode, VarDeclarationNode, BlockNode


def test_constant_folding():
    source = """
    let math = (10 + 20) * 2;
    let text = "Hello" + " " + "World";
    let logic = not false and (5 > 2);
    """
    ast = parse_string(source)
    opt = ASTOptimizer()
    opt_ast = opt.optimize(ast)

    assert len(opt_ast.statements) == 3

    # Check math folded
    stmt1 = opt_ast.statements[0]
    assert isinstance(stmt1, VarDeclarationNode)
    assert isinstance(stmt1.initializer, NumberNode)
    assert stmt1.initializer.value == 60

    # Check string folded
    stmt2 = opt_ast.statements[1]
    assert isinstance(stmt2, VarDeclarationNode)
    assert isinstance(stmt2.initializer, StringNode)
    assert stmt2.initializer.value == "Hello World"

    # Check logic folded
    stmt3 = opt_ast.statements[2]
    assert isinstance(stmt3, VarDeclarationNode)
    assert isinstance(stmt3.initializer, BooleanNode)
    assert stmt3.initializer.value is True


def test_dead_code_elimination():
    source = """
    if (false) {
        print "dead branch";
    } else {
        print "alive branch";
    }

    while (false) {
        print "dead loop";
    }
    """
    ast = parse_string(source)
    opt = ASTOptimizer()
    opt_ast = opt.optimize(ast)

    # The dead if-branch and dead while loop are eliminated
    assert len(opt_ast.statements) == 1
    assert isinstance(opt_ast.statements[0], BlockNode)


def run_all():
    test_constant_folding()
    test_dead_code_elimination()
    print("All optimizer tests passed!")


if __name__ == "__main__":
    run_all()
