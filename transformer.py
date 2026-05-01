import logging
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)

def rel(
    data: Union[Tuple[Dict[str, Any], Dict[str, Any]], List[Any], None]
) -> List[Dict[str, Any]]:
    """
    Extract relationships between classes from parsed data.

    Args:
        data: A tuple or list containing (imports dict, classes dict).

    Returns:
        List[Dict[str, Any]]: List of relationship dicts with keys: rel_type, from, to.
    """
    if not data or len(data) < 2:
        return []

    imports, classes = data[0], data[1]

    if not isinstance(imports, dict) or not isinstance(classes, dict):
        logger.error(
            f"Invalid data format: Expected dicts for imports and classes, got {type(imports).__name__} and {type(classes).__name__}."
        )
        raise TypeError(
            f"Expected imports and classes to be dicts, "
            f"got {type(imports).__name__} and {type(classes).__name__}."
        )

    logger.info(f"Classes found: {list(classes.keys())}")
    logger.info(f"Imports found: {imports}")

    cls_names: List[str] = list(classes.keys())
    relations: List[Dict[str, Any]] = []
    import_names: List[str] = []

    # Extract import names robustly
    for info in imports.values():
        if hasattr(info, "func_name") and info.func_name:
            import_names.extend(info.func_name)
        elif isinstance(info, dict) and "func_name" in info and info["func_name"]:
            import_names.extend(info["func_name"])

    def add_relation(relations: List[Dict[str, Any]], new_rel: Dict[str, Any]) -> None:
        """
        Adds a relationship to the list, handling conflicts and deduplication.
        """
        for r in relations:
            if r["from"] == new_rel["from"] and r["to"] == new_rel["to"]:
                if new_rel["rel_type"] in ("inheritance", "inner_class"):
                    return
                if r["rel_type"] == "composition":
                    return
                if r["rel_type"] == "association" and new_rel["rel_type"] == "dependency":
                    return
                if r["rel_type"] == "dependency" and new_rel["rel_type"] == "association":
                    relations.remove(r)
                    break
                if r["rel_type"] == "association" and new_rel["rel_type"] == "composition":
                    relations.remove(r)
                    break
        relations.append(new_rel)

    def get_base_type(t: Any) -> Any:
        """
        Extracts the base type from a possibly generic type string.
        """
        if not t or not isinstance(t, str):
            return t
        return t.split("[")[-1].replace("]", "").replace("'", "")

    # Inheritance
    for name, info in classes.items():
        for base in getattr(info, "bases", []):
            base_name = base.split("[")[0]
            if base_name in cls_names or base_name in import_names:
                add_relation(relations, {
                    "rel_type": "inheritance",
                    "from": name,
                    "to": base_name
                })

    # Composition
    for name, info in classes.items():
        for instance, attr in getattr(info, "instance_attributes", {}).items():
            attr_type = getattr(attr, "type", None)
            if attr_type in cls_names:
                is_association = False
                for method_info in getattr(info, "methods", {}).values():
                    for param in getattr(method_info, "parameters", []):
                        if param.name == instance and getattr(param, "ann_type", None) == attr_type:
                            is_association = True
                            break
                    if is_association:
                        break
                if not is_association:
                    add_relation(relations, {
                        "rel_type": "composition",
                        "from": name,
                        "to": attr_type
                    })

    # Association
    for name, info in classes.items():
        for method_info in getattr(info, "methods", {}).values():
            for p in getattr(method_info, "parameters", []):
                if getattr(p, "ann_type", None) in cls_names:
                    if p.name in getattr(info, "instance_attributes", {}):
                        add_relation(relations, {
                            "rel_type": "association",
                            "from": name,
                            "to": p.ann_type
                        })

    # Dependency
    for name, info in classes.items():
        for method_name, method_info in getattr(info, "methods", {}).items():
            if method_name == "__init__":
                continue
            for called in getattr(method_info, "local_var", []):
                if called in cls_names and called != name:
                    add_relation(relations, {
                        "rel_type": "dependency",
                        "from": name,
                        "to": called
                    })

    # Self-reference
    for name, info in classes.items():
        for attr in getattr(info, "instance_attributes", {}).values():
            base_type = get_base_type(getattr(attr, "type", None))
            if base_type == name:
                add_relation(relations, {
                    "rel_type": "association",
                    "from": name,
                    "to": name
                })

    # Inner classes
    for name, info in classes.items():
        for inner in getattr(info, "inner_classes", []):
            add_relation(relations, {
                "rel_type": "inner_class",
                "from": name,
                "to": getattr(inner, "name", None)
            })

    # Remove duplicates
    unique: List[Dict[str, Any]] = []
    seen = set()
    for r in relations:
        key = (r["rel_type"], r["from"], r["to"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique

def get_classes(data: Union[Tuple[Any, Any], List[Any]]) -> Any:
    """
    Returns the classes dictionary from the input tuple/list.
    """
    if not data or len(data) < 2:
        return None
    return data[1]
