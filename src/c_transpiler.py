import re
from typing import List, Dict, Set, Optional, Any
from pathlib import Path

try:
    from .ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ASTVisitor,
        ListNode, DictNode, IndexNode, IndexAssignmentNode,
        ClassDefNode, GetPropertyNode, SetPropertyNode, ThisNode, SuperPropertyNode,
        DebuggerNode, TryCatchNode, ThrowNode, BreakNode, ContinueNode, LambdaNode,
        ImportNode
    )
    from .parser import load_module_ast
except ImportError:
    from ast_nodes import (
        ASTNode, NumberNode, StringNode, BooleanNode, NilNode,
        VariableNode, BinaryOpNode, UnaryOpNode, AssignmentNode,
        VarDeclarationNode, BlockNode, IfNode, WhileNode,
        FunctionDefNode, CallNode, ReturnNode, PrintNode,
        ExpressionStmtNode, ProgramNode, ASTVisitor,
        ListNode, DictNode, IndexNode, IndexAssignmentNode,
        ClassDefNode, GetPropertyNode, SetPropertyNode, ThisNode, SuperPropertyNode,
        DebuggerNode, TryCatchNode, ThrowNode, BreakNode, ContinueNode, LambdaNode,
        ImportNode
    )
    from parser import load_module_ast


def escape_c_string(s: str) -> str:
    escaped = []
    for ch in s:
        if ch == '\\':
            escaped.append('\\\\')
        elif ch == '"':
            escaped.append('\\"')
        elif ch == '\n':
            escaped.append('\\n')
        elif ch == '\t':
            escaped.append('\\t')
        elif ch == '\r':
            escaped.append('\\r')
        else:
            escaped.append(ch)
    return "".join(escaped)


class CTranspiler(ASTVisitor):
    def __init__(self, include_runtime: bool = True, base_dir: Optional[str] = None):
        self.include_runtime = include_runtime
        self.base_dir = base_dir
        self.imported_modules: Set[str] = set()
        self.indent_level = 0

        self.global_vars: Set[str] = set()
        self.classes: Dict[str, ClassDefNode] = {}
        self.functions: Dict[str, FunctionDefNode] = {}
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.local_vars: Set[str] = set()
        self.try_depth: int = 0
        self.loop_try_depth: int = 0
        self.scope_depth: int = 0
        self.lambda_counter: int = 0
        self.lambda_decls: List[str] = []
        self.lambda_defs: List[str] = []

    def _expand_imports(self, statements: List[ASTNode]) -> List[ASTNode]:
        expanded: List[ASTNode] = []
        for stmt in statements:
            if isinstance(stmt, ImportNode):
                canonical_path, mod_ast = load_module_ast(stmt.path, self.base_dir)
                if canonical_path in self.imported_modules:
                    continue
                self.imported_modules.add(canonical_path)
                prev_base = self.base_dir
                self.base_dir = str(Path(canonical_path).parent)
                try:
                    expanded.extend(self._expand_imports(mod_ast.statements))
                finally:
                    self.base_dir = prev_base
            else:
                expanded.append(stmt)
        return expanded

    def indent(self) -> str:
        return "    " * self.indent_level

    def c_ident(self, name: str) -> str:
        if name == "this":
            return "this"
        return f"_v_{name}"

    def c_fn_ident(self, name: str) -> str:
        return f"_fn_{name}"

    def transpile_statement(self, stmt: ASTNode) -> str:
        code = self.visit(stmt)
        if code and not code.endswith(';') and not code.endswith('}'):
            code += ';'
        return code

    def transpile(self, node: ProgramNode) -> str:
        all_statements = self._expand_imports(node.statements)

        # Pre-scan for classes, functions, and top-level variables
        for stmt in all_statements:
            if isinstance(stmt, ClassDefNode):
                self.classes[stmt.name] = stmt
            elif isinstance(stmt, FunctionDefNode):
                self.functions[stmt.name] = stmt
            elif isinstance(stmt, VarDeclarationNode):
                self.global_vars.add(stmt.name)
            elif isinstance(stmt, AssignmentNode):
                self.global_vars.add(stmt.variable)

        method_impls: List[str] = []
        for cname, cnode in self.classes.items():
            self.current_class = cname
            for method in cnode.methods:
                method_impls.append(self.transpile_method(cname, method))
            self.current_class = None

        fn_impls: List[str] = []
        for fname, fnode in self.functions.items():
            self.current_function = fname
            fn_impls.append(self.visit_FunctionDefNode(fnode))
            self.current_function = None

        main_lines: List[str] = []
        main_lines.append("int main(int argc, char** argv) {")
        self.indent_level = 1

        # Class registration
        for cname, cnode in self.classes.items():
            super_expr = f"class_{cnode.superclass}" if cnode.superclass else "NULL"
            main_lines.append(f"{self.indent()}class_{cname} = val_make_class(\"{cname}\", {super_expr}).as.klass;")
            for method in cnode.methods:
                main_lines.append(f"{self.indent()}val_class_add_method(class_{cname}, \"{method.name}\", _method_{cname}_{method.name});")

        main_lines.append("")

        # Top-level statements
        for stmt in all_statements:
            if not isinstance(stmt, (ClassDefNode, FunctionDefNode)):
                code = self.transpile_statement(stmt)
                if code:
                    main_lines.append(f"{self.indent()}{code}")

        main_lines.append(f"{self.indent()}return 0;")
        self.indent_level = 0
        main_lines.append("}\n")

        lines: List[str] = []

        # 1. Header inclusion or embedded runtime
        if self.include_runtime:
            runtime_path = Path(__file__).parent / "runtime.h"
            if runtime_path.exists():
                with open(runtime_path, 'r', encoding='utf-8') as f:
                    lines.append(f.read())
            else:
                lines.append('#include "runtime.h"')
        else:
            lines.append('#include "runtime.h"')

        lines.append("\n/* Forward declarations for global variables */")
        for gvar in sorted(self.global_vars):
            lines.append(f"static Value {self.c_ident(gvar)};")

        lines.append("\n/* Forward declarations for classes */")
        for cname in sorted(self.classes.keys()):
            lines.append(f"static ObjClass* class_{cname};")

        lines.append("\n/* Forward declarations for functions */")
        for fname, fnode in self.functions.items():
            params_str = ", ".join(f"Value {self.c_ident(p)}" for p in fnode.params) if fnode.params else "void"
            lines.append(f"Value {self.c_fn_ident(fname)}({params_str});")
            lines.append(f"Value _fnwrap_{fname}(int __argc, Value* __argv);")

        for ldecl in self.lambda_decls:
            lines.append(ldecl)

        for cname, cnode in self.classes.items():
            for method in cnode.methods:
                lines.append(f"Value _method_{cname}_{method.name}(Value this, int __argc, Value* __argv);")

        if self.lambda_defs:
            lines.append("\n/* Lambda implementations */")
            lines.extend(self.lambda_defs)

        lines.append("\n/* Class method implementations */")
        lines.extend(method_impls)

        lines.append("\n/* Function implementations */")
        lines.extend(fn_impls)

        lines.append("\n/* Main entrypoint */")
        lines.extend(main_lines)

        return "\n".join(lines)

    def transpile_method(self, class_name: str, method: FunctionDefNode) -> str:
        lines: List[str] = []
        lines.append(f"Value _method_{class_name}_{method.name}(Value this, int __argc, Value* __argv) {{")
        self.indent_level = 1
        prev_fn = self.current_function
        prev_try = self.try_depth
        self.current_function = method.name
        self.try_depth = 0

        # Bind parameters from __argv
        for idx, param in enumerate(method.params):
            lines.append(f"{self.indent()}Value {self.c_ident(param)} = ({idx} < __argc) ? __argv[{idx}] : val_nil();")

        for stmt in method.body.statements:
            code = self.transpile_statement(stmt)
            if code:
                lines.append(f"{self.indent()}{code}")

        # Implicit return this for init, or nil
        if method.name == "init":
            lines.append(f"{self.indent()}return this;")
        else:
            lines.append(f"{self.indent()}return val_nil();")

        self.current_function = prev_fn
        self.try_depth = prev_try
        self.indent_level = 0
        lines.append("}\n")
        return "\n".join(lines)

    def visit_ProgramNode(self, node: ProgramNode) -> str:
        return self.transpile(node)

    def visit_FunctionDefNode(self, node: FunctionDefNode) -> str:
        lines: List[str] = []
        params_str = ", ".join(f"Value {self.c_ident(p)}" for p in node.params) if node.params else "void"
        lines.append(f"Value {self.c_fn_ident(node.name)}({params_str}) {{")
        self.indent_level += 1
        prev_try = self.try_depth
        self.try_depth = 0

        for stmt in node.body.statements:
            code = self.transpile_statement(stmt)
            if code:
                lines.append(f"{self.indent()}{code}")

        lines.append(f"{self.indent()}return val_nil();")
        self.try_depth = prev_try
        self.indent_level -= 1
        lines.append("}")

        wrap_args = ", ".join(f"({idx} < __argc) ? __argv[{idx}] : val_nil()" for idx in range(len(node.params)))
        lines.append(f"Value _fnwrap_{node.name}(int __argc, Value* __argv) {{")
        lines.append(f"    return {self.c_fn_ident(node.name)}({wrap_args});")
        lines.append("}\n")
        return "\n".join(lines)

    def visit_LambdaNode(self, node: LambdaNode) -> str:
        self.lambda_counter += 1
        lname = f"_lambda_{self.lambda_counter}"
        self.lambda_decls.append(f"Value {lname}(int __argc, Value* __argv);")

        prev_indent = self.indent_level
        prev_fn = self.current_function
        prev_try = self.try_depth
        prev_scope = self.scope_depth
        self.indent_level = 1
        self.current_function = lname
        self.try_depth = 0
        self.scope_depth = 0

        lines: List[str] = [f"Value {lname}(int __argc, Value* __argv) {{"]
        for idx, param in enumerate(node.params):
            lines.append(f"{self.indent()}Value {self.c_ident(param)} = ({idx} < __argc) ? __argv[{idx}] : val_nil();")

        for stmt in node.body.statements:
            code = self.transpile_statement(stmt)
            if code:
                lines.append(f"{self.indent()}{code}")

        lines.append(f"{self.indent()}return val_nil();")
        lines.append("}\n")

        self.indent_level = prev_indent
        self.current_function = prev_fn
        self.try_depth = prev_try
        self.scope_depth = prev_scope

        self.lambda_defs.append("\n".join(lines))
        return f"val_function({lname})"

    def visit_ClassDefNode(self, node: ClassDefNode) -> str:
        return ""

    def visit_BlockNode(self, node: BlockNode) -> str:
        lines: List[str] = ["{"]
        self.indent_level += 1
        self.scope_depth += 1
        for stmt in node.statements:
            code = self.transpile_statement(stmt)
            if code:
                lines.append(f"{self.indent()}{code}")
        self.scope_depth -= 1
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return "\n".join(lines)

    def visit_VarDeclarationNode(self, node: VarDeclarationNode) -> str:
        init_code = self.visit(node.initializer) if node.initializer else "val_nil()"
        ident = self.c_ident(node.name)
        if self.current_function is None and self.current_class is None and self.scope_depth == 0:
            # Top-level global initialization
            return f"{ident} = {init_code};"
        return f"Value {ident} = {init_code};"

    def visit_AssignmentNode(self, node: AssignmentNode) -> str:
        val_code = self.visit(node.value)
        return f"{self.c_ident(node.variable)} = {val_code};"

    def visit_IfNode(self, node: IfNode) -> str:
        cond_code = self.visit(node.condition)
        lines: List[str] = []
        lines.append(f"if (val_is_truthy({cond_code})) {{")
        self.indent_level += 1
        then_code = self.visit(node.then_branch)
        if then_code:
            lines.append(f"{self.indent()}{then_code}")
        self.indent_level -= 1

        if node.else_branch:
            lines.append(f"{self.indent()}}} else {{")
            self.indent_level += 1
            else_code = self.visit(node.else_branch)
            if else_code:
                lines.append(f"{self.indent()}{else_code}")
            self.indent_level -= 1

        lines.append(f"{self.indent()}}}")
        return "\n".join(lines)

    def visit_WhileNode(self, node: WhileNode) -> str:
        cond_code = self.visit(node.condition)
        lines: List[str] = []
        if node.increment is not None:
            inc_node = node.increment.expression if isinstance(node.increment, ExpressionStmtNode) else node.increment
            inc_code = self.visit(inc_node).rstrip(';')
            lines.append(f"for (; val_is_truthy({cond_code}); {inc_code}) {{")
        else:
            lines.append(f"while (val_is_truthy({cond_code})) {{")
        self.indent_level += 1
        prev_loop_try = self.loop_try_depth
        self.loop_try_depth = self.try_depth
        body_code = self.visit(node.body)
        if body_code:
            lines.append(f"{self.indent()}{body_code}")
        self.loop_try_depth = prev_loop_try
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return "\n".join(lines)

    def visit_BreakNode(self, node: BreakNode) -> str:
        diff = self.try_depth - self.loop_try_depth
        if diff > 0:
            return f"{{ _exc_top -= {diff}; break; }}"
        return "break;"

    def visit_ContinueNode(self, node: ContinueNode) -> str:
        diff = self.try_depth - self.loop_try_depth
        if diff > 0:
            return f"{{ _exc_top -= {diff}; continue; }}"
        return "continue;"

    def visit_ReturnNode(self, node: ReturnNode) -> str:
        if node.value:
            val_expr = self.visit(node.value)
        elif self.current_class is not None and self.current_function == "init":
            val_expr = "this"
        else:
            val_expr = "val_nil()"

        if self.try_depth > 0:
            return f"{{ Value _ret_val = {val_expr}; _exc_top -= {self.try_depth}; return _ret_val; }}"
        return f"return {val_expr};"

    def visit_PrintNode(self, node: PrintNode) -> str:
        expr_code = self.visit(node.expression)
        return f"val_print({expr_code});"

    def visit_ExpressionStmtNode(self, node: ExpressionStmtNode) -> str:
        expr_code = self.visit(node.expression)
        return f"{expr_code};"

    def visit_DebuggerNode(self, node: DebuggerNode) -> str:
        return '/* debugger statement */'

    def visit_TryCatchNode(self, node: TryCatchNode) -> str:
        lines: List[str] = []
        lines.append("if (setjmp(_exc_stack[_exc_top++].env) == 0) {")
        self.indent_level += 1
        self.try_depth += 1
        self.scope_depth += 1
        for stmt in node.try_block.statements:
            code = self.transpile_statement(stmt)
            if code:
                lines.append(f"{self.indent()}{code}")
        self.scope_depth -= 1
        self.try_depth -= 1
        lines.append(f"{self.indent()}_exc_top--;")
        self.indent_level -= 1
        lines.append(f"{self.indent()}}} else {{")
        self.indent_level += 1
        self.scope_depth += 1
        if node.catch_var:
            lines.append(f"{self.indent()}Value {self.c_ident(node.catch_var)} = _current_exception;")
        for stmt in node.catch_block.statements:
            code = self.transpile_statement(stmt)
            if code:
                lines.append(f"{self.indent()}{code}")
        self.scope_depth -= 1
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return "\n".join(lines)

    def visit_ThrowNode(self, node: ThrowNode) -> str:
        expr_code = self.visit(node.expression)
        return f"val_throw({expr_code});"

    def visit_NumberNode(self, node: NumberNode) -> str:
        if isinstance(node.value, int):
            return f"val_int_val({node.value}LL)"
        return f"val_number({node.value})"

    def visit_StringNode(self, node: StringNode) -> str:
        return f'val_string("{escape_c_string(node.value)}")'

    def visit_BooleanNode(self, node: BooleanNode) -> str:
        return "val_bool(true)" if node.value else "val_bool(false)"

    def visit_NilNode(self, node: NilNode) -> str:
        return "val_nil()"

    def visit_VariableNode(self, node: VariableNode) -> str:
        if node.name in self.functions and node.name not in self.global_vars and node.name not in self.local_vars:
            return f"val_function(_fnwrap_{node.name})"
        return self.c_ident(node.name)

    def visit_ThisNode(self, node: ThisNode) -> str:
        return "this"

    def visit_SuperPropertyNode(self, node: SuperPropertyNode) -> str:
        if self.current_class and self.current_class in self.classes:
            superclass_name = self.classes[self.current_class].superclass
            if superclass_name:
                return f"val_class_find_method(class_{superclass_name}, \"{node.property_name}\")(this, 0, NULL)"
        return "val_nil()"

    def visit_BinaryOpNode(self, node: BinaryOpNode) -> str:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.operator

        if op == '+':
            return f"val_add({left}, {right})"
        elif op == '-':
            return f"val_sub({left}, {right})"
        elif op == '*':
            return f"val_mul({left}, {right})"
        elif op == '/':
            return f"val_div({left}, {right})"
        elif op == '%':
            return f"val_mod({left}, {right})"
        elif op == '==':
            return f"val_equal({left}, {right})"
        elif op == '!=':
            return f"val_not_equal({left}, {right})"
        elif op == '<':
            return f"val_less({left}, {right})"
        elif op == '<=':
            return f"val_less_equal({left}, {right})"
        elif op == '>':
            return f"val_greater({left}, {right})"
        elif op == '>=':
            return f"val_greater_equal({left}, {right})"
        elif op == 'and':
            return f"val_bool(val_is_truthy({left}) && val_is_truthy({right}))"
        elif op == 'or':
            return f"val_bool(val_is_truthy({left}) || val_is_truthy({right}))"
        else:
            return f"val_nil()"

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> str:
        operand = self.visit(node.operand)
        if node.operator == '-':
            return f"val_negate({operand})"
        elif node.operator in ('not', '!'):
            return f"val_not({operand})"
        return operand

    def visit_ListNode(self, node: ListNode) -> str:
        if not node.elements:
            return "val_make_list(0, NULL)"
        elems = ", ".join(self.visit(e) for e in node.elements)
        return f"val_make_list({len(node.elements)}, (Value[]){{ {elems} }})"

    def visit_DictNode(self, node: DictNode) -> str:
        if not node.entries:
            return "val_make_dict(0, NULL, NULL)"
        keys_str = ", ".join(f'"{escape_c_string(str(k.value if hasattr(k, "value") else k))}"' for k, _ in node.entries)
        vals_str = ", ".join(self.visit(v) for _, v in node.entries)
        return f"val_make_dict({len(node.entries)}, (const char*[]){{ {keys_str} }}, (Value[]){{ {vals_str} }})"

    def visit_IndexNode(self, node: IndexNode) -> str:
        target = self.visit(node.target)
        index = self.visit(node.index)
        return f"val_get_index({target}, {index})"

    def visit_IndexAssignmentNode(self, node: IndexAssignmentNode) -> str:
        target = self.visit(node.target)
        index = self.visit(node.index)
        val = self.visit(node.value)
        return f"val_set_index({target}, {index}, {val})"

    def visit_GetPropertyNode(self, node: GetPropertyNode) -> str:
        target = self.visit(node.target)
        return f"val_get_property({target}, \"{node.property_name}\")"

    def visit_SetPropertyNode(self, node: SetPropertyNode) -> str:
        target = self.visit(node.target)
        val = self.visit(node.value)
        return f"val_set_property({target}, \"{node.property_name}\", {val})"

    def visit_CallNode(self, node: CallNode) -> str:
        args_code = [self.visit(arg) for arg in node.arguments]

        # 1. Method call on property: obj.method(args...)
        if isinstance(node.callee, GetPropertyNode):
            obj = self.visit(node.callee.target)
            prop = node.callee.property_name
            if args_code:
                args_arr = f"(Value[]){{ {', '.join(args_code)} }}"
            else:
                args_arr = "NULL"
            return f"val_call_method({obj}, \"{prop}\", {len(args_code)}, {args_arr})"

        # 2. Super method call: super.method(args...)
        if isinstance(node.callee, SuperPropertyNode):
            prop = node.callee.property_name
            if self.current_class and self.current_class in self.classes:
                superclass_name = self.classes[self.current_class].superclass
                if superclass_name:
                    if args_code:
                        args_arr = f"(Value[]){{ {', '.join(args_code)} }}"
                    else:
                        args_arr = "NULL"
                    return f"val_class_find_method(class_{superclass_name}, \"{prop}\")(this, {len(args_code)}, {args_arr})"

        # 3. Class instantiation: ClassName(args...)
        if isinstance(node.callee, VariableNode) and node.callee.name in self.classes:
            cname = node.callee.name
            if args_code:
                args_arr = f"(Value[]){{ {', '.join(args_code)} }}"
            else:
                args_arr = "NULL"
            return f"val_instantiate(class_{cname}, {len(args_code)}, {args_arr})"

        # 4. Standard Library Built-ins
        if isinstance(node.callee, VariableNode):
            name = node.callee.name
            if name == "len" and len(args_code) == 1:
                return f"val_len({args_code[0]})"
            elif name == "append" and len(args_code) == 2:
                return f"val_append({args_code[0]}, {args_code[1]})"
            elif name == "pop" and len(args_code) == 1:
                return f"val_pop({args_code[0]})"
            elif name == "keys" and len(args_code) == 1:
                return f"val_keys({args_code[0]})"
            elif name == "values" and len(args_code) == 1:
                return f"val_values({args_code[0]})"
            elif name == "str" and len(args_code) == 1:
                return f"val_str({args_code[0]})"
            elif name == "int" and len(args_code) == 1:
                return f"val_int({args_code[0]})"
            elif name == "float" and len(args_code) == 1:
                return f"val_float({args_code[0]})"
            elif name == "type" and len(args_code) == 1:
                return f"val_type_name({args_code[0]})"
            elif name == "clock" and len(args_code) == 0:
                return "val_clock()"
            elif name == "abs" and len(args_code) == 1:
                return f"val_abs({args_code[0]})"
            elif name == "sqrt" and len(args_code) == 1:
                return f"val_sqrt({args_code[0]})"
            elif name == "min" and len(args_code) == 2:
                return f"val_min({args_code[0]}, {args_code[1]})"
            elif name == "max" and len(args_code) == 2:
                return f"val_max({args_code[0]}, {args_code[1]})"
            elif name == "read_file" and len(args_code) == 1:
                return f"val_read_file({args_code[0]})"
            elif name == "write_file" and len(args_code) == 2:
                return f"val_write_file({args_code[0]}, {args_code[1]})"
            elif name == "remove_file" and len(args_code) == 1:
                return f"val_remove_file({args_code[0]})"
            elif name == "map" and len(args_code) == 2:
                return f"val_map({args_code[0]}, {args_code[1]})"
            elif name == "filter" and len(args_code) == 2:
                return f"val_filter({args_code[0]}, {args_code[1]})"
            elif name == "reduce" and len(args_code) == 2:
                return f"val_reduce({args_code[0]}, {args_code[1]}, false, val_nil())"
            elif name == "reduce" and len(args_code) == 3:
                return f"val_reduce({args_code[0]}, {args_code[1]}, true, {args_code[2]})"
            elif name in self.functions and name not in self.global_vars and name not in self.local_vars:
                return f"{self.c_fn_ident(name)}({', '.join(args_code)})"

        # 5. Dynamic / first-class function or lambda call
        callee_code = self.visit(node.callee)
        args_arr = f"(Value[]){{ {', '.join(args_code)} }}" if args_code else "NULL"
        return f"val_call({callee_code}, {len(args_code)}, {args_arr})"
