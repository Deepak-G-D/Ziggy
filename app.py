"""
Flask Application for Ziggy: Generate UML Class Diagrams from Python Code

This application allows users to upload a Python (.py) file, checks the file for potentially dangerous code,
and generates a UML class diagram using PlantUML. The diagram is displayed and can be downloaded or previewed.

Key Features:
- File upload with size and type validation
- Static analysis to block dangerous code patterns
- Uses PlantUML server to generate and serve diagrams
- Logging for debugging and security auditing

Routes:
- "/" (GET, POST): Main page for file upload and diagram display
- "/download": Download the generated diagram as a PNG file


"""

from main import run
import requests
from flask import Flask, request, render_template, send_file
import plantuml
import ast
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="ziggy_log.log",
    filemode="w"
)
logger = logging.getLogger(__name__)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Dangerous calls and attributes to block in uploaded code
DANGER_CALLS = [
    'eval', 'exec', 'subprocess',
    '__import__', 'compile', 'shutil.rmtree'
]
DANGER_ATTRS = {
    'os': {'system', 'popen'},
    'subprocess': {'Popen'},
    'shutil': {'rmtree'},
    'pickle': {'loads'},       # only loads, not load
    'marshal': {'loads'},      # only loads, not load
    'pty': {'spawn'}
}

MAX_FILE_SIZE = 150 * 1024  # 150KB

def is_safe(source: str) -> tuple:
    """
    Checks if the uploaded Python source code is safe to process.

    Args:
        source (str): The Python source code as a string.

    Returns:
        tuple: (True, None) if safe, (False, error_message) if not.
    """
    # File size check
    if len(source.encode('utf-8')) > MAX_FILE_SIZE:
        logger.error("File size exceeds the maximum limit")
        return False, "File too large! Maximum file size is 150KB."

    try:
        tree = ast.parse(source)
    except SyntaxError:
        logger.error("Invalid Python file!")
        return False, "Invalid Python file!"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Calls like eval(), exec(), etc.
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGER_CALLS:
                    logger.error(f"Dangerous call '{node.func.id}' detected!")
                    return False, f"Dangerous call '{node.func.id}' detected!"

            # Attribute calls like pickle.loads(), etc.
            elif isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    module = node.func.attr
                    if module in DANGER_ATTRS and attr in DANGER_ATTRS[module]:
                        logger.error(f"Dangerous call '{module}.{attr}' detected!")
                        return False, f" Dangerous call '{module}.{attr}' detected!"

    return True, None  # File is safe

# PlantUML server configuration
pl = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/png/')

def get_diagram_url(puml_txt):
    """
    Attempts to get a working PlantUML server URL for the generated diagram.

    Args:
        puml_txt (str): PlantUML text.

    Returns:
        str or None: URL to the diagram image, or None if all servers fail.
    """
    encoded = pl.get_url(puml_txt).split('/')[-1]
    servers = [
        f"http://www.plantuml.com/plantuml/png/{encoded}",
        f"https://www.plantuml.com/plantuml/png/{encoded}",
        f"https://kroki.io/plantuml/png/{encoded}"
    ]

    for url in servers:
        try:
            response = requests.get(url, timeout=6)
            if response.status_code == 200:  # Success
                return url
        except requests.exceptions.RequestException:
            continue
    return None

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main route for file upload and diagram generation.

    GET: Renders the upload form.
    POST: Processes the uploaded file, checks safety, generates diagram URL, and renders the result.
    """
    url = None
    error = None
    if request.method == "POST":
        app.logger.debug("Received file upload request")
        file = request.files["file"]
        source_code = file.read().decode('utf-8')
        
        if not file.filename.endswith('.py'):
            app.logger.warning("Rejected file upload: Invalid file type")
            return render_template("index.html", error="Only .py files are allowed!")
            
        is_file_safe, error = is_safe(source_code)
        if not is_file_safe:
            app.logger.warning(f"Rejected file upload: {error}") 
            return render_template("index.html", error=error)

        puml_txt = run(source_code)
        url = get_diagram_url(puml_txt)
        if url is None:
            error = "Could not render class diagram, please try again later!!!"
            app.logger.error("Failed to get diagram URL from all servers")
    app.logger.debug("Rendering index page with class diagram URL")
    return render_template("index.html", class_diagram=url, error=error)

@app.route('/download')
def download():
    """
    Downloads the diagram image from the provided URL and sends it as an attachment.

    Query Parameters:
        url (str): The URL of the diagram image.

    Returns:
        Flask response: The image file as a downloadable attachment.
    """
    image_url = request.args.get("url")
    response = requests.get(image_url)
    return send_file(
        BytesIO(response.content),
        mimetype='image/png',
        as_attachment=True,
        download_name='diagram.png'
    )

if __name__ == "__main__":  
    app.run(debug=True)

