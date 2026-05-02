"""
Tests for Ziggy: UML Class Diagram Generator
Covers extractor, transformer, and security (is_safe) logic.

Run with:
    pytest test_ziggy.py -v
"""

import ast
import pytest
from extractor import analyze_py_source
from transformer import rel
from app import is_safe


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def extract(source: str):
    """Parse source and return (imports, classes)."""
    return analyze_py_source(source)


def get_class(source: str, name: str):
    """Return a single ClassInfo by name."""
    _, classes = extract(source)
    return classes[name]


def get_relations(source: str):
    """Return relationship list for a source string."""
    data = extract(source)
    return rel(data)


# ──────────────────────────────────────────────
# Extractor — Basic class detection
# ──────────────────────────────────────────────

def test_class_detected():
    src = "class Foo: pass"
    _, classes = extract(src)
    assert "Foo" in classes


def test_multiple_classes_detected():
    src = """
class A: pass
class B: pass
class C: pass
"""
    _, classes = extract(src)
    assert set(classes.keys()) == {"A", "B", "C"}


def test_empty_source():
    _, classes = extract("")
    assert classes == {}


# ──────────────────────────────────────────────
# Extractor — Inheritance
# ──────────────────────────────────────────────

def test_single_inheritance():
    src = """
class Animal: pass
class Dog(Animal): pass
"""
    cls = get_class(src, "Dog")
    assert "Animal" in cls.bases


def test_multiple_inheritance():
    src = """
class A: pass
class B: pass
class C(A, B): pass
"""
    cls = get_class(src, "C")
    assert "A" in cls.bases
    assert "B" in cls.bases


def test_no_inheritance():
    src = "class Solo: pass"
    cls = get_class(src, "Solo")
    assert cls.bases == []


# ──────────────────────────────────────────────
# Extractor — Visibility
# ──────────────────────────────────────────────

def test_public_method_visibility():
    src = """
class Foo:
    def bar(self): pass
"""
    cls = get_class(src, "Foo")
    assert cls.methods["bar"].visibility == "public"


def test_protected_method_visibility():
    src = """
class Foo:
    def _bar(self): pass
"""
    cls = get_class(src, "Foo")
    assert cls.methods["_bar"].visibility == "protected"


def test_private_method_visibility():
    src = """
class Foo:
    def __bar(self): pass
"""
    cls = get_class(src, "Foo")
    assert cls.methods["__bar"].visibility == "private"


def test_public_attribute_visibility():
    src = """
class Foo:
    def __init__(self):
        self.name = "ziggy"
"""
    cls = get_class(src, "Foo")
    assert cls.instance_attributes["name"].visibility == "public"


def test_private_attribute_visibility():
    src = """
class Foo:
    def __init__(self):
        self.__secret = 42
"""
    cls = get_class(src, "Foo")
    assert cls.instance_attributes["__secret"].visibility == "private"


# ──────────────────────────────────────────────
# Extractor — Async methods
# ──────────────────────────────────────────────

def test_async_method_detected():
    src = """
class Fetcher:
    async def fetch(self): pass
"""
    cls = get_class(src, "Fetcher")
    assert cls.methods["fetch"].is_async is True


def test_sync_method_not_async():
    src = """
class Worker:
    def run(self): pass
"""
    cls = get_class(src, "Worker")
    assert cls.methods["run"].is_async is False


# ──────────────────────────────────────────────
# Extractor — Method types
# ──────────────────────────────────────────────

def test_static_method_detected():
    src = """
class Util:
    @staticmethod
    def helper(): pass
"""
    cls = get_class(src, "Util")
    assert cls.methods["helper"].func_type == "static method"


def test_class_method_detected():
    src = """
class Factory:
    @classmethod
    def create(cls): pass
"""
    cls = get_class(src, "Factory")
    assert cls.methods["create"].func_type == "class method"


def test_abstract_method_detected():
    src = """
from abc import abstractmethod
class Base:
    @abstractmethod
    def do(self): pass
"""
    cls = get_class(src, "Base")
    assert cls.methods["do"].func_type == "abstract method"


# ──────────────────────────────────────────────
# Extractor — Type hints and return types
# ──────────────────────────────────────────────

def test_return_type_extracted():
    src = """
class Calculator:
    def add(self, x: int, y: int) -> int: pass
"""
    cls = get_class(src, "Calculator")
    assert cls.methods["add"].return_type == "int"


def test_parameter_type_extracted():
    src = """
class Printer:
    def print_name(self, name: str): pass
"""
    cls = get_class(src, "Printer")
    params = cls.methods["print_name"].parameters
    name_param = next(p for p in params if p.name == "name")
    assert name_param.ann_type == "str"


def test_annotated_class_attribute():
    src = """
class Config:
    debug: bool
    timeout: int
"""
    cls = get_class(src, "Config")
    assert cls.cls_attributes["debug"].type == "bool"
    assert cls.cls_attributes["timeout"].type == "int"


# ──────────────────────────────────────────────
# Extractor — Inner classes
# ──────────────────────────────────────────────

def test_inner_class_detected():
    src = """
class Outer:
    class Inner:
        pass
"""
    cls = get_class(src, "Outer")
    inner_names = [c.name for c in cls.inner_classes]
    assert "Inner" in inner_names


# ──────────────────────────────────────────────
# Extractor — Docstrings
# ──────────────────────────────────────────────

def test_class_docstring_extracted():
    src = '''
class Documented:
    """This is a docstring."""
    pass
'''
    cls = get_class(src, "Documented")
    assert "docstring" in cls.docstring.lower()


def test_no_docstring_is_empty_string():
    src = "class Plain: pass"
    cls = get_class(src, "Plain")
    assert cls.docstring == ""


# ──────────────────────────────────────────────
# Transformer — Relationships
# ──────────────────────────────────────────────

def test_inheritance_relationship():
    src = """
class Animal: pass
class Dog(Animal): pass
"""
    rels = get_relations(src)
    assert any(r["rel_type"] == "inheritance" and r["from"] == "Dog" and r["to"] == "Animal"
               for r in rels)


def test_composition_relationship():
    src = """
class Engine: pass
class Car:
    def __init__(self):
        self.engine = Engine()
"""
    rels = get_relations(src)
    assert any(r["rel_type"] == "composition" and r["from"] == "Car" and r["to"] == "Engine"
               for r in rels)


def test_inner_class_relationship():
    src = """
class Outer:
    class Inner:
        pass
"""
    rels = get_relations(src)
    assert any(r["rel_type"] == "inner_class" and r["from"] == "Outer" and r["to"] == "Inner"
               for r in rels)


def test_no_self_inheritance():
    src = "class Lone: pass"
    rels = get_relations(src)
    assert not any(r["from"] == "Lone" and r["to"] == "Lone" and r["rel_type"] == "inheritance"
                   for r in rels)


def test_empty_relations_for_single_class():
    src = "class Solo: pass"
    rels = get_relations(src)
    # No relationships expected for a single isolated class
    assert rels == []


# ──────────────────────────────────────────────
# Security — is_safe()
# ──────────────────────────────────────────────

def test_safe_code_passes():
    src = """
class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}"
"""
    safe, err = is_safe(src)
    assert safe is True
    assert err is None


def test_eval_blocked():
    src = "eval('1 + 1')"
    safe, err = is_safe(src)
    assert safe is False
    assert "eval" in err


def test_exec_blocked():
    src = "exec('x = 1')"
    safe, err = is_safe(src)
    assert safe is False
    assert "exec" in err


def test_pickle_loads_blocked():
    src = """
import pickle
pickle.loads(data)
"""
    safe, err = is_safe(src)
    assert safe is False


def test_pickle_load_allowed():
    """pickle.load (not loads) should be permitted — intentional design decision."""
    src = """
import pickle
with open('file.pkl', 'rb') as f:
    data = pickle.load(f)
"""
    safe, err = is_safe(src)
    assert safe is True


def test_os_system_blocked():
    src = """
import os
os.system('rm -rf /')
"""
    safe, err = is_safe(src)
    assert safe is False


def test_file_too_large_blocked():
    src = "x" * (150*1024+1) # generates > 150KB
    safe, err = is_safe(src)
    assert safe is False
    assert "150KB" in err or "large" in err.lower()


def test_invalid_python_blocked():
    src = "def broken(:"
    safe, err = is_safe(src)
    assert safe is False
    assert "Invalid" in err or "invalid" in err.lower()


def test_compile_blocked():
    src = "compile('x=1', '<str>', 'exec')"
    safe, err = is_safe(src)
    assert safe is False