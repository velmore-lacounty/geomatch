import pandas as pd
import numpy as np
import geopandas as gpd
import regex as re
from datetime import datetime
import requests, os, sys, time, json, openpyxl, io, traceback, csv
from requests.exceptions import RequestException
from vars import replacement_strings_dict, dd_pattern, dms_pattern, la_county_cities, north_american_states, unknowns, lac_boundary_shp, lac_3nm_buffer_shp

def log_error_to_file(error, txt_log_path='logs/error_log.txt', csv_log_path='logs/error_summary.csv'):
    """
    Logs detailed and summary error info to .txt and .csv files.

    Args:
        error (Exception): The exception object.
        source (str): Description of the module or function where the error occurred.
        txt_log_path (str): Path to the detailed .txt log.
        csv_log_path (str): Path to the summary .csv log.
    """
    os.makedirs(os.path.dirname(txt_log_path), exist_ok=True)

    # write full traceback to .txt log
    with open(txt_log_path, "a") as f:
        f.write("==== ERROR LOG ENTRY ====\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Error Type: {type(error).__name__}\n")
        f.write(f"Error Message: {str(error)}\n")
        f.write("Traceback:\n")
        f.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))
        f.write("\n\n")

    # write summary info to .csv log
    write_header = not os.path.exists(csv_log_path)
    with open(csv_log_path, mode='a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["Timestamp", "Error Type"])
        writer.writerow([datetime.now().isoformat(), type(error).__name__])


def read_file(file_path):
    """
    Reads a file into a pandas DataFrame.
    Supports .xlsx, comma-delimited .csv, and pipe-delimited .csv files.
    
    Args:
    file_path (str): The path to the file.

    Returns:
    pd.DataFrame: The file's contents as a pandas DataFrame.
    """
    
    # Check the file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Read the file into a pandas DataFrame based on the file extension
    if file_ext == ".csv":
        # Determine if the file is comma- or pipe-delimited
        with open(file_path, 'r') as file:
            first_line = file.readline()
            delimiter = ',' if ',' in first_line and '|' not in first_line else '|'
        
        df = pd.read_csv(file_path, delimiter=delimiter)
    elif file_ext == ".xlsx":
        df = pd.read_excel(file_path)
    
    return df
  
def postprocess_vrbis(df, null_fields, state_centroid=False, country_centroid=False, la_centroid=False):
    """
    Apply additional unmatch criteria to geocoded results according to specific criteria for geocoding vital records.
    
    Args:
    df (pd.DataFrame): The DataFrame produced during postprocess_geocode_results.
    null_fields (list of str): list of fields whose values will be cleared for records matched by the locator but no meeting
        user-defined criteria (score and address type)
    state_centroid (bool): If True, unmatch records where "Address_Type" = Locality and "Address_Subtype" = State or Province.
    country_centroid (bool): If True, unmatch records where "Address_Type" = Locality and "Address_Subtype" = Country.
    la_centroid (bool): If True, unmatch records where "Address_Type" = Locality and "Address_Subtype" = City and 
        "Match_City" = Los Angeles.
    
    Returns:
    pd.DataFrame: The updated DataFrame with additional unmatch criteria applied.
    """
    
    # Apply additional criteria if not already unmatched by locator
    unmatched_by_locator_condition = df['Locator_Match_Status'] == 'U'
    
    # Apply additional criteria
    if state_centroid:
        condition = ~unmatched_by_locator_condition & (df['Address_Type'] == 'Locality') & (df['Address_Subtype'] == 'State or Province')
        df.loc[condition, 'Matched'] = 'N'
        df.loc[condition, null_fields] = np.nan
        df.loc[condition, 'Notes'] += 'Excluded address subtype'
    if country_centroid:
        condition = ~unmatched_by_locator_condition & (df['Address_Type'] == 'Locality') & (df['Address_Subtype'] == 'Country')
        df.loc[condition, 'Matched'] = 'N'
        df.loc[condition, null_fields] = np.nan
        df.loc[condition, 'Notes'] += 'Excluded address subtype'
    if la_centroid:
        condition = ~unmatched_by_locator_condition & (df['Address_Type'] == 'Locality') & (df['Address_Subtype'] == 'City') & (df['Match_City'] == 'Los Angeles')
        df.loc[condition, 'Matched'] = 'N'
        df.loc[condition, null_fields] = np.nan
        df.loc[condition, 'Notes'] += 'Excluded address subtype (City of LA centroid)'
    
    return df


def geocode(df, 
            locator,
            url,
            candidate_fields,
            null_fields,
            field_map,
            batch_size=1000,
            is_singleField=False, 
            singleLine_field=None, 
            street_field=None,
            apt_or_unit_field=None,
            city_field=None, 
            state_field=None, 
            zip_field=None, 
            min_score=70, 
            accepted_addr_types=[],
            addl_params=None,
            vrbis=False,
            **kwargs):

    """
    Geocode a table of addresses using a geocoding service and post-process the results.

    Args:
    file_to_geocode (str): path to a CSV or XLSX file containing addresses  
    locator (str): abbreviation of the locator used for geocoding (SMP or CAMS)
    url (str): URL to the REST endpoint of the geocoding service
    candidate_fields (list of str): list of field names returned by the locator that will be included in the output table
    null_fields (list of str): list of fields whose values will be cleared for records matched by the locator but no meeting
        user-defined criteria (score and address type)
    field_map (dict): dictionary mapping field names returned by the locator to the field names that will be included in the 
        output table
    is_singleField (bool): True if addresses are stored as single line inputs, False if the addresses are parsed into components
    singleLine_field (str): name of the field containing the single line input
    street_field (str): name of the field containing the parsed street address
    apt_or_unit_field (str): name of the field containing the apartment or unit #
    city_field (str): name of the field containing the parsed city
    state_field (str): name of the field containing the parsed state
    zip_field (str): name of the field containing the parsed zipcode
    min_score (int): number 70-100 representing the minimum accepted score for addresses matched by the locator 
    accepted_addr_types (list of str): list of address types accepted for addresses matched by the locator
    addl_params (dict): additional parameters that may be passed to the locator (depending on which locator is used)
    vrbis (bool): True if additional post-processing for vital records is required, False if not
    
    Additional keyword arguments (**kwargs):
    - state_centroid (bool): Unmatch records where "Address_Type" = Locality and "Address_Subtype" = State or Province.
    - country_centroid (bool): Unmatch records where "Address_Type" = Locality and "Address_Subtype" = Country.
    - la_centroid (bool): Unmatch records where "Address_Type" = Locality and "Address_Subtype" = City and 
                          "Match_City" = Los Angeles.
    
    Returns:
    The geocoded and post-processed records as a Pandas DataFrame.
    """

    # Add a unique ID field (EID) based on the dataframe index
    df['EID'] = df.index
    
    if is_singleField: # Execute for tables with addresses in a single field
        if singleLine_field is None:
            raise ValueError("singleLine_field argument must be provided when is_singleField is True.")
        
        # Generate a list of single-line addresses
        address_list = df[singleLine_field].tolist()
    
    else: # Execute for tables with addresses in multiple fields
        
        # Check if at least one of the required fields is provided
        if not any([street_field, city_field, state_field, zip_field]):
            raise ValueError("At least one of street_field, city_field, state_field, or zip_field must be provided when is_singleField is False.")
        
        # Convert the DataFrame to a list of dictionaries
        addresses = df.to_dict(orient='records')
        
        # Prepare a list of dictionaries with the required keys for each address component; if a field doesn't exist, use an empty string
        address_list = []
        for addr in addresses:
            address_dict = {
                "Address": addr.get(street_field, ""),
                "Address2": addr.get(apt_or_unit_field, ""),
                "City": addr.get(city_field, ""),
                "Region": addr.get(state_field, ""),
                "Postal": addr.get(zip_field, "")
            }
            address_list.append(address_dict)
        
    addr_count = len(address_list) 
    
    total_results = []  # Empty list to store all geocoded results
    
    # Initiate session to make requests to Portal server
    session = requests.Session()  
    
    # Create batches of addresses to send to the batch geocoding REST endpoint
    for start_idx in range(0, addr_count, batch_size):
        end_idx = start_idx + batch_size
        batch_addresses = address_list[start_idx:end_idx]

        # Prepare data for POST request
        if is_singleField: # Format POST request for single line input
            records = [{"attributes": {"OBJECTID": i + start_idx, "SingleLine": addr}}
                       for i, addr in enumerate(batch_addresses)]
        else: # Format POST request for multi-field input
            records = [{"attributes": {"OBJECTID": i + start_idx, "Address": addr["Address"], "Address2": addr["Address2"], "City": addr["City"], "Region": addr["Region"], "Postal": addr["Postal"]}}
                       for i, addr in enumerate(batch_addresses)]
                       
        # Construct the JSON for the POST request
        data = {
            "addresses": json.dumps({"records": records}),
            "f": "json",
            "sourceCountry": "USA"
        }
        if addl_params:
            data.update(addl_params)

        try:
            # Make the POST request
            response = session.post(url, data=data)
            response.raise_for_status()  # Check for HTTP errors

            # Extract and append results
            batch_results = response.json().get('locations', [])
            total_results.extend(batch_results)

        except requests.RequestException as e:
            # Handle errors such as connectivity issues, timeouts, etc.
            raise ValueError(f"Error processing batch {start_idx} to {end_idx - 1}: {str(e)}")

    session.close()  # Close the session
    
    # Begin post-processing geocoded results
    
    # Filter the fields returned by the geocoding service to only include those listed in 'candidate_fields' variable
    formatted_results = []
    for result in total_results:
        result_dict = {}
        attr = result['attributes']
        for field in candidate_fields:
            if field in attr:
                result_dict[field] = attr[field]
        formatted_results.append(result_dict)
        
    # Sort the results into their original order, as they are returned by batch geocoding endpoint in random order 
    geocode_results = sorted(formatted_results, key=lambda x: x['ResultID'])
    
    # Convert the list of dictionaries to a DataFrame
    geocode_df = pd.DataFrame(geocode_results)
    
    # Rename fields in the geocode DataFrame according to the field map 
    geocode_df = geocode_df.rename(columns=field_map)
      
    # Join the geocoded results back to the input addresses DataFrame
    result_df = pd.merge(df, geocode_df, left_on='EID', right_on='ResultID', how='left')
    
    # Add the "Locator" field
    result_df['Locator'] = locator
    
    # Add the "Notes" field
    result_df['Notes'] = ''
    
    # Add the "Matched" field and initialize it with 'Y'
    result_df['Matched'] = 'Y'
    
    # Check locator match status. Begin populating 'Matched' field accordingly.
    locator_status_condition = result_df['Locator_Match_Status'] == 'U'
    result_df.loc[locator_status_condition, 'Matched'] = 'N'
    result_df.loc[locator_status_condition, 'Notes'] = 'Not matched by locator'
    
    # For records matched or tied by locator, check other conditions to determine 'Matched' field value
    other_conditions = ~locator_status_condition
    
    # Check geocoding score. Populate matched field accordingly. 
    score_condition = other_conditions & (result_df['Geocoding_Score'] < min_score)
    result_df.loc[score_condition, 'Matched'] = 'N'
    result_df.loc[score_condition, 'Notes'] += 'Score below threshold set by user; '
    
    # Check address type and populated matched field accordingly
    if accepted_addr_types:
        invalid_addr_type_condition = other_conditions & ~result_df['Address_Type'].isin(accepted_addr_types)
        result_df.loc[invalid_addr_type_condition, 'Matched'] = 'N'
        result_df.loc[invalid_addr_type_condition, 'Notes'] += 'Excluded address type; '
        
    # Nullify Match_<address component> fields for records with 'N' in 'Matched' field
    existing_fields_to_nullify = [field for field in null_fields if field in result_df.columns]
    result_df.loc[result_df['Matched'] == 'N', existing_fields_to_nullify] = np.nan
    
    if vrbis:
        # Extract additional arguments from kwargs (with default values)
        state_centroid = kwargs.get('state_centroid', False)
        country_centroid = kwargs.get('country_centroid', False)
        la_centroid = kwargs.get('la_centroid', False)
        
        # Call the postprocess_vrbis function with these additional parameters
        result_df = postprocess_vrbis(df=result_df, 
                                      null_fields=null_fields, 
                                      state_centroid=state_centroid,
                                      country_centroid=country_centroid, 
                                      la_centroid=la_centroid)
    
    # Remove trailing semicolon and space from the 'Notes' column
    result_df['Notes'] = result_df['Notes'].str.rstrip('; ')
    
    # Drop the ResultID and EID fields
    result_df = result_df.drop(columns=['ResultID', 'EID'])
    
    return result_df
  
  
def perform_spatial_join(points_gdf, polygons_gdf, fields_to_keep, output_field_names):
    """
    Perform a spatial join between points and polygons, keeping specified fields.

    Args:
    points_gdf (GeoDataFrame): GeoDataFrame containing point data.
    polygons_gdf (GeoDataFrame): GeoDataFrame containing polygon data.
    fields_to_keep (list): List of field names from the polygon data to keep in the joined data.
    output_fields_name (dictionary): Dictionary mapping fields_to_keep fields to their new names. 

    Returns:
    GeoDataFrame: A GeoDataFrame with the spatially joined data.
    """
    joined_gdf = gpd.sjoin(points_gdf, polygons_gdf[fields_to_keep + ['geometry']], how="left", predicate="intersects")
    
    # Rename fields after the join
    joined_gdf = joined_gdf.rename(columns=output_field_names)
    
    # Drop the 'index_right' column
    if 'index_right' in joined_gdf.columns:
        joined_gdf = joined_gdf.drop(columns='index_right')
    
    return joined_gdf

def sequential_sj(point_df, x_field, y_field, shapefiles_to_join, shp_map, shapefiles_folder):
    
    for col in [x_field, y_field]:
      point_df[col] = pd.to_numeric(point_df[col], errors="coerce")
    
    gdf = gpd.GeoDataFrame(point_df, geometry=gpd.points_from_xy(point_df[x_field], point_df[y_field]), crs="EPSG:4326")
    
    for shapefile_name in shapefiles_to_join:
        filename = shp_map[shapefile_name]['shapefile_name']
        shapefile_path = os.path.abspath(os.path.join(shapefiles_folder, filename + ".shp"))
        fields_to_keep = list(shp_map[shapefile_name]['join_fields'].keys())
        output_field_names = shp_map[shapefile_name]['join_fields']
    
        polygons_gdf = gpd.read_file(shapefile_path)
        
        gdf = perform_spatial_join(points_gdf=gdf, 
                                   polygons_gdf=polygons_gdf, 
                                   fields_to_keep=fields_to_keep, 
                                   output_field_names=output_field_names)
    
    df = gdf.drop(columns="geometry")
    return df

def extract_ct_field_names(shp_map):
    """
    Extracts the join field names of Census Tract and Split Census tract datasets from the shapefile map in vars.py.

    Args:
        shp_map (dict): A dictionary where keys represent dataset colloquial names, 
                        and values are dictionaries containing shapefile names and join fields.

    Returns:
        list: A list of join field names from datasets whose colloquial names contain "Census Tracts".
    """
    # Initialize a list to hold join fields
    ct_fields = []
    
    # Loop through the dictionary items
    for dataset_name, dataset_info in shp_map.items():
        # Check if the dataset name contains "Census Tracts"
        if "Census Tracts" in dataset_name:
            # Get the join fields for the dataset
            join_fields = list(dataset_info['join_fields'].values())
            # Add the join fields to the list
            ct_fields.extend(join_fields)
    
    return ct_fields
  
def clear_ct_fields(df, addr_type_field, shp_map):
    """
    Clears (sets to None) the values in optional CT fields for rows where 
    the 'Address_Type' field contains 'Postal', 'PostalLoc', or 'Locality'.

    Args:
        df (pd.DataFrame): The input pandas DataFrame that contains an 'Address_Type' field.
        addr_type_field (str): The name of the field containing address types (from geocoding)
        shp_map (dict): A dictionary where keys represent dataset full/colloquial names, 
                        and values are dictionaries containing shapefile names and join fields.

    Returns:
        pd.DataFrame: The modified DataFrame with cleared CT field values where applicable.
    """
    # Use the extract_census_tract_join_fields function to get CT fields dynamically
    ct_fields = extract_ct_field_names(shp_map=shp_map)
    
    # Check if the CT fields are present in the DataFrame
    present_ct_fields = [field for field in ct_fields if field in df.columns]
    
    # Add 'Notes' field if it does not exist
    if 'Notes' not in df.columns:
        df['Notes'] = ''
    
    if present_ct_fields:
        # Address types to check for
        address_types_to_clear = ['Postal', 'PostalLoc', 'Locality']
        
        # Find rows where 'Address_Type' matches the condition and 'Matched' is not 'N'
        rows_to_update = df['Address_Type'].isin(address_types_to_clear) # & (df['Matched'] == 'Y')
        
        # Clear the present CT fields where the address type matches
        df.loc[rows_to_update, present_ct_fields] = None
        
        # Prepare the message with a comma-separated string of present CT fields
        ct_fields_str = ", ".join(present_ct_fields)
        message = f"Joins removed for {ct_fields_str} due to unsuitable address type."
        
        # Update the 'Notes' field
        for idx, row in df[rows_to_update].iterrows():
            # If the 'Notes' field is empty, add the message
            if pd.isna(row['Notes']) or row['Notes'] == '' or row['Notes'] == ' ':
                df.at[idx, 'Notes'] = message
            else:
                # If the 'Notes' field is not empty, append the message with a semicolon
                df.at[idx, 'Notes'] = f"{row['Notes']}; {message}"
    return df
  
def assign_spa_98(point_df, x_field, y_field, spa_field):
    """
    Assigns 98 in the SPA field to geocoded addresses in the input DataFrame that fall outside LA County.

    Args:
    point_df (pd.DataFrame): A DataFrame containing point data with coordinate fields in WGS1984 (decimal degrees).
    x_field (str): The column name in point_df containing x-coordinate values (longitude).
    y_field (str): The column name in point_df containing y-coordinate values (latitude).
    spa_field (str): The column name in point_df containing SPAs (1-8, 98, 99)

    Returns:
    pd.DataFrame: The input DataFrame updated to reflect SPA 98 for records matched to locations outside LA County.
    """     
    points = gpd.GeoDataFrame(point_df, geometry=gpd.points_from_xy(point_df[x_field], point_df[y_field]), crs="EPSG:4326")
    polygons = gpd.read_file(lac_boundary_shp)
    
    # Perform the spatial join to find points within LA County
    points_within_polygons = gpd.sjoin(points, polygons, how="inner", predicate="within")
    
    # In the points dataframe, assign a value of 98 in the spa field for points that were matched to locations outside 
    # the LAC boundary + 3nm buffer polygons
    valid_xy_mask = point_df[x_field].notnull() & point_df[y_field].notnull() # Only assign values to records matched during geocoding
    point_df.loc[valid_xy_mask & ~point_df.index.isin(points_within_polygons.index), spa_field] = 98
    
    return point_df

def assign_spa_99(point_df, x_field, y_field, spa_field):
    """
    Assigns 99 in the SPA field to geocoded addresses in the input DataFrame that fall within 3nm of the LA County coastline.

    Args:
    point_df (pd.DataFrame): A DataFrame containing point data with coordinate fields in WGS1984 (decimal degrees).
    x_field (str): The column name in point_df containing x-coordinate values (longitude).
    y_field (str): The column name in point_df containing y-coordinate values (latitude).
    spa_field (str): The column name in point_df containing SPAs (1-8, 98, 99)

    Returns:
    pd.DataFrame: The input DataFrame updated to reflect SPA 99 for records matched to locations within 3nm of LA County's coastline.
    """     
    points = gpd.GeoDataFrame(point_df, geometry=gpd.points_from_xy(point_df[x_field], point_df[y_field]), crs="EPSG:4326")
    polygons = gpd.read_file(lac_3nm_buffer_shp)
    
    # Perform the spatial join to find points within 3nm of the LA County coastline (i.e., join to the LAC 3nm offshore buffer polygon)
    points_within_polygons = gpd.sjoin(points, polygons, how="inner", predicate="within")
    
    # In the points dataframe, assign a value of 99 in the spa field for points within the LAC 3 nm buffer polygon(s)
    point_df.loc[point_df.index.isin(points_within_polygons.index), spa_field] = 99
    
    return point_df

def assign_alt_spas(df, city_field, state_field, spa_field, x_field, y_field):
    """
    Assigns alternative Service Planning Area (SPA) codes (98 and 99) to geocoded address 
    records in a DataFrame based on the spatial location within Los Angeles County boundaries 
    and additional address components (city and state).

    Args:
    df (pd.DataFrame): DataFrame containing address data including columns for coordinates, street, city, state, ZIP, and SPA.
    city_field (str): Column name for the city.
    state_field (str): Column name for the state/province.
    spa_field (str): Column name for the SPA assignment field.
    x_field (str): Column name for the x-coordinate (longitude).
    y_field (str): Column name for the y-coordinate (latitude).

    Returns:
    pd.DataFrame: The input DataFrame updated with SPA assignments:
                  - SPA 1-8: Within specific LA County areas.
                  - SPA 98: Outside LA County.
                  - SPA 99: Within 3 nautical miles offshore of LA County, or within the county
                    but with insufficient address information to geocode. 
    """
    # Print summary of remaining null SPAs
    remaining_null_count = df[spa_field].isnull().sum()
    print(f"There are {remaining_null_count} records with null {spa_field} values after spatial join.")
    
    # Strip leading and trailing whitespace from address and lat/long fields
    columns_to_strip = [city_field, state_field, x_field, y_field]
    for col in columns_to_strip:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Replace empty strings in xy fields with NaN to facilitate successful spatial joins
    df[x_field] = df[x_field].replace('', np.nan)
    df[y_field] = df[y_field].replace('', np.nan)
    
    # Call assign_spa_98 to assign SPA 98 to records outside the LA County boundary 
    df = assign_spa_98(point_df=df,
                       x_field=x_field,
                       y_field=y_field, 
                       spa_field=spa_field)
    
    df = assign_spa_99(point_df=df, 
                       x_field=x_field, 
                       y_field=y_field, 
                       spa_field=spa_field)
    
    ##################################################################################################################
    # All records matched during geocoding should now have a value in spa_field. Records matched to a location in LA 
    # County were assigned the appropriate SPA value (1-8) during the initial spatial join. Records matched to a location
    # outside of LA County (other CA counties, other states, and other North American countries) were assigned SPA 98
    # by the assign_spa_98 helper function in the previous code block. Any records matched to an offshore location that
    # is within 3 nautical miles of the LA County coastline were assigned SPA 99 by the assign_spa_99 helper function in
    # the previous code block. These types of records are very rare, typically representing birth or death records for
    # indviduals living on boats in a port or harbor (e.g., Port of Long Beach) or points of injury that occur on boats
    # offshore. The remaining records with null values in the SPA field(s) should all be unmatched after geocoding. The 
    # following code blocks will address alternate SPA assignments using components of the original address. 
    ###################################################################################################################
    
                           
    # Function that returns True if a city is known to be in LA County (i.e., included in the list of LAC postal cities)
    # or is an unknown or null value, else False.
    def is_potential_lac_city(city):
        if pd.isnull(city) or city.upper() in unknowns:
            return True
        return city.title() in la_county_cities

    # Function that returns True if a state is in North America (i.e., included in the list of North American states,
    # provinces, and territories), else False. False includes null values or states/provinces outside of North America.
    def is_NA_state(state):
        return str(state).upper() in north_american_states

    # Define conditions for SPA assignment
    
    # Define spa field condition
    null_spa_mask = df[spa_field].isnull()
    
    # Define state field conditions
    state_in_NA = null_spa_mask & df[state_field].apply(lambda x: is_NA_state(x)) # North American state, not CA
    state_is_ca = null_spa_mask & df[state_field].str.upper().isin(['CA', 'CALIFORNIA']) # California
    state_is_null = null_spa_mask & df[state_field].isnull() # Null 
    state_in_unknowns = null_spa_mask & df[state_field].isin(unknowns)  # Placeholder/Unknown states
    state_not_na = null_spa_mask & ~df[state_field].isin(north_american_states + ['CA', 'CALIFORNIA', *unknowns]) # Non-North American state
    
    # Define the city conditions
    city_is_lac = df[city_field].apply(is_potential_lac_city)  # LA County postal city or unknown city
    city_is_null = df[city_field].isnull()  # Null
    city_non_lac = ~df[city_field].apply(is_potential_lac_city) # Non-null, known, but not in LAC (e.g., "Anaheim" or " 'Shenzhen')
    
    ### Apply SPA Assignments Based on State and City Combinations ### 
    
    # Assign SPA 98 to North American, non-CA records, e.g., TX
    df.loc[state_in_NA, spa_field] = 98
    
    # Handle California 
    
    # Assign SPA 99 to California records associated with a potential LA County city, e.g., Mission Hills, CA or UNK, CA
    df.loc[state_is_ca & city_is_lac, spa_field] = 99
    
    # Assign SPA 99 to California records associated with a potential LA County city, e.g., Mission Hills, CA or UNK, CA
    df.loc[state_is_ca & city_is_null, spa_field] = 99
    
    # Assign SPA 98 to California records associated with a non-LA County city, e.g., Ananheim, CA
    df.loc[state_is_ca & city_non_lac, spa_field] = 98
    
    # Handle null states
    df.loc[state_is_null & city_is_null, spa_field] = 99
    df.loc[state_is_null & city_is_lac, spa_field] = 99
    df.loc[state_is_null & city_non_lac, spa_field] = 98
    
    # Handle unknown states, e.g. UNK
    df.loc[state_in_unknowns & city_is_null, spa_field] = 99
    df.loc[state_in_unknowns & city_is_lac, spa_field] = 99
    df.loc[state_in_unknowns & city_non_lac, spa_field] = 98
    
    # Handle states not in North America or placeholders, e.g., GBR, XX, or ZZ
    df.loc[state_not_na & city_is_null, spa_field] = 98
    df.loc[state_not_na & city_is_lac, spa_field] = 99
    df.loc[state_not_na & city_non_lac, spa_field] = 98

    # Print summary of remaining null SPAs
    remaining_null_count = df[spa_field].isnull().sum()
    print(f"Remaining records with null {spa_field} after assignments: {remaining_null_count}")

    return df

def clean_whitespace(text):
    """
    Cleans text by:
    - Stripping leading and trailing whitespace.
    - Replacing consecutive spaces with a single space.
    - Replacing cells containing only whitespace with an empty string.
    
    Args:
    - text (str): The input text from which to remove extra whitespace.
    
    Returns:
    - str: The cleaned text with no leading/trailing whitespace and no consecutive spaces.
    """
    if not isinstance(text, str):
        return text
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return '' if not re.search(r'[^\s]', text) else text

def clean_address(address):
    """
    Cleans and standardizes an address string by applying common text replacements defined in a dictionary.
    
    Args:
    - address (str): The raw input address that needs to be cleaned.
    
    Returns:
    - str: The cleaned address after applying the replacement rules.
    
    Uses:
    - replacement_strings_dict: A dictionary of patterns and their replacements for cleaning addresses.
    """
    for original, replacement in replacement_strings_dict.items():
        address = re.sub(original, replacement, address, flags=re.IGNORECASE)
    return address

def format_xy(address):
    """
    Formats address strings that contain coordinates by correcting misplaced commas or apostrophes
    and converting coordinates from degrees, minutes, and seconds (DMS) or decimal degrees (DD) format.
    
    Args:
    - address (str): The raw input address string, which may contain coordinates in DMS or DD format.
    
    Returns:
    - str: The formatted address with standardized coordinates.
    
    Uses:
    - dd_pattern: A compiled regex pattern for matching decimal degrees (DD) coordinates.
    - dms_pattern: A compiled regex pattern for matching degrees, minutes, and seconds (DMS) coordinates.
    """
    address = re.sub(r"(3\d)[,'](\d\d\d+)", r"\1.\2", address)
    address = re.sub(r"(1\d\d)[,'](\d\d\d+)", r"\1.\2", address)
    dms_match = dms_pattern.match(address)
    dd_match = dd_pattern.match(address)

    if dms_match:
        dms_tuple = dms_match.groups()
        dms_tuple = tuple(x for x in dms_tuple if x is not None)

        if len(dms_tuple) == 4:
            lat = str(round(float(dms_tuple[0]) + float(dms_tuple[1]) / 60, 6))
            lon = '-' + str(round(float(dms_tuple[2]) + float(dms_tuple[3]) / 60, 6))
            address = f"{lat}, {lon}"
        elif len(dms_tuple) == 6:
            lat = str(round(float(dms_tuple[0]) + float(dms_tuple[1]) / 60 + float(dms_tuple[2]) / 3600, 6))
            lon = '-' + str(round(float(dms_tuple[3]) + float(dms_tuple[4]) / 60 + float(dms_tuple[5]) / 3600, 6))
            address = f"{lat}, {lon}"

    elif dd_match:
        decimal_degrees_tuple = dd_match.groups()
        address = f"{decimal_degrees_tuple[0]}, -{decimal_degrees_tuple[1]}"

    return address
  

def clean_addresses(df, is_singleField, singleLine_field=None, street_field=None, apt_or_unit_field=None, city_field=None, state_field=None, zip_field=None):
    """
    Clean addresses in the dataframe based on whether the addresses are in a single field or multiple fields.
    
    Args:
    - df: The input pandas DataFrame containing address data.
    - is_singleField (bool): Either True for single field or False for multiple fields to specify the address format.
    - singleLine_field (str): The column name for the full address if in a single field.
    - street_field, city_field, state_field, zip_field (str): The column names for the street, city, state, and zip fields if addresses are in multiple fields.
    
    Returns:
    - The cleaned DataFrame with changes flagged.
    """
    df = df.astype(str)
    df.fillna('', inplace=True)
    
    # Initialize a change flag column
    df['Address_Modified'] = False

    # Process single field addresses
    if is_singleField and singleLine_field:
        # Apply all transformations in one chain
        df[f"Cleaned_{singleLine_field}"] = (
            df[singleLine_field]
            .apply(clean_address)
            .apply(format_xy)
            .apply(clean_whitespace)
        )
        
        # Flag rows where a change occurred
        df['Address_Modified'] = df[f"Cleaned_{singleLine_field}"] != df[singleLine_field]

    # Process multiple field addresses
    else:
        for col in [street_field, apt_or_unit_field, city_field, state_field, zip_field]:
            if col and col in df.columns:

                # Apply cleaning to each field
                df[f"Cleaned_{col}"] = (
                    df[col]
                    .apply(clean_address)
                    .pipe(lambda s: s.apply(format_xy) if col == street_field else s)  # Apply format_xy only to street_field
                    .apply(clean_whitespace)
                )
                
                # Flag changes
                df['Address_Modified'] = df['Address_Modified'] | (df[f"Cleaned_{col}"] != df[col])

    return df
