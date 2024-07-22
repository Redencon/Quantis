"""A Dash app with a DataTable with a large number of rows and pagination."""
import dash
from dash import dcc, html, dash_table
import pandas as pd

# Create a Dash app
app = dash.Dash(__name__, assets_folder='Package/quantis/assets')

# Create a DataFrame
df = pd.DataFrame({
    'a': range(1000),
    'b': range(1000),
    'c': ["A" for _ in range (1000)]
})

# Create the layout
app.layout = html.Div([
    dash_table.DataTable(
        id='table',
        columns=[
            {'name': i, 'id': i}
            for i in df.columns if i != 'c'] + [
                {'name': 'c', 'id': 'c', 'presentation': 'dropdown'}
            ],
        data=df.to_dict('records'),
        page_size=10,
        editable=True,
        dropdown={'c': {
            'options': [
                {'label': i, 'value': i}
                for i in ["A", "B", "C"]
            ]
        }},
        cell_selectable=False
    )
])

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)