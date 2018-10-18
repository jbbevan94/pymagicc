"""
This module contains all of the relevant definitions for handling MAGICC data.

The definitions are given in `Data Packages <https://frictionlessdata.io/docs/
creating-tabular-data-packages-in-python/>`_. These store the data in an easy to read
CSV file whilst providing comprehensive metadata describing the data (column meanings
and expected types) in the accompanying ``datapackage.json`` file. Please see this
metadata for further details.

For more details about how these constants are used, see the documentation of
``pymagicc.io``. In particular, the documentation of
``pymagicc.io.get_special_scen_code``, ``pymagicc.io.get_dattype_regionmode`` and
``pymagicc.io.get_region_order`` in :ref:`pymagicc.io`.
"""
from pathlib import Path
from copy import deepcopy


import pandas as pd
from pandas_datapackage_reader import read_datapackage


DATA_HIERARCHY_SEPARATOR = "|"
"""str: String used to define different levels in our data hierarchies.

We copy this straight from pyam_ to maintain easy compatibility.
"""

path = Path(__file__).parent


_dtrm = read_datapackage(path, "magicc_dattype_regionmode_regions")

_region_cols = _dtrm.columns.to_series().apply(lambda x: x.startswith("region"))

dattype_regionmode_regions = _dtrm.loc[:, ~_region_cols].copy()
""":obj:`pandas.DataFrame` Mapping between regions and whether a file is SCEN7 or not and the expected values of THISFILE_DATTYPE and THISFILE_REGIONMODE flags in MAGICC.
"""

dattype_regionmode_regions["regions"] = [
    [r for r in raw if not pd.isnull(r)]
    for raw in _dtrm.loc[:, _region_cols].values.tolist()
]

magicc7_emissions_units = read_datapackage(path, "magicc_emisssions_units")
""":obj:`pandas.DataFrame` Definitions of emissions variables and their expected units in MAGICC7.
"""

part_of_scenfile_with_emissions_code_0 = magicc7_emissions_units[
    magicc7_emissions_units["part_of_scenfile_with_emissions_code_0"]
]["magicc_variable"].tolist()
"""list: The emissions which are included in a SCEN file if the SCEN emms code is 0.

See documentation of ``pymagicc.io.get_special_scen_code`` for more details.
"""

part_of_scenfile_with_emissions_code_1 = magicc7_emissions_units[
    magicc7_emissions_units["part_of_scenfile_with_emissions_code_1"]
]["magicc_variable"].tolist()
"""list: The emissions which are included in a SCEN file if the SCEN emms code is 1.

See documentation of ``pymagicc.io.get_special_scen_code`` for more details.
"""

part_of_prnfile = magicc7_emissions_units[magicc7_emissions_units["part_of_prnfile"]][
    "magicc_variable"
].tolist()
"""list: The emissions which are included in a ``.prn`` file.
"""

magicc7_concentrations_units = read_datapackage(path, "magicc_concentrations_units")
""":obj:`pandas.DataFrame` Definitions of concentrations variables and their expected units in MAGICC7.
"""


def _replace_from_replacement_dict(inputs, replacements, inverse=False):
    def careful_replacement(in_str, old, new, edge_cases):
        if old in edge_cases.values():
            for full_str, sub_str in edge_cases.items():
                avoid_partial_replacement = (
                    (full_str in in_str)
                    and (sub_str in old)
                    and (not full_str in old)
                )
                if avoid_partial_replacement:
                    return in_str

        return in_str.replace(old, new)

    if inverse:
        replacements = {v: k for k, v in replacements.items()}

    # Find any edge cases i.e. cases where our old key is a substring of a
    # different old key and if we replace the substring, we will miss the full
    # string we intended to replace e.g. we want to replace "NMVOC" with "nmvoc"
    # but instead replace "OC" and so end up with "NMVoc", which isn't what we
    # wanted.
    edge_cases = {}
    for j, r in enumerate(replacements.keys()):
        for k in list(replacements.keys())[j:]:
            if (r in k) and (r != k):
                edge_cases[k] = r

    inputs_return = deepcopy(inputs)
    for old, new in replacements.items():
        if isinstance(inputs_return, list):
            inputs_return = [careful_replacement(v, old, new, edge_cases) for v in inputs_return]
        else:
            inputs_return = careful_replacement(inputs_return, old, new, edge_cases)

    return inputs_return


def _get_magicc_region_to_openscm_region_mapping(inverse=False):
    def get_openscm_replacement(in_region):
        world = "World"
        if in_region in ("WORLD", "GLOBAL"):
            return world
        if in_region in ("BUNKERS"):
            return DATA_HIERARCHY_SEPARATOR.join([world, "Bunkers"])
        elif in_region.startswith(("NH", "SH")):
            in_region = in_region.replace("-", "")
            hem = "Northern Hemisphere" if "NH" in in_region else "Southern Hemisphere"
            if in_region in ("NH", "SH"):
                return DATA_HIERARCHY_SEPARATOR.join([world, hem])

            land_ocean = "Land" if "LAND" in in_region else "Ocean"
            return DATA_HIERARCHY_SEPARATOR.join([world, hem, land_ocean])
        else:
            return DATA_HIERARCHY_SEPARATOR.join([world, in_region])

    # we generate the mapping dynamically, the first name in the list
    # is the one which will be used for inverse mappings i.e. NH-LAND from
    # MAGICC will be mapped back to NHLAND, not NH-LAND
    _magicc_regions = [
        "WORLD",
        "GLOBAL",
        "OECD90",
        "ALM",
        "REF",
        "ASIA",
        "R5ASIA",
        "R5OECD",
        "R5REF",
        "R5MAF",
        "R5LAM",
        "R6OECD90",
        "R6REF",
        "R6LAM",
        "R6MAF",
        "R6ASIA",
        "NHOCEAN",
        "SHOCEAN",
        "NHLAND",
        "SHLAND",
        "NH-OCEAN",
        "SH-OCEAN",
        "NH-LAND",
        "SH-LAND",
        "SH",
        "NH",
        "BUNKERS",
    ]

    replacements = {}
    for magicc_region in _magicc_regions:
        openscm_region = get_openscm_replacement(magicc_region)
        # i.e. if we've already got a value for the inverse, we don't want to overwrite
        if (openscm_region in replacements.values()) and inverse:
            continue
        replacements[magicc_region] = openscm_region

    if inverse:
        return {v: k for k, v in replacements.items()}
    else:
        return replacements

MAGICC_REGION_TO_OPENSCM_REGION_MAPPING = _get_magicc_region_to_openscm_region_mapping()
"""dict: Mappings from MAGICC regions to openscm regions"""

OPENSCM_REGION_TO_MAGICC_REGION_MAPPING = _get_magicc_region_to_openscm_region_mapping(inverse=True)
"""dict: Mappings from openscm regions to MAGICC regions

This is not a pure inverse of the other way around. For example, we never provide
"GLOBAL" as a MAGICC return value because it's unnecesarily confusing when we also
have "WORLD". Fortunately MAGICC doesn't ever read the name "GLOBAL" so this shouldn't
matter.
"""

def _convert_magicc_region_to_openscm_region(regions, inverse=False):
    if inverse:
        return _replace_from_replacement_dict(regions, OPENSCM_REGION_TO_MAGICC_REGION_MAPPING)
    else:
        return _replace_from_replacement_dict(regions, MAGICC_REGION_TO_OPENSCM_REGION_MAPPING)


def _get_magicc7_to_openscm_variable_mapping(inverse=False):
    def get_openscm_replacement(in_var):
        if in_var.endswith("_EMIS"):
            prefix = "Emissions"
        elif in_var.endswith("_CONC"):
            prefix = "Atmospheric Concentrations"
        elif in_var.endswith("_RF"):
            prefix = "Radiative Forcing"
        elif in_var.endswith("_OT"):
            prefix = "Optical Thickness"
        else:
            raise ValueError("This shouldn't happen")

        variable = in_var.split("_")[0]
        # I hate edge cases
        edge_case_B = variable.upper() in ("HCFC141B", "HCFC142B")
        if variable.endswith("I"):
            variable = DATA_HIERARCHY_SEPARATOR.join(
                [variable[:-1], "MAGICC Fossil and Industrial"]
            )
        elif variable.endswith("B") and not edge_case_B:
            variable = DATA_HIERARCHY_SEPARATOR.join([variable[:-1], "MAGICC AFOLU"])

        case_adjustments = {
            "SOX": "SOx",
            "NOX": "NOx",
            "HFC134A": "HFC134a",
            "HFC143A": "HFC143a",
            "HFC152A": "HFC152a",
            "HFC227EA": "HFC227ea",
            "HFC236FA": "HFC236fa",
            "HFC245FA": "HFC245fa",
            "HFC365MFC": "HFC365mfc",
            "HCFC141B": "HCFC141b",
            "HCFC142B": "HCFC142b",
            "CH3CCL3": "CH3CCl3",
            "CCL4": "CCl4",
            "CH3CL": "CH3Cl",
            "CH2CL2": "CH2Cl2",
            "CHCL3": "CHCl3",
            "CH3BR": "CH3Br",
            "HALON1211": "Halon1211",
            "HALON1301": "Halon1301",
            "HALON2402": "Halon2402",
            "HALON1202": "Halon1202",
            "SOLAR": "Solar",
            "VOLCANIC": "Volcanic",
        }
        variable = _replace_from_replacement_dict(variable, case_adjustments)

        return DATA_HIERARCHY_SEPARATOR.join([prefix, variable])

    magicc7_suffixes = ["_EMIS", "_CONC", "_RF", "_OT"]
    magicc7_base_vars = magicc7_emissions_units.magicc_variable.tolist() + [
        "SOLAR",
        "VOLCANIC",
    ]
    magicc7_vars = [
        base_var + suffix
        for base_var in magicc7_base_vars
        for suffix in magicc7_suffixes
    ]

    replacements = {m7v: get_openscm_replacement(m7v) for m7v in magicc7_vars}

    replacements.update({"SURFACE_TEMP": "Surface Temperature"})

    agg_ocean_heat_top = "Aggregated Ocean Heat Content"
    heat_content_aggreg_depths = {
        "HEATCONTENT_AGGREG_DEPTH{}".format(i): "{}{}Depth {}".format(
            agg_ocean_heat_top, DATA_HIERARCHY_SEPARATOR, i
        )
        for i in range(1, 4)
    }
    replacements.update(heat_content_aggreg_depths)
    replacements.update({"HEATCONTENT_AGGREG_TOTAL": agg_ocean_heat_top})

    ocean_temp_layer = {
        "OCEAN_TEMP_LAYER_{0:03d}".format(i): "Ocean Temperature{}Layer {}".format(
            DATA_HIERARCHY_SEPARATOR, i
        )
        for i in range(1, 999)
    }
    replacements.update(ocean_temp_layer)

    if inverse:
        return {v: k for k,v in replacements.items()}
    else:
        return replacements


MAGICC7_TO_OPENSCM_VARIABLES_MAPPING = _get_magicc7_to_openscm_variable_mapping()
"""dict: Mappings from MAGICC7 variables to openscm variables"""

OPENSCM_TO_MAGICC7_VARIABLES_MAPPING = _get_magicc7_to_openscm_variable_mapping(inverse=True)
"""dict: Mappings from openscm variables to MAGICC7 variables
"""


def _convert_magicc7_to_openscm_variables(variables, inverse=False):
    if inverse:
        return _replace_from_replacement_dict(variables, OPENSCM_TO_MAGICC7_VARIABLES_MAPPING)
    else:
        return _replace_from_replacement_dict(variables, MAGICC7_TO_OPENSCM_VARIABLES_MAPPING)


def _get_magicc6_to_magicc7_variable_mapping(inverse=False):
    # we generate the mapping dynamically, the first name in the list
    # is the one which will be used for inverse mappings i.e. HFC4310 from
    # MAGICC7 will be mapped back to HFC43-10, not HFC-43-10
    # TODO: make this a constant and put it somewhere so we don't regenerate the
    # mapping everytime. Also makes it easier to doc.
    magicc6_vars = [
        "FossilCO2",
        "OtherCO2",
        "SOx",
        "NOx",
        "HFC43-10",
        "HFC-43-10",
        "HFC134a",
        "HFC143a",
        "HFC227ea",
        "HFC245fa",
        "CFC-11",
        "CFC-12",
        "CFC-113",
        "CFC-114",
        "CFC-115",
        "CCl4",
        "CH3CCl3",
        "HCFC-22",
        "HFC-23",
        "HFC-32",
        "HFC-125",
        "HFC-134a",
        "HFC-143a",
        "HCFC-141b",
        "HCFC-142b",
        "HFC-227ea",
        "HFC-245ca",
        "Halon 1211",
        "Halon 1202",
        "Halon 1301",
        "Halon 2402",
        "Halon1211",
        "Halon1202",
        "Halon1301",
        "Halon2402",
        "CH3Br",
        "CH3Cl",
    ]

    # special case replacements
    special_case_replacements = {
        "FossilCO2": "CO2I",
        "OtherCO2": "CO2B",
        "HFC-245ca": "HFC245FA",  # need to check with Malte if this is right...
    }
    replacements = {}
    for m6v in magicc6_vars:
        if m6v in special_case_replacements:
            replacements[m6v] = special_case_replacements[m6v]
        else:
            m7v = m6v.replace("-", "").replace(" ", "").upper()
            # i.e. if we've already got a value for the inverse, we don't # want to overwrite
            if (m7v in replacements.values()) and inverse:
                continue
            replacements[m6v] = m7v

    if inverse:
        return {v: k for k, v in replacements.items()}
    else:
        return replacements


MAGICC6_TO_MAGICC7_VARIABLES_MAPPING = _get_magicc6_to_magicc7_variable_mapping()
"""dict: Mappings from MAGICC6 variables to MAGICC7 variables
"""

MAGICC7_TO_MAGICC6_VARIABLES_MAPPING = _get_magicc6_to_magicc7_variable_mapping(inverse=True)
"""dict: Mappings from MAGICC7 variables to MAGICC6 variables
"""

def _convert_magicc6_to_magicc7_variables(variables, inverse=False):
    if inverse:
        return _replace_from_replacement_dict(variables, MAGICC7_TO_MAGICC6_VARIABLES_MAPPING)
    else:
        return _replace_from_replacement_dict(variables, MAGICC6_TO_MAGICC7_VARIABLES_MAPPING)
