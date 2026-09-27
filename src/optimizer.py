from typing import Optional, List, Any
try:
    from .ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ListNode, DictNode,
        IndexNode, IndexAssignmentNode, ClassDefNode,
        GetPropertyNode, SetPropertyNode, ThisNode, SuperPropertyNode,
        DebuggerNode
    )
except ImportError:
    from ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ListNode, DictNode,
        IndexNode, IndexAssignmentNode, ClassDefNode,
        GetPropertyNode, SetPropertyNode, ThisNode, SuperPropertyNode,
        DebuggerNode
    )


class ASTOptimizer:
    """Performs compile-time constant folding and dead code elimination."""

    def optimize(self, node: ASTNode) -> Optional[ASTNode]:
        method_name = f"opt_{type(node).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is not None:
            return visitor(node)
        return node

    def opt_ProgramNode(self, node: ProgramNode) -> ProgramNode:
        new_stmts = []
        for stmt in node.statements:
            opt_stmt = self.optimize(stmt)
            if opt_stmt is not None:
                new_stmts.append(opt_stmt)
        return ProgramNode(new_stmts, line=node.line, column=node.column)

    def opt_BlockNode(self, node: BlockNode) -> BlockNode:
        new_stmts = []
        for stmt in node.statements:
            opt_stmt = self.optimize(stmt)
            if opt_stmt is not None:
                new_stmts.append(opt_stmt)
        return BlockNode(new_stmts, line=node.line, column=node.column)

    def opt_ExpressionStmtNode(self, node: ExpressionStmtNode) -> ExpressionStmtNode:
        return ExpressionStmtNode(self.optimize(node.expression), line=node.line, column=node.column)

    def opt_PrintNode(self, node: PrintNode) -> PrintNode:
        return PrintNode(self.optimize(node.expression), line=node.line, column=node.column)

    def opt_ReturnNode(self, node: ReturnNode) -> ReturnNode:
        val = self.optimize(node.value) if node.value else None
        return ReturnNode(val, line=node.line, column=node.column)

    def opt_VarDeclarationNode(self, node: VarDeclarationNode) -> VarDeclarationNode:
        init = self.optimize(node.initializer) if node.initializer else None
        return VarDeclarationNode(node.name, init, line=node.line, column=node.column)

    def opt_AssignmentNode(self, node: AssignmentNode) -> AssignmentNode:
        return AssignmentNode(node.variable, self.optimize(node.value), line=node.line, column=node.column)

    def opt_IndexAssignmentNode(self, node: IndexAssignmentNode) -> IndexAssignmentNode:
        return IndexAssignmentNode(
            self.optimize(node.target),
            self.optimize(node.index),
            self.optimize(node.value),
            line=node.line,
            column=node.column
        )

    def opt_FunctionDefNode(self, node: FunctionDefNode) -> FunctionDefNode:
        opt_body = self.opt_BlockNode(node.body)
        return FunctionDefNode(node.name, node.params, opt_body, line=node.line, column=node.column)

    def opt_CallNode(self, node: CallNode) -> CallNode:
        opt_callee = self.optimize(node.callee)
        opt_args = [self.optimize(a) for a in node.arguments]
        return CallNode(opt_callee, opt_args, line=node.line, column=node.column)

    def opt_ListNode(self, node: ListNode) -> ListNode:
        opt_elems = [self.optimize(e) for e in node.elements]
        return ListNode(opt_elems, line=node.line, column=node.column)

    def opt_DictNode(self, node: DictNode) -> DictNode:
        opt_entries = [(self.optimize(k), self.optimize(v)) for k, v in node.entries]
        return DictNode(opt_entries, line=node.line, column=node.column)

    def opt_IndexNode(self, node: IndexNode) -> IndexNode:
        return IndexNode(self.optimize(node.target), self.optimize(node.index), line=node.line, column=node.column)

    def opt_ClassDefNode(self, node: ClassDefNode) -> ClassDefNode:
        opt_methods = [self.opt_FunctionDefNode(m) for m in node.methods]
        return ClassDefNode(node.name, node.superclass, opt_methods, line=node.line, column=node.column)

    def opt_GetPropertyNode(self, node: GetPropertyNode) -> GetPropertyNode:
        return GetPropertyNode(self.optimize(node.target), node.property_name, line=node.line, column=node.column)

    def opt_SetPropertyNode(self, node: SetPropertyNode) -> SetPropertyNode:
        return SetPropertyNode(
            self.optimize(node.target),
            node.property_name,
            self.optimize(node.value),
            line=node.line,
            column=node.column
        )

    def opt_ThisNode(self, node: ThisNode) -> ThisNode:
        return node

    def opt_SuperPropertyNode(self, node: SuperPropertyNode) -> SuperPropertyNode:
        return node

    def opt_IfNode(self, node: IfNode) -> Optional[ASTNode]:
        cond = self.optimize(node.condition)
        then_branch = self.optimize(node.then_branch)
        else_branch = self.optimize(node.else_branch) if node.else_branch else None

        # Dead code elimination
        if isinstance(cond, BooleanNode):
            if cond.value:
                return then_branch
            else:
                return else_branch

        return IfNode(cond, then_branch, else_branch, line=node.line, column=node.column)

    def opt_WhileNode(self, node: WhileNode) -> Optional[ASTNode]:
        cond = self.optimize(node.condition)
        if isinstance(cond, BooleanNode) and not cond.value:
            # while (false) loop never runs; eliminate it completely!
            return None

        body = self.optimize(node.body)
        return WhileNode(cond, body, line=node.line, column=node.column)

    def opt_UnaryOpNode(self, node: UnaryOpNode) -> ASTNode:
        operand = self.optimize(node.operand)

        if node.operator == '-' and isinstance(operand, NumberNode):
            return NumberNode(-operand.value, line=node.line, column=node.column)

        if node.operator in ('not', '!') and isinstance(operand, BooleanNode):
            return BooleanNode(not operand.value, line=node.line, column=node.column)

        return UnaryOpNode(node.operator, operand, line=node.line, column=node.column)

    def opt_BinaryOpNode(self, node: BinaryOpNode) -> ASTNode:
        left = self.optimize(node.left)
        right = self.optimize(node.right)
        op = node.operator

        # Arithmetic on numbers
        if isinstance(left, NumberNode) and isinstance(right, NumberNode):
            l = left.value
            r = right.value
            if op == '+':
                res = l + r
                return NumberNode(int(res) if isinstance(res, float) and res.is_integer() else res, line=node.line, column=node.column)
            elif op == '-':
                res = l - r
                return NumberNode(int(res) if isinstance(res, float) and res.is_integer() else res, line=node.line, column=node.column)
            elif op == '*':
                res = l * r
                return NumberNode(int(res) if isinstance(res, float) and res.is_integer() else res, line=node.line, column=node.column)
            elif op == '/' and r != 0:
                res = l / r
                return NumberNode(int(res) if isinstance(res, float) and res.is_integer() else res, line=node.line, column=node.column)
            elif op == '%' and r != 0:
                res = l % r
                return NumberNode(int(res) if isinstance(res, float) and res.is_integer() else res, line=node.line, column=node.column)
            elif op == '==':
                return BooleanNode(l == r, line=node.line, column=node.column)
            elif op == '!=':
                return BooleanNode(l != r, line=node.line, column=node.column)
            elif op == '<':
                return BooleanNode(l < r, line=node.line, column=node.column)
            elif op == '<=':
                return BooleanNode(l <= r, line=node.line, column=node.column)
            elif op == '>':
                return BooleanNode(l > r, line=node.line, column=node.column)
            elif op == '>=':
                return BooleanNode(l >= r, line=node.line, column=node.column)

        # String operations
        if isinstance(left, StringNode) and isinstance(right, StringNode):
            if op == '+':
                return StringNode(left.value + right.value, line=node.line, column=node.column)
            elif op == '==':
                return BooleanNode(left.value == right.value, line=node.line, column=node.column)
            elif op == '!=':
                return BooleanNode(left.value != right.value, line=node.line, column=node.column)

        if isinstance(left, StringNode) and isinstance(right, NumberNode) and op == '*':
            if int(right.value) == right.value:
                return StringNode(left.value * int(right.value), line=node.line, column=node.column)

        # Logical operations
        if op == 'and':
            if isinstance(left, BooleanNode):
                if not left.value:
                    return BooleanNode(False, line=node.line, column=node.column)
                return right
        elif op == 'or':
            if isinstance(left, BooleanNode):
                if left.value:
                    return BooleanNode(True, line=node.line, column=node.column)
                return right

        return BinaryOpNode(left, op, right, line=node.line, column=node.column)

    def opt_DebuggerNode(self, node: DebuggerNode) -> DebuggerNode:
        return node
