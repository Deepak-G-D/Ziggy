from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Union

# -----------------------------
# Symbols / Labels
# -----------------------------

VISIBILITY_SYMBOLS: Dict[str, str] = {
    "public": "+",
    "private": "-",
    "protected": "#"
}

RELATIONSHIP_SYMBOLS: Dict[str, str] = {
    "composition": "*--",
    "association": "-->",
    "dependency": "..>",
    "inheritance": "--|>",
    "inner_class": "+--"
}

RELATIONSHIP_LABELS: Dict[str, str] = {
    "composition": "has",
    "association": "uses",
    "dependency": "depends on",
    "inheritance": "is a",
    "inner_class": "contains"
}

# -----------------------------
# Helpers
# -----------------------------

def _format_parameters(params: List[Dict[str, Any]]) -> str:
    """Format method parameters for PlantUML."""
    formatted: List[str] = []

    for p in params:
        if p.get("name") == "self":
            continue

        if p.get("ann_type"):
            formatted.append(f"{p['name']}: {p['ann_type']}")
        else:
            formatted.append(p["name"])

    return ", ".join(formatted)


def _format_type(type_: Any) -> str:
    """Format type annotation."""
    return f": {type_}" if type_ else ""


def _normalize_classes(classes: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure class objects are dicts (supports dataclasses or raw dicts)."""
    normalized = {}

    for k, v in classes.items():
        if is_dataclass(v):
            normalized[k] = asdict(v)
        else:
            normalized[k] = v

    return normalized


# -----------------------------
# Class Block Builder
# -----------------------------

def _build_class_block(cls: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    # decorators → stereotype
    decorators = cls.get("decorators", [])
    stereotype = f"<<{','.join(decorators)}>>" if decorators else ""

    header = f"class {cls['name']}{stereotype}"
    lines.append(header + " {")

    # docstring
    if cls.get("docstring"):
        lines.append(f"  .. {cls['docstring']} ..")

    # class attributes
    for attr in cls.get("cls_attributes", {}).values():
        vis = VISIBILITY_SYMBOLS.get(attr.get("visibility", "public"), "+")
        lines.append(f"  {vis} {attr['name']}{_format_type(attr.get('type'))}")

    # instance attributes
    for attr in cls.get("instance_attributes", {}).values():
        vis = VISIBILITY_SYMBOLS.get(attr.get("visibility", "public"), "+")
        lines.append(f"  {vis} {attr['name']}{_format_type(attr.get('type'))}")

    # methods
    for method in cls.get("methods", {}).values():
        if method["name"] == "__init__":
            continue

        vis = VISIBILITY_SYMBOLS.get(method.get("visibility", "public"), "+")
        params = _format_parameters(method.get("parameters", []))
        ret = _format_type(method.get("return_type"))

        decorators = method.get("decorators", [])
        dec = f" <<{'|'.join(decorators)}>>" if decorators else ""
        async_flag = " {async}" if method.get("is_async") else ""

        lines.append(
            f"  {vis} {method['name']}({params}){ret}{dec}{async_flag}"
        )

    lines.append("}")
    return lines


# -----------------------------
# Relationship Builder
# -----------------------------

def _build_relationships(relationships: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []

    for rel in relationships:
        rel_type = rel.get("rel_type", "association")

        symbol = RELATIONSHIP_SYMBOLS.get(rel_type, "-->")
        label = RELATIONSHIP_LABELS.get(rel_type, "")

        from_cls = rel["from"]
        to_cls = rel["to"]

        if label:
            lines.append(f"{from_cls} {symbol} {to_cls} : {label}")
        else:
            lines.append(f"{from_cls} {symbol} {to_cls}")

    return lines


# -----------------------------
# Main Generator
# -----------------------------

def generate_plantuml(
    classes: Dict[str, Any],
    relationships: Union[List[Dict[str, Any]], Dict[str, Any]]
) -> str:

    if isinstance(relationships, dict):
        relationships = list(relationships.values())

    classes = _normalize_classes(classes)

    lines: List[str] = ["@startuml"]

    # classes
    for cls in classes.values():
        lines.extend(_build_class_block(cls))
        lines.append("")

        # inner classes (kept structural, not relationship-based)
        for inner in cls.get("inner_classes", []):
            lines.extend(_build_class_block(inner))
            lines.append("")

    # relationships
    if relationships:
        lines.extend(_build_relationships(relationships))
        lines.append("")

    lines.append("@enduml")

    return "\n".join(lines)
