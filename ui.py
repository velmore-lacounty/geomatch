from shiny import ui

def app_ui(request=None):
    return ui.page_fluid(
        # Main title
        ui.h4("                                                                                                               ", class_="mb-4"),
        ui.div(
            ui.div(
                # Outer container for logo and text
                ui.div(
                    # Logo image
                    ui.img(
                        src="https://lh6.googleusercontent.com/proxy/7-fWANcXB1VwfImWucUj3TeGVm6W9yxLmCvZmxAoDS2uWnCLRwccXSv2Y8TnyZm8f7bGrUddYNd82t8NJUg8SsF5bHtSFixVB_RV_So1t3M1dHAGc7I",
                        style="max-height: 120px; width: auto; margin-right: 15px;"  # Fixed max height for the logo
                    ),
                    style="display: flex; align-items: center; height: 100%;"  # Ensure the logo aligns vertically
                ),
                # Title and subtitle
                ui.div(
                    ui.h1(
                        "GeoMatch",
                        style="font-size: 4rem; font-weight: bold; margin-bottom: 5px; text-align: center;"
                    ),
                    ui.h2(
                        "LA County Department of Public Health Secure Geocoding Application",
                        style="font-size: 2rem; margin-bottom: 0; text-align: center;"
                    ),
                    style="flex: 1; display: flex; flex-direction: column; justify-content: center;"  # Center text vertically
                ),
                class_="d-flex align-items-center justify-content-center",
                style="height: 140px;"  # Ensure both elements have the same height
            ),
            class_="mb-4"  # Add margin below the header section
        ),
        
        # File upload section
        ui.panel_well(
            ui.h3(
              ui.tags.strong("Step 1: Upload a File")
              ),
            ui.input_file("file_upload", "Click Browse or drag and drop to upload a file (.csv or .xlsx) containing addresses or latitude/longitude (xy coordinates).", accept=['.csv', '.xlsx']),
            ui.p(
              "To geocode, your file must contain addresses in one or more fields. To execute a spatial join that will assign common demographic, political, and/or administrative units, your file must contain latitude (Y) and longitude (X) fields, with coordinates in decimal degree format (e.g., 32.1599830, -118.2311459).",
              class_="text-muted"
            ),
            class_="mb-4"
        ),
        
        # Address type selection section
        ui.panel_well(
            ui.h3(
              ui.tags.strong("Step 2: Select Input Data Type")
              ),
            ui.p(
              "My file contains:",
              class_="mb-3"
            ),
            ui.input_radio_buttons("address_type", "", 
                                   {"single": "Addresses in a single field", 
                                   "multiple": "Addresses parsed in multiple fields",
                                   "xy": "Latitude and Longitude fields"}),
             # Dynamic UI for field selectors
            ui.output_ui("field_selector_ui"),
            class_="mb-4"
        ),

        # Advanced geocoding options (conditionally shown)
        ui.panel_well(
            ui.h3(
              ui.tags.strong("Step 3: Set Geoprocessing Parameters (optional)")
              ),
            ui.p(
              "The menus below provide options to refine the geocoding or spatial joining processes. The default settings will meet most users' needs. "
              "To run the tool with the default settings, skip to Step 4. To adjust the tool settings, please read the instructions "
              "carefully and refer to the tool documentation for more information. "
              ),
            ui.div(
                ui.output_ui("clean_addresses_ui"),  # Dynamically show/hide based on address_type
                ui.output_ui("geocoding_score_ui"),
                ui.output_ui("advanced_geocoding_options_ui"),
                ui.output_ui("shapefile_checkbox_ui"),  # Shapefile selection for spatial join (conditionally shown for XY input)
                ui.output_ui("census_warning_ui"), # Field selection for address type field (conditionally shown for spatial joins to census tracts and/or split tracts)
                ui.output_ui("vital_records_ui"), # Radio buttons for opting into Vital Records Geocoding settings
                #style="padding-left: 20px;"
            ),
            class_="mb-4"
        ),
        
        # Output format selection
        ui.panel_well(
            ui.h3(
              ui.tags.strong("Step 4: Select Output File Format")
              ),
            ui.p("Choose the type of file to generate as an output. Available file types are .csv and .xlsx."),
            ui.input_radio_buttons("output_format", "", 
                                   choices={"csv": "CSV", "xlsx": "Excel"},
                                   selected="csv"),
            class_="mb-4"
        ),
        
        # Error message placeholder
        ui.output_ui("error_message"),
        
        # Run button with task label
        ui.input_task_button("run_button", "Run", task_label="Processing...", class_="btn btn-primary mb-4"),
        
        # File upload warning
        ui.output_ui("file_upload_warning"),
        
        # Dynamically display download button after geocoding is complete
        ui.output_ui("download_button_ui"),
        
        # Dynamically display function failure message if geocoding or spatial joining fails
        ui.output_ui("function_failed_message"),
        
        # Footer with credits or other info
        ui.div("Created by the Information Management and Analytics Office", class_="text-muted mt-5 text-center")
    )
