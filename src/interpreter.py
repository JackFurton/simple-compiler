from typing import Dict, Any, Optional, Callable
try:
    from .ast_nodes import *
except ImportError:
    from ast_nodes import *


class RuntimeError(Exception):
    pass


class ReturnException(Exception):
    def __init__(self, value: Any):
        self.value = value


class Environment:
    def __init__(self, parent: Optional['Environment'] = None):
        self.parent = parent
        self.variables: Dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]

        if self.parent:
            return self.parent.get(name)

        raise RuntimeError(f"Undefined variable: '{name}'")

    def set(self, name: str, value: Any) -> None:
        if name in self.variables:
            self.variables[name] = value
            return

        if self.parent:
            try:
                self.parent.set(name, value)
                return
            except RuntimeError:
                pass

        self.variables[name] = value

    def __str__(self) -> str:
        return f"Environment({self.variables})"


class UserFunction:
    def __init__(self, declaration: FunctionDefNode, closure: Environment, is_initializer: bool = False):
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer

    def bind(self, instance: 'InterpreterInstance') -> 'UserFunction':
        env = Environment(self.closure)
        env.define("this", instance)
        return UserFunction(self.declaration, env, self.is_initializer)

    def call(self, interpreter: 'Interpreter', arguments: list) -> Any:
        env = Environment(self.closure)
        for param, arg in zip(self.declaration.params, arguments):
            env.define(param, arg)

        try:
            interpreter.execute_block(self.declaration.body.statements, env)
        except ReturnException as ret:
            if self.is_initializer:
                return self.closure.get("this")
            return ret.value
        if self.is_initializer:
            return self.closure.get("this")
        return None


class InterpreterClass:
    def __init__(self, name: str, superclass: Optional['InterpreterClass'], methods: Dict[str, UserFunction]):
        self.name = name
        self.superclass = superclass
        self.methods = methods

    def find_method(self, name: str) -> Optional[UserFunction]:
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def call(self, interpreter: 'Interpreter', arguments: list) -> Any:
        instance = InterpreterInstance(self)
        init_method = self.find_method("init")
        if init_method is not None:
            init_method.bind(instance).call(interpreter, arguments)
        return instance

    def __repr__(self) -> str:
        return f"<class {self.name}>"


class InterpreterInstance:
    def __init__(self, klass: InterpreterClass):
        self.klass = klass
        self.fields: Dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name in self.fields:
            return self.fields[name]
        method = self.klass.find_method(name)
        if method is not None:
            return method.bind(self)
        raise RuntimeError(f"Undefined property '{name}' on instance of {self.klass.name}")

    def set(self, name: str, value: Any) -> None:
        self.fields[name] = value

    def __repr__(self) -> str:
        return f"<instance of {self.klass.name}>"


class Interpreter(ASTVisitor):
    def __init__(self, output_callback: Optional[Callable] = None):
        self.globals = Environment()
        self.environment = self.globals
        self.output_callback = output_callback or print

    def interpret(self, node: ASTNode) -> Any:
        return self.visit(node)

    def execute_block(self, statements: list, env: Environment) -> Any:
        previous = self.environment
        try:
            self.environment = env
            result = None
            for stmt in statements:
                result = self.visit(stmt)
            return result
        finally:
            self.environment = previous

    def visit_ProgramNode(self, node: ProgramNode) -> Any:
        result = None
        for statement in node.statements:
            result = self.visit(statement)
        return result

    def visit_BlockNode(self, node: BlockNode) -> Any:
        return self.execute_block(node.statements, Environment(self.environment))

    def visit_NumberNode(self, node: NumberNode) -> Any:
        return node.value

    def visit_StringNode(self, node: StringNode) -> str:
        return node.value

    def visit_BooleanNode(self, node: BooleanNode) -> bool:
        return node.value

    def visit_NilNode(self, node: NilNode) -> None:
        return None

    def visit_ListNode(self, node: ListNode) -> Any:
        return [self.visit(e) for e in node.elements]

    def visit_DictNode(self, node: DictNode) -> Any:
        return {self.visit(k): self.visit(v) for k, v in node.entries}

    def visit_IndexNode(self, node: IndexNode) -> Any:
        target = self.visit(node.target)
        index = self.visit(node.index)
        return target[index]

    def visit_IndexAssignmentNode(self, node: IndexAssignmentNode) -> Any:
        target = self.visit(node.target)
        index = self.visit(node.index)
        value = self.visit(node.value)
        target[index] = value
        return value

    def visit_VariableNode(self, node: VariableNode) -> Any:
        return self.environment.get(node.name)

    def visit_VarDeclarationNode(self, node: VarDeclarationNode) -> Any:
        value = None
        if node.initializer:
            value = self.visit(node.initializer)
        self.environment.define(node.name, value)
        return value

    def visit_AssignmentNode(self, node: AssignmentNode) -> Any:
        value = self.visit(node.value)
        self.environment.set(node.variable, value)
        return value

    def visit_IfNode(self, node: IfNode) -> Any:
        condition = self.visit(node.condition)
        if bool(condition):
            return self.visit(node.then_branch)
        elif node.else_branch:
            return self.visit(node.else_branch)
        return None

    def visit_WhileNode(self, node: WhileNode) -> Any:
        result = None
        while bool(self.visit(node.condition)):
            result = self.visit(node.body)
        return result

    def visit_FunctionDefNode(self, node: FunctionDefNode) -> Any:
        fn = UserFunction(node, self.environment)
        self.environment.define(node.name, fn)
        return fn

    def visit_CallNode(self, node: CallNode) -> Any:
        callee = self.visit(node.callee)
        arguments = [self.visit(arg) for arg in node.arguments]

        if isinstance(callee, (UserFunction, InterpreterClass)):
            return callee.call(self, arguments)
        elif callable(callee):
            return callee(*arguments)
        else:
            raise RuntimeError(f"Can only call functions, got {type(callee).__name__}")

    def visit_ClassDefNode(self, node: ClassDefNode) -> Any:
        superclass = None
        if node.superclass:
            superclass = self.environment.get(node.superclass)
            if not isinstance(superclass, InterpreterClass):
                raise RuntimeError(f"Superclass '{node.superclass}' must be a class")

        methods = {}
        for method in node.methods:
            fn = UserFunction(method, self.environment, is_initializer=(method.name == "init"))
            methods[method.name] = fn

        klass = InterpreterClass(node.name, superclass, methods)
        self.environment.define(node.name, klass)
        return klass

    def visit_GetPropertyNode(self, node: GetPropertyNode) -> Any:
        target = self.visit(node.target)
        if not isinstance(target, InterpreterInstance):
            raise RuntimeError(f"Only instances have properties, got {type(target).__name__}")
        return target.get(node.property_name)

    def visit_SetPropertyNode(self, node: SetPropertyNode) -> Any:
        target = self.visit(node.target)
        if not isinstance(target, InterpreterInstance):
            raise RuntimeError(f"Only instances have fields, got {type(target).__name__}")
        value = self.visit(node.value)
        target.set(node.property_name, value)
        return value

    def visit_ThisNode(self, node: ThisNode) -> Any:
        return self.environment.get("this")

    def visit_SuperPropertyNode(self, node: SuperPropertyNode) -> Any:
        receiver = self.environment.get("this")
        if not isinstance(receiver, InterpreterInstance):
            raise RuntimeError("Cannot use 'super' outside an instance method")
        if receiver.klass.superclass is None:
            raise RuntimeError(f"Class '{receiver.klass.name}' has no superclass")
        method = receiver.klass.superclass.find_method(node.property_name)
        if method is None:
            raise RuntimeError(f"Undefined property '{node.property_name}' in superclass")
        return method.bind(receiver)

    def visit_ReturnNode(self, node: ReturnNode) -> None:
        val = None
        if node.value:
            val = self.visit(node.value)
        raise ReturnException(val)

    def visit_BinaryOpNode(self, node: BinaryOpNode) -> Any:
        if node.operator == 'and':
            left = self.visit(node.left)
            if not bool(left):
                return left
            return self.visit(node.right)

        if node.operator == 'or':
            left = self.visit(node.left)
            if bool(left):
                return left
            return self.visit(node.right)

        left = self.visit(node.left)
        right = self.visit(node.right)

        if node.operator == '+':
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            return str(left) + str(right)
        elif node.operator == '-':
            return left - right
        elif node.operator == '*':
            return left * right
        elif node.operator == '/':
            if right == 0:
                raise RuntimeError("Division by zero")
            return left / right
        elif node.operator == '%':
            if right == 0:
                raise RuntimeError("Modulo by zero")
            return left % right
        elif node.operator == '==':
            return left == right
        elif node.operator == '!=':
            return left != right
        elif node.operator == '<':
            return left < right
        elif node.operator == '<=':
            return left <= right
        elif node.operator == '>':
            return left > right
        elif node.operator == '>=':
            return left >= right
        else:
            raise RuntimeError(f"Unknown binary operator: {node.operator}")

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> Any:
        operand = self.visit(node.operand)

        if node.operator == '+':
            return +operand
        elif node.operator == '-':
            return -operand
        elif node.operator in ('not', '!'):
            return not bool(operand)
        else:
            raise RuntimeError(f"Unknown unary operator: {node.operator}")

    def visit_PrintNode(self, node: PrintNode) -> Any:
        value = self.visit(node.expression)
        self.output_callback(value)
        return value

    def visit_ExpressionStmtNode(self, node: ExpressionStmtNode) -> Any:
        return self.visit(node.expression)

    def visit_DebuggerNode(self, node: DebuggerNode) -> Any:
        if hasattr(self, "debugger") and self.debugger is not None:
            return self.debugger.on_ast_debugger(node)
        return None

    def get_variables(self) -> Dict[str, Any]:
        return self.environment.variables.copy()

    def set_variable(self, name: str, value: Any) -> None:
        self.environment.set(name, value)

    def clear_variables(self) -> None:
        self.environment.variables.clear()


def interpret_string(source: str, output_callback=None) -> Any:
    try:
        from .parser import parse_string
    except ImportError:
        from parser import parse_string

    ast = parse_string(source)
    interpreter = Interpreter(output_callback)
    return interpreter.interpret(ast)
