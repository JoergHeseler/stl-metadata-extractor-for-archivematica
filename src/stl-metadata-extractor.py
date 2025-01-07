# Title: stl-metadata-extractor
# Version: 1.0.0
# Publisher: NFDI4Culture
# Publication date: December 5, 2024
# License: CC BY-SA 4.0
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
import struct

SUCCESS_CODE = 0
ERROR_CODE = 1
DEBUG = 1

######################## GEOMETRY FUNCTIONS ########################

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

# New feature: Recalculate facet normal if invalid
def recalculate_normal(vertex1, vertex2, vertex3):
    """
    Recalculates the normal vector for a given facet using the cross product.
    """
    edge1 = [v2 - v1 for v1, v2 in zip(vertex1, vertex2)]
    edge2 = [v3 - v1 for v1, v3 in zip(vertex1, vertex3)]
    return normalize_vector(cross_product(edge1, edge2))

def are_vectors_close(v1, v2, tol=1e-3):
    return all(abs(a - b) <= tol for a, b in zip(v1, v2))

# def is_facet_oriented_correctly(vertex1, vertex2, vertex3, normal):
#     edge1 = [v2 - v1 for v1, v2 in zip(vertex1, vertex2)]
#     edge2 = [v3 - v1 for v1, v3 in zip(vertex1, vertex3)]
#     calculated_normal = normalize_vector(cross_product(edge1, edge2))
#     normal = normalize_vector(normal)
#     return are_vectors_close(calculated_normal, normal)

# def ensure_counterclockwise(vertex1, vertex2, vertex3, normal):
#     edge1 = [v2 - v1 for v1, v2 in zip(vertex1, vertex2)]
#     edge2 = [v3 - v1 for v1, v3 in zip(vertex1, vertex3)]
#     calculated_normal = cross_product(edge1, edge2)
#     if dot_product(calculated_normal, normal) < 0:
#         vertex2, vertex3 = vertex3, vertex2
#     return vertex1, vertex2, vertex3

def is_counterclockwise(vertex1, vertex2, vertex3, normal):
    edge1 = [v2 - v1 for v1, v2 in zip(vertex1, vertex2)]
    edge2 = [v3 - v1 for v1, v3 in zip(vertex1, vertex3)]
    calculated_normal = cross_product(edge1, edge2)
    return dot_product(calculated_normal, normal) > 0

# New feature: Detect non-manifold geometry
# def count_shared_edges_optimized(facets):
#     """
#     Optimized detection of shared edges between facets using a hash table.
#     """
#     edge_count = {}
#     for facet in facets:
#         # Extract edges as sorted tuples to ensure consistent order
#         edges = [
#             tuple(sorted((tuple(facet[1]), tuple(facet[2])))),
#             tuple(sorted((tuple(facet[2]), tuple(facet[3])))),
#             tuple(sorted((tuple(facet[3]), tuple(facet[1]))))
#         ]
#         for edge in edges:
#             if edge in edge_count:
#                 edge_count[edge] += 1
#             else:
#                 edge_count[edge] = 1

#     # Count edges shared by more than two facets (non-manifold)
#     non_manifold_edges = [edge for edge, count in edge_count.items() if count > 2]
#     return len(non_manifold_edges), non_manifold_edges


def is_model_manifold(facets):
    edge_usage = {}

    # Step 1: Count usage of each edge
    for facet in facets:
        edges = [
            tuple(sorted((tuple(facet[1]), tuple(facet[2])))),
            tuple(sorted((tuple(facet[2]), tuple(facet[3])))),
            tuple(sorted((tuple(facet[3]), tuple(facet[1]))))
        ]
        for edge in edges:
            if edge in edge_usage:
                edge_usage[edge] += 1
            else:
                edge_usage[edge] = 1

    # Step 2: Analyze edge usage
    non_manifold_edges = {edge: count for edge, count in edge_usage.items() if count != 2}
    is_manifold = len(non_manifold_edges) == 0

    # # Step 3: Return result
    # report = {
    #     "is_manifold": is_manifold,
    #     "non_manifold_edges": non_manifold_edges,
    #     "total_edges": len(edge_usage),
    #     "non_manifold_edge_count": len(non_manifold_edges),
    # }

    return is_manifold #, report

######################## STL FUNCTIONS ########################

def is_binary_stl(file_path):
    # Check if the STL file is binary or ASCII.
    with open(file_path, 'rb') as file:
        file_size = os.path.getsize(file_path)
        file.read(80).decode('ascii', errors='ignore')
        try:
            triangle_count = struct.unpack('<I', file.read(4))[0]
        except struct.error:
            return False
        return 80 + 4 + 50 * triangle_count == file_size

def extract_binary_stl_metadata(file_path):
    # Extract metadata from a binary STL file.
    with open(file_path, 'rb') as file:
        header = file.read(80).decode('ascii', errors='ignore').strip()
        solid_name = re.sub(r'[^\x20-\x7E]', '', header)
        triangle_count = struct.unpack('<I', file.read(4))[0]
        has_valid_positive_vertice_coordinates = True
        has_valid_counterclockwise_vertices = True
        has_valid_normals = True
        has_valid_manifold_edges = True

        facets = []

        for _ in range(triangle_count):
            data = struct.unpack('<12fH', file.read(50)) # Normal vector (3 floats), vertices (9 floats), attribute byte count
            normal = data[0:3]
            vertex1 = data[3:6]
            vertex2 = data[6:9]
            vertex3 = data[9:12]
            vertices = data[3:12] # Skip normal vector
            if not is_counterclockwise(vertex1, vertex2, vertex3, normal):
                has_valid_counterclockwise_vertices = False
            if any(v < 0 for v in vertices):
                has_valid_positive_vertice_coordinates = False
            # Validate normals
            recalculated_normal = recalculate_normal(vertex1, vertex2, vertex3)
            if not are_vectors_close(normal, recalculated_normal):
                normal = recalculated_normal # Fix invalid normals
                has_valid_normals = False
            
            facets.append([normal, vertex1, vertex2, vertex3])


        # # Optimized non-manifold detection
        # non_manifold_count, non_manifold_edges = count_shared_edges_optimized(facets)
        # if non_manifold_count > 0:
        #     has_valid_manifold_edges = False

        has_valid_manifold_edges = is_model_manifold(facets)



    return {
        "solid_name": solid_name,
        "total_triangle_count": triangle_count,
        "has_valid_positive_vertice_coordinates": has_valid_positive_vertice_coordinates,
        "has_valid_counterclockwise_vertices": has_valid_counterclockwise_vertices,
        "has_valid_normals": has_valid_normals,
        "has_valid_manifold_edges" : has_valid_manifold_edges
    }

def extract_ascii_stl_metadata(file_path):
    # Extract metadata from an ascii STL file.
    with open(file_path, 'r') as file:
        lines = [re.sub(r'\s+', ' ' , line.strip()) for line in file.readlines() if line.strip()]
    
    if not lines[0].startswith("solid"):
        print_error("File does not start with 'solid'.")

    solid_name = str(lines[0][6:]).lstrip()
    total_facet_count = (len(lines) - 2) // 7
    has_valid_positive_vertice_coordinates = True
    has_valid_counterclockwise_vertices = True
    has_valid_normals = True
    has_valid_manifold_edges = True

    facets = []

    for i in range(total_facet_count):
        y = i * 7 + 1
        normal = list(map(float, lines[y].split()[2:]))
        vertices = []
        for j in range(3):
            vertex = list(map(float, lines[y + 2 + j].split()[1:]))
            if any(coord < 0 for coord in vertex):
                has_valid_positive_vertice_coordinates = False
            vertices.append(vertex)
        if not is_counterclockwise(vertices[0], vertices[1], vertices[2], normal):
            has_valid_counterclockwise_vertices = False
        # Validate normals
        recalculated_normal = recalculate_normal(vertices[0], vertices[1], vertices[2])
        if not are_vectors_close(normal, recalculated_normal):
            normal = recalculated_normal # Fix invalid normals
            has_valid_normals = False

        facets.append([normal, vertices[0], vertices[1], vertices[2]])

    # # Optimized non-manifold detection
    # non_manifold_count, non_manifold_edges = count_shared_edges_optimized(facets)
    # if non_manifold_count > 0:
    #     has_valid_manifold_edges = False

    has_valid_manifold_edges = is_model_manifold(facets)


    return {
        "solid_name": solid_name,
        "total_triangle_count": total_facet_count,
        "has_valid_positive_vertice_coordinates": has_valid_positive_vertice_coordinates,
        "has_valid_counterclockwise_vertices": has_valid_counterclockwise_vertices,
        "has_valid_normals": has_valid_normals,
        "has_valid_manifold_edges" : has_valid_manifold_edges
    }

######################## COMMON METDATA EXTRACTOR FUNCTIONS ######################## 

def get_target_file_name_from_arguments():
    for arg in sys.argv:
        if arg.startswith("--file-full-name="):
            return arg.split("=", 1)[1]
    return sys.argv[1]

def calculate_checksum(file_path, algorithm='sha256'):
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def print_warning(message):
    if DEBUG:
        print(f"Warning: {message}")

def print_error(message):
    raise STLValidatorException(message)

######################## SPECIFIC METDATA EXTRACTOR FUNCTIONS ######################## 

class STLValidatorException(Exception):
    def __init__(self, result):
        super().__init__(result)
        if DEBUG:
            print(result)

def extract_stl_metadata(file_path):
    # Main function to extract STL metadata.
    try:
        if is_binary_stl(file_path):
            metadata = extract_binary_stl_metadata(file_path)
            format_version = 'binary'
        else:
            metadata = extract_ascii_stl_metadata(file_path)
            format_version = 'ASCII'

        file_size = os.path.getsize(file_path)
        checksum = calculate_checksum(file_path)
        creation_date = datetime.utcfromtimestamp(os.path.getctime(file_path)).isoformat()
        modification_date = datetime.utcfromtimestamp(os.path.getmtime(file_path)).isoformat()

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
        ET.SubElement(root, 'formatName').text = 'STL (Standard Tessellation Language)'
        ET.SubElement(root, 'formatVersion').text = format_version
        ET.SubElement(root, 'size').text = str(file_size)
        ET.SubElement(root, 'SHA256Checksum').text = checksum
        ET.SubElement(root, 'creationDate').text = creation_date
        ET.SubElement(root, 'modificationDate').text = modification_date
        # 3D metadata
        ET.SubElement(root, 'solidName').text = metadata.get("solid_name")
        ET.SubElement(root, 'totalTriangleCount').text = str(metadata["total_triangle_count"])
        # Validation specific metadata
        ET.SubElement(root, 'hasValidCounterclockwiseVertices').text =  str(metadata["has_valid_counterclockwise_vertices"]).lower()
        ET.SubElement(root, 'hasValidPositiveVerticeCoordinates').text = str(metadata["has_valid_positive_vertice_coordinates"]).lower()
        ET.SubElement(root, 'hasValidNormals').text = str(metadata["has_valid_normals"]).lower()
        ET.SubElement(root, 'hasValidManifoldEdges').text = str(metadata["has_valid_manifold_edges"]).lower()

        # Convert ElementTree to minidom document for CDATA support
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_str)
        
        # Print formatted XML with CDATA
        print(dom.toprettyxml(indent="    "))
        return SUCCESS_CODE

    except STLValidatorException as e:
        print(json.dumps({"eventOutcomeInformation": "fail", "eventOutcomeDetailNote": str(e)}), file=sys.stderr)
        return ERROR_CODE

######################## MAIN FUNCTION ########################

if __name__ == '__main__':
    target = get_target_file_name_from_arguments()
    sys.exit(extract_stl_metadata(target))
