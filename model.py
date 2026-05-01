from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ParameterInfo:
    """Stores information about a function/method parameter."""
    name: str
    ann_type: Optional[str] = None
    default_value: Optional[Any] = None  # Store default/assigned value

@dataclass
class FunctionInfo:
    """Stores information about a function or method."""
    name: str
    visibility: str
    docstring: str = ""
    parameters: List[ParameterInfo] = field(default_factory=list)
    local_var: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    func_type: Optional[str] = "instance"  # "instance", "static method", "class method", etc.
    is_async: bool = False
    return_type: Optional[str] = None

@dataclass
class AttributeInfo:
    """Stores information about a class or instance attribute."""
    name: str
    type: Optional[str] = None  # Attribute data type or assigned value if no annotation
    default_value: Optional[Any] = None
    visibility: Optional[str] = "public"  # "public", "protected", "private"
    defined_in: Optional[str] = None  # e.g. "class body", "__init__", or method name

@dataclass
class ClassInfo:
    """Stores information about a class, including attributes, methods, and inner classes."""
    name: str
    bases: List[str] = field(default_factory=list)
    cls_attributes: Dict[str, AttributeInfo] = field(default_factory=dict)
    instance_attributes: Dict[str, AttributeInfo] = field(default_factory=dict)
    methods: Dict[str, FunctionInfo] = field(default_factory=dict)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    inner_classes: List["ClassInfo"] = field(default_factory=list)

@dataclass
class ImportsInfo:
    """Stores information about an import statement."""
    module_name: str
    import_type: str  # "import" or "import-from"
    func_name: Optional[List[str]] = field(default_factory=list)
    as_name: Optional[str] = None
    level: Optional[int] = None

