from dataclasses import dataclass, field
from typing import List, Optional, Any
from abc import ABC, abstractmethod


class ASTNode(ABC):
    line: int = 1
    column: int = 1


@dataclass
class NumberNode(ASTNode):
    value: float
    line: int = 1
    column: int = 1

    def __str__(self):
        val_str = int(self.value) if self.value == int(self.value) else self.value
        return f"Number({val_str})"


@dataclass
class StringNode(ASTNode):
    value: str
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"String({repr(self.value)})"


@dataclass
class BooleanNode(ASTNode):
    value: bool
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"Boolean({self.value})"


@dataclass
class NilNode(ASTNode):
    line: int = 1
    column: int = 1

    def __str__(self):
        return "Nil()"


@dataclass
class VariableNode(ASTNode):
    name: str
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"Variable({self.name})"


@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"BinaryOp({self.left} {self.operator} {self.right})"


@dataclass
class UnaryOpNode(ASTNode):
    operator: str
    operand: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"UnaryOp({self.operator}{self.operand})"


@dataclass
class AssignmentNode(ASTNode):
    variable: str
    value: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"Assignment({self.variable} = {self.value})"


@dataclass
class VarDeclarationNode(ASTNode):
    name: str
    initializer: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def __str__(self):
        if self.initializer:
            return f"VarDecl({self.name} = {self.initializer})"
        return f"VarDecl({self.name})"


@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __str__(self):
        stmts = "; ".join(str(s) for s in self.statements)
        return f"Block([{stmts}])"


@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def __str__(self):
        if self.else_branch:
            return f"If({self.condition} then {self.then_branch} else {self.else_branch})"
        return f"If({self.condition} then {self.then_branch})"


@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"While({self.condition} do {self.body})"


@dataclass
class FunctionDefNode(ASTNode):
    name: str
    params: List[str]
    body: BlockNode
    line: int = 1
    column: int = 1

    def __str__(self):
        params_str = ", ".join(self.params)
        return f"Function({self.name}({params_str}) {self.body})"


@dataclass
class CallNode(ASTNode):
    callee: ASTNode
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __str__(self):
        args_str = ", ".join(str(a) for a in self.arguments)
        return f"Call({self.callee}({args_str}))"


@dataclass
class ReturnNode(ASTNode):
    value: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def __str__(self):
        if self.value:
            return f"Return({self.value})"
        return "Return()"


@dataclass
class PrintNode(ASTNode):
    expression: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"Print({self.expression})"


@dataclass
class ExpressionStmtNode(ASTNode):
    expression: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"ExprStmt({self.expression})"


@dataclass
class ListNode(ASTNode):
    elements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __str__(self):
        elems_str = ", ".join(str(e) for e in self.elements)
        return f"List([{elems_str}])"


@dataclass
class DictNode(ASTNode):
    entries: List[tuple] = field(default_factory=list)  # List of (key_expr, val_expr)
    line: int = 1
    column: int = 1

    def __str__(self):
        pairs = ", ".join(f"{k}: {v}" for k, v in self.entries)
        return f"Dict({{{pairs}}})"


@dataclass
class IndexNode(ASTNode):
    target: ASTNode
    index: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"Index({self.target}[{self.index}])"


@dataclass
class IndexAssignmentNode(ASTNode):
    target: ASTNode
    index: ASTNode
    value: ASTNode
    line: int = 1
    column: int = 1

    def __str__(self):
        return f"IndexAssign({self.target}[{self.index}] = {self.value})"


@dataclass
class ProgramNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __str__(self):
        statements_str = "; ".join(str(stmt) for stmt in self.statements)
        return f"Program([{statements_str}])"


class ASTVisitor(ABC):
    def visit_NumberNode(self, node: NumberNode) -> Any:
        pass

    def visit_StringNode(self, node: StringNode) -> Any:
        pass

    def visit_BooleanNode(self, node: BooleanNode) -> Any:
        pass

    def visit_NilNode(self, node: NilNode) -> Any:
        pass

    def visit_ListNode(self, node: ListNode) -> Any:
        pass

    def visit_DictNode(self, node: DictNode) -> Any:
        pass

    def visit_IndexNode(self, node: IndexNode) -> Any:
        pass

    def visit_IndexAssignmentNode(self, node: IndexAssignmentNode) -> Any:
        pass

    def visit_VariableNode(self, node: VariableNode) -> Any:
        pass

    def visit_BinaryOpNode(self, node: BinaryOpNode) -> Any:
        pass

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> Any:
        pass

    def visit_AssignmentNode(self, node: AssignmentNode) -> Any:
        pass

    def visit_VarDeclarationNode(self, node: VarDeclarationNode) -> Any:
        pass

    def visit_BlockNode(self, node: BlockNode) -> Any:
        pass

    def visit_IfNode(self, node: IfNode) -> Any:
        pass

    def visit_WhileNode(self, node: WhileNode) -> Any:
        pass

    def visit_FunctionDefNode(self, node: FunctionDefNode) -> Any:
        pass

    def visit_CallNode(self, node: CallNode) -> Any:
        pass

    def visit_ReturnNode(self, node: ReturnNode) -> Any:
        pass

    def visit_PrintNode(self, node: PrintNode) -> Any:
        pass

    def visit_ExpressionStmtNode(self, node: ExpressionStmtNode) -> Any:
        return self.visit(node.expression)

    def visit_ProgramNode(self, node: ProgramNode) -> Any:
        pass

    def visit(self, node: ASTNode) -> Any:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, None)
        if visitor is None:
            raise Exception(f'No visit method for {type(node).__name__}')
        return visitor(node)
