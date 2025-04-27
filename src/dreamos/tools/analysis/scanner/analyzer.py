# Language analysis logic 

import ast
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")

class LanguageAnalyzer:
    """Handles language-specific code analysis for different programming languages."""
    def __init__(self):
        """Initialize language analyzers and parsers."""
        self.rust_parser = self._init_tree_sitter_language("rust")
        self.js_parser = self._init_tree_sitter_language("javascript")

    def _init_tree_sitter_language(self, lang_name: str) -> Optional[Parser]:
        """
        Initializes and returns a Parser for the given language name (rust, javascript).
        Adjust grammar_paths to point at your compiled .so files if using tree-sitter.
        """
        if not Language or not Parser:
            logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")
            return None

        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",          # <-- Adjust as needed
            "javascript": "path/to/tree-sitter-javascript.so"  # <-- Adjust as needed
        }
        if lang_name not in grammar_paths:
            logger.warning(f"⚠️ No grammar path for {lang_name}. Skipping.")
            return None

        grammar_path = grammar_paths[lang_name]
        if not Path(grammar_path).exists():
            logger.warning(f"⚠️ {lang_name} grammar not found at {grammar_path}")
            return None

        try:
            lang_lib = Language(grammar_path, lang_name)
            parser = Parser()
            parser.set_language(lang_lib)
            return parser
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize tree-sitter {lang_name} parser: {e}")
            return None

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """
        Analyzes source code based on file extension.

        Args:
            file_path: Path to the source file
            source_code: Contents of the source file

        Returns:
            Dict with structure {language, functions, classes, routes, complexity}
        """
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return self._analyze_python(source_code)
        elif suffix == ".rs" and self.rust_parser:
            return self._analyze_rust(source_code)
        elif suffix in [".js", ".ts"] and self.js_parser:
            return self._analyze_javascript(source_code)
        else:
            return {
                "language": suffix,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0
            }

    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts a naive list of function defs, classes, routes, complexity, etc.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"Syntax error parsing Python file: {e}")
            return {"language": ".py", "functions": [], "classes": {}, "routes": [], "complexity": -1, "error": str(e)}
            
        functions = []
        classes = {}
        routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)

                # Route detection (Flask/FastAPI style) from existing logic
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                        func_attr = decorator.func.attr.lower()
                        if func_attr in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [func_attr.upper()]
                            if decorator.args:
                                arg0 = decorator.args[0]
                                # Handle different types for path argument
                                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                                    path_arg = arg0.value
                                elif isinstance(arg0, ast.Str): # Python < 3.8
                                    path_arg = arg0.s
                                    
                            # Check for "methods" kwarg
                            for kw in decorator.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                    extracted_methods = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                            extracted_methods.append(elt.value.upper())
                                        elif isinstance(elt, ast.Str): # Python < 3.8
                                            extracted_methods.append(elt.s.upper())
                                            
                                    if extracted_methods:
                                        methods = extracted_methods
                            for m in methods:
                                routes.append({"function": node.name, "method": m, "path": path_arg})

            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_parts = []
                        attr_node = base
                        while isinstance(attr_node, ast.Attribute):
                            base_parts.append(attr_node.attr)
                            attr_node = attr_node.value
                        if isinstance(attr_node, ast.Name):
                            base_parts.append(attr_node.id)
                        base_classes.append(".".join(reversed(base_parts)))
                    else:
                        # Attempt to represent other base types reasonably
                        try: base_classes.append(ast.dump(base))
                        except: base_classes.append("complex_base")
                classes[node.name] = {
                    "methods": method_names,
                    "docstring": docstring,
                    "base_classes": base_classes
                }

        # Complexity = function count + sum of class methods
        complexity = len(functions) + sum(len(c["methods"]) for c in classes.values())
        return {
            "language": ".py",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }

    def _analyze_rust(self, source_code: str) -> Dict:
        """Analyzes Rust source code using tree-sitter (if available)."""
        if not self.rust_parser:
            return {"language": ".rs", "functions": [], "classes": {}, "routes": [], "complexity": 0}
        try:
            tree = self.rust_parser.parse(bytes(source_code, "utf-8"))
        except Exception as e: # Catch potential parsing errors
             logger.error(f"Error parsing Rust file with tree-sitter: {e}")
             return {"language": ".rs", "functions": [], "classes": {}, "routes": [], "complexity": -1, "error": str(e)}
             
        functions = []
        classes = {} # Use dict for structs/impls

        def _traverse(node):
            try:
                if node.type == "function_item":
                    fn_name_node = node.child_by_field_name("name")
                    if fn_name_node:
                        functions.append(fn_name_node.text.decode("utf-8"))
                elif node.type == "struct_item":
                    struct_name_node = node.child_by_field_name("name")
                    if struct_name_node:
                        struct_name = struct_name_node.text.decode("utf-8")
                        if struct_name not in classes:
                             classes[struct_name] = {"methods": [], "type": "struct"}
                elif node.type == "impl_item":
                    impl_type_node = node.child_by_field_name("type")
                    if impl_type_node:
                        # Handle potential complex impl types like generics `<T>` or traits `Trait for Struct`
                        # This is a simplified representation
                        impl_name = impl_type_node.text.decode("utf-8").split('<')[0].split(' for ')[-1].strip()
                        if impl_name not in classes:
                            classes[impl_name] = {"methods": [], "type": "impl"}
                        # Find function items within the impl block
                        impl_body = node.child_by_field_name("body")
                        if impl_body:
                             for child in impl_body.children:
                                 if child.type == "function_item":
                                     method_node = child.child_by_field_name("name")
                                     if method_node:
                                         classes[impl_name]["methods"].append(method_node.text.decode("utf-8"))
                # Recursively traverse children
                for child in node.children:
                    _traverse(child)
            except Exception as traverse_err:
                logger.warning(f"Error during Rust AST traversal: {traverse_err} on node type {node.type}")

        _traverse(tree.root_node)
        # Adjust complexity: functions + methods within classes
        complexity = len(functions) + sum(len(c.get("methods", [])) for c in classes.values())
        return {
            "language": ".rs",
            "functions": functions,
            "classes": classes, # Store struct/impl info
            "routes": [],
            "complexity": complexity
        }

    def _analyze_javascript(self, source_code: str) -> Dict:
        """Analyzes JS/TS using tree-sitter (if available)."""
        if not self.js_parser:
            return {"language": ".js", "functions": [], "classes": {}, "routes": [], "complexity": 0}
        try:
            tree = self.js_parser.parse(bytes(source_code, "utf-8"))
        except Exception as e:
            logger.error(f"Error parsing JS/TS file with tree-sitter: {e}")
            return {"language": ".js", "functions": [], "classes": {}, "routes": [], "complexity": -1, "error": str(e)}
            
        root = tree.root_node
        functions = []
        classes = {}
        routes = []

        def get_node_text(node):
             try: return node.text.decode("utf-8")
             except: return "<decode_error>"

        def _traverse(node):
            try:
                node_type = node.type
                if node_type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node: functions.append(get_node_text(name_node))
                elif node_type == "method_definition": # For methods inside classes
                    name_node = node.child_by_field_name("name")
                    # Optionally capture method name if needed, currently focusing on top-level functions
                elif node_type == "class_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        cls_name = get_node_text(name_node)
                        methods = []
                        class_body = node.child_by_field_name("body")
                        if class_body:
                             for child in class_body.children:
                                 if child.type == "method_definition":
                                     method_name_node = child.child_by_field_name("name")
                                     if method_name_node:
                                         methods.append(get_node_text(method_name_node))
                        classes[cls_name] = {"methods": methods}
                elif node_type == "lexical_declaration" or node_type == "variable_declaration":
                    # arrow functions assigned to const/let/var
                    for child in node.named_children: # Use named_children for potentially more robust iteration
                        if child.type == "variable_declarator":
                            name_node = child.child_by_field_name("name")
                            value_node = child.child_by_field_name("value")
                            if name_node and value_node and value_node.type == "arrow_function":
                                functions.append(get_node_text(name_node))
                elif node_type == "call_expression": # Route detection
                    # Simplified route detection
                    callee_node = node.child_by_field_name("function")
                    args_node = node.child_by_field_name("arguments")
                    if callee_node and args_node:
                        callee_text = get_node_text(callee_node)
                        # Check for patterns like app.get(...), router.post(...)
                        if '.' in callee_text:
                            obj, method = callee_text.rsplit('.', 1)
                            if method.lower() in {"get", "post", "put", "delete", "patch", "use", "route"}:
                                path_str = "/unknown"
                                # Extract path from first argument if it's a string literal
                                if args_node.child_count > 0:
                                    first_arg = args_node.children[0]
                                    if first_arg.type == "string":
                                        # Extract content within quotes
                                        path_str = get_node_text(first_arg).strip('"\'')
                                    elif first_arg.type == "template_string":
                                         path_str = get_node_text(first_arg).strip('`') # Basic template literal handling
                                routes.append({
                                    "object": obj,
                                    "method": method.upper(),
                                    "path": path_str
                                })
                # Recursively traverse children
                for child in node.children:
                    _traverse(child)
            except Exception as traverse_err:
                logger.warning(f"Error during JS/TS AST traversal: {traverse_err} on node type {node.type}")

        _traverse(root)
        complexity = len(functions) + sum(len(c.get("methods", [])) for c in classes.values())
        return {
            "language": ".js/.ts", # Indicate potential TS
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        } 