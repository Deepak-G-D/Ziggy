# Ziggy

> **Effortless UML Class Diagram generation from Python source code.**

Ziggy is a Flask web application that takes a Python `.py` file, statically analyzes its AST (Abstract Syntax Tree), and produces a PlantUML class diagram — complete with attributes, methods, visibility markers, and class relationships (inheritance, composition, association, dependency, and inner classes).

---

## Features

- **Drag-and-drop file upload** — upload any `.py` file (up to 150 KB) via browser
- **Full AST-based analysis** — extracts classes, methods, attributes, type hints, decorators, docstrings, async methods, and more
- **Relationship detection** — automatically infers inheritance, composition, association, dependency, and inner-class relationships
- **Security-first** — static analysis blocks dangerous code patterns (`eval`, `exec`, `os.system`, `pickle.loads`, etc.) before processing
- **PlantUML rendering** — diagrams are rendered via the PlantUML public server with automatic fallback to Kroki
- **Download & fullscreen** — generated diagrams can be downloaded as PNG or previewed in fullscreen

---

## Project Structure

```
Ziggy/
├── app.py          # Flask app — routes, file upload, safety checks, PlantUML integration
├── main.py         # Orchestrator — ties extractor → transformer → puml_gen together
├── extractor.py    # AST visitor — extracts classes, methods, attributes, imports
├── transformer.py  # Relationship inference — inheritance, composition, association, etc.
├── puml_gen.py     # PlantUML text generation from extracted metadata
├── model.py        # Dataclasses — ClassInfo, FunctionInfo, AttributeInfo, etc.
├── static/
│   ├── style.css   # UI styles (warm serif theme)
│   └── script.js   # Drag-and-drop, file validation, loading bar
└── templates/
    └── index.html  # Jinja2 template — upload form and diagram display
```

---

## How It Works

```
.py file upload
     │
     ▼
[Safety Check]  ── dangerous code? ──► Error shown to user
     │
     ▼
[Extractor]  (extractor.py)
  AST visitor walks the parse tree:
  • Classes, bases, decorators, docstrings
  • Instance & class attributes with type hints
  • Methods: visibility, parameters, return types, async, decorators
     │
     ▼
[Transformer]  (transformer.py)
  Infers relationships:
  • Inheritance  (--|>)
  • Composition  (*--)
  • Association  (-->)
  • Dependency   (..>)
  • Inner class  (+--)
     │
     ▼
[PlantUML Generator]  (puml_gen.py)
  Produces @startuml ... @enduml text
     │
     ▼
[PlantUML Server / Kroki]
  Returns PNG diagram URL
     │
     ▼
[Browser]  — view, fullscreen, or download PNG
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
git clone https://github.com/Deepak-G-D/Ziggy.git
cd Ziggy
pip install flask plantuml requests
```

### Running the App

```bash
python app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

### Usage

1. Click or drag-and-drop a `.py` file onto the upload area
2. Click **Generate Diagram**
3. View the generated UML class diagram
4. Download as PNG or preview fullscreen

---

## Relationship Types Detected

| Relationship | PlantUML Symbol | Detected When |
|---|---|---|
| Inheritance | `--|>` | Class inherits from another class |
| Composition | `*--` | Instance attribute typed as another class |
| Association | `-->` | Method parameter typed as another class |
| Dependency | `..>` | Method uses another class internally |
| Inner Class | `+--` | Class defined inside another class |

---

## Security

Uploaded files are checked against a blocklist of dangerous Python patterns before any processing occurs:

- Blocked calls: `eval`, `exec`, `compile`, `__import__`, `subprocess`, `shutil.rmtree`
- Blocked attributes: `os.system`, `os.popen`, `subprocess.Popen`, `pickle.loads`, `marshal.loads`, `pty.spawn`
- File size limit: 150 KB
- Only `.py` files are accepted

---

## License

See [LICENSE](LICENSE) for details.

---

## Acknowledgements

Built with [Flask](https://flask.palletsprojects.com/), [PlantUML](https://plantuml.com/), and Python's built-in `ast` module.
