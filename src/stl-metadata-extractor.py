# Title: stl-validator
# Version: 1.0.0
# Publisher: NFDI4Culture
# Publication date: 2024, May 21th
# License: CC BY 4.0
# Author: Joerg Heseler
# References: https://www.fabbers.com/tech/STL_Format#Sct_specs


from __future__ import print_function
import json
import subprocess
import sys
from lxml import etree
import re
import math
import numpy as np


SUCCESS_CODE = 0
ERROR_CODE = 1
DEBUG = 1


def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def vector_magnitude(v):
    return math.sqrt(sum(x ** 2 for x in v))

def angle_with_z_axis(normal):
    # Z-axis vector
    z_axis = [0, 0, 1]
    
    # Calculate the dot product and the magnitude of the normal vector
    dot_prod = dot_product(normal, z_axis)
    normal_magnitude = vector_magnitude(normal)
    
    # Calculate the cosine of the angle
    cos_theta = dot_prod / normal_magnitude # The magnitude of the Z-axis vector is 1
    
    # Calculate the angle in radians
    angle_radians = math.acos(cos_theta)
    
    # Convert the angle to degrees
    angle_degrees = math.degrees(angle_radians)
    
    return angle_degrees

def is_facet_oriented_correctly(vertex1, vertex2, vertex3, normal):
    # Create vectors for two edges of the triangle
    edge1 = np.subtract(vertex2, vertex1)
    edge2 = np.subtract(vertex3, vertex1)

    # Calculate the cross product of the edges to get the normal vector
    calculated_normal = np.cross(edge1, edge2)

    # Normalize the vectors
    calculated_normal = calculated_normal / np.linalg.norm(calculated_normal)
    normal = normal / np.linalg.norm(normal)

    # Check if the calculated normal matches the provided normal (points outward)
    return np.allclose(calculated_normal, normal)


def ensure_counterclockwise(vertex1, vertex2, vertex3, normal):
    # Create vectors for two edges of the triangle
    edge1 = np.subtract(vertex2, vertex1)
    edge2 = np.subtract(vertex3, vertex1)

    # Calculate the cross product of the edges to get the normal vector
    calculated_normal = np.cross(edge1, edge2)

    # Check if the normal is pointing outward (using the dot product)
    dot_product = np.dot(calculated_normal, normal)
    
    if dot_product < 0:
        # If the normal is pointing inward, reverse the order of the vertices
        vertex2, vertex3 = vertex3, vertex2

    return vertex1, vertex2, vertex3


class STLValidatorException(Exception):
    
    def __init__(self, result):
        super().__init__(result)
        if DEBUG:
            print(result)
        
    # def __init__(self, y, expected, got):
        # super().__init__(result)
        # if DEBUG:
            # print(result)

warning_count = 0
errors_count = 0
first_error_message = ""
# stop_on_first_error = False

def print_info(y, message):
    global warning_count
    print(f"Warning on line {y + 1}: {message}")
    warning_count += 1
    
def print_warning(y, expected, got):
    global warning_count
    print(f"Warning on line {y + 1}: Expected '{expected}' but got '{got.strip()}'.")
    warning_count += 1
    
def print_error(y, expected, got):
    global errors_count
    global first_error_message
    global stop_on_first_error
    if first_error_message == "":
        first_error_message = f"line {y + 1}: Expected '{expected}' but got '{got.strip()}'."
    error_message = f"Error on {first_error_message}"
    errors_count += 1
    # if stop_on_first_error:
    raise STLValidatorException(error_message)
    # else:
    # print(error_message)


def has_isolated_triangle(triangles):
    for i, tri1 in enumerate(triangles):
        shared_count = 0
        for j, tri2 in enumerate(triangles):
            if i != j:
                shared_vertices = set(tuple(v) for v in tri1).intersection(set(tuple(v) for v in tri2))
                if len(shared_vertices) == 2:
                    shared_count += 1
                    break

        if shared_count == 0:
            return True # i, tri1 # Found a triangle that does not share two vertices

    return False # None, None # All triangles share vertices




def format_event_outcome_detail_note(format, version, result):
    note = 'format="{}";'.format(format)
    if version is not None:
        note = note + ' version="{}";'.format(version)
    if result is not None:
        note = note + ' result="{}"'.format(result)

    return note

def main(target):
    try:
        with open(target, 'r') as file:
            lines = file.readlines()
                                 
        lines = [line.strip() for line in lines]
        
        y = 0
        if not lines[y].startswith("solid"):
            print_error(y, "solid", lines[y])     
        if not re.search(f"^solid [^\n]+$", lines[y]):
            print_warning(y, "solid <string>", lines[y])
            name = ""
        else:
            name = str(lines[y][6:]).lstrip()
        y += 1
        
        # The notation, “{…}+,” means that the contents of the brace brackets
        # can be repeated one or more times.
        # --> Changed by the author to “{…}*”, meaning that the contents of the
        # brace brackets can be repeated none, one or more times, to support
        # empty scenes as many programs are able to export.

        all_facets_normals_are_correct = True
        all_vertices_of_facets_are_ordered_clockwise = True
        total_facet_count = int((len(lines) - 2) / 7)

        old_angle = 0.0

        triangles = []
        for i in range(total_facet_count):
            if not re.search(f"^facet normal -?\d*(\.\d+)?([Ee][+-]?\d+)? -?\d*(\.\d+)?([Ee][+-]?\d+)? -?\d*(\.\d+)?([Ee][+-]?\d+)?$", lines[y]):
                print_error(y, "facet normal <float> <float> <float>", lines[y])
            parts = lines[y].split(' ')
            normal = np.array(list(map(float, parts[2:])))

            y += 1
            if not "outer loop" == lines[y]:
                print_error(y, "outer loop", lines[y])
            y += 1

            vertices = []
            for j in range(3):
            
                # A facet normal coordinate may have a leading minus sign; 
                # a vertex coordinate may not.
                # --> Changed by the author to vertex coordinates may have a
                # leading minus, to support negative vertices to support many
                # programs are able to export
                if not re.search(f"^vertex -?\d*(\.\d+)?([Ee][+-]?\d+)? -?\d*(\.\d+)?([Ee][+-]?\d+)? -?\d*(\.\d+)?([Ee][+-]?\d+)?$", lines[y]):
                    print_error(y, "vertex <unsigned float> <unsigned float> <unsigned float>", lines[y])
                parts = lines[y].split(' ')
                vertices += [np.array(list(map(float, parts[1:])))]
                y += 1

            triangles += [vertices]
            # Check if the facet is oriented correctly
            if not is_facet_oriented_correctly(vertices[0], vertices[1], vertices[2], normal):
                all_facets_normals_are_correct = False
                print_info(y, message="The facet is not oriented correctly.")

            #angle = angle_with_z_axis(normal)
            if not ensure_counterclockwise(vertices[0], vertices[1], vertices[2], normal):
                all_vertices_of_facets_are_ordered_clockwise = False
            # old_angle = angle
            # print(f"The angle between the normal and the Z-axis is: {angle_z:.2f} degrees")



            if not "endloop" == lines[y]:
                print_error(y, "endloop", lines[y])
            y += 1
            if not "endfacet" == lines[y]:
                print_error(y, "endfacet", lines[y])
            y += 1
        if not re.search("^endsolid", lines[y]):
            print_error(y, "endsolid", lines[y])
        if name != "":
            if not f"endsolid {name}" == lines[y]:
                print_error(y, f"endsolid {name}", lines[y])
        y += 1

        
        if errors_count >= 1:
            raise STLValidatorException(f"STL file validation failed, errors: {errors_count}, warnings: {warning_count}, first error on {first_error_message}")

            
        format = "STL"
        version = "1.0"
        
        note = format_event_outcome_detail_note(format, version, f"errors: {errors_count}, warnings: {warning_count}")

        print(
            json.dumps(
                {
                    "eventOutcomeInformation": "pass",
                    "eventOutcomeDetailNote": note,
                    "stdout": target + " validates.",
                }
            )
        )

        print(f"totalVertexCount: {total_facet_count * 3}")  
        print(f"totalTriangleCount: {total_facet_count}")
        print(f"allVerticesOfFacetsAreOrderedClockwise: {all_vertices_of_facets_are_ordered_clockwise}")
        print(f"allFacetNormalsAreCorrect: {all_facets_normals_are_correct}")
        print(f"hasIsolatedTriangle: {has_isolated_triangle(triangles)}")
        return SUCCESS_CODE
    except STLValidatorException as e:
        print(
            json.dumps(
                {
                    "eventOutcomeInformation": "fail",
                    "eventOutcomeDetailNote": str(e),
                    "stdout": None,
                }
            ),
            file=sys.stderr,
        )
        return ERROR_CODE

if __name__ == "__main__":
    target = sys.argv[1]
    sys.exit(main(target))
