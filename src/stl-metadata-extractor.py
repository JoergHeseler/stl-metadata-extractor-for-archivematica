# Title: stl-metadata-extractor
# Version: 1.0.0
# Publisher: NFDI4Culture
# Publication date: December 5, 2024
# License: CC BY 4.0
# Author: Joerg Heseler
# References: https://www.fabbers.com/tech/STL_Format#Sct_specs

import hashlib
import json
import os
import re
from datetime import datetime
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import math

SUCCESS_CODE = 0
ERROR_CODE = 1
DEBUG = 1

def get_target_file_name_from_arguments():
    for arg in sys.argv:
        if arg.startswith("--file-full-name="):
            return arg.split("=", 1)[1]
    return None

def calculate_checksum(file_path, algorithm='sha256'):
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def cross_product(v1, v2):
    return [
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0]
    ]

def vector_magnitude(v):
    return math.sqrt(sum(x ** 2 for x in v))

def normalize_vector(v):
    magnitude = vector_magnitude(v)
    if magnitude == 0:
        return [0, 0, 0]
    return [x / magnitude for x in v]

def are_vectors_close(v1, v2, tol=1e-9):
    return all(abs(a - b) <= tol for a, b in zip(v1, v2))

def angle_with_z_axis(normal):
    z_axis = [0, 0, 1]
    dot_prod = dot_product(normal, z_axis)
    normal_magnitude = vector_magnitude(normal)
    cos_theta = dot_prod / normal_magnitude
    angle_radians = math.acos(cos_theta)
    return math.degrees(angle_radians)

def is_facet_oriented_correctly(vertex1, vertex2, vertex3, normal):
    edge1 = [v2 - v1 for v1, v2 in zip(vertex1, vertex2)]
    edge2 = [v3 - v1 for v1, v3 in zip(vertex1, vertex3)]
    calculated_normal = normalize_vector(cross_product(edge1, edge2))
    normal = normalize_vector(normal)
    return are_vectors_close(calculated_normal, normal)

def ensure_counterclockwise(vertex1, vertex2, vertex3, normal):
    edge1 = [v2 - v1 for v1, v2 in zip(vertex1, vertex2)]
    edge2 = [v3 - v1 for v1, v3 in zip(vertex1, vertex3)]
    calculated_normal = cross_product(edge1, edge2)
    if dot_product(calculated_normal, normal) < 0:
        vertex2, vertex3 = vertex3, vertex2
    return vertex1, vertex2, vertex3

class STLValidatorException(Exception):
    def __init__(self, result):
        super().__init__(result)
        if DEBUG:
            print(result)

def print_warning(message):
    if DEBUG:
        print(f"Warning: {message}")

def print_error(message):
    raise STLValidatorException(message)

def extract_stl_metadata(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = [re.sub(r'\s+', ' ' , line.strip()) for line in file.readlines() if line.strip()]
        
        if not lines[0].startswith("solid"):
            print_error("File does not start with 'solid'.")

        model_name = str(lines[0][6:]).lstrip()        
        total_facet_count = (len(lines) - 2) // 7
        all_vertex_coordinates_are_positive = True
        all_facets_normals_are_correct = True
        all_vertices_of_facets_are_ordered_clockwise = True
        triangles = []

        for i in range(total_facet_count):
            y = i * 7 + 1
            normal = list(map(float, lines[y].split()[2:]))
            vertices = []
            for j in range(3):
                vertex = list(map(float, lines[y + 2 + j].split()[1:]))
                if any(coord < 0 for coord in vertex):
                    all_vertex_coordinates_are_positive = False
                vertices.append(vertex)
            triangles.append(vertices)
            if not is_facet_oriented_correctly(vertices[0], vertices[1], vertices[2], normal):
                all_facets_normals_are_correct = False
            if not ensure_counterclockwise(vertices[0], vertices[1], vertices[2], normal):
                all_vertices_of_facets_are_ordered_clockwise = False


        file_size = os.path.getsize(file_path)
        checksum = calculate_checksum(file_path)
        creation_date = datetime.utcfromtimestamp(os.path.getctime(file_path)).isoformat()
        modification_date = datetime.utcfromtimestamp(os.path.getmtime(file_path)).isoformat()

        root = ET.Element('STLMetadataExtractor', {
            'xmlns': "http://nfdi4culture.de/stl-metadata-extractor1",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xsi:schemaLocation': "http://nfdi4culture.de/stl-metadata-extractor1 schema_location_url"
        })

        # File metadata
        file_size = os.path.getsize(file_path)
        creation_date = datetime.utcfromtimestamp(os.path.getctime(file_path)).isoformat()
        modification_date = datetime.utcfromtimestamp(os.path.getmtime(file_path)).isoformat()
        checksum = calculate_checksum(file_path)

        # Create XML tree with namespace and schema location
        ET.register_namespace('', "http://nfdi4culture.de/stl-metadata-extractor1") # Register default namespace
        root = ET.Element('STLMetadataExtractor', {
            'xmlns': "http://nfdi4culture.de/stl-metadata-extractor1",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xsi:schemaLocation': "http://nfdi4culture.de/stl-metadata-extractor1 https://raw.githubusercontent.com/JoergHeseler/stl-metadata-extractor-for-archivematica/refs/heads/main/src/stl-metadata-extractor.xsd"
        })

        # Create XML tree
        ET.SubElement(root, 'formatName').text = 'STL'
        # ET.SubElement(root, 'formatVersion').text = ?
        ET.SubElement(root, 'size').text = str(file_size)
        ET.SubElement(root, 'SHA256Checksum').text = checksum
        ET.SubElement(root, 'creationDate').text = creation_date
        ET.SubElement(root, 'modificationDate').text = modification_date
        # 3D metadata
        ET.SubElement(root, 'totalTriangleCount').text = str(total_facet_count)
        # Validation specific metadata
        ET.SubElement(root, 'allVerticesOfFacetsAreOrderedClockwise').text = str(all_vertices_of_facets_are_ordered_clockwise).lower()
        ET.SubElement(root, 'allFacetNormalsAreCorrect').text = str(all_facets_normals_are_correct).lower()
        ET.SubElement(root, 'allVertexCoordinatesArePositive').text = str(all_vertex_coordinates_are_positive).lower()

        # Convert ElementTree to minidom document for CDATA support
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_str)
        
        # Print formatted XML with CDATA
        print(dom.toprettyxml(indent="    "))
        return SUCCESS_CODE

    except STLValidatorException as e:
        print(json.dumps({"eventOutcomeInformation": "fail", "eventOutcomeDetailNote": str(e)}), file=sys.stderr)
        return ERROR_CODE

if __name__ == '__main__':
    target = get_target_file_name_from_arguments()
    if not target:
        print("No argument with --file-full-name= found.", file=sys.stderr)
    else:
        sys.exit(extract_stl_metadata(target))
