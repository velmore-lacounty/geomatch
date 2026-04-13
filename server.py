from shiny import reactive, App, ui, render, req
from shiny.types import SilentException
from functions.functions import log_error_to_file, read_file, geocode, sequential_sj, clean_addresses, clear_ct_fields, assign_alt_spas
from vars import log_txt, log_csv, locator_smp, smp_geocode_url, candidate_fields, rename_dict, fields_to_nullify, shapefiles_folder, shp_map, replacement_strings_dict, dd_pattern, dms_pattern, la_county_cities, north_american_states, unknowns, lac_boundary_shp, lac_3nm_buffer_shp
import pandas as pd
import regex as re
import io, os, traceback
from openpyxl import Workbook
from datetime import datetime

def server(input, output, session):
    
# Handle errors and warnings
    
    # Set global warning message(s)
    upload_file_warning = ui.p(
                            'Please upload a file',
                            class_="text-danger")
    
    # Render upload_file_warning below the run button until a file has been uploaded
    @render.ui
    def file_upload_warning():
        # Check if a file has been uploaded
        file_info = input.file_upload()
        if not file_info:  
            return upload_file_warning
          
    # Render function failure message below run button if geocoding or spatial joining fails      
    function_failed_message_store = reactive.Value(None)
    @render.ui
    def function_failed_message():
        failure_message = function_failed_message_store.get()
        return ui.p(failure_message, class_="text-danger") if failure_message else None
    output.function_failed_message = function_failed_message
    
    # Render missing required or recommended inputs message above run buttons if inputs are missing
    error_message_store = reactive.Value(None)
    @render.ui
    def error_message():
        current_message = error_message_store.get()
        return current_message if current_message else None  # Return the current message or None if no message
    output.error_message = error_message
    
# Begin handling app inputs
    
    # Store the uploaded file
    @reactive.Calc
    def uploaded_file():
        file_info = input.file_upload()
        if file_info and isinstance(file_info, list):
            # Assuming only one file is uploaded, so we use the first file
            return file_info[0]['datapath']
        return None

    
    # Dynamically generate field selectors based on address type selection
    @render.ui
    def field_selector_ui():
        file_path = uploaded_file()
        if file_path is None:
            return upload_file_warning
        
        else:
            df = read_file(file_path)
              
            columns = list(df.columns)

            # Check if user selected single or multiple fields
            if input.address_type() == "single":
                # potential_addr_fields = [column for column in columns if 'Address' in column]
                # default_choice = potential_addr_fields[0] if potential_addr_fields else 'Select a field'
                
                return ui.TagList(
                  ui.div(
                    ui.input_select("single_field_selector", "Full address*", choices=["Select a field"] + columns), #, selected=default_choice),
                    class_="col-md-3"),
                  ui.p("*Field is required.",
                       class_="text-muted")
            )
            elif input.address_type() == "multiple":
              
                return ui.TagList(   # Multiple field selectors for street, city, state, and zip
                    ui.div(
                      ui.input_select("street_field", "Address 1", choices=["Select a field"] + columns), #,selected=default_choice),
                      class_="col-md-3"
                    ),
                    ui.div(
                      ui.input_select("street2_field", "Address 2", choices=["Select a field"] + columns), #,selected=default_choice),
                      class_="col-md-3"
                    ),
                    ui.div(
                      ui.input_select("city_field", "City", choices=["Select a field"] + columns), #,selected=default_choice),
                      class_="col-md-3"
                    ),
                    ui.div(
                      ui.input_select("state_field", "State", choices=["Select a field"] + columns), #,selected=default_choice),
                      class_="col-md-3"
                    ),
                    ui.div(
                      ui.input_select("zip_field", "Zip code", choices=["Select a field"] + columns), #,selected=default_choice),
                      class_="col-md-3"
                    ),
                    ui.p("It is recommended to provide field names for the Address 1, City, State, and Zip code fields. Use the Address 2 field only if your data contains apartment "
                    "or unit numbers (e.g., Apt 12) in a separate field from the house number and street (e.g., 123 Main St.). If your data is missing one of these fields, you may "
                    "leave the value of that field blank. However, leaving the Address 1, City, State, and/or Zip code field(s) blank may decrease the number or quality of matches "
                    "you receive during geocoding.",
                       class_="text-muted")
            )
            elif input.address_type() == "xy":
                # Multiple field selectors for Latitude and Longitude
                return ui.TagList(
                    ui.div(
                      ui.input_select("latitude_field", "Select Latitude (Y) Field*", choices=["Select a field"] + columns),
                      class_="col-md-3"
                    ),
                    ui.div(
                      ui.input_select("longitude_field", "Select Longitude (X) Field*", choices=["Select a field"] + columns),
                      class_="col-md-3"
                    ),
                    ui.p("*Field is required.",
                       class_="text-muted")
                )
        return None
      
    
    # Dynamically show/hide clean_addresses checkbox based on address type
    @render.ui
    def clean_addresses_ui():
        if input.address_type() in ["single", "multiple"]:
            return ui.div(
                          # Outer div for the hollow rectangle
                          ui.div(
                              # Title block
                              ui.div(
                                  ui.h4(
                                      "Clean and standardize addresses",
                                      style=(
                                          "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                                          "width: 100%; text-align: center; margin: 0;"
                                      )
                                  ),
                                  style="width: 100%; margin: 0 auto;"
                              ),
                              # Content inside the hollow rectangle
                              ui.div(
                                  ui.p(
                                      'The number and quality of matches made during geocoding depends significantly on the quality (completeness and correctness) of the input addresses. '
                                      'We can often improve the number and quality of matches by correcting spelling and syntax errors before geocoding; e.g., changing "OUTH PASADENA" '
                                      'to "SOUTH PASADENA", or "NORTHBOUND 5, MAIN ST EXIT" to "I-5 N @ MAIN ST". The IMAO GIS team has developed an algorithm for correcting common spelling '
                                      'and syntax errors in addresses before geocoding. To apply this algorithm to your input data, check the box below (recommended). Although the algorithm '
                                      'has been thoroughly tested, it cannot catch every error, and it can make mistakes. If you choose to apply the address cleaning algorithm to your input '
                                      'data, you can review any changes in the output file, which contains both the original and cleaned addresses. For more information, please see the app '
                                      'documentation.'
                                  ),
                                  ui.input_checkbox("clean_addresses", "Yes, clean my addresses", value=True),
                                  ui.h4("  ", class_="mb-4"),
                                  style="padding: 20px;"  # Inner content padding
                              ),
                              style=(
                                  "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                              )
                          )
                      )


        return None  # Return None if 'xy' is selected
    
    # Dynamically show/hide geocoding score slider
    @render.ui
    def geocoding_score_ui():
        if input.address_type() in ["single", "multiple"]:
            return ui.div(
                          # Outer div for the hollow rectangle
                          ui.div(
                              # Title block
                              ui.div(
                                  ui.h4(
                                      "Select a minimum match score for geocoded records",
                                      style=(
                                          "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                                          "width: 100%; text-align: center; margin: 0;"
                                      )
                                  ),
                                  style="width: 100%; margin: 0 auto;"
                              ),
                              # Content inside the hollow rectangle
                              ui.div(
                                  ui.p(
                                      "During geocoding, the locator compiles a list of addresses that may be matches for each input address. "
                                      "Each address in the list is assigned a score (0-100) assessing its similarity to the input address. "
                                      "Addresses on the list that receive a minimum score of 70 are considered ",
                                      ui.tags.em("candidates"),
                                      ". The candidate with the highest score is a ",
                                      ui.tags.em("match "),
                                      "for the input address. If no addresses on the list exceed a score of 70, the input address is considered ",
                                      ui.tags.em("unmatched"), ".",
                                      ui.br(),
                                      ui.br(),
                                      "You can set minimum score higher than 70 to decrease the likelihood of incorrect matches. However, selecting "
                                      "a higher minimum score may result in fewer matches.",
                                      ui.br(),
                                      ui.br(),
                                      ui.tags.strong(
                                                    "To increase the minimum match score, set the slider to the desired score. Otherwise, leave "
                                                    "the slider set to 70."  
                                                    )
                                  ),
                                  # Wrap the slider in a div and apply Bootstrap class to control the width
                                  ui.div(
                                      ui.input_slider("min_score", "", min=70, max=100, value=70, step=1),
                                      class_="col-md-4 mb-4",
                                      style="margin-left: 40px;",
                                  ),
                                  style="padding: 20px;"  # Inner content padding
                              ),
                              style=(
                                  "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                              )
                          )
                      )

    
    # Dynamically show/hide advanced geocoding options based on address type
    @render.ui
    def advanced_geocoding_options_ui():
        if input.address_type() in ["single", "multiple"]:
            return ui.TagList(
               ui.div(
                      # Outer div for the hollow rectangle
                      ui.div(
                          # Title block
                          ui.div(
                              ui.h4(
                                  "Select the type(s) of addresses to match",
                                  style=(
                                      "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                                      "width: 100%; text-align: center; margin: 0;"
                                  )
                              ),
                              style="width: 100%; margin: 0 auto;"
                          ),
                          # Content inside the hollow rectangle
                          ui.div(
                              ui.p(
                                  "In geocoding, a locator is used to find the best match for each input address. The locator will always "
                                  "attempt to find the most precise match for an address. If a precise match cannot be found for a full street "
                                  "address, the locator will attempt to match using components of the address, such as the street name, zipcode, "
                                  "city, or state. If an address is incomplete or not a traditional street address, the locator will use the available "
                                  "components to find the best available match.",
                                  ui.br(),
                                  ui.br(),
                                  "You can determine the level of precision of your matches by selecting acceptable address types from the checklist below. "
                                  "The default values are good for datasets that contain primarily street addresses (e.g., 123 Main St., Los Angeles, CA 90002) "
                                  "and users who want to maximize their number of matches, even if some of the matches are less precise, such as matches to a "
                                  "zipcode or city centroid. If your data includes non-traditional addresses, such as street intersections or mile markers, or if "
                                  "your project requires a high level of precision for your matches, you may want to change the default values. A full explanation "
                                  "of each address type is included in the app documentation."
                              ),
                              # Custom layout using CSS for a 3-column layout
                              ui.div(
                                  ui.div(
                                      ui.input_checkbox_group(
                                          "accepted_addr_types_1",
                                          " ",
                                          choices=[
                                              "Subaddress",
                                              "PointAddress",
                                              "Parcel",
                                              "StreetAddress",
                                              "StreetInt",
                                          ],
                                          selected=[
                                              "Subaddress",
                                              "PointAddress",
                                              "Parcel",
                                              "StreetAddress",
                                              "StreetInt",
                                          ],
                                      ),
                                      class_="col-md-4",
                                  ),
                                  ui.div(
                                      ui.input_checkbox_group(
                                          "accepted_addr_types_2",
                                          " ",
                                          choices=[
                                              "StreetAddressExt",
                                              "POI",
                                              "DistanceMarker",
                                              "StreetMidBlock",
                                              "StreetName",
                                          ],
                                          selected=[
                                              "StreetAddressExt",
                                              "POI",
                                              "DistanceMarker",
                                              "StreetMidBlock",
                                              "StreetName",
                                          ],
                                      ),
                                      class_="col-md-4",
                                  ),
                                  ui.div(
                                      ui.input_checkbox_group(
                                          "accepted_addr_types_3",
                                          " ",
                                          choices=[
                                              "PostalExt",
                                              "Postal",
                                              "PostalLoc",
                                              "Locality",
                                              "LatLong",
                                          ],
                                          selected=[
                                              "PostalExt",
                                              "Postal",
                                              "PostalLoc",
                                              "Locality",
                                              "LatLong",
                                          ],
                                      ),
                                      class_="col-md-4",
                                  ),
                                  class_="row",
                              ),
                              ui.h4("  ", class_="mb-4"),
                              style="padding: 20px;"  # Inner content padding
                          ),
                          style=(
                              "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                          )
                      )
                  ),

            
                # Advanced geocoding options: Set special address type criteria
                ui.panel_conditional(
                        "input.accepted_addr_types_3 !== undefined && input.accepted_addr_types_3.includes('Locality')",
                        ui.div(
                              # Outer div for the hollow rectangle
                              ui.div(
                                  # Title block
                                  ui.div(
                                      ui.h4(
                                          "Set special address type criteria",
                                          style=(
                                              "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                                              "width: 100%; text-align: center; margin: 0;"
                                          )
                                      ),
                                      style="width: 100%; margin: 0 auto;"
                                  ),
                                  # Content inside the hollow rectangle
                                  ui.div(
                                      ui.p(
                                          ui.tags.strong("You selected 'Locality' from the list of address types to match above."),
                                          ui.br(),
                                          ui.br(),
                                          "Locality matches have several subtypes, including Country, State/Province, and City. "
                                          "Sometimes, state or city level matches are precise enough for your needs, but country level matches are not. In this case, you can check ",
                                          ui.tags.em("Unmatch country centroids "),
                                          "to unmatch any records with a Country address subtype. Similarly, if city level matches are precise enough, but state level "
                                          "are not, check ", 
                                          ui.tags.em("Unmatch state centroids "),
                                          "to unmatch records with a State address subtype. Finally, in some cases, city level matches may be precise enough, unless the record matches to "
                                          "the City of Los Angeles, which is very large. To unmatch records with a City address subtype that are matched to the City of LA, check ",
                                          ui.tags.em("Unmatch City of LA centroid."),
                                          " For a more detailed explanation of this setting, please see the application documentation."
                                      ),
                                      ui.input_checkbox("country_centroid", "Unmatch country centroids", value=False),
                                      ui.input_checkbox("state_centroid", "Unmatch state centroids", value=False),
                                      ui.input_checkbox("la_centroid", "Unmatch City of LA centroid", value=False),
                                      style="padding: 20px;"  # Inner content padding
                                  ),
                                  style=(
                                      "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                                  )
                              )
                          )

                )
        )
        return None  # Return None if 'xy' is selected 
      
    
    # Dynamically render checkbox group for shapefiles if address type is xy
    @render.ui
    def shapefile_checkbox_ui():
        if input.address_type() == "xy":
            # Generate a list of choices from the outermost keys of shp_map
            shp_choices = [k for k in shp_map]
            years = [
                  '2020',
                  '2021', 
                  '2022',
                  '2027'
              ]
            default_selection = [k for k in shp_map if any(year in k for year in years)]
            return ui.div(
                          # Outer div for the hollow rectangle
                          ui.div(
                              # Title block
                              ui.div(
                                  ui.h4(
                                      "Select the geographies to join to your point (xy) locations",
                                      style=(
                                          "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                                          "width: 100%; text-align: center; margin: 0;"
                                      )
                                  ),
                                  style="width: 100%; margin: 0 auto;"
                              ),
                              # Content inside the hollow rectangle
                              ui.div(
                                  ui.p(
                                      "To determine the demographic, political, or administrative districts a point falls within, "
                                      "conduct a spatial join. The spatial join will add one or more fields to your input table "
                                      "identifying attribute(s) of the district(s) each point falls within. For more information about "
                                      "spatial joins, please see the app documentation."
                                  ),
                                  ui.input_checkbox_group("shapefile_selection", " ", choices=shp_choices, selected=default_selection),
                                  style="padding: 20px;"  # Inner content padding
                              ),
                              style=(
                                  "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                              )
                          )
                      )

        return None

    # Render warning message if census tracts or split census tracts are selected
    @render.ui
    def census_warning_ui():
        if input.address_type() != "xy":
            return None

        selected_layers = input.shapefile_selection()  # Get selected shapefiles
        census_layers = [c for c in shp_map if "Census Tracts" in c]
        selected_census_layers = [layer for layer in selected_layers if layer in census_layers]

        if not selected_census_layers:
            return None

        if len(selected_census_layers) == 1:
            ct_layer_selection = selected_census_layers[0]
        elif len(selected_census_layers) == 2:
            ct_layer_selection = f"{selected_census_layers[0]} and {selected_census_layers[1]}"
        else:
            ct_layer_selection = f"{', '.join(selected_census_layers[:-1])}, and {selected_census_layers[-1]}"

        # UI title block
        title_block = ui.div(
            ui.h4(
                "Special handling for Census Tract and Split Census Tract joins",
                style=(
                    "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                    "width: 100%; text-align: center; margin: 0;"
                )
            ),
            style="width: 100%; margin: 0 auto;"
        )

        # UI body text (above field selector)
        outer_content = ui.p(
            ui.tags.strong(f"You have selected {ct_layer_selection} to join to your input data."),
            ui.br(),
            "Points geocoded to the zip code level or locality level (city, county, state/province, or country) should not be joined to census tracts "
            "or split census tracts because zip codes and localities are generally larger than tracts. Joining points that were geocoded at the "
            "zip code or locality level to census tracts or split census tracts can lead to biases and/or errors if the joined data is aggregated to "
            "census tract or split census tracts. To avoid such errors, the app will not, by default, provide census tract or split census tract matches "
            "for records geocoded to 'Postal', 'PostalLoc', or 'Locality' address types.",
            ui.br(), ui.br(),
            "If you want to override the default handling of tract-level joins because your data does not contain address type information "
            "or because you will not be aggregating your joined data to census tracts or split census tracts, you can opt out of the default "
            "tool behavior.",
            ui.br(), ui.br(),
            ui.tags.strong("Opting out is not advised for geocoded data.")
        )

        # Check for the uploaded file
        file_path = uploaded_file()
        if file_path is None:
            return ui.div(
                title_block,
                ui.div(
                    outer_content,
                    upload_file_warning,
                    style="padding: 20px;"
                ),
                style=(
                    "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                )
            )

        # Read the uploaded file
        df = read_file(file_path)
        column_choices = list(df.columns)

        if "Address_Type" in column_choices:
          default_choice = "Address_Type"
        elif "Addr_type" in column_choices:
          default_choice = "Addr_type"
        else:
          default_choice = "Select a field"

        return ui.div(
            title_block,
            ui.div(
                ui.p(
                    ui.tags.strong(f"You have selected {ct_layer_selection} to join to your input data."),
                    ui.br(),
                    "Points geocoded to the zip code level or locality level (city, county, state/province, or country) should not be joined to census tracts "
                    "or split census tracts because zip codes and localities are generally larger than tracts. Joining points that were geocoded at the "
                    "zip code or locality level to census tracts or split census tracts can lead to biases and/or errors if the joined data is aggregated to "
                    "census tract or split census tracts. To avoid such errors, the app will not, by default, provide census tract or split census tract matches "
                    "for records geocoded to 'Postal', 'PostalLoc', or 'Locality' address types.",
                    ui.br(),
                    ui.br(),
                    "If you want to override the default handling of tract-level joins because your data does not contain address type information "
                    "or because you will not be aggregating your joined data to census tracts or split census tracts, you can opt out of the default "
                    "tool behavior.",
                    ui.br(),
                    ui.br(),
                    ui.tags.strong("Opting out is not advised for geocoded data."),
                ),
                *ui.TagList(
                    ui.div(
                        ui.input_select(
                            "addr_type_field_selector",
                            "Address type field*:",
                            choices=["Select a field"] + column_choices + ["Opt out"],
                            selected=default_choice,
                        ),
                        class_="col-md-3"
                    ),
                    ui.p(
                        ui.tags.strong("Guidance for address type field selection"),
                        ui.tags.ul(
                            ui.tags.li(
                                "If you geocoded your data with this application and are now running a spatial join, leave the default selection ('Address_Type') in the dropdown menu."
                            ),
                            ui.tags.li(
                                "If you geocoded your data with another application, such as ArcGIS Pro or ArcMap, leave the default selection ('Addr_type') in the dropdown menu."
                            ),
                            ui.tags.li(
                                "If you believe your data contains address type information in a field with a different name (for example, you changed the name of the address type field after geocoding), "
                                "select the name of that field from the dropdown menu below."
                            ),
                            ui.tags.li(
                                "If your data does not include an address type field or you want to override this setting, select 'Opt out' from the dropdown menu below. "
                            )
                        ),
                    ),
                    ui.panel_conditional(
                        "input.addr_type_field_selector === 'Opt out'",
                        ui.div(
                            ui.p(
                                ui.tags.strong(
                                    "Please check the box below to confirm you understand that opting out may affect the accuracy of your results."
                                )
                            ),
                            ui.input_checkbox(
                                "opt_out_confirmation",
                                "I understand that I am opting out of the recommended tool behavior.",
                                value=False
                            )
                        )
                    ),
                    ui.p("*Field is required.", class_="text-muted")
                ),
                style="padding: 20px;"
            ),
            style=(
                "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; "
                "width: 99%; margin-left: auto; margin-right: auto;"
            )
        )



# Dynamically render vital records UI when SPA layer(s) are selected to join to input data
    @render.ui
    def vital_records_ui():
        if input.address_type() == "xy":
            selected_layers = input.shapefile_selection()  # Get selected shapefiles
            selected_spa_layers = [layer for layer in selected_layers if "Service Planning Areas" in layer]
    
            if selected_spa_layers:
                # Generate the SPA layer selection text
                if len(selected_spa_layers) == 1:
                    spa_layer_selection = selected_spa_layers[0]
                elif len(selected_spa_layers) == 2:
                    spa_layer_selection = f"{selected_spa_layers[0]} and {selected_spa_layers[1]}"
                else:
                    spa_layer_selection = f"{', '.join(selected_spa_layers[:-1])}, and {selected_spa_layers[-1]}"
    
                # Check file upload status and prepare content
                file_path = uploaded_file()
                if not file_path:
                    spa_content = upload_file_warning
                else:
                    df = read_file(file_path)
                    input_fields = list(df.columns)
                    spa_content = ui.TagList(
                        ui.div(
                            ui.input_select(
                                "spa_city_field",
                                "City field*",
                                choices=["Select a field"] + input_fields,
                            ),
                            class_="col-md-3"
                        ),
                        ui.div(
                            ui.input_select(
                                "spa_state_field",
                                "State field*",
                                choices=["Select a field"] + input_fields,
                            ),
                            class_="col-md-3"
                        ),
                        ui.p("*Field is required.", class_="text-muted")
                    )
    
                # Generate the main container for the vital records section
                return ui.div(
                    # Title block
                    ui.div(
                        ui.h4(
                            "Special handling for vital records data",
                            style=(
                                "background-color: black; color: white; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; "
                                "width: 100%; text-align: center; margin: 0;"
                            )
                        ),
                        style="width: 100%; margin: 0 auto;"
                    ),
                    # Content inside the hollow rectangle
                    ui.div(
                        ui.p(
                            ui.tags.strong(f"You have selected {spa_layer_selection} to join to your input data.")
                        ),
                        ui.p(
                            "Vital records data (births, deaths, and points of injury) often requires special handling of SPAs when executing spatial joins.",
                            ui.br(),
                            "Are you working with vital records data?"
                        ),
                        ui.input_radio_buttons("vr_radio", "", choices={"yes": "Yes", "no": "No"}, selected="no"),
                        ui.panel_conditional(
                            "input.vr_radio === 'yes'",
                            ui.div(
                                ui.p(
                                    "When working with vital records, all records are traditionally assigned a value in the SPA field. Records that are successfully geocoded to locations "
                                    "within LA County are joined to SPAs 1-8, depending on each record's location. Records geocoded to locations outside LA County and records that cannot be "
                                    "geocoded (typically due to unknown, incomplete, or incorrect addresses) are assigned values of 98 or 99:",
                                    ui.tags.ul(
                                        ui.tags.li(
                                            ui.tags.strong("SPA 98:  "),
                                            "addresses outside LA County, e.g., '1600 Pennsylvania Ave NW, Washington, D.C. 20500'"
                                        ),
                                        ui.tags.li(
                                            ui.tags.strong("SPA 99:  "),
                                            "addresses assumed to be within LA County but unable to be matched by the locator during geocoding, e.g., 'Homeless, Los Angeles, CA'"
                                        )
                                    ),
                                    "Assigning alternate SPA values requires validating the original input address, which must be parsed (multiple fields).",
                                    ui.br(),
                                    ui.br(),
                                    ui.tags.strong("Provide the city and state field names in the dropdown menus below.")
                                    ),
                                spa_content
                            )
                        ),
                        style="padding: 20px;"  # Inner content padding
                    ),
                    style=(
                        "border: 1px solid black; border-radius: 8px; padding: 0; margin-top: 20px; width: 99%; margin-left: auto; margin-right: auto;"
                    )
                )
        return None


    # Store geocoding results
    geocoded_data_store = reactive.Value(None)
    
    output_suffix = reactive.Value("_")  # Initiate output_suffix reactive val
    
# Begin geoprocessing workflow 
    
    # Track the number of times the "Run" button has been clicked
    run_button_clicks = reactive.Value(0)
    
    # Run geocoding or spatial join function when run button is clicked
    @reactive.Effect
    def trigger_geocoding():
        if input.run_button() > run_button_clicks.get():
            run_button_clicks.set(input.run_button())  # Update the click counter
            
            missing_required = [] # Initialize a list to track required inputs for geocoding or spatial join functions
            missing_recommended = [] # Initialize a list to track recommended inputs for geocoding or spatial join functions
            
            if input.address_type() == "xy":
                if input.latitude_field() in [None, 'Select a field']:
                    missing_required.append(ui.HTML('<b>Step 2:</b> Latitude (Y) field is missing. Provide a latitude (Y) field.'))
                if input.longitude_field() in [None, 'Select a field']:
                    missing_required.append(ui.HTML('<b>Step 2:</b> Longitude (X) field is missing. Provide a longitude (X) field.'))
                if not input.shapefile_selection():
                    missing_required.append(
                        ui.HTML(
                          '<b>Step 3:</b> No demographic, political, or administrative districts have been selected. '
                          'Select one or more districts to join to your input data.'
                        )
                    )
                else:
                  census_layers = [c for c in shp_map if "Census Tracts" in c]
                  if any(layer in input.shapefile_selection() for layer in census_layers):
                      if input.addr_type_field_selector() in [None, "Select a field"]:
                          missing_required.append(ui.HTML('<b>Step 3:</b> Address type field is missing. Provide an address type field, or select "Opt out".'))
                      if input.addr_type_field_selector() == "Opt out":
                          missing_recommended.append(
                            ui.HTML(
                              '<b>Step 3:</b> You opted out of the recommended tool behavior for census and/or split census tract joins.'
                              '<br><b>Note:</b> You joined Census Tracts or Split Census Tracts to your input data, but opted out of '
                              'providing an address type field. If your input data contains points geocoded to the zipcode or locality '
                              '(city, county, state/province, or country) level, the accuracy of tract-level joins cannot be guaranteed '
                              'for those records. Take caution when aggregating the joined data. <b>For more information, refer to the app '
                              'documentation.</b>'
                              )
                          )
                          if not input.opt_out_confirmation():
                              missing_required.append(
                                  ui.HTML(
                                    '<b>Step 3:</b> Acknowledgement of census tract/split census tract override is missing. '
                                    'Check the box to confirm you want to opt out of the default tool behavior.'
                                  )
                              )
                              
                if input.vr_radio() == 'yes':
                    if input.spa_city_field() is None or input.spa_city_field() == 'Select a field':
                        missing_required.append(ui.HTML('<b>Step 3:</b> City field is missing. Provide a city field or select "No" under "Are you working with vital records data?"'))
                    if input.spa_state_field() is None or input.spa_state_field() == 'Select a field':
                        missing_required.append(ui.HTML('<b>Step 3:</b> State field is missing. Provide a state field or select "No" under "Are you working with vital records data?"'))
            else:
                if input.address_type() == "single":    
                    # Check if a single line input field was provided
                    if input.single_field_selector() in [None, 'Select a field']:
                        missing_required.append(ui.HTML("<b>Step 2:</b> Full address field is missing. Provide a full address field."))
                
                elif input.address_type() == "multiple":
                    # Check if all of the input address component fields are blank
                    if all(field in [None, 'Select a field'] for field in [input.street_field(), input.city_field(), input.state_field(), input.zip_field()]):
                        missing_required.append(ui.HTML('<b>Step 2:<b> All required address fields are missing. At least one of the following fields must be '
                                                        'provided: Address 1 (street), City, State, Zip Code'))
                    # Check if any of the recommended address component fields are blank
                    if any(field in [None, 'Select a field'] for field in [input.street_field(), input.city_field(), input.state_field(), input.zip_field()]):
                        missing_recommended.append(ui.HTML('<b>Step 2:</b> It is recommended to provide Address 1 (street), City, State, Zip Code fields. '
                                                           'Leaving any of these fields blank may result in fewer or lower quality matches during geocoding.'))    
                    
                # Concatenate the selected values from the three input lists (groups)
                accepted_addr_types = input.accepted_addr_types_1() + input.accepted_addr_types_2() + input.accepted_addr_types_3()
                # Check if any acceptable address types have been selected
                if not accepted_addr_types:
                    missing_required.append(ui.HTML('<b>Step 3:</b> No address type(s) have been selected. Select one or more type(s) of addresses '
                                                    'to match during geocding.'))
                                              
            if missing_required or missing_recommended:
                if missing_required:
                    # Create a bulleted list in HTML format
                    missing_requirements_list = ui.tags.ul(*[ui.tags.li(field) for field in missing_required], 
                                                           class_="text-danger")
                    error_message_store.set(ui.TagList(
                        ui.p("Required inputs are missing:", class_="text-danger"),
                        missing_requirements_list
                    ))
                    return
                
                if missing_recommended:
                    # Create a bulleted list in HTML format
                    missing_recommendations_list = ui.tags.ul(*[ui.tags.li(field) for field in missing_recommended],
                                                              class_="text-warning")
                    error_message_store.set(ui.TagList(
                        ui.p("Tool ran with the following warnings:", class_="text-warning"),
                        missing_recommendations_list
                    ))
            else:
                # Clear error message and run the appropriate function
                error_message_store.set(None)
            
            
            try:
                file_path = uploaded_file()
                if file_path:
                    df = read_file(file_path)
                    columns = list(df.columns)
                  
                    # Get the minimum score and accepted address types from user input
                    min_score = input.min_score()
                    # Concatenate the selected values from the three input lists (groups)
                    accepted_addr_types = input.accepted_addr_types_1() + input.accepted_addr_types_2() + input.accepted_addr_types_3()
                    
                    # Check the state of the vrbis checkboxes
                    state_centroid = input.state_centroid()
                    country_centroid = input.country_centroid()
                    la_centroid = input.la_centroid()
                    
                    # Set vrbis to True if any of the checkboxes is checked
                    vrbis = any([state_centroid, country_centroid, la_centroid])
                    
                    # Check if the 'clean_addresses' checkbox is selected
                    clean_addresses_selected = input.clean_addresses()
                  
                    # Check the address type and pass appropriate field(s) to the geocode or SJ function
                    if input.address_type() == "single":
                        single_field = input.single_field_selector() if input.single_field_selector() != 'Select a field' else None
                        
                        if clean_addresses_selected:
                            df = clean_addresses(df=df,
                                                 is_singleField=True,
                                                 singleLine_field=single_field)
                            single_field = f"Cleaned_{single_field}"
                        
                        geocoded_data = geocode(df=df, 
                                                locator=locator_smp,
                                                url=smp_geocode_url,
                                                candidate_fields=candidate_fields,
                                                null_fields=fields_to_nullify,
                                                field_map=rename_dict, 
                                                is_singleField=True, 
                                                singleLine_field=single_field, 
                                                min_score=min_score, 
                                                accepted_addr_types=accepted_addr_types,
                                                vrbis=vrbis,
                                                state_centroid=state_centroid,
                                                country_centroid=country_centroid,
                                                la_centroid=la_centroid)
                        
                        geocoded_data_store.set(geocoded_data)
                        output_suffix.set("_GEO")  # Set suffix for geocoding
                
                    elif input.address_type() == "multiple":
                        street_field = input.street_field() if input.street_field() != "Select a field" else None
                        street2_field = input.street2_field() if input.street2_field() != "Select a field" else None
                        city_field = input.city_field() if input.city_field() != "Select a field" else None
                        state_field = input.state_field() if input.state_field() != "Select a field" else None
                        zip_field = input.zip_field() if input.zip_field() != "Select a field" else None
                        
                        if clean_addresses_selected:
                            df = clean_addresses(df=df,
                                                 is_singleField=False,
                                                 street_field=street_field,
                                                 apt_or_unit_field=street2_field,
                                                 city_field=city_field, 
                                                 state_field=state_field, 
                                                 zip_field=zip_field)
                            
                            street_field=f"Cleaned_{street_field}"
                            street2_field=f"Cleaned_{street2_field}"
                            city_field=f"Cleaned_{city_field}" 
                            state_field=f"Cleaned_{state_field}" 
                            zip_field=f"Cleaned_{zip_field}"
                        
                        geocoded_data = geocode(df=df, 
                                                locator=locator_smp,
                                                url=smp_geocode_url,
                                                candidate_fields=candidate_fields,
                                                null_fields=fields_to_nullify,
                                                field_map=rename_dict, 
                                                is_singleField=False, 
                                                street_field=street_field,
                                                apt_or_unit_field=street2_field,
                                                city_field=city_field, 
                                                state_field=state_field, 
                                                zip_field=zip_field, 
                                                min_score=min_score, 
                                                accepted_addr_types=accepted_addr_types,
                                                vrbis=vrbis,
                                                state_centroid=state_centroid,
                                                country_centroid=country_centroid,
                                                la_centroid=la_centroid)
                                                
                        geocoded_data_store.set(geocoded_data)
                        output_suffix.set("_GEO")  # Set suffix for geocoding
                    
                    elif input.address_type() == "xy":
                        # Get field selections for latitude and longitude
                        x_field = input.longitude_field()
                        y_field = input.latitude_field()
        
                        # Get selected shapefiles from the checkbox group
                        shapefiles_to_join = input.shapefile_selection()
        
                        # Perform spatial joins
                        spatial_joined_data = sequential_sj(
                                                  point_df=df,
                                                  x_field=x_field,
                                                  y_field=y_field,
                                                  shapefiles_to_join=shapefiles_to_join,
                                                  shp_map=shp_map,
                                                  shapefiles_folder=shapefiles_folder
                                                  )

                        # Optionally clear ct fields
                        try:
                            shapefiles = input.shapefile_selection()
                            # Only continue if it's a non-empty list and contains 'Census Tract'
                            if shapefiles and any("Census Tract" in name for name in shapefiles):
                                addr_type_field = input.addr_type_field_selector()
                                if addr_type_field not in [None, "Opt out", "Select a field"]:
                                    spatial_joined_data = spatial_joined_data.replace(to_replace='nan', value=' ',
                                                                                      regex=False)
                                    spatial_joined_data = clear_ct_fields(
                                        df=spatial_joined_data,
                                        addr_type_field=addr_type_field,
                                        shp_map=shp_map
                                    )
                        except SilentException:
                            # One of the inputs hasn't been initialized yet — skip safely
                            pass
                        
                        # Determine whether to add SPA 98/99 values, and process accordingly
                        vital_records_true = input.vr_radio()
                        if vital_records_true == 'yes':
                            spa_city_field = f"Cleaned_{input.spa_city_field()}" if f"Cleaned_{input.spa_city_field()}" in columns else input.spa_city_field() # Checks for presence of cleaned address data
                            spa_state_field = f"Cleaned_{input.spa_state_field()}" if f"Cleaned_{input.spa_state_field()}" in columns else input.spa_state_field()
                            spa_fields = spa_values = [next(iter(shp_map[shapefile_name]['join_fields'].values())) for shapefile_name in shapefiles_to_join if 'Service Planning Areas' in shapefile_name] # Retrive joined SPA fields
                            if spa_city_field != 'Select a field' and spa_state_field != 'Select a field':
                                for spa_field in spa_fields:
                                    spatial_joined_data = assign_alt_spas(
                                                                df=spatial_joined_data, 
                                                                city_field=spa_city_field, 
                                                                state_field=spa_state_field, 
                                                                spa_field=spa_field,
                                                                x_field=x_field,
                                                                y_field=y_field)
    
                        # Store the result DataFrame
                        geocoded_data_store.set(spatial_joined_data)
                        output_suffix.set("_SJ")  # Set suffix for spatial join
                    
                    # Explicitly trigger UI re-render to show the download button
                    session.send_input_message("download_button_ui", {})
                    
                    function_failed_message_store.set(None)
                    
            except Exception as e:
                error_type = {type(e).__name__}
                traceback_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                timestamp = datetime.now().isoformat()
                function_failed_message_store.set(f"""
                    An unexpected error occurred. Please check that you have selected input parameters correctly. If you are unsure, 
                    please refer to the tool documentation. If you believe your input parameters are correct, refresh the page and try 
                    again. If the error persists, contact the IMAO GIS team at gis@ph.lacounty.gov and provide the following timestamp: 
                    {timestamp}
                    """)
                log_error_to_file(
                    error=e, 
                    txt_log_path=log_txt,
                    csv_log_path=log_csv
                )
                print("An error occurred:")
                print(f"Error type: {error_type}")
                print(f"Error message: {e}")
                print(f"Traceback details:\n{traceback_str}")

    
    # Dynamically render the download button when data is ready
    @render.ui
    def download_button_ui():
        geocoded_data = geocoded_data_store.get()
        if geocoded_data is not None:
            return ui.download_button("download_geocoded", "Download", class_="btn btn-primary mb-4")
      
    
    # Provide the downloadable file with dynamic filename
    @reactive.Calc
    def dynamic_filename():
        file_info = input.file_upload()  # Directly access file info here
        if file_info and isinstance(file_info, list):
            base_name = os.path.splitext(file_info[0]['name'])[0]  # Extract base name from file
        else:
            base_name = "output"  # Fallback name if no file uploaded
        suffix = output_suffix()  # Get the suffix (_GEO or _SJ)
        output_format = input.output_format()  # Get the file format
    
        return f"{base_name}{suffix}.{output_format}"  # Correct dynamic filename

    
    # Provide the downloadable CSV when the user clicks the download button
    @render.download(filename=lambda: dynamic_filename())
    def download_geocoded():
        geocoded_data = geocoded_data_store.get()  # Retrieve stored geocoded data (DataFrame)
        output_format = input.output_format()  # Retrieve the user’s selected output format
        
        if geocoded_data is not None:
            # Replace NaN values with empty strings
            geocoded_data = geocoded_data.fillna('')
            geocoded_data = geocoded_data.replace(to_replace='nan', value=' ', regex=False)
            output = io.BytesIO() if output_format == 'xlsx' else io.StringIO()
            
            if output_format == "csv":
                geocoded_data.to_csv(output, index=False)
                output.seek(0)
                yield output.getvalue() # Yield CSV data for download

            elif output_format == "xlsx":
                geocoded_data.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                yield output.read()  # Yield Excel data for download
        else:
            yield "No data available for download"
