from shiny import reactive
from Forceringen.Database.fetch_bits_db import PLCBitRepositoryAsync
from Forceringen.util.unified_db_connection import DatabaseConnection


def create_save_reason_handler(inputs, plc_bits_data, selected_plc, selected_resource, save_message, config_loader,
                               selected_bit_detail=None, bit_history_data=None):
    """
    Information:
        Creates a unified reactive effect handler for saving reason and forced_by values
        when the Enter key is pressed in either table view or detail view.
        Handles both view contexts based on the provided parameters.

    Parameters:
        Input: inputs - Shiny inputs object
              plc_bits_data - Reactive value containing the current bit data
              selected_plc - Reactive value for the selected PLC
              selected_resource - Reactive value for the selected resource
              save_message - Reactive value to display status messages
              config_loader - ConfigLoader instance for database access
              selected_bit_detail - Optional reactive value for the selected bit detail (detail view)
              bit_history_data - Optional reactive value to store the bit history data (detail view)
        Output: Reactive effect function that handles saving reasons on Enter key

    Date: 08/06/2025
    Author: TOVY
    """

    # Handler for table view (resource/ALL view)
    @reactive.effect
    @reactive.event(inputs.save_reason_triggered)
    async def handle_save_reason_table():
        await _save_reason_common("table", inputs.save_reason_triggered())

    # Handler for detail view
    @reactive.effect
    @reactive.event(inputs.save_reason_detail_triggered)
    async def handle_save_reason_detail():
        await _save_reason_common("detail", inputs.save_reason_detail_triggered())

    async def _save_reason_common(view_type, trigger_data):
        """Common logic for saving reasons in both views"""
        if not trigger_data:
            return

        # ✅ Extra defensieve check voor view type
        if view_type == "detail":
            bit_data = selected_bit_detail()
            if not bit_data:
                print("Warning: Save reason triggered for detail view but no bit selected - ignoring")
                return  # ✅ Gewoon returnen zonder error message te zetten

        # Get data based on view type
        if view_type == "table":
            # Table view logic
            index = int(trigger_data.get('index', -1))
            reason_text = trigger_data.get('reasonValue', '')
            melding_text = trigger_data.get('meldingValue', '')  # Add melding extraction
            forced_text = trigger_data.get('forcedValue', '')

            data = plc_bits_data()
            if not data or index < 0 or index >= len(data):
                print("Warning: Save reason triggered for table view but no valid data - ignoring")
                return

            record = data[index]
            plc_name = selected_plc.get()
            resource_name = selected_resource.get()
            bit_number = record.get('bit_number')

        else:  # detail view
            # Detail view logic
            reason_text = trigger_data.get('reasonValue', '')
            melding_text = trigger_data.get('meldingValue', '')
            forced_text = trigger_data.get('forcedValue', '')

            bit_data = selected_bit_detail()
            if not bit_data:
                print("Warning: Save reason triggered for detail view but no bit selected - ignoring")
                return

            plc_name = bit_data.get('PLC') or selected_plc()
            resource_name = bit_data.get('resource') or selected_resource()
            bit_number = bit_data.get('bit_number')
            record = bit_data

        print(f"Saving reason in {view_type} view for bit {bit_number} on PLC {plc_name} resource {resource_name}...")

        try:
            # Create DB connection using unified connection
            db_connection = DatabaseConnection(config_loader)
            conn = await db_connection.get_connection(is_async=True)

            try:
                # Update the reason in the database with SQL Server syntax - FIXED PARAMETER ORDER
                result = await conn.execute(
                    "EXEC insert_force_reason :plc_name, :resource_name, :bit_number, :reason_text, :melding_text, :forced_text",
                    {
                        "plc_name": plc_name,
                        "resource_name": resource_name,
                        "bit_number": bit_number,
                        "reason_text": reason_text,
                        "melding_text": melding_text,
                        "forced_text": forced_text
                    }
                )

                # Check result and update status
                if result:
                    save_message.set(f"Reason saved for bit {bit_number}")
                    print(f"Updated reason for bit {bit_number} to: {reason_text}")
                    print(f"Updated melding for bit {bit_number} to: {melding_text}")
                    print(f"Updated forced_by for bit {bit_number} to: {forced_text}")

                    # Update local data based on view type
                    if view_type == "table":
                        # Update table data
                        record['reason'] = reason_text
                        record['melding'] = melding_text  # Add melding update
                        record['forced_by'] = forced_text
                        new_data = data.copy()
                        new_data[index] = record
                        plc_bits_data.set(new_data)
                    else:  # detail view
                        # Update detail data
                        updated_bit_data = record.copy()
                        updated_bit_data['reason'] = reason_text
                        updated_bit_data['melding'] = melding_text  # Add melding update
                        updated_bit_data['forced_by'] = forced_text
                        selected_bit_detail.set(updated_bit_data)

                        # Refresh history data if available
                        if bit_history_data is not None:
                            repository = PLCBitRepositoryAsync(config_loader)
                            history_results = await repository.fetch_bit_history(updated_bit_data, selected_plc())
                            bit_history_data.set(history_results)

                else:
                    save_message.set(f"Failed to save reason for bit {bit_number}")
            finally:
                await conn.disconnect()

        except Exception as e:
            save_message.set(f"Error: {str(e)}")
            print(f"Database error: {str(e)}")

    return handle_save_reason_table, handle_save_reason_detail