from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto

try:
    from .tokens import Token, TokenType
    from .ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ASTVisitor,
        ListNode, DictNode, IndexNode, IndexAssignmentNode,
        ClassDefNode, GetPropertyNode, SetPropertyNode, ThisNode, SuperPropertyNode,
        DebuggerNode
    )
    from .opcodes import OpCode
    from .chunk import Chunk, FunctionObject
except ImportError:
    from tokens import Token, TokenType
    from ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ASTVisitor,
        ListNode, DictNode, IndexNode, IndexAssignmentNode,
        ClassDefNode, GetPropertyNode, SetPropertyNode, ThisNode, SuperPropertyNode,
        DebuggerNode
    )
    from opcodes import OpCode
    from chunk import Chunk, FunctionObject


class FunctionType(Enum):
    TYPE_SCRIPT = auto()
    TYPE_FUNCTION = auto()
    TYPE_METHOD = auto()
    TYPE_INITIALIZER = auto()


@dataclass
class CompilerUpvalue:
    index: int
    is_local: bool


@dataclass
class Local:
    name: str
    depth: int  # -1 if uninitialized, >= 0 initialized
    is_captured: bool = False


class CompileError(Exception):
    def __init__(self, message: str, line: int = 1, column: int = 1):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Compile error at {line}:{column}: {message}")


class BytecodeCompiler(ASTVisitor):
    def __init__(
        self,
        fn_type: FunctionType = FunctionType.TYPE_SCRIPT,
        name: str = "",
        enclosing: Optional['BytecodeCompiler'] = None,
        current_class: Optional[str] = None
    ):
        self.type = fn_type
        self.enclosing = enclosing
        self.current_class = current_class or (enclosing.current_class if enclosing else None)
        self.function = FunctionObject(name=name, arity=0)
        self.locals: List[Local] = []
        self.upvalues: List[CompilerUpvalue] = []
        self.scope_depth: int = 0

        # Slot 0 in call frame is reserved for function/closure, or "this" in methods
        slot0_name = "this" if fn_type in (FunctionType.TYPE_METHOD, FunctionType.TYPE_INITIALIZER) else ""
        self.locals.append(Local(name=slot0_name, depth=0))
        if slot0_name:
            self.function.debug_locals[0] = slot0_name

    def is_global_scope(self) -> bool:
        return self.type == FunctionType.TYPE_SCRIPT and self.scope_depth == 0

    @property
    def chunk(self) -> Chunk:
        return self.function.chunk

    def emit_byte(self, byte_val: int, line: int = 1) -> int:
        return self.chunk.write_byte(byte_val, line)

    def emit_opcode(self, opcode: OpCode, line: int = 1) -> int:
        return self.chunk.write_opcode(opcode, line)

    def emit_u16(self, val: int, line: int = 1) -> int:
        return self.chunk.write_u16(val, line)

    def emit_constant(self, value: Any, line: int = 1) -> None:
        const_idx = self.chunk.add_constant(value)
        self.emit_opcode(OpCode.OP_CONSTANT, line)
        self.emit_u16(const_idx, line)

    def emit_jump(self, opcode: OpCode, line: int = 1) -> int:
        self.emit_opcode(opcode, line)
        # Placeholder jump offset
        return self.emit_u16(0xFFFF, line)

    def patch_jump(self, offset: int) -> None:
        # Jump offset is relative to instruction immediately following the jump operand (offset + 2)
        jump_distance = len(self.chunk.code) - (offset + 2)
        if jump_distance > 0xFFFF:
            raise CompileError("Too much code to jump over")
        self.chunk.patch_u16(offset, jump_distance)

    def emit_loop(self, loop_start: int, line: int = 1) -> None:
        self.emit_opcode(OpCode.OP_LOOP, line)
        offset = len(self.chunk.code) - loop_start + 2
        if offset > 0xFFFF:
            raise CompileError("Loop body too large")
        self.emit_u16(offset, line)

    def emit_return(self, line: int = 1) -> None:
        self.emit_opcode(OpCode.OP_NIL, line)
        self.emit_opcode(OpCode.OP_RETURN, line)

    def begin_scope(self) -> None:
        self.scope_depth += 1

    def end_scope(self, line: int = 1) -> None:
        self.scope_depth -= 1
        # Pop locals that went out of scope
        while self.locals and self.locals[-1].depth > self.scope_depth:
            if self.locals[-1].is_captured:
                self.emit_opcode(OpCode.OP_CLOSE_UPVALUE, line)
            else:
                self.emit_opcode(OpCode.OP_POP, line)
            self.locals.pop()

    def resolve_local(self, name: str, line: int = 1) -> Optional[int]:
        for i in range(len(self.locals) - 1, -1, -1):
            local = self.locals[i]
            if local.name == name:
                if local.depth == -1:
                    raise CompileError(f"Cannot read local variable '{name}' in its own initializer", line)
                return i
        return None

    def add_upvalue(self, index: int, is_local: bool) -> int:
        for i, u in enumerate(self.upvalues):
            if u.index == index and u.is_local == is_local:
                return i
        self.upvalues.append(CompilerUpvalue(index, is_local))
        self.function.upvalue_count = len(self.upvalues)
        return len(self.upvalues) - 1

    def resolve_upvalue(self, name: str, line: int = 1) -> Optional[int]:
        if self.enclosing is None:
            return None

        # 1. Local in immediately enclosing function
        local = self.enclosing.resolve_local(name, line)
        if local is not None:
            self.enclosing.locals[local].is_captured = True
            return self.add_upvalue(local, is_local=True)

        # 2. Upvalue from an enclosing function
        upvalue = self.enclosing.resolve_upvalue(name, line)
        if upvalue is not None:
            return self.add_upvalue(upvalue, is_local=False)

        return None

    def add_local(self, name: str, line: int = 1) -> int:
        # Check for duplicate in current scope
        for i in range(len(self.locals) - 1, -1, -1):
            local = self.locals[i]
            if local.depth != -1 and local.depth < self.scope_depth:
                break
            if local.name == name:
                raise CompileError(f"Variable '{name}' already declared in this scope", line)

        self.locals.append(Local(name=name, depth=-1))
        slot = len(self.locals) - 1
        self.function.debug_locals[slot] = name
        return slot

    def mark_initialized(self) -> None:
        if self.locals:
            self.locals[-1].depth = self.scope_depth

    def compile_statement(self, stmt: ASTNode) -> None:
        self.visit(stmt)
        if isinstance(stmt, (AssignmentNode, IndexAssignmentNode, SetPropertyNode)):
            self.emit_opcode(OpCode.OP_POP, stmt.line)

    # AST Visitor methods
    def visit_ProgramNode(self, node: ProgramNode) -> FunctionObject:
        for stmt in node.statements:
            self.compile_statement(stmt)
        self.emit_return()
        return self.function

    def visit_NumberNode(self, node: NumberNode) -> None:
        self.emit_constant(node.value, node.line)

    def visit_StringNode(self, node: StringNode) -> None:
        self.emit_constant(node.value, node.line)

    def visit_BooleanNode(self, node: BooleanNode) -> None:
        if node.value:
            self.emit_opcode(OpCode.OP_TRUE, node.line)
        else:
            self.emit_opcode(OpCode.OP_FALSE, node.line)

    def visit_NilNode(self, node: NilNode) -> None:
        self.emit_opcode(OpCode.OP_NIL, node.line)

    def visit_ListNode(self, node: ListNode) -> None:
        for elem in node.elements:
            self.visit(elem)
        self.emit_opcode(OpCode.OP_BUILD_LIST, node.line)
        self.emit_u16(len(node.elements), node.line)

    def visit_DictNode(self, node: DictNode) -> None:
        for key, val in node.entries:
            self.visit(key)
            self.visit(val)
        self.emit_opcode(OpCode.OP_BUILD_MAP, node.line)
        self.emit_u16(len(node.entries), node.line)

    def visit_IndexNode(self, node: IndexNode) -> None:
        self.visit(node.target)
        self.visit(node.index)
        self.emit_opcode(OpCode.OP_GET_INDEX, node.line)

    def visit_IndexAssignmentNode(self, node: IndexAssignmentNode) -> None:
        self.visit(node.target)
        self.visit(node.index)
        self.visit(node.value)
        self.emit_opcode(OpCode.OP_SET_INDEX, node.line)

    def visit_VariableNode(self, node: VariableNode) -> None:
        slot = self.resolve_local(node.name, node.line)
        if slot is not None:
            self.emit_opcode(OpCode.OP_GET_LOCAL, node.line)
            self.emit_u16(slot, node.line)
            return

        upvalue = self.resolve_upvalue(node.name, node.line)
        if upvalue is not None:
            self.emit_opcode(OpCode.OP_GET_UPVALUE, node.line)
            self.emit_u16(upvalue, node.line)
            return

        const_idx = self.chunk.add_constant(node.name)
        self.emit_opcode(OpCode.OP_GET_GLOBAL, node.line)
        self.emit_u16(const_idx, node.line)

    def visit_AssignmentNode(self, node: AssignmentNode) -> None:
        self.visit(node.value)

        slot = self.resolve_local(node.variable, node.line)
        if slot is not None:
            self.emit_opcode(OpCode.OP_SET_LOCAL, node.line)
            self.emit_u16(slot, node.line)
            return

        upvalue = self.resolve_upvalue(node.variable, node.line)
        if upvalue is not None:
            self.emit_opcode(OpCode.OP_SET_UPVALUE, node.line)
            self.emit_u16(upvalue, node.line)
            return

        const_idx = self.chunk.add_constant(node.variable)
        self.emit_opcode(OpCode.OP_SET_GLOBAL, node.line)
        self.emit_u16(const_idx, node.line)

    def visit_VarDeclarationNode(self, node: VarDeclarationNode) -> None:
        if not self.is_global_scope():
            self.add_local(node.name, node.line)
            if node.initializer:
                self.visit(node.initializer)
            else:
                self.emit_opcode(OpCode.OP_NIL, node.line)
            self.mark_initialized()
        else:
            if node.initializer:
                self.visit(node.initializer)
            else:
                self.emit_opcode(OpCode.OP_NIL, node.line)
            const_idx = self.chunk.add_constant(node.name)
            self.emit_opcode(OpCode.OP_DEFINE_GLOBAL, node.line)
            self.emit_u16(const_idx, node.line)

    def visit_BlockNode(self, node: BlockNode) -> None:
        self.begin_scope()
        for stmt in node.statements:
            self.compile_statement(stmt)
        self.end_scope(node.line)

    def visit_IfNode(self, node: IfNode) -> None:
        self.visit(node.condition)

        then_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, node.line)
        self.emit_opcode(OpCode.OP_POP, node.line)  # Pop condition if truthy

        self.compile_statement(node.then_branch)

        if node.else_branch:
            else_jump = self.emit_jump(OpCode.OP_JUMP, node.line)
            self.patch_jump(then_jump)
            self.emit_opcode(OpCode.OP_POP, node.line)  # Pop condition if falsy
            self.compile_statement(node.else_branch)
            self.patch_jump(else_jump)
        else:
            self.patch_jump(then_jump)
            self.emit_opcode(OpCode.OP_POP, node.line)  # Pop condition if falsy

    def visit_WhileNode(self, node: WhileNode) -> None:
        loop_start = len(self.chunk.code)

        self.visit(node.condition)
        exit_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, node.line)
        self.emit_opcode(OpCode.OP_POP, node.line)

        self.compile_statement(node.body)
        self.emit_loop(loop_start, node.line)

        self.patch_jump(exit_jump)
        self.emit_opcode(OpCode.OP_POP, node.line)

    def visit_BinaryOpNode(self, node: BinaryOpNode) -> None:
        # Logical short-circuiting operators
        if node.operator == 'and':
            self.visit(node.left)
            end_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, node.line)
            self.emit_opcode(OpCode.OP_POP, node.line)
            self.visit(node.right)
            self.patch_jump(end_jump)
            return

        if node.operator == 'or':
            self.visit(node.left)
            else_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, node.line)
            end_jump = self.emit_jump(OpCode.OP_JUMP, node.line)
            self.patch_jump(else_jump)
            self.emit_opcode(OpCode.OP_POP, node.line)
            self.visit(node.right)
            self.patch_jump(end_jump)
            return

        self.visit(node.left)
        self.visit(node.right)

        op = node.operator
        line = node.line

        if op == '+':
            self.emit_opcode(OpCode.OP_ADD, line)
        elif op == '-':
            self.emit_opcode(OpCode.OP_SUB, line)
        elif op == '*':
            self.emit_opcode(OpCode.OP_MUL, line)
        elif op == '/':
            self.emit_opcode(OpCode.OP_DIV, line)
        elif op == '%':
            self.emit_opcode(OpCode.OP_MOD, line)
        elif op == '==':
            self.emit_opcode(OpCode.OP_EQUAL, line)
        elif op == '!=':
            self.emit_opcode(OpCode.OP_EQUAL, line)
            self.emit_opcode(OpCode.OP_NOT, line)
        elif op == '<':
            self.emit_opcode(OpCode.OP_LESS, line)
        elif op == '<=':
            self.emit_opcode(OpCode.OP_GREATER, line)
            self.emit_opcode(OpCode.OP_NOT, line)
        elif op == '>':
            self.emit_opcode(OpCode.OP_GREATER, line)
        elif op == '>=':
            self.emit_opcode(OpCode.OP_LESS, line)
            self.emit_opcode(OpCode.OP_NOT, line)
        else:
            raise CompileError(f"Unknown binary operator: {op}", line)

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> None:
        self.visit(node.operand)
        if node.operator == '-':
            self.emit_opcode(OpCode.OP_NEGATE, node.line)
        elif node.operator in ('not', '!'):
            self.emit_opcode(OpCode.OP_NOT, node.line)
        elif node.operator == '+':
            pass  # Unary plus is a no-op
        else:
            raise CompileError(f"Unknown unary operator: {node.operator}", node.line)

    def visit_FunctionDefNode(self, node: FunctionDefNode) -> None:
        if not self.is_global_scope():
            self.add_local(node.name, node.line)
            self.mark_initialized()

        fn_compiler = BytecodeCompiler(
            fn_type=FunctionType.TYPE_FUNCTION,
            name=node.name,
            enclosing=self
        )
        fn_compiler.function.arity = len(node.params)

        for param in node.params:
            fn_compiler.add_local(param, node.line)
            fn_compiler.mark_initialized()

        for stmt in node.body.statements:
            fn_compiler.visit(stmt)

        # Implicit return nil at end of function
        fn_compiler.emit_return(node.line)

        compiled_fn = fn_compiler.function
        compiled_fn.upvalue_count = len(fn_compiler.upvalues)
        const_idx = self.chunk.add_constant(compiled_fn)
        self.emit_opcode(OpCode.OP_CLOSURE, node.line)
        self.emit_u16(const_idx, node.line)

        for u in fn_compiler.upvalues:
            self.emit_byte(1 if u.is_local else 0, node.line)
            self.emit_u16(u.index, node.line)

        if self.is_global_scope():
            name_idx = self.chunk.add_constant(node.name)
            self.emit_opcode(OpCode.OP_DEFINE_GLOBAL, node.line)
            self.emit_u16(name_idx, node.line)

    def visit_CallNode(self, node: CallNode) -> None:
        self.visit(node.callee)
        for arg in node.arguments:
            self.visit(arg)
        self.emit_opcode(OpCode.OP_CALL, node.line)
        self.emit_byte(len(node.arguments), node.line)

    def visit_ReturnNode(self, node: ReturnNode) -> None:
        if self.type == FunctionType.TYPE_SCRIPT:
            raise CompileError("Cannot return from top-level code", node.line)

        if self.type == FunctionType.TYPE_INITIALIZER:
            if node.value is not None:
                raise CompileError("Cannot return a value from an initializer", node.line)
            self.emit_opcode(OpCode.OP_GET_LOCAL, node.line)
            self.emit_u16(0, node.line)
            self.emit_opcode(OpCode.OP_RETURN, node.line)
            return

        if node.value:
            self.visit(node.value)
        else:
            self.emit_opcode(OpCode.OP_NIL, node.line)

        self.emit_opcode(OpCode.OP_RETURN, node.line)

    def visit_ClassDefNode(self, node: ClassDefNode) -> None:
        name_idx = self.chunk.add_constant(node.name)
        self.emit_opcode(OpCode.OP_CLASS, node.line)
        self.emit_u16(name_idx, node.line)

        if not self.is_global_scope():
            self.add_local(node.name, node.line)
            self.mark_initialized()

        if node.superclass:
            if node.superclass == node.name:
                raise CompileError("A class cannot inherit from itself", node.line)
            self.visit_VariableNode(VariableNode(node.superclass, line=node.line))
            self.emit_opcode(OpCode.OP_INHERIT, node.line)

        for method in node.methods:
            fn_type = FunctionType.TYPE_INITIALIZER if method.name == "init" else FunctionType.TYPE_METHOD
            method_compiler = BytecodeCompiler(
                fn_type=fn_type,
                name=method.name,
                enclosing=self,
                current_class=node.name
            )
            method_compiler.function.arity = len(method.params)

            for param in method.params:
                method_compiler.add_local(param, method.line)
                method_compiler.mark_initialized()

            for stmt in method.body.statements:
                method_compiler.visit(stmt)

            if fn_type == FunctionType.TYPE_INITIALIZER:
                method_compiler.emit_opcode(OpCode.OP_GET_LOCAL, method.line)
                method_compiler.emit_u16(0, method.line)
                method_compiler.emit_opcode(OpCode.OP_RETURN, method.line)
            else:
                method_compiler.emit_return(method.line)

            compiled_method = method_compiler.function
            compiled_method.upvalue_count = len(method_compiler.upvalues)
            const_idx = self.chunk.add_constant(compiled_method)
            self.emit_opcode(OpCode.OP_CLOSURE, method.line)
            self.emit_u16(const_idx, method.line)

            for u in method_compiler.upvalues:
                self.emit_byte(1 if u.is_local else 0, method.line)
                self.emit_u16(u.index, method.line)

            method_name_idx = self.chunk.add_constant(method.name)
            self.emit_opcode(OpCode.OP_METHOD, method.line)
            self.emit_u16(method_name_idx, method.line)

        if self.is_global_scope():
            self.emit_opcode(OpCode.OP_DEFINE_GLOBAL, node.line)
            self.emit_u16(name_idx, node.line)

    def visit_GetPropertyNode(self, node: GetPropertyNode) -> None:
        self.visit(node.target)
        const_idx = self.chunk.add_constant(node.property_name)
        self.emit_opcode(OpCode.OP_GET_PROPERTY, node.line)
        self.emit_u16(const_idx, node.line)

    def visit_SetPropertyNode(self, node: SetPropertyNode) -> None:
        self.visit(node.target)
        self.visit(node.value)
        const_idx = self.chunk.add_constant(node.property_name)
        self.emit_opcode(OpCode.OP_SET_PROPERTY, node.line)
        self.emit_u16(const_idx, node.line)

    def visit_ThisNode(self, node: ThisNode) -> None:
        slot = self.resolve_local("this", node.line)
        if slot is not None:
            self.emit_opcode(OpCode.OP_GET_LOCAL, node.line)
            self.emit_u16(slot, node.line)
            return

        upvalue = self.resolve_upvalue("this", node.line)
        if upvalue is not None:
            self.emit_opcode(OpCode.OP_GET_UPVALUE, node.line)
            self.emit_u16(upvalue, node.line)
            return

        raise CompileError("Cannot use 'this' outside of a class method", node.line, node.column)

    def visit_SuperPropertyNode(self, node: SuperPropertyNode) -> None:
        slot = self.resolve_local("this", node.line)
        if slot is not None:
            self.emit_opcode(OpCode.OP_GET_LOCAL, node.line)
            self.emit_u16(slot, node.line)
        else:
            upvalue = self.resolve_upvalue("this", node.line)
            if upvalue is not None:
                self.emit_opcode(OpCode.OP_GET_UPVALUE, node.line)
                self.emit_u16(upvalue, node.line)
            else:
                raise CompileError("Cannot use 'super' outside of a class method", node.line, node.column)

        name_idx = self.chunk.add_constant(node.property_name)
        self.emit_opcode(OpCode.OP_GET_SUPER, node.line)
        self.emit_u16(name_idx, node.line)

    def visit_PrintNode(self, node: PrintNode) -> None:
        self.visit(node.expression)
        self.emit_opcode(OpCode.OP_PRINT, node.line)

    def visit_ExpressionStmtNode(self, node: ExpressionStmtNode) -> None:
        self.visit(node.expression)
        self.emit_opcode(OpCode.OP_POP, node.line)

    def visit_DebuggerNode(self, node: DebuggerNode) -> None:
        self.emit_opcode(OpCode.OP_DEBUGGER, node.line)
