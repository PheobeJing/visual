import dash
from dash import html

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Script('console.log("=== SIMPLE JAVASCRIPT TEST ==="); console.log("Time:", new Date().toISOString());'),
    html.H1('Test App - JavaScript Execution Test')
])

if __name__ == '__main__':
    print('Starting simple test app...')
    app.run_server(debug=True, host='127.0.0.1', port=8051)
