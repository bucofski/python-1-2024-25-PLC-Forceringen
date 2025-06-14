"""
PLC Management and Monitoring Shiny Application

Information:
    This module provides a web-based interface for managing and monitoring PLCs.
    It allows users to view PLC resources, bit statuses, run operations,
    edit configuration, and interact with the database.

Date: 03/06/2025
Author: TOVY
"""
from Forceringen.config.config_path import config_path
from Forceringen.util.config_manager import ConfigLoader
from shiny import App, ui, render, reactive
from Forceringen.ui.ui_components import (
    create_app_ui, create_resource_buttons_ui,
    create_resource_table, create_plc_table, create_detail_view,
    create_config_view, create_output_view, create_search_view, create_search_results_table

)
from Forceringen.util.server_functions import (
    run_distributor_and_capture_output, validate_yaml, update_configuration,
    update_ui_components, sync_with_database,
    create_resource_click_handler, create_plc_click_handler,
    create_detail_click_handler, create_save_reason_handler,
    create_back_button_handler, create_search_handler

)
import os

try:
    config_loader = config_path.create_config_loader()
    config = config_loader.config  # Store for backward compatibility
    host_options = config_loader.get_host_options()
except FileNotFoundError:
    raise RuntimeError(
        f"YAML config file not found: {config_path.get_path()}\n"
        "Please make sure 'plc.yaml' exists in the group work folder next to this script."
    )


# Create the UI with initial host options
app_ui = create_app_ui(host_options)


def server(inputs, outputs, session):
    """
    Information:
        Defines the server-side logic for the Shiny application.
        Handles reactive values, event handlers, and UI rendering.

    Parameters:
        Input: inputs - Object containing all input values from the UI
              outputs - Object for registering output renderers
              session - The current Shiny session

    Date: 03/06/2025
    Author: TOVY
    """
    # Reactive values
    assert session
    terminal_text = reactive.Value("")
    selected_view = reactive.Value("output")  # "output", "Config", "resource", "ALL", or "detail"
    selected_resource = reactive.Value(None)
    selected_plc = reactive.Value(None)  # Only when used "all"
    plc_bits_data = reactive.Value([])
    resource_buttons_trigger = reactive.Value(0)
    save_message = reactive.Value("")
    selected_bit_detail = reactive.Value(None)  # Store selected bit for detail view
    bit_history_data = reactive.Value([])  # Store history data for detail view
    current_host_options = reactive.Value(config_loader.get_host_options())
    current_config_loader = reactive.Value(config_loader)
    current_config = reactive.Value(config)
    search_results = reactive.Value([])
    search_results_count = reactive.Value("")


    # Initialize host select with current data on startup
    @reactive.effect
    def initialize_host_select():
        """Initialize host select with fresh data from config file"""
        fresh_config_loader = ConfigLoader(str(config_path.get_path()))
        fresh_options = fresh_config_loader.get_host_options()
        current_host_options.set(fresh_options)
        current_config_loader.set(fresh_config_loader)
        current_config.set(fresh_config_loader.config)

        option_keys = list(fresh_options.keys()) if fresh_options else []
        ui.update_select(
            "host_select",
            choices=fresh_options,
            selected=option_keys[0] if option_keys else None
        )

    # View-switching logic
    @reactive.effect
    @reactive.event(inputs.view_output)
    def _():
        selected_view.set("output")
        save_message.set("")
        print("Selected view is:", selected_view())

    @reactive.effect
    @reactive.event(inputs.view_config)
    def _():
        selected_view.set("Config")
        save_message.set("")
        save_message.set("")
        plc_bits_data.set([])
        selected_resource.set(None)
        selected_plc.set(None)
        selected_bit_detail.set(None)
        bit_history_data.set([])
        print("Selected view is:", selected_view())

    @reactive.effect
    @reactive.event(inputs.view_resource)
    def _():
        selected_view.set("resource")
        save_message.set("")

    @reactive.effect
    @reactive.event(inputs.view_all)
    def _():
        selected_view.set("ALL")
        save_message.set("")

    @reactive.effect
    @reactive.event(inputs.view_detail)
    def _():
        selected_view.set("detail")

    # In de server functie, voeg toe na de andere view event handlers:
    @reactive.effect
    @reactive.event(inputs.view_search)
    def _():
        selected_view.set("search")
        save_message.set("")
        print("Selected view is:", selected_view())

    # Create event handlers with reactive config - MOVED TO INSIDE EFFECTS
    @reactive.effect
    def setup_event_handlers():
        """Setup event handlers with current config"""
        current_cfg = current_config()
        current_cfg_loader = current_config_loader()

        create_resource_click_handler(
            current_cfg, inputs, selected_resource, selected_plc, selected_view, plc_bits_data, current_cfg_loader
        )

        create_plc_click_handler(
            current_cfg, inputs, selected_plc, selected_resource, selected_view, plc_bits_data, current_cfg_loader
        )

        create_detail_click_handler(
            plc_bits_data, inputs, selected_bit_detail, selected_view, bit_history_data, current_cfg_loader, selected_plc
        )

        create_save_reason_handler(
            inputs,
            plc_bits_data,
            selected_plc,
            selected_resource,
            save_message,
            current_cfg_loader,
            selected_bit_detail,
            bit_history_data
        )

        #
        # create_save_reason_handler(
        #     inputs,
        #     plc_bits_data,
        #     selected_plc,
        #     selected_resource,
        #     save_message,
        #     config_loader,
        #     selected_bit_detail,  # Voor detail view
        #     bit_history_data  # Voor detail view
        # )

        create_back_button_handler(
            inputs, selected_resource, selected_view, plc_bits_data, current_cfg_loader, selected_plc
        )

    # In de server functie, voeg toe na de setup_event_handlers:
    @reactive.effect
    def setup_search_handlers():
        """Setup search handlers with current config"""
        current_cfg = current_config()
        handle_search, handle_clear = create_search_handler(inputs, outputs, session, current_cfg)

    @outputs()
    @render.text
    def selected_host():
        return f"Selected Host: {inputs.host_select()}"

    @outputs()
    @render.text
    def terminal_output():
        return terminal_text()

    @reactive.effect
    @reactive.event(inputs.start_btn)
    def on_start():
        # Switch to output view first
        selected_view.set("output")

        # Then run the distributor with current config
        selected_host_value = inputs.host_select()
        current_cfg_loader = current_config_loader()
        captured_output = run_distributor_and_capture_output(current_cfg_loader, selected_host_value)
        terminal_text.set(captured_output or "[No output produced]")

    @outputs()
    @render.ui
    def resource_buttons():
        # Make this output depend on the trigger AND current config
        resource_buttons_trigger()
        current_cfg = current_config()

        # Use the current config instead of the global one
        return create_resource_buttons_ui(current_cfg, inputs, selected_resource, selected_plc)

    # En in de main_panel render functie, voeg de zoekview toe:
    @outputs()
    @render.ui
    def main_panel():
        if selected_view() == "output":
            return create_output_view()
        elif selected_view() == "Config":
            return create_config_view(config_path.get_path())
        elif selected_view() == "search":  # Voeg deze regel toe
            current_cfg = current_config()
            return create_search_view(current_cfg)  # Gebruik current_cfg
        elif selected_view() == "resource":
            data = plc_bits_data()
            return create_resource_table(data, selected_resource, selected_plc)
        elif selected_view() == "ALL":
            data = plc_bits_data()
            return create_plc_table(data, selected_plc)
        elif selected_view() == "detail":
            bit_data = selected_bit_detail()
            history_data = bit_history_data()
            return create_detail_view(bit_data, history_data)
        return None

    # Voeg zoek outputs toe:
    @outputs()
    @render.ui
    def search_results_table():
        results = search_results()
        return create_search_results_table(results)

    @outputs()
    @render.text
    def search_results_count_display():
        return search_results_count.get()


    # Voeg zoek event handlers toe:
    @reactive.effect
    @reactive.event(inputs.search_execute)
    async def handle_search_execute():  # Async functie
        try:
            current_cfg = current_config()
            current_cfg_loader = current_config_loader()
            
            # Create a temporary message handler for sync_with_database
            temp_message = reactive.Value("")
            
            # Get all data by syncing with database
            await sync_with_database(current_cfg_loader, temp_message, session)
            
            # Now get the actual data from your stored data
            # Since sync_with_database synchronizes but doesn't return data directly,
            # we need to get the data from wherever it's stored after sync
            
            all_search_data = []
            sftp_hosts = current_cfg.get('sftp_hosts', [])
            
            for host in sftp_hosts:
                plc_name = host.get('hostname', host.get('ip_address'))
                resources = host.get('resources', [])
                
                for resource in resources:
                    # Instead of calling sync_with_database here, we should get data
                    # from wherever it's stored after the sync above
                    # This depends on your implementation - you might need to call
                    # a different function that actually retrieves the data
                    
                    # For now, create empty data structure
                    resource_data = []
                    
                    # Add PLC name and resource to each item
                    for item in resource_data:
                        item['plc_name'] = plc_name
                        item['resource'] = resource
                    
                    all_search_data.extend(resource_data)
            
            # Apply filters
            search_filters = {
                'kks': inputs.search_kks() if hasattr(inputs, 'search_kks') else '',
                'comment': inputs.search_comment() if hasattr(inputs, 'search_comment') else '',
                'plc': inputs.filter_plc() if hasattr(inputs, 'filter_plc') else 'Alle PLCs',
                'resource': inputs.filter_resource() if hasattr(inputs, 'filter_resource') else 'Alle Resources',
                'force_status': inputs.filter_force_status() if hasattr(inputs, 'filter_force_status') else 'Alle',
                'value': inputs.filter_value() if hasattr(inputs, 'filter_value') else 'Alle'
            }
            
            filtered_data = filter_search_data(all_search_data, search_filters)
            
            # Update results
            search_results.set(filtered_data)
            count_text = f"Gevonden: {len(filtered_data)} resultaten"
            if len(all_search_data) > 0:
                count_text += f" van {len(all_search_data)} totaal"
            search_results_count.set(count_text)
            
        except Exception as e:
            print(f"Search error: {e}")
            search_results.set([])
            search_results_count.set("Fout bij zoeken")

    @reactive.effect
    @reactive.event(inputs.search_clear)
    def handle_search_clear():
        # Clear all search inputs (inclusief bit_number en melding)
        ui.update_text("search_kks", value="")
        ui.update_text("search_comment", value="")
        ui.update_text("search_bit_number", value="")  # Nieuw toegevoegd
        ui.update_text("search_melding", value="")     # Nieuw toegevoegd
        ui.update_select("filter_plc", selected="Alle PLCs")
        ui.update_select("filter_resource", selected="Alle Resources")
        ui.update_select("filter_force_status", selected="Alle")
        ui.update_select("filter_value", selected="Alle")
        
        # Clear results
        search_results.set([])
        search_results_count.set("")

    @reactive.effect
    @reactive.event(inputs.save_config)
    async def save_yaml_config():
        """Handle YAML configuration saving and database synchronization."""
        global config, config_loader

        try:
            save_message.set("")
            
            # Step 1: Get and validate YAML content
            yaml_content = inputs.yaml_editor()
            test_config = validate_yaml(yaml_content, save_message)
            if not test_config:
                return

            # Update configuration
            config, config_loader = update_configuration(yaml_content, test_config, config_loader, save_message)

            # Update ALL reactive values with new config
            current_config_loader.set(config_loader)
            current_config.set(config)
            new_host_options = config_loader.get_host_options()
            current_host_options.set(new_host_options)

            # Update the select input with new options
            option_keys = list(new_host_options.keys()) if new_host_options else []
            ui.update_select(
                "host_select", 
                choices=new_host_options,
                selected=option_keys[0] if option_keys else None
            )

            update_ui_components(config_loader, inputs, selected_resource, resource_buttons_trigger)

            await sync_with_database(config_loader, save_message, session)

            # Force update of resource buttons by incrementing trigger
            resource_buttons_trigger.set(resource_buttons_trigger() + 1)

            plc_bits_data.set([])
            selected_bit_detail.set(None)
            bit_history_data.set([])

            save_message.set("Configuration saved successfully!")

        except Exception as e:
            save_message.set(f"Error saving file: {str(e)}")

    # Voeg de filter functie toe (uitgebreid met bit_number en melding):
    def filter_search_data(all_data, search_filters):
        """
        Filters data based on search criteria.
        """
        if not all_data:
            return []
        
        filtered = all_data.copy()
        
        # Filter by KKS
        if search_filters.get('kks') and search_filters['kks'].strip():
            kks_term = search_filters['kks'].strip().lower()
            filtered = [item for item in filtered 
                       if kks_term in str(item.get('kks', '')).lower()]
        
        # Filter by comment
        if search_filters.get('comment') and search_filters['comment'].strip():
            comment_term = search_filters['comment'].strip().lower()
            filtered = [item for item in filtered 
                       if (comment_term in str(item.get('comment', '')).lower() or
                           comment_term in str(item.get('second_comment', '')).lower())]
        
        # Filter by bit_number
        if search_filters.get('bit_number') and search_filters['bit_number'].strip():
            bit_term = search_filters['bit_number'].strip().lower()
            filtered = [item for item in filtered 
                       if bit_term in str(item.get('bit_number', '')).lower()]
        
        # Filter by melding
        if search_filters.get('melding') and search_filters['melding'].strip():
            melding_term = search_filters['melding'].strip().lower()
            filtered = [item for item in filtered 
                       if melding_term in str(item.get('melding', '')).lower()]
        
        # Filter by PLC
        if search_filters.get('plc') and search_filters['plc'] != "Alle PLCs":
            filtered = [item for item in filtered 
                       if item.get('plc_name') == search_filters['plc']]
        
        # Filter by Resource
        if search_filters.get('resource') and search_filters['resource'] != "Alle Resources":
            filtered = [item for item in filtered 
                       if item.get('resource') == search_filters['resource']]
        
        # Filter by Force Status
        if search_filters.get('force_status') == "Alleen Geforceerde":
            filtered = [item for item in filtered if item.get('force_active')]
        elif search_filters.get('force_status') == "Alleen Niet-geforceerde":
            filtered = [item for item in filtered if not item.get('force_active')]
        
        # Filter by Value
        if search_filters.get('value') and search_filters['value'] != "Alle":
            target_value = search_filters['value'].upper()
            filtered = [item for item in filtered 
                       if str(item.get('value', '')).upper() == target_value]
        
        return filtered

    @outputs()
    @render.text
    def save_status_output():
        return save_message()

    @outputs()
    @render.text
    def save_status():
        message = save_message()
        if message:
            ui.notification_show(message, duration=3)
            save_message.set("")
        return ""

    # Voeg zoek event handlers toe - Synchrone versie met bit_number en melding:
    @reactive.effect
    @reactive.event(inputs.search_execute)
    def handle_search_execute():
        try:
            current_cfg = current_config()

            existing_data = plc_bits_data.get()

            if not existing_data:
                all_search_data = []
            else:
                all_search_data = existing_data.copy()

            search_filters = {
                'kks': inputs.search_kks() if hasattr(inputs, 'search_kks') else '',
                'comment': inputs.search_comment() if hasattr(inputs, 'search_comment') else '',
                'bit_number': inputs.search_bit_number() if hasattr(inputs, 'search_bit_number') else '',
                'melding': inputs.search_melding() if hasattr(inputs, 'search_melding') else '',
                'plc': inputs.filter_plc() if hasattr(inputs, 'filter_plc') else 'Alle PLCs',
                'resource': inputs.filter_resource() if hasattr(inputs, 'filter_resource') else 'Alle Resources',
                'force_status': inputs.filter_force_status() if hasattr(inputs, 'filter_force_status') else 'Alle',
                'value': inputs.filter_value() if hasattr(inputs, 'filter_value') else 'Alle'
            }
            
            filtered_data = filter_search_data(all_search_data, search_filters)
            
            # Update results
            search_results.set(filtered_data)
            count_text = f"Gevonden: {len(filtered_data)} resultaten"
            if len(all_search_data) > 0:
                count_text += f" van {len(all_search_data)} totaal"
            search_results_count.set(count_text)
            
        except Exception as e:
            print(f"Search error: {e}")
            search_results.set([])
            search_results_count.set("Fout bij zoeken")


app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app(app)