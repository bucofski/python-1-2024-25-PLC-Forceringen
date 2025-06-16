from shiny import reactive
from Forceringen.Database.fetch_bits_db import PLCBitRepositoryAsync


def create_resource_click_handler(config, inputs, selected_resource, selected_plc, selected_view, plc_bits_data,
                                  config_loader):
    """
    Information:
        Creates a reactive effect handler for resource button clicks.
        Tracks click counts to detect only new clicks and prevent duplicate processing.
        When a resource button is clicked, it updates the selected resource and PLC,
        changes the view to "resource", and fetches the bit data for the selected resource.

    Parameters:
        Input: config - Application configuration dictionary
              inputs - Shiny inputs object
              selected_resource - Reactive value for the selected resource
              selected_plc - Reactive value for the selected PLC
              selected_view - Reactive value for the current view mode
              plc_bits_data - Reactive value to store the fetched bit data
              config_loader - ConfigLoader instance for database access
        Output: Reactive effect function that handles resource button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    # Track previous click counts to detect NEW clicks only
    previous_resource_clicks = {}

    @reactive.effect
    async def handle_resource_clicks():
        sftp_hosts = config.get('sftp_hosts', [])
        selected_host_val = inputs.host_select()

        # Filter the right host(s)
        if selected_host_val == "all":
            hosts = sftp_hosts
        else:
            hosts = [h for h in sftp_hosts if
                     h.get('hostname') == selected_host_val or h.get('ip_address') == selected_host_val]

        for i, host in enumerate(hosts):
            resources = host.get('resources', [])
            for j, resource in enumerate(resources):
                btn_id = f"resource_{j}"
                if hasattr(inputs, btn_id):
                    btn_input = getattr(inputs, btn_id)
                    current_count = btn_input()

                    # Get previous count for this button (default to 0)
                    prev_count = previous_resource_clicks.get(btn_id, 0)

                    # Only process if there's a NEW click (current > previous)
                    if current_count > prev_count:
                        hostname = host.get("hostname", host.get("ip_address"))
                        selected_resource.set(resource)
                        selected_plc.set(hostname)
                        selected_view.set("resource")
                        print(f"NEW click - Selected resource: {resource} on PLC: {hostname}")
                        print(f"Selected view: {selected_view()}")

                        # --- Fetch plc_bits for this PLC and resource ---
                        repo = PLCBitRepositoryAsync(config_loader)

                        async def get_bits():
                            return await repo.fetch_plc_bits(hostname, resource_name=resource)

                        results = await get_bits()
                        plc_bits_data.set(results)

                        print("Results from plc_bits view:")
                        for row in results:
                            print(row)

                    # Update the stored count
                    previous_resource_clicks[btn_id] = current_count

    return handle_resource_clicks


def create_plc_click_handler(config, inputs, selected_plc, selected_resource, selected_view, plc_bits_data,
                             config_loader):
    """
    Information:
        Creates a reactive effect handler for PLC button clicks.
        Tracks click counts to detect only new clicks and prevent duplicate processing.
        When a PLC button is clicked (only when "all" is selected in the dropdown),
        it updates the selected PLC, clears the selected resource,
        changes the view to "ALL", and fetches all bit data for the selected PLC.

    Parameters:
        Input: config - Application configuration dictionary
              inputs - Shiny inputs object
              selected_plc - Reactive value for the selected PLC
              selected_resource - Reactive value for the selected resource
              selected_view - Reactive value for the current view mode
              plc_bits_data - Reactive value to store the fetched bit data
              config_loader - ConfigLoader instance for database access
        Output: Reactive effect function that handles PLC button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    # Track previous click counts to detect NEW clicks only
    previous_plc_clicks = {}

    @reactive.effect
    async def handle_plc_clicks():

        sftp_hosts = config.get('sftp_hosts', [])

        if inputs.host_select() != "all":
            return  # only active when "all" is selected

        for i, host in enumerate(sftp_hosts):
            btn_id = f"plc_{i}"
            if hasattr(inputs, btn_id):
                btn_input = getattr(inputs, btn_id)
                current_count = btn_input()

                # Get previous count for this button (default to 0)
                prev_count = previous_plc_clicks.get(btn_id, 0)

                # Only process if there's a NEW click (current > previous)
                if current_count > prev_count:
                    hostname = host.get("hostname", host.get("ip_address"))
                    print(f"NEW click - PLC clicked: {hostname}")
                    selected_plc.set(hostname)
                    selected_resource.set(None)

                    selected_view.set("ALL")

                    repo = PLCBitRepositoryAsync(config_loader)

                    async def get_bits():
                        return await repo.fetch_plc_bits(hostname)

                    results = await get_bits()
                    plc_bits_data.set(results)

                    print("Results for PLC:", hostname)
                    for row in results:
                        print(row)

                # Update the stored count
                previous_plc_clicks[btn_id] = current_count

    return handle_plc_clicks


def create_detail_click_handler(plc_bits_data, inputs, selected_bit_detail, selected_view, bit_history_data,
                                config_loader, selected_plc):
    """
    Information:
        Creates a reactive effect handler for detail button clicks.
        Tracks click counts to detect only new clicks and prevent duplicate processing.
        When a detail button is clicked, it updates the selected bit detail,
        changes the view to "detail", and fetches the bit history data.

    Parameters:
        Input: plc_bits_data - Reactive value containing the current bit data
              inputs - Shiny inputs object
              selected_bit_detail - Reactive value for the selected bit detail
              selected_view - Reactive value for the current view mode
              bit_history_data - Reactive value to store the bit history data
              config_loader - ConfigLoader instance for database access
              selected_plc - Reactive value for the selected PLC
        Output: Reactive effect function that handles detail button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    # Track previous click counts to detect NEW clicks only
    previous_clicks = {}

    @reactive.effect
    async def handle_detail_clicks():
        data = plc_bits_data()
        for i, item in enumerate(data):
            detail_btn_id = f"detail_btn_{i}"
            if hasattr(inputs, detail_btn_id):
                btn_input = getattr(inputs, detail_btn_id)
                current_count = btn_input()

                # Get previous count for this button (default to 0)
                prev_count = previous_clicks.get(detail_btn_id, 0)

                # Only process if there's a NEW click (current > previous)
                if current_count > prev_count:
                    selected_bit_detail.set(item)
                    selected_view.set("detail")
                    print(f"Detail view for bit: {item.get('bit_number', '')}")

                    # Fetch history data for this bit
                    repository = PLCBitRepositoryAsync(config_loader)
                    history_results = await repository.fetch_bit_history(item, selected_plc())
                    bit_history_data.set(history_results)

                # Update the stored count
                previous_clicks[detail_btn_id] = current_count

    return handle_detail_clicks


def create_back_button_handler(inputs, selected_resource, selected_view, plc_bits_data, config_loader, selected_plc):
    """
    Information:
        Creates a reactive effect handler for the back button in the detail view.
        When clicked, it returns to either the resource view or the PLC view,
        depending on the current context, and refreshes the bit data.

    Parameters:
        Input: inputs - Shiny inputs object
              selected_resource - Reactive value for the selected resource
              selected_view - Reactive value for the current view mode
              plc_bits_data - Reactive value to store the fetched bit data
              config_loader - ConfigLoader instance for database access
              selected_plc - Reactive value for the selected PLC
        Output: Reactive effect function that handles back button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    @reactive.effect
    @reactive.event(inputs.back_to_list)
    async def handle_back_button():
        # Return to the appropriate view based on what was selected
        if selected_resource():
            selected_view.set("resource")
            # Refresh the resource data
            repo = PLCBitRepositoryAsync(config_loader)
            results = await repo.fetch_plc_bits(selected_plc(), resource_name=selected_resource())
            plc_bits_data.set(results)
            print(f"Refreshed data for resource {selected_resource()} on PLC {selected_plc()}")
        else:
            selected_view.set("ALL")
            # Refresh the PLC data
            repo = PLCBitRepositoryAsync(config_loader)
            results = await repo.fetch_plc_bits(selected_plc())
            plc_bits_data.set(results)
            print(f"Refreshed data for PLC {selected_plc()}")

    return handle_back_button