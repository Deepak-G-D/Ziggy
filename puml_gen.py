from dataclasses import asdict
from typing import Any, Dict, List, Union

visibility_Symbols: Dict[str, str] = {
    "public": "+",
    "private": "-",
    "protected": "#"
}

relationship_Symbol: Dict[str, str] = {
    "composition": "*--",
    "association": "-->",
    "dependency": "..>",
    "inheritance": "--|>",
    "inner_class": "+--"
}

relationship_Labels: Dict[str, str] = {
    "composition": "has",
    "association": "uses",
    "dependency": "depends on",
    "inheritance": "is a",
    "inner_class": "contains"
}

def _format_parameters(params: List[Dict[str, Any]]) -> str:
    """
    Formats function/method parameters for PlantUML, excluding 'self'.
    """
    res: List[str] = []
    for p in params:
        if p["name"] == "self":
            continue
        if p.get("ann_type"):
            res.append(f"{p['name']}: {p['ann_type']}")
        else:
            res.append(p['name'])
    return ", ".join(res)

def _format_type_ann(type_: Any) -> str:
    """
    Formats a type annotation for PlantUML.
    """
    if type_:
        return f": {type_}"
    else:
        return ""

def _build_cls_bloc(cls: Dict[str, Any]) -> List[str]:
    """
    Builds the PlantUML block for a class, including attributes and methods.
    """
    lines: List[str] = []
    stereotype = ""
    if cls.get("decorators"):
        stereotype = f"<<{','.join(cls['decorators'])}>>"

    header = f"class {cls['name']}"
    if stereotype.strip():
        header += f"{stereotype.strip()}"
    lines.append(header + " {")

    # Docstring
    if cls.get("docstring"):
        lines.append(f"  .. {cls['docstring']} ..")

    # Class attributes
    for attr in cls.get("cls_attributes", {}).values():
        vis = visibility_Symbols.get(attr.get("visibility", "public"), "+")
        type_str = _format_type_ann(attr.get("type"))
        lines.append(f"  {vis} {attr['name']}{type_str}")

    # Instance attributes
    for attr in cls.get("instance_attributes", {}).values():
        vis = visibility_Symbols.get(attr.get("visibility", "public"), "+")
        type_str = _format_type_ann(attr.get("type"))
        lines.append(f"  {vis} {attr['name']}{type_str}")

    # Methods
    for method in cls.get("methods", {}).values():
        if method["name"] == "__init__":
            continue
        vis = visibility_Symbols.get(method.get("visibility", "public"), "+")
        params = _format_parameters(method.get("parameters", []))
        return_type = _format_type_ann(method.get("return_type"))

        decorators = method.get("decorators", [])
        dec_str = f" <<{'|'.join(decorators)}>>" if decorators else ""
        async_str = " {async}" if method.get("is_async") else ""

        lines.append(f"  {vis} {method['name']}({params}){return_type}{dec_str}{async_str}")

    lines.append("}")
    return lines

def _generate_relationships(relationships: List[Dict[str, Any]]) -> List[str]:
    """
    Generates PlantUML lines for class relationships.
    """
    lines: List[str] = []
    for rel in relationships:
        symbol = relationship_Symbol.get(rel["rel_type"], "-->")
        label = relationship_Labels.get(rel["rel_type"], "")
        lines.append(f"{rel['from']} {symbol} {rel['to']} : {label}")
    return lines

def generate_plantuml(
    classes: Dict[str, Any],
    relationships: Union[List[Dict[str, Any]], Dict[str, Any]]
) -> str:
    """
    Generates a PlantUML class diagram from class and relationship metadata.

    Args:
        classes (Dict[str, Any]): Dictionary of class metadata.
        relationships (List[Dict[str, Any]] or Dict[str, Any]): List or dict of relationship metadata.

    Returns:
        str: PlantUML diagram as a string.
    """
    # Convert relationships dict to list if needed
    if isinstance(relationships, dict):
        relationships = list(relationships.values())

    classes = {k: asdict(v) for k, v in classes.items()}
    lines: List[str] = ["@startuml"]

    for cls in classes.values():
        lines.extend(_build_cls_bloc(cls))
        lines.append("")
        for inner in cls.get("inner_classes", []):
            lines.extend(_build_cls_bloc(inner))
            lines.append("")

    if relationships:
        lines.extend(_generate_relationships(relationships))
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)
