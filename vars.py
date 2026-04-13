# Variables for functions.py
import os
import regex as re

########## Variable for all functions ###################
logs_folder = "/srv/shiny-server/geomatch/logs" #r"C:\Users\e685531\OneDrive - County of Los Angeles\Documents\GIS\Projects\Geocoding\Geocoding_App\geomatch-backup\logs" #r"C:\Users\e685531\Documents\GIS\Projects\Geocoding\Geocoding_App\geomatch-backup\logs" #
log_txt = os.path.join(logs_folder, 'error_log.txt')
log_csv = os.path.join(logs_folder, 'error_summary.csv')

########## Variables for geocoding function(s) ##########

# Value used to represent Street Map Premium in the output table's 'locator' field
locator_smp = 'SMP'
locator_cams = 'CAMS'

# Street Map Premium batch geocoding REST endpoint (geocodeAddresses)
smp_geocode_url = "https://portal.gis.lacounty.gov/arcgis/rest/services/Locator/StreetMAP_Premium_NorthAmerica_Locator/GeocodeServer/geocodeAddresses"

# CAMS batch geocoding REST endpoint (geocodeAddresses). Note: CAMS is not currently in use by this application (09/2024)
cams_geocode_url = "https://dph.gis.lacounty.gov/arcgis/rest/services/CAMS_Locator_Pro/GeocodeServer/geocodeAddresses"

# Additional parameters passed to SMP for geocoding. We do not need to store the geocoded results, so we set the forStorage parameter to False. 
# See https://developers.arcgis.com/documentation/mapping-and-location-services/geocoding/geocode-addresses/ for more info
esri_params = {"forStorage": "false"}

# Subset of fields retrieved from the geocoding service that will be maintained in the output table. 
candidate_fields = [
  'ResultID', # This is the unique ID that can be used to join the geocoded result back to the corresponding row in the input table
  'Status',
  'Score',
  'Match_addr',
  'Addr_type',
  'Type',
  'PlaceName',
  'SubAddr',
  'StAddr',
  'City',
  #'Subregion',
  'RegionAbbr',
  'Postal',
  'Country',
  'X',
  'Y'
  ]
  

# Dictionary mapping field names returned by the geocoding service to field names that will appear in the output table
rename_dict = {
  'Status': 'Locator_Match_Status',
  'Score': "Geocoding_Score",
  'Match_addr': "Match_Address",
  'Addr_type': "Address_Type",
  'Type': "Address_Subtype",
  'PlaceName': "Place_Name",
  'SubAddr': "Match_Subaddress",
  'StAddr': "Match_Street",
  'City': "Match_City",
  'RegionAbbr': "Match_State",
  'Postal': "Match_Zipcode",
  'Country': "Match_Country",
  'X': "Longitude",
  'Y': "Latitude"
}

# Fields that will be cleared for records matched by the locator but not meeting the user-defined score or address type thresholds 
fields_to_nullify = [
  'Match_Subaddress',
  'Match_Street', 
  'Match_City', 
  'Match_State', 
  'Match_Zipcode', 
  'Match_Country', 
  'Longitude', 
  'Latitude'
  ]

########## Variables for spatial join function(s) ##########

data_folder = "/srv/shiny-server/geomatch/data" #r"C:\Users\e685531\OneDrive - County of Los Angeles\Documents\GIS\Projects\Geocoding\Geocoding_App\geomatch-backup\data" #r"C:\Users\e685531\Documents\GIS\Projects\Geocoding\Geocoding_App\geomatch-backup\data" #

# Path to the folder containing shapefiles available to be spatial joined to geocoded records. This should point to a location on/accessible to the server where the application is hosted.
shapefiles_folder = os.path.join(data_folder, "district_shp")

# Dictionary/JSON for mapping join fields. The main dictionary keys are the full names of the shapefiles that are available to app users for spatial joins. These are the names that will
# appear in the app UI for users to select from. The property shapefile_name refers to the file name of the shapefile in the designated shapefiles folder (i.e., <name>.shp). 
# The property join_fields is a dictionary where keys are field names of the fields from that shapefile that will be maintained in the joined output. Fields not in the join_fields 
# dictionary will be removed from the output table before it is returned to the user. The values in this dictionary are field aliases that will appear as the column names in 
# the .csv or .xlsx file returned to the user. For example, the shapefile representing 'School Districts (Elementary, HS, and Unified) is named SCHOOL_DISTRICTS.shp. Three fields
# from this shapefile will be maintained in the output table: 'LABEL', 'ABBR', and 'DISTRICT_T' as 'SCHOOL_NAME', 'SCHOOL_DISTRICT_CODE', and 'SCHOOL_DISTRICT_TYPE', respectively.

shp_map = {
    "Census Tracts (2010)": {
        "shapefile_name": "CT2010",
        "join_fields": {
            "CT10": "CT2010"
        }
    },
    "Census Tracts (2020)": {
        "shapefile_name": "CT2020",
        "join_fields": {
            "CT20": "CT2020"
        }
    },
    "Split Census Tracts (2020)": {
        "shapefile_name": "CT20FIP20CSA",
        "join_fields": {
            "CT20FIP20C": "CT20FIP20CSA"
        }
    },
    "Split Census Tracts (2024)": {
        "shapefile_name": "CT20FIP24CSA",
        "join_fields": {
            "CT20FIP24C": "CT20FIP24CSA"
        }
    },
    "Countywide Statistical Areas (2020)": {
        "shapefile_name": "CSA2020",
        "join_fields": {
            "LABEL": "CSA2020"
        }
    },
    "Countywide Statistical Areas (2024)": {
        "shapefile_name": "CSA2024",
        "join_fields": {
            "LABEL": "CSA2024"
        }
    },
    "City and Unincorporated Community Boundaries (LAC Planning Dept)": {
        "shapefile_name": "CUCB",
        "join_fields": {
            "CITY_COMM_": "CITY_COMMUNITY_NAME",
            "JURISDICTI": "JURISDICTION"
        }
    },
    "Supervisorial Districts (2011)": {
        "shapefile_name": "SD2011",
        "join_fields": {
            "DISTRICT": "SD2011"
        }
    },
    "Supervisorial Districts (2021)": {
        "shapefile_name": "SD2021",
        "join_fields": {
            "DISTRICT": "SD2021"
        }
    },
    "Los Angeles City Council Districts (2012)": {
        "shapefile_name": "LACD2012",
        "join_fields": {
            "DISTNO": "LACD2012"
        }
    },
    "Los Angeles City Council Districts (2021)": {
        "shapefile_name": "LACD2021",
        "join_fields": {
            "DISTRICT": "LACD2021"
        }
    },
    "Health Districts (2012)": {
        "shapefile_name": "HD2012",
        "join_fields": {
            "HD_2012": "HD2012"
        }
    },
    "Health Districts (2022)": {
        "shapefile_name": "HD2022",
        "join_fields": {
            "HD_NUM": "HD2022"
        }
    },
    "Service Planning Areas (2012)": {
        "shapefile_name": "SPA2012",
        "join_fields": {
            "SPA_2012": "SPA2012"
        }
    },
    "Service Planning Areas (2022)": {
        "shapefile_name": "SPA2022",
        "join_fields": {
            "SPA_NUM": "SPA2022"
        }
    },
    "School Districts (Elementary, HS, and Unified)": {
        "shapefile_name": "SCHLDIST",
        "join_fields": {
            "LABEL": "SCHOOL_NAME",
            "ABBR": "SCHOOL_DISTRICT_CODE",
            "DISTRICT_T": "SCHOOL_DISTRICT_TYPE"
        }
    }
}

us_states = [
    'AL', 'AK', 'AZ', 'AR', 'DC', 'CO', 'CT', 'DE', 'FL', 'GA', 
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',  # 49 states and DC
    'AS', 'GU', 'MP', 'PR', 'VI',  # US territories in North America
]

can_provinces = [
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
]

mex_states = [
    'AG', 'BC', 'BS', 'CM', 'CS', 'CH', 'CO', 'CL', 'DG', 'GT', 'GR', 'HG', 'JA', 
    'MX', 'MI', 'MO', 'NA', 'NL', 'OA', 'PU', 'QE', 'QR', 'SL', 'SI', 'SO', 'TB', 
    'TM', 'TL', 'VE', 'YU', 'ZA', # States
    'CDMX'  # Capital
]

north_american_states = list(set(us_states + can_provinces + mex_states))

# flagged cities were added as alternate spellings
la_county_cities = [
          'Acton', 
          'Agoura', 
          'Agoura Hills', 
          'Agua Dulce', 
          'Alhambra', 
          'Altadena', 
          'Arcadia', 
          'Artesia', 
          'Avalon', 
          'Azusa', 
          'Baldwin Hills', 
          'Baldwin Park', 
          'Bassett', 
          'Bell', 
          'Bell Gardens', 
          'Bellflower', 
          'Beverly Hills', 
          'Bradbury', 
          'Brentwood', 
          'Burbank', 
          'Calabasas', 
          'Canoga Park', 
          'Canyon Country', 
          'Carson', 
          'Castaic', 
          'Century City', 
          'Cerritos', 
          'Charter Oak', 
          'Chatsworth', 
          'City Of Industry', 
          'Claremont', 
          'Commerce', 
          'Compton', 
          'Covina', 
          'Culver City', 
          'Del Sur', 
          'Diamond Bar', 
          'Dodgertown', 
          'Downey', 
          'Duarte', 
          'East Los Angeles',
          'East LA', # flag
          'East Rancho Dominguez', 
          'El Monte', 
          'El Segundo', 
          'Elizabeth Lake', 
          'Encino', 
          'Gardena', 
          'Glendale', 
          'Glendora', 
          'Gorman', 
          'Granada Hills', 
          'Hacienda Heights', 
          'Harbor City', 
          'Hawaiian Gardens', 
          'Hawthorne', 
          'Hermosa Beach', 
          'Hi Vista',
          'High Vista',
          'Hidden Hills', 
          'Hollywood', 
          'Huntington Park', 
          'Industry', 
          'Inglewood', 
          'Irwindale', 
          'La Canada Flintridge', 
          'La Crescenta',
          'La Crescenta-Montrose' # flag
          'La Crescenta Montrose' # flag
          'La Habra Heights', 
          'La Mirada', 
          'La Puente', 
          'La Verne', 
          'Lake Hughes', 
          'Lake Los Angeles',
          'Lake LA', # flag
          'Lake View Terrace',
          'Lakeview Terrace', # flag
          'Lakewood', 
          'Lancaster', 
          'Lawndale', 
          'Lennox', 
          'Littlerock', 
          'Llano', 
          'Lomita', 
          'Long Beach', 
          'Los Angeles',
          'LA', # flag
          'Lynwood', 
          'Malibu', 
          'Manhattan Beach', 
          'Marina Del Rey', 
          'Maywood', 
          'Mission Hills', 
          'Monrovia', 
          'Montebello', 
          'Monterey Park', 
          'Montrose', 
          'Mt Wilson',
          'Mount Wilson', # flag
          'Mt. Wilson', # flag
          'Newhall', 
          'North Hills', 
          'North Hollywood', 
          'Northridge', 
          'Norwalk', 
          'Pacific Palisades', 
          'Pacoima', 
          'Palmdale', 
          'Palos Verdes Estates', 
          'Palos Verdes Peninsula', 
          'Panorama City', 
          'Paramount', 
          'Pasadena', 
          'Pearblossom',
          'Pear Blossom', # flag
          'Pico Rivera', 
          'Playa Del Rey', 
          'Playa Vista', 
          'Pomona', 
          'Porter Ranch', 
          'Quartz Hill', 
          'Rancho Dominguez', 
          'Rancho Palos Verdes',
          'Redondo Beach', 
          'Reseda', 
          'Rosemead', 
          'Rowland Heights',
          'RPV', # flag
          'San Dimas', 
          'San Fernando', 
          'San Gabriel', 
          'San Marino', 
          'San Pedro', 
          'Santa Clarita', 
          'Santa Fe Springs', 
          'Santa Monica', 
          'Shadow Hills', 
          'Sherman Oaks', 
          'Sierra Madre', 
          'Signal Hill', 
          'South El Monte', 
          'South Gate', 
          'South Pasadena', 
          'South San Gabriel', 
          'Stevenson Ranch', 
          'Studio City', 
          'Sun Valley', 
          'Sunland', 
          'Sylmar', 
          'Tarzana', 
          'Temple City', 
          'Toluca Lake', 
          'Topanga', 
          'Torrance', 
          'Tujunga', 
          'Universal City', 
          'Val Verde', 
          'Valencia', 
          'Valley Village', 
          'Valyermo', 
          'Van Nuys', 
          'Venice', 
          'Verdugo City', 
          'Vernon', 
          'View Park', 
          'Walnut', 
          'Walnut Park', 
          'West Covina', 
          'West Hills', 
          'West Hollywood', 
          'Westchester', 
          'Westlake Village',
          'Whittier', 
          'Wilmington', 
          'Winnetka', 
          'Woodland Hills'
]

# values representing unknown city/state
unknowns = [
  'UNK', 
  'UNK,', 
  'UNK.', 
  'UNKNOWN', 
  'UKNOWN', 
  'UNKOWN', 
  'HOMELESS', 
  'HOMLESS', 
  'UNSHELTERED', 
  '', 
  ' ', 
  '-'
]

lac_boundary_shp = os.path.join(data_folder, "lac_boundary_shp/lac_boundary.shp")

lac_3nm_buffer_shp = os.path.join(data_folder, "lac_boundary_shp/lac_3nm_buffer.shp")

########## Variables used for address cleaning functions ###########

dd_pattern = re.compile(r'\D*(?:[-+N]|LAT.|LAT|LATITUDE|N\.)?:?\s?([1-8]\d(?:\.\d+))\s?(?:N|N\.|NORTH)?[\W]*(?:LON|LONG|LONGITUDE|W|-|)?\.?:?\s?-?\s?((?:(?:1[0-7]\d))(?:\.\d+)?)\s?(?:W|W\.|WEST)?.*?')
dms_pattern = re.compile(r'\D*(?:(3\d))\W*D?\W*(\d{1,2}(?:\.\d*)?)\W+(\d+(?:\.\d+)?)?\D*(1[0-7][1-9])[\WD]+(\d+\.?\d*)\W+(\d+(?:\.\d+)?)?.*')

replacement_strings_dict = {
    r'^FREEWAY UNDERPASS AT ': '',
    r'SOUTH SHOULDER OF': '',
    r'\bOVERCROSS(?:\s+OF)?\b': '',
    r'OVERCROSSING': '',
    r'UNDERPASS':'',
    r'COLLECTOR ROAD ': '',
    r'SOUTHEAST CORNER OF': '',
    r'WEST EDGE OF': '',
    r'EAST EDGE OF': '',
    r'1/2': '',
    r'1/4': '',
    r'EXIT': '',
    r'^EAST OF ': '',
    r'^WEST OF ': '',
    r'^NORTH OF ': '',
    r'^SOUTH OF ': '',
    r'^NORTHWEST OF ': '',
    r'^SOUTHWEST OF ': '',
    r'^NORTHEAST OF ': '',
    r'^SOUTHEAST OF ': '',
    r'INTERCHANGE': '',
    r'INTERCHANGE, ': ', ',
    r'^ADJACENT TO ': '',
    r'^NEAR THE': '',
    r'^NEAT THE': '',
    r'^NEAR ': '',
    r'^NEAT ': '',
    r'\bUNK\b': '',
    r'\bUNK\.\b': '',
    r'\bUNK,\b': '',
    r'\bUNKNOWN,?\b': '',
    r'\bUNKOWN,?\b': '',
    r'^ACROSS FROM ': '',
    r'^NORTHWEST CORNER OF ': '',
    r'^NORTHEAST CORNER OF ': '',
    r'^SOUTHWEST CORNER OF ': '',
    r'^SOUTHEAST CORNER OF ': '',
    r'^CORNER OF ': '',
    r'^IN FRONT OF': '',
    r'^FRONT OF': '',
    r'^IFO: ': '',
    r'^IFO ': '',
    r'^INTERSECTION OF ': '',
    r'^INTERSECTION': '',
    r'REAR ALLEY': '',
    r'REAR HOUSE': '',
    r'^REAR OF ': '',
    r'^BEHIND ': '',
    r'^TRANSITION TO ': '',
    r'^TRANSITION ': '',
    r'^UNDER ': '',
    r'^BENEATH ': '',
    r'^UNDERNEATH ': '',
    r'^ABOVE ': '',
    r'^AT ': '',
    r'^BETWEEN ': '',
    r'^R/O ': '',
    r'^L/O ': '',
    r'^B/O ': '',
    r'^F/O ': '',
    r'^ , , ': '',
    r'^ , ': '',
    r'\(\)': '',
    r' IN HOV LANE($|\s)': '',
    r'\bUNSHELTERED,?\b': '',
    r'\bHOMELESS,?\b': '',
    r'\bHOMLESS,?\b': '',
    r'-\s*$': '',
    r'^\s*-': '',
    r'-+\s*-+': '',
    r'SOUTH EAST OF': 'SOUTHEAST OF',
    r'NORTH EAST OF': 'NORTHEAST OF',
    r'SOUTH WEST OF': 'SOUTHWEST OF',
    r'NORTH WEST OF': 'NORTHWEST OF',
    r'(?:\d+(\.\d+)?\s+)?MILES\s+(NORTH|SOUTH|EAST|WEST|N|S|E|W|NE|SE|NW|SW)\s+OF\s+': '@ ',
    r' NORTHWEST OF ': ' @ ',
    r' NORTHEAST OF ': ' @ ',
    r' SOUTHWEST OF ': ' @ ',
    r' SOUTHEAST OF ': ' @ ',
    r' NW OF ': ' @ ',
    r' NE OF ': ' @ ',
    r' SW OF ': ' @ ',
    r' SE OF ': ' @ ',
    r' JUST EAST OF ': ' @ ',
    r' JUST E/O ': ' @ ',
    r' J / EAST OF ': ' @ ',
    r' EAST OF ': ' @ ',
    r' JUST WEST OF ': ' @ ',
    r' JUST W/O ': ' @ ',
    r' J / WEST OF ': ' @ ',
    r' WEST OF ': ' @ ',
    r' JUST NORTH OF ': ' @ ',
    r' JUST N/O ': ' @ ',
    r' J / NORTH OF ': ' @ ',
    r' NORTH OF ': ' @ ',
    r' JUST SOUTH OF ': ' @ ',
    r' JUST S/O ': ' @ ',
    r' J / SOUTH OF ': ' @ ',
    r' SOUTH OF ': ' @ ',
    r' SOUT OF ': ' @ ',
    r' WOUTH OF ': ' @ ',
    r' [NSEW]/O ': ' @ ',
    r' [NSEW]/O/ ': ' @ ',
    r' J[NSEW]O ': ' @ ',
    r' J/[NSEW]/O ': ' @ ',
    r' JUST PAST ': ' @ ',
    r' PAST ': ' @ ',
    r' NEAR TO ': ' @ ',
    r' NEAR ': ' @ ',
    r' NEAT ': ' @ ',
    r' OFF OF ': ' @ ',
    r' OFF ': ' @ ',
    r' ON ': ' @ ',
    r' S\. OF ': ' @ ',
    r' S OF ': ' @ ',
    r' N\. OF ': ' @ ',
    r' N OF ': ' @ ',
    r' E\. OF ': ' @ ',
    r' E OF ': ' @ ',
    r' W\. OF ': ' @ ',
    r' W OF ': ' @ ',
    r' BENEATH ': ' @ ',
    r' UNDERNEATH ': ' @ ',
    r' UNDER ': ' @ ',
    r' ABOVE ': ' @ ',
    r' AT ': ' @ ',
    r' BETWEEN ': ' @ ',
    r' CONNECTOR TO ': ' @ ',
    r' TRANSITION TO ': ' @ ',
    r' TRANSITION RAMP TO ': ' @ ',
    r' TRANS TO ': ' @ ',
    r'OFF RAMP': 'OFFRAMP',
    r'ON RAMP': 'ONRAMP',
    r'\bONRAMP\b(?!\s+(OF|TO)\b)':'',
    r'\bOFFRAMP\b(?!\s+(OF|TO)\b)':'',
    r' ON-RAMP TO ': ' @ ',
    r' OFF-RAMP TO ': ' @ ',
    r' ONRAMP TO ': ' @ ',
    r' OFFRAMP TO ': ' @ ',
    r' ON-RAMP OF ': ' @ ',
    r' OFF-RAMP OF ': ' @ ',
    r' ONRAMP OF ': ' @ ',
    r' OFFRAMP OF ': ' @ ',
    r' ONTO ': ' @ ',
    r' ON RAMP AT ': ' @ ',
    r' B/T ': ' @ ',
    r' BY ': ' @ ',
    r' RUNNING PARALLEL TO ': ' @ ',
    r' AT OVERPASS OF ': ' @ ',
    r' ADJACENT TO ': ' @ ',
    r' ONR TO ': ' @ ',
    r' TO ': ' @ ',
    r' AT THE INTERSECTION OF ': ' @ ',
    r' FROM THE ': ' @ ',
    r' FROM ': ' @ ',
    r'0 BLOCK OF': '0',
    r'0 BLOCK': '0',
    r' STEET': ' STREET',
    r' STREE ': ' STREET ',
    r' STREE,': ' STREET,',
    r'AEVNUE': 'AVENUE',
    r' SSTREET ': ' STREET ',
    r' EASTT ': ' EAST ',
    r' WESTT ': ' WEST ',
    r' STREEET': ' STREET',
    r'\bINTERSTATE\s+5(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-5',
    r'\bINTERSTATE\s+7(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-7',
    r'\bINTERSTATE\s+8(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-8',
    r'\bINTERSTATE\s+9(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-9',
    r'\bINTERSTATE\s+10(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-10',
    r'\bINTERSTATE\s+15(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-15',
    r'\bINTERSTATE\s+40(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-40',
    r'\bINTERSTATE\s+80(?:\s+NORTH|\s+SOUTH|\s+EAST|\s+WEST|\s+N|\s+S|\s+E|\s+W)?\b': 'I-80',
    r'[^I\-]210 (FWY\.|FWY|FREEWAY)': 'I-210',
    r'405 (FWY\.|FWY|FREEWAY)': 'I-405',
    r'101 (FWY\.|FWY|FREEWAY)': 'US-101',
    r'(THE|NORTHBOUND|SOUTHBOUND|NB|SB) 101': 'US-101',
    r'(^|[^A-Za-z])I\s(\d+)': r'\1I-\2',
    r'[^I\-\d]14 (FWY\.|FWY|FREEWAY)': ' CA-14',
    r'118 (HWY\.|HWY|HIGHWAY)': 'CA-118',
    r'[^I\-\d]2 (FWY\.|FWY|FREEWAY)': ' CA-2',
    r'[^I\-\d]5 (FWY\.|FWY|FREEWAY)': ' I-5',
    r'105 (FWY\.|FWY|FREEWAY)': 'I-105',
    r'NORTHBOUND 5,': 'I-5 N ',
    r'SOUTHBOUND 110 FREEWAY,': 'I-110 S',
    r'SOUTHBOUND 405 (FWY\.|FWY|FREEWAY),': 'I-405 S',
    r'[^I\-\d]15 (FWY\.|FWY|FREEWAY)': ' I-15',
    r'[^I\-\d]10 (FWY\.|FWY|FREEWAY)': ' I-10',
    r'170 (FWY\.|FWY|FREEWAY)': 'CA-170',
    r'[^I\-\d]60 (FWY\.|FWY|FREEWAY)': ' CA-60',
    r'[^I\-\d]91 (FWY\.|FWY|FREEWAY)': ' CA-91',
    r' 71 FWY': ' CA-71',
    r'(WB|EB|WESTBOUND|EASTBOUND) 60': 'CA-60',
    r'(NB|SB|NORTHBOUND|SOUTHBOUND) 170': 'CA-170',
    r'(HWY\.|HWY|HIGHWAY) 178': 'CA-178',
    r'(HWY\.|HWY|HIGHWAY) 91': 'CA-91',
    r'(EB|WB|EASTBOUND|WESTBOUND) 91': 'CA-91',
    r'(EB|WB|EASTBOUND|WESTBOUND) 210 (FWY\.|FWY|FREEWAY)?': 'I-210',
    r'210 (FWY\.|FWY|FREEWAY)': 'I-210',
    r'SR(-|\W)39': 'CA-39',
    r'NORTHBOUND 5($|\W)': 'I-5 N ',
    r'HIGHWAY 29($|\W)': 'CA-29 ',
    r'SOUTHBOUND 5($|\W)': 'I-5 S ',
    r'EASTBOUND 9 THE FREEWAY': 'CA-9 E',
    r'(NB|SB|NORTHBOUND|SOUTHBOUND) 14($|\W)': 'CA-14 ',
    r'ISR ': 'I-',
    r'ISR': 'I-',
    r'(HWY\.|HWY|HIGHWAY)(-|\W)138': 'CA-138',
    r'THE 57 FREEWAY': 'CA-57',
    r'SR(-|\W)99': 'CA-99',
    r'STATE HIGHWAY 18': 'CA-18',
    r'US 395': 'US-395',
    r'STATE ROUTE 134': 'CA-134',
    r'SR(-|\W)110': 'CA-110',
    r'(HWY\.|HWY|HIGHWAY)(-|\W)198': 'CA-198',
    r'SR(-|\W)58 ': 'CA-58 ',
    r'SR(-|\W)14 ': 'CA-14 ',
    r'105 E\.': 'I-105 E',
    r' PCH': ' PACIFIC COAST HIGHWAY',
    r'^PCH': 'PACIFIC COAST HIGHWAY',
    r'S/B': 'S',
    r'N/B': 'N',
    r'E/B': 'E',
    r'W/B': 'W',
    r'SOUTH BOUND': 'S',
    r'NORTH BOUND': 'N',
    r'EAST BOUND': 'E',
    r'WEST BOUND': 'W',
    r'(^|\W)WB ': ' W ',
    r'(^|\W)EB ': ' E ',
    r'(^|\W)NB ': ' N ',
    r'(^|\W)SB ': ' S ',
    r'SOUTHBOND': 'S',
    r'NORTHBOND': 'N',
    r'EASTBOND': 'E',
    r'WESTBOND': 'W',
    r' NORH ': ' N ',
    r' ORTH ': ' N ',
    r' OUTH ': ' S ',
    r' SOTUH ': ' S ',
    r'NORTHBOUND': 'N',
    r'SOUTHBOUND': 'S',
    r'EASTBOUND': 'E',
    r'WESTBOUND': 'W',
    r'MIL MARKER': 'MILE',
    r' MM ': ' MILE ',
    r' M/M ': ' MILE ',
    r'^MM ': 'MILE ',
    r'MILE MARKER': 'MILE',
    r'MILE POST': 'MILE',
    r'MM(\d)': r'MILE \1',
    r'INT\. (\d+)': r'I-\1',
    r'INT (\d+)': r'I-\1',
    r'MPM': 'MILE',
    r'MILEPOST MARKER': 'MILE',
    r'MILEPOST': 'MILE',
    r'MILE MRKER': 'MILE',
    r' MI ': ' MILE ',
    r'29 PALMS HWY': 'TWENTYNINE PALMS HWY',
    r'FWY\. ': 'FWY ',
    r',\s*,+': ',',
    r'^\s*,+|,+\s*$': ''}
