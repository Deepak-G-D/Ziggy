from extractor import analyze_py_source
from transformer import rel, get_classes
from puml_gen import generate_plantuml

import logging
logger = logging.getLogger(__name__)

def run(source: str):
    data = analyze_py_source(source)  # changed from analyze_py_file
    logger.info("Analyzed Python source code successfully!!!")
    cls_info_dict = get_classes(data)
    relationships = rel(data)
    logger.info("Extracted classes and relationships successfully!!!")
    puml_txt = generate_plantuml(cls_info_dict, relationships)
    logger.info("Generated PlantUML text successfully!!!")
    #for debugging .puml txt
    with open("debug.puml", "w") as f:
        f.write(puml_txt)
        
    return puml_txt
