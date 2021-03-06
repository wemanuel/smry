"""
Name Dictionaries to Map NCA Regions
    W. R. Emanuel, University of Maryland, College Park
    E-Mail: wemanuel@umd.edu
    Gmail: wemanuel@gmail.com
"""

# Dictionaries to map region short names to long names.
name_dct = {"Alaska": "Alaska", "GrtPlns": "Great Plains",
                       "Hawaii": "Hawaii", "MidWest": "Midwest",
                       "NorthEast": "Northeast", "NorthWest": "Northwest",
                       "PuertoRico": "Puerto Rico and the Virgin Islands",
                       "SouthEast": "Southeast", "SouthWest": "Southwest",
                       "USA48": "Conterminous 48 U.S. States"}
short_name_dct = {"Alaska": "Alaska", "GrtPlns": "Great Plains",
                       "Hawaii": "Hawaii", "MidWest": "Midwest",
                       "NorthEast": "Northeast", "NorthWest": "Northwest",
                       "PuertoRico": "Puerto Rico and the Virgin Islands",
                       "SouthEast": "Southeast", "SouthWest": "Southwest",
                       "USA48": "Conterminous 48 U.S. States"}

# Dictionary to map region names to abbreviations. This mapping
# is used to resolve selected discrepancies between region names
# and file names containing data or images for corresponding
# regions.
abbrv_to_rgn = {"AlaskaWH": "Alaska", "GrtPlns": "Great Plains",
                "MidWest": "Midwest", "NorthEast": "Northeast",
                "NorthWest": "Northwest", "SouthEast": "Southeast",
                "SouthWest": "Southwest", "Hawaii": "Hawaii",
                "PuertoRicoVirginIS": "PuertoRico", 
                "PuertoRicoVirginIS": "Puerto Rico",
                "USA48": "Conterminous 48 U.S. States"}
rgn_to_abbrv = {"Alaska": "AlaskaWH", "Great Plains": "GrtPlns",
                "Midwest": "MidWest", "Northeast": "NorthEast",
                "Northwest": "NorthWest", "Southeast": "SouthEast",
                "Southwest": "SouthWest", "Hawaii": "Hawaii",
                "PuertoRico": "PuertoRicoVirginIS", 
                "Puerto Rico": "PuertoRicoVirginIS",
                "USA48": "USA48",
                "Conterminous 48 U.S. States": "USA48"}