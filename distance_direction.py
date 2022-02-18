"""
AUTHOR(S):    Zofie Cimburova
PURPOSE:      Computes distance and direction from trees (points)
to three nearest buildings (polygons) within defined distance
COPYRIGHT:    (C) 2022 by Zofie Cimburova
REFERENCES:   Cimburova, Z., Barton, D.N., 2020. The potential
of geospatial analysis and Bayesian networks to enable i-Tree Eco
assessment of existing tree inventories. Urban Forestry and Urban
Greening. 55, 126801. https://doi.org/10.1016/j.ufug.2020.126801
"""

import arcpy
from arcpy import env
import random
import string


# Check if field exists
def FieldExist(featureclass, fieldname):
    fieldList = arcpy.ListFields(featureclass, fieldname)
    fieldCount = len(fieldList)

    if fieldCount == 1:
        return True
    else:
        return False


# Join table 2 to table 1 and copy source fields from table 2 to destination
# fields of table 1
def join_and_copy(
    table_to, key_to, table_from, key_from, field_list_from, field_list_to
):
    name1 = arcpy.Describe(table_to).name
    name2 = arcpy.Describe(table_from).name

    # Create layer from table_to
    layer1 = tempname(9)
    arcpy.MakeFeatureLayer_management(table_to, layer1)

    # Create join
    arcpy.AddJoin_management(layer1, key_to, table_from, key_from)

    i = 0
    for source_field in field_list_from:
        arcpy.CalculateField_management(
            layer1,
            "{}.{}".format(name1, field_list_to[i]),
            "[{}.{}]".format(name2, field_list_from[i]),
        )
        i = i + 1


# Create a random temporary name
def tempname(length):
    characters = string.ascii_letters + string.digits
    suffix = "".join(random.choice(characters) for i in range(length))
    tempname = "tmp_" + suffix
    return tempname


# ==============================================================
# Workspace settings
# ==============================================================
env.overwriteOutput = True
env.workspace = "in_memory"


# ==============================================================
# Input data
# ==============================================================
# Trees (points, must contain "OBJECTID")
v_trees = arcpy.GetParameterAsText(0)

# Buildings (polygons)
v_buildings = arcpy.GetParameterAsText(1)

# Number of nearest buildings
n_buildings = 3

# Maximum distance [m]
max_dist = 18


# ==============================================================
# Add fields to store distance and direction values
# ==============================================================
for i in range(1, n_buildings + 1):
    field_dist = "BLD_DIST_{}".format(i)
    field_dir = "BLD_DIR_{}".format(i)

    if not FieldExist(v_trees, field_dist):
        arcpy.AddField_management(v_trees, field_dist, "Float")
    if not FieldExist(v_trees, field_dir):
        arcpy.AddField_management(v_trees, field_dir, "Float")


# ==============================================================
# Compute near table
# ==============================================================
t_near = tempname(12)
arcpy.GenerateNearTable_analysis(
    v_trees,
    v_buildings,
    t_near,
    search_radius="{} Meters".format(max_dist),
    location="NO_LOCATION",
    angle="ANGLE",
    closest="ALL",
    closest_count="{}".format(n_buildings),
    method="PLANAR",
)

# ==============================================================
# Calculate azimuth from angle
# ==============================================================
azimuth = tempname(5)
arcpy.AddField_management(t_near, azimuth, "Float")

codeblock = """def toAzimuth(angle):
    azimuth = -1*angle+90
    if azimuth < 0:
        return 360+ azimuth
    else:
        return azimuth"""

arcpy.CalculateField_management(
    t_near,
    azimuth,
    "toAzimuth(!NEAR_ANGLE!)",
    "PYTHON_9.3",
    codeblock,
)

# ==============================================================
# Split near table and copy attributes to trees
# ==============================================================
for i in range(1, n_buildings + 1):
    t_near_i = "{}_{}".format(tempname(5), i)
    arcpy.TableToTable_conversion(
        t_near,
        env.workspace,
        t_near_i,
        "NEAR_RANK = {}".format(i),
    )

    join_and_copy(
        v_trees,
        "OBJECTID",
        t_near_i,
        "IN_FID",
        ["NEAR_DIST", azimuth],
        ["BLD_DIST_{}".format(i), "BLD_DIR_{}".format(i)],
    )

    arcpy.Delete_management(t_near_i)

arcpy.Delete_management(t_near)
