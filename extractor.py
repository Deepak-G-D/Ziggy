import ast
from model import ClassInfo, AttributeInfo, FunctionInfo, ParameterInfo, ImportsInfo
from typing import List, Dict, Optional, Any, Union

import logging
from pathlib import Path

log = logging.getLogger(__name__)

class Extractor(ast.NodeVisitor):
    """
    AST-based extractor for Python source code.
    Extracts classes, functions, attributes, and imports with detailed metadata.
    """

    def __init__(self) -> None:
        self.classes: Dict[str, ClassInfo] = {}
        self.stack_of_classes: List[ClassInfo] = []  # Stores nested classes (inner classes)
        self.fun_stack: List[FunctionInfo] = []      # Helps to deal with nested functions
        self.imports: Dict[str, ImportsInfo] = {}

    @property
    def _current_class(self) -> Optional[ClassInfo]:
        """
        Returns the current class being processed (top of the stack), or None if not in a class.
        """
        return self.stack_of_classes[-1] if self.stack_of_classes else None

    @property
    def _current_method(self) -> Optional[FunctionInfo]:
        """
        Returns the current function/method being processed (top of the stack), or None if not in a function.
        """
        return self.fun_stack[-1] if self.fun_stack else None

    def _get_decorators(self, dec: ast.AST) -> str:
        """
        Recursively retrieves the decorator name as a string.
        """
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Attribute):
            return f"{self._get_decorators(dec.value)}.{dec.attr}"
        elif isinstance(dec, ast.Call):
            deco_func_id = self._get_decorators(dec.func)
            arg = [ast.unparse(arg) for arg in dec.args]
            return f"{deco_func_id}({arg})"
        else:
            return ast.dump(dec)

    def _custom_ann_retriever(self, node: ast.AST) -> str:
        """
        Retrieves annotation/type hint as a string for Python versions < 3.9.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            value = self._custom_ann_retriever(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            value = self._custom_ann_retriever(node.value)
            slice_value = self._custom_ann_retriever(node.slice)
            return f"{value}[{slice_value}]"
        elif isinstance(node, ast.Tuple):
            ele_in_tuple = [self._custom_ann_retriever(elt) for elt in node.elts]
            return ", ".join(ele_in_tuple)
        elif isinstance(node, ast.AnnAssign):
            return self._custom_ann_retriever(node.annotation)
        elif hasattr(ast, "Index") and isinstance(node, ast.Index):  # Py 3.8
            return self._custom_ann_retriever(node.value)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Handles Python 3.10+ Union types: A | B
            left = self._custom_ann_retriever(node.left)
            right = self._custom_ann_retriever(node.right)
            return f"{left} | {right}"
        return ""

    def _get_annotations(self, node: ast.AST) -> Optional[str]:
        """
        Returns the annotation/type hint as a string, using ast.unparse if available.
        """
        try:
            result = ast.unparse(node)
            if not result.strip():
                return self._custom_ann_retriever(node)
            return result
        except Exception:
            return self._custom_ann_retriever(node)

    @staticmethod
    def _get_visibility(name: str) -> str:
        """
        Determines the visibility of a name based on Python naming conventions.
        """
        if name.startswith("__"):
            return "private"
        elif name.startswith("_"):
            return "protected"
        return "public"

    def _get_default_values(self, node: ast.FunctionDef) -> List[Any]:
        """
        Retrieves default values for function parameters.
        """
        if not node.args.defaults:
            return []
        default_val: List[Any] = []
        for default in node.args.defaults:
            if isinstance(default, ast.Constant):
                default_val.append(default.value)
            else:
                default_val.append(ast.unparse(default))
        return default_val

    def _get_parameters(self, node: ast.FunctionDef) -> List[ParameterInfo]:
        """
        Extracts parameters from a function definition node.
        """
        args = node.args
        params: List[ParameterInfo] = []

        defaults = self._get_default_values(node)
        offset = len(args.args) - len(defaults)

        for i, arg in enumerate(args.args):
            default = defaults[i - offset] if i >= offset else None
            params.append(ParameterInfo(
                name=arg.arg,
                ann_type=self._get_annotations(arg.annotation) if arg.annotation else None,
                default_value=default
            ))

        for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
            params.append(ParameterInfo(
                name=arg.arg,
                ann_type=self._get_annotations(arg.annotation) if arg.annotation else None,
                default_value=ast.unparse(kw_default) if kw_default else None
            ))

        if args.vararg:
            params.append(ParameterInfo(name=f"*{args.vararg.arg}"))
        if args.kwarg:
            params.append(ParameterInfo(name=f"**{args.kwarg.arg}"))

        return params

    def _get_functions(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool) -> FunctionInfo:
        """
        Extracts function/method information from a function definition node.
        """
        func_info = FunctionInfo(
            name=node.name,
            visibility=self._get_visibility(node.name)
        )

        if node.decorator_list:
            for dec in node.decorator_list:
                func_info.decorators.append(self._get_decorators(dec))

        if node.returns:
            func_info.return_type = self._get_annotations(node.returns)

        func_info.parameters.extend(self._get_parameters(node))

        if "staticmethod" in func_info.decorators:
            func_info.func_type = "static method"
        elif "classmethod" in func_info.decorators:
            func_info.func_type = "class method"
        elif (
            "abstractmethod" in func_info.decorators
            or "abs.abstractmethod" in func_info.decorators
        ):
            func_info.func_type = "abstract method"
        else:
            func_info.func_type = "instance"

        func_info.is_async = is_async

        return func_info

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """
        Visits a class definition node and extracts class metadata.
        """
        class_info = ClassInfo(name=node.name)
        if self.stack_of_classes:  # it's a nested class
            parent_class = self.stack_of_classes[-1]
            parent_class.inner_classes.append(class_info)
            log.debug(f"nested class: '{node.name}' at line {node.lineno}")
        else:  # top level class only
            self.classes[node.name] = class_info
            log.debug(f"class: '{node.name}' at line {node.lineno}")
        self.stack_of_classes.append(class_info)

        # Inheritance
        if node.bases:
            for base in node.bases:
                if isinstance(base, ast.Name):
                    class_info.bases.append(base.id)
                    log.debug(f"class: '{node.name}' inherits from '{base.id}' at line {node.lineno}")
                elif isinstance(base, ast.Subscript):
                    value = self._custom_ann_retriever(base.value)
                    slice_val = self._custom_ann_retriever(base.slice)
                    class_info.bases.append(f"{value}[{slice_val}]")
                    log.debug(f"class: '{node.name}' inherits from '{value}[{slice_val}]' at line {node.lineno}")

        # Decorators
        if node.decorator_list:
            for dec in node.decorator_list:
                class_info.decorators.append(self._get_decorators(dec))
                log.debug(f"decorator: '{node.name}' at line {node.lineno}")

        docstring = ast.get_docstring(node)
        class_info.docstring = "" if docstring is None else docstring

        self.generic_visit(node)
        self.stack_of_classes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """
        Visits an assignment node and extracts class or instance attribute information.
        """
        if not self._current_class:
            return

        for target in node.targets:
            if isinstance(target, ast.Name) and not self._current_method:
                attr_info = AttributeInfo(name=target.id)
                attr_info.visibility = self._get_visibility(target.id)
                attr_info.defined_in = self._current_class.name
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    attr_info.type = node.value.func.id
                self._current_class.cls_attributes[target.id] = attr_info
                log.debug(f"class attribute: '{target.id}' at line {target.lineno}")

            elif isinstance(target, ast.Name) and self._current_method:
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    called = node.value.func.id
                    if called not in self._current_method.local_var:
                        self._current_method.local_var.append(called)
                        
            elif (
                isinstance(target, ast.Attribute) and
                isinstance(target.value, ast.Name) and
                target.value.id == "self"
            ):
                attr_info = AttributeInfo(name=target.attr)
                attr_info.visibility = self._get_visibility(target.attr)
                attr_info.defined_in = "__init__"

                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    attr_info.type = node.value.func.id
                elif isinstance(node.value, ast.Name) and self._current_method:
                    for param in self._current_method.parameters:
                        if param.name == node.value.id and param.ann_type:
                            attr_info.type = param.ann_type
                            break

                self._current_class.instance_attributes[target.attr] = attr_info
                log.debug(f"instance attribute: '{target.attr}' at line {target.lineno}")

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """
        Visits an annotated assignment node and extracts attribute information with type hints.
        """
        if not self._current_class:
            return

        if isinstance(node.target, ast.Name):
            if self._current_method:
                # Local annotated variable inside a method, not a class attribute
                self.generic_visit(node)
                return

            attr_info = AttributeInfo(
                name=node.target.id,
                defined_in=self._current_class.name,
                type=self._get_annotations(node.annotation),
                visibility=self._get_visibility(node.target.id)
            )
            self._current_class.cls_attributes[node.target.id] = attr_info
            log.debug(f"class attribute: '{node.target.id}' at line {node.target.lineno}")

        elif (
            isinstance(node.target, ast.Attribute) and
            isinstance(node.target.value, ast.Name) and
            node.target.value.id == "self"
        ):
            attr_info = AttributeInfo(
                name=node.target.attr,
                defined_in="__init__",
                type=self._get_annotations(node.annotation),
                visibility=self._get_visibility(node.target.attr)
            )
            self._current_class.instance_attributes[node.target.attr] = attr_info
            log.debug(f"instance attribute: '{node.target.attr}' type: '{attr_info.type}' at line {node.target.lineno}")

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        Visits a function definition node and extracts method information.
        """
        if not self._current_class:
            return

        fun_info = self._get_functions(node, False)
        self.fun_stack.append(fun_info)
        self._current_class.methods[node.name] = fun_info
        log.debug(f"function: '{node.name}' params: {[arg.arg for arg in node.args.args]} at line {node.lineno}")

        self.generic_visit(node)
        self.fun_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """
        Visits an async function definition node and extracts method information.
        """
        if not self._current_class:
            return

        fun_info = self._get_functions(node, True)
        self.fun_stack.append(fun_info)
        self._current_class.methods[node.name] = fun_info
        log.debug(f"async function: '{node.name}' at line {node.lineno}")

        self.generic_visit(node)
        self.fun_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        """
        Visits an import statement and extracts import information.
        """
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_info = ImportsInfo(
                    module_name=alias.name,
                    as_name=alias.asname,
                    import_type="import",
                    func_name=None
                )
                if import_info.module_name not in self.imports:
                    self.imports[import_info.module_name] = import_info
                    log.debug(f"import: '{alias.name}' at line {alias.lineno}")

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """
        Visits a 'from ... import ...' statement and extracts import information.
        """
        if isinstance(node, ast.ImportFrom):
            import_from_info = ImportsInfo(
                module_name=node.module,
                import_type="import-from"
            )
            for alias in node.names:
                import_from_info.func_name.append(alias.name)
                if alias.asname:
                    import_from_info.as_name = alias.asname
            if node.level:
                import_from_info.level = node.level

            if import_from_info.module_name not in self.imports:
                self.imports[import_from_info.module_name] = import_from_info
                log.debug(f"import-from: '{node.module}' at line {alias.lineno}")
        self.generic_visit(node)

def analyze_py_source(source: str, filename: str = "<uploaded>") -> Any:
    """
    Parses Python source code and returns extracted imports and classes.

    Args:
        source (str): Python source code as a string.
        filename (str, optional): Filename for error reporting. Defaults to "<uploaded>".

    Returns:
        Tuple[Dict[str, ImportsInfo], Dict[str, ClassInfo]]: Extracted imports and classes.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        log.error("Syntax error at line %d in '%s'", exc.lineno, filename)
        raise

    analyzer = Extractor()
    analyzer.visit(tree)

    return analyzer.imports, analyzer.classes
