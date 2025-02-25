import pandas as pd
import xlsxwriter

def create_xlsx_file(filename, headers, data):
    # Convert data to a Pandas DataFrame
    df = pd.DataFrame(data, columns=headers.keys())

    # Replace NaN/Inf values before writing
    df = df.replace([float('inf'), float('-inf')], "").fillna("")

    # Create an Excel writer with XlsxWriter
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='License Holders')

        # Get the XlsxWriter workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['License Holders']

        # Ensure that NaN/Inf do not cause issues
        workbook.set_properties({'nan_inf_to_errors': True})

        # Define a header format
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4F81BD',
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        # Apply header format and set column widths
        for col_num, (col_name, width) in enumerate(headers.items()):
            worksheet.write(0, col_num, col_name, header_format)
            worksheet.set_column(col_num, col_num, width)

        # Define a cell format with text wrapping
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })

        # Apply format to all cells
        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = df.iloc[row, col]
                if isinstance(value, (int, float)) and pd.notna(value):
                    worksheet.write_number(row + 1, col, value, cell_format)
                else:
                    worksheet.write(row + 1, col, str(value), cell_format)

        # Freeze the header row
        worksheet.freeze_panes(1, 0)

        # Enable auto-filter
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

