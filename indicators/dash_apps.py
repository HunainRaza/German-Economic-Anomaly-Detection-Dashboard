"""
Enhanced Dash Dashboard with Interactive LLM Explanations
==========================================================
Features:
- Click on anomaly markers (red X) to view LLM explanation
- "View Explanation" button in anomaly table
- Explanations loaded from database (pre-generated)
- Modal popup for rich explanation display
- Optional "Regenerate" button for fresh explanations

Location: indicators/dash_apps.py
"""

from django.conf import settings
from django_plotly_dash import DjangoDash
import dash
from dash import dcc, html, Input, Output, State, ctx
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc


def get_year_range():
    """Get actual year range from database."""
    try:
        from .models import EconomicIndicator
        years = EconomicIndicator.objects.values_list('year', flat=True).distinct().order_by('year')
        if years:
            return int(min(years)), int(max(years))
        return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch year range: {e}")
        return None


def load_data():
    """Load data from database including anomaly explanations."""
    try:
        from .models import EconomicIndicator
        
        queryset = EconomicIndicator.objects.all().order_by('year')
        if not queryset.exists():
            return pd.DataFrame()
        
        data = list(queryset.values(
            'year',
            'gdp_growth_rate',
            'inflation_rate',
            'unemployment_rate',
            'export_share_gdp',
            'industrial_production_index',
            'is_anomaly',
            'anomaly_score',
            'anomaly_explanation'  # ⭐ Load LLM explanation from database
        ))
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"⚠️ Warning: Could not load data: {e}")
        return pd.DataFrame()


def get_anomaly_explanation(year):
    """Get explanation for a specific year from database."""
    try:
        from .models import EconomicIndicator
        obj = EconomicIndicator.objects.get(year=year)
        
        if obj.is_anomaly and obj.anomaly_explanation:
            return obj.anomaly_explanation
        elif obj.is_anomaly:
            return "This year was detected as anomalous, but no detailed explanation is available yet. Run 'python manage.py detect_anomalies' to generate explanations."
        else:
            return f"{year} was not detected as an economic anomaly."
    except Exception as e:
        return f"Error loading explanation: {str(e)}"


# =============================================================================
# Create Dash App with Bootstrap
# =============================================================================

app = DjangoDash(
    'EconomicDashboard',
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css'
    ]
)

# Layout with modal for explanations
app.layout = html.Div([
    # Store for year range
    dcc.Store(id='year-range-store'),
    
    # Store for selected anomaly year
    dcc.Store(id='selected-anomaly-year'),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # 30 seconds
        n_intervals=0
    ),
    
    # Modal for showing explanations
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id='modal-title'), close_button=True),
        dbc.ModalBody([
            html.Div(id='modal-explanation', style={'fontSize': '16px', 'lineHeight': '1.6'}),
            html.Hr(),
            html.Div(id='modal-indicators', style={'fontSize': '14px'}),
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
        ]),
    ], id="explanation-modal", size="lg", is_open=False),
    
    # Loading overlay
    dcc.Loading(
        id="loading-main",
        type="default",
        children=[
            html.Div(id='main-content')
        ]
    )
], style={'backgroundColor': '#f8f9fa', 'padding': '20px'})


# =============================================================================
# Callbacks
# =============================================================================

@app.callback(
    Output('year-range-store', 'data'),
    Input('interval-component', 'n_intervals')
)
def fetch_year_range(n):
    """Fetch actual year range from database."""
    year_range = get_year_range()
    if year_range:
        min_year, max_year = year_range
        return {'min': min_year, 'max': max_year}
    return {'min': None, 'max': None}


@app.callback(
    Output('main-content', 'children'),
    Input('year-range-store', 'data')
)
def render_dashboard(year_data):
    """Render the entire dashboard after we know the actual year range."""
    if not year_data or year_data['min'] is None:
        return html.Div([
            html.Div([
                html.H1("🇩🇪 German Economic Dashboard", className="text-center mb-4 mt-4"),
                html.Div([
                    html.Div(className="spinner-border text-primary", role="status"),
                    html.P("Loading data from database...", className="mt-3 text-muted")
                ], className="text-center mt-5")
            ], className="container", style={'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'color': 'white', 'padding': '20px', 'borderRadius': '8px'}),
        ])
    
    min_year = year_data['min']
    max_year = year_data['max']
    
    return html.Div([
        # Header
        html.Div([
            html.H1("🇩🇪 German Economic Dashboard", className="text-center mb-4 mt-4"),
            html.P(
                f"AI-Powered Economic Anomaly Detection System ({min_year}-{max_year})",
                className="text-center mb-2", style={'color': '#DFD3E3', 'fontSize': '18px'}
            ),
            html.P(
                "💡 Click on red anomaly markers or table buttons to view LLM-generated explanations",
                className="text-center mb-4", style={'color': '#E8DFF5', 'fontSize': '14px', 'fontStyle': 'italic'}
            ),
        ], className="container", style={'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'color': 'white', 'padding': '20px', 'borderRadius': '8px'}),
        
        # Summary Cards
        html.Div([
            html.Div([
                # GDP Card
                html.Div([
                    html.Div([
                        html.H6("GDP Growth", className="card-title text-muted"),
                        html.H3(id='gdp-value', className="mb-0"),
                        html.Small("Latest Year", className="text-muted")
                    ], className="card-body")
                ], className="card shadow-sm"),
                
                # Inflation Card
                html.Div([
                    html.Div([
                        html.H6("Inflation Rate", className="card-title text-muted"),
                        html.H3(id='inflation-value', className="mb-0"),
                        html.Small("Latest Year", className="text-muted")
                    ], className="card-body")
                ], className="card shadow-sm"),
                
                # Unemployment Card
                html.Div([
                    html.Div([
                        html.H6("Unemployment", className="card-title text-muted"),
                        html.H3(id='unemployment-value', className="mb-0"),
                        html.Small("Latest Year", className="text-muted")
                    ], className="card-body")
                ], className="card shadow-sm"),
                
                # Anomalies Card
                html.Div([
                    html.Div([
                        html.H6("Anomalies Detected", className="card-title text-muted"),
                        html.H3(id='anomaly-count', className="mb-0 text-danger"),
                        html.Small("Out of Total Years", className="text-muted")
                    ], className="card-body")
                ], className="card shadow-sm"),
                
            ], className="row row-cols-1 row-cols-md-4 g-4 mb-4")
        ], className="container"),
        
        # Year Range Slider
        html.Div([
            html.Div([
                html.Label(f"Select Year Range ({min_year}-{max_year}):", className="form-label fw-bold"),
                dcc.RangeSlider(
                    id='year-slider',
                    min=min_year,
                    max=max_year,
                    value=[min_year, max_year],
                    marks={year: str(year) for year in range(min_year, max_year + 1)},
                    step=1,
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], className="card-body")
        ], className="container mb-4"),
        
        # Charts
        html.Div([
            # GDP Chart
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("📈 GDP Growth Rate (%)", className="card-title"),
                        html.P("Click red X markers to view anomaly explanations", 
                               className="text-muted small mb-3"),
                        dcc.Graph(id='gdp-chart')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
            # Inflation Chart
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("💰 Inflation Rate (%)", className="card-title"),
                        dcc.Graph(id='inflation-chart')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
            # Unemployment Chart
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("👔 Unemployment Rate (%)", className="card-title"),
                        dcc.Graph(id='unemployment-chart')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
            # Anomaly Table with View Buttons
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("🔍 Detected Anomalies", className="card-title"),
                        html.P("Click 'View Explanation' to see LLM-generated analysis", 
                               className="text-muted small mb-3"),
                        html.Div(id='anomaly-table')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
        ], className="container"),
    ], style={'paddingBottom': '50px'})


@app.callback(
    Output('gdp-value', 'children'),
    Output('inflation-value', 'children'),
    Output('unemployment-value', 'children'),
    Output('anomaly-count', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_summary_cards(n):
    """Update summary cards with latest data"""
    df = load_data()
    
    if df.empty:
        return "N/A", "N/A", "N/A", "0"
    
    latest = df.iloc[-1]
    anomaly_count = df['is_anomaly'].sum() if 'is_anomaly' in df.columns else 0
    
    gdp_text = f"{latest['gdp_growth_rate']:.2f}%" if pd.notna(latest.get('gdp_growth_rate')) else "N/A"
    inflation_text = f"{latest['inflation_rate']:.2f}%" if pd.notna(latest.get('inflation_rate')) else "N/A"
    unemployment_text = f"{latest['unemployment_rate']:.2f}%" if pd.notna(latest.get('unemployment_rate')) else "N/A"
    anomaly_text = f"{int(anomaly_count)}"
    
    return gdp_text, inflation_text, unemployment_text, anomaly_text


@app.callback(
    Output('gdp-chart', 'figure'),
    Input('year-slider', 'value'),
    Input('interval-component', 'n_intervals')
)
def update_gdp_chart(year_range, n):
    """Update GDP chart with clickable anomaly markers"""
    df = load_data()
    
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    filtered = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    
    fig = go.Figure()
    
    # Main line
    fig.add_trace(go.Scatter(
        x=filtered['year'],
        y=filtered['gdp_growth_rate'],
        mode='lines+markers',
        name='GDP Growth',
        line=dict(color='#3498db', width=3),
        marker=dict(size=10),
        hovertemplate='<b>Year:</b> %{x}<br><b>GDP Growth:</b> %{y:.2f}%<extra></extra>'
    ))
    
    # Highlight anomalies with click events
    if 'is_anomaly' in filtered.columns:
        anomalies = filtered[filtered['is_anomaly'] == True]
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies['year'],
                y=anomalies['gdp_growth_rate'],
                mode='markers',
                name='Anomaly (Click for explanation)',
                marker=dict(
                    size=18,
                    color='red',
                    symbol='x',
                    line=dict(width=3, color='darkred')
                ),
                customdata=anomalies['year'],  # Store year for click handling
                hovertemplate='<b>🚨 ANOMALY DETECTED</b><br>' +
                             '<b>Year:</b> %{x}<br>' +
                             '<b>GDP Growth:</b> %{y:.2f}%<br>' +
                             '<i>Click to view explanation</i><extra></extra>'
            ))
    
    fig.update_layout(
        title='GDP Growth Rate Over Time',
        xaxis_title='Year',
        yaxis_title='GDP Growth Rate (%)',
        template='plotly_white',
        hovermode='closest',
        clickmode='event+select'  # Enable click events
    )
    
    return fig


@app.callback(
    Output('inflation-chart', 'figure'),
    Input('year-slider', 'value'),
    Input('interval-component', 'n_intervals')
)
def update_inflation_chart(year_range, n):
    """Update inflation chart with selected year range"""
    df = load_data()
    
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    filtered = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    
    # Color bars based on ECB target (2%)
    colors = ['red' if x > 2 else 'green' for x in filtered['inflation_rate']]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=filtered['year'],
        y=filtered['inflation_rate'],
        name='Inflation',
        marker_color=colors,
        text=filtered['inflation_rate'].round(2),
        textposition='outside'
    ))
    
    # Add ECB target line
    fig.add_hline(y=2, line_dash="dash", line_color="orange", 
                  annotation_text="ECB Target: 2%")
    
    # Highlight anomalies
    if 'is_anomaly' in filtered.columns:
        anomalies = filtered[filtered['is_anomaly'] == True]
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies['year'],
                y=anomalies['inflation_rate'],
                mode='markers',
                name='Anomaly',
                marker=dict(
                    size=18,
                    color='red',
                    symbol='x',
                    line=dict(width=3, color='darkred')
                ),
                hovertemplate='<b>🚨 ANOMALY</b><br>Year: %{x}<extra></extra>'
            ))
    
    fig.update_layout(
        title='Inflation Rate (vs ECB Target)',
        xaxis_title='Year',
        yaxis_title='Inflation Rate (%)',
        template='plotly_white'
    )
    
    return fig


@app.callback(
    Output('unemployment-chart', 'figure'),
    Input('year-slider', 'value'),
    Input('interval-component', 'n_intervals')
)
def update_unemployment_chart(year_range, n):
    """Update unemployment chart with selected year range"""
    df = load_data()
    
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    filtered = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=filtered['year'],
        y=filtered['unemployment_rate'],
        mode='lines+markers',
        name='Unemployment',
        fill='tozeroy',
        line=dict(color='#f39c12', width=3),
        marker=dict(size=10)
    ))
    
    # Highlight anomalies
    if 'is_anomaly' in filtered.columns:
        anomalies = filtered[filtered['is_anomaly'] == True]
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies['year'],
                y=anomalies['unemployment_rate'],
                mode='markers',
                name='Anomaly',
                marker=dict(
                    size=18,
                    color='red',
                    symbol='x',
                    line=dict(width=3, color='darkred')
                ),
                hovertemplate='<b>🚨 ANOMALY</b><br>Year: %{x}<extra></extra>'
            ))
    
    fig.update_layout(
        title='Unemployment Rate Over Time',
        xaxis_title='Year',
        yaxis_title='Unemployment Rate (%)',
        template='plotly_white'
    )
    
    return fig


@app.callback(
    Output('anomaly-table', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_anomaly_table(n):
    """Update anomaly detection table with 'View Explanation' buttons"""
    df = load_data()
    
    if df.empty or 'is_anomaly' not in df.columns:
        return html.P("No anomaly data available", className="text-muted")
    
    anomalies = df[df['is_anomaly'] == True].sort_values('year', ascending=False)
    
    if anomalies.empty:
        return html.P("✅ No anomalies detected in the current dataset", className="text-success")
    
    # Create table with action buttons
    table_header = html.Thead(html.Tr([
        html.Th('Year', className="fw-bold"),
        html.Th('GDP Growth (%)', className="fw-bold"),
        html.Th('Inflation (%)', className="fw-bold"),
        html.Th('Unemployment (%)', className="fw-bold"),
        html.Th('Anomaly Score', className="fw-bold"),
        html.Th('Action', className="fw-bold text-center"),
    ]))
    
    table_rows = []
    for _, row in anomalies.iterrows():
        year = int(row['year'])
        table_rows.append(html.Tr([
            html.Td(str(year), className="text-center"),
            html.Td(f"{row['gdp_growth_rate']:.2f}" if pd.notna(row.get('gdp_growth_rate')) else "N/A", 
                   className="text-center"),
            html.Td(f"{row['inflation_rate']:.2f}" if pd.notna(row.get('inflation_rate')) else "N/A",
                   className="text-center"),
            html.Td(f"{row['unemployment_rate']:.2f}" if pd.notna(row.get('unemployment_rate')) else "N/A",
                   className="text-center"),
            html.Td(f"{row['anomaly_score']:.3f}" if pd.notna(row.get('anomaly_score')) else "N/A",
                   className="text-center text-danger fw-bold"),
            html.Td(
                dbc.Button(
                    "🤖 View Explanation",
                    id={'type': 'view-explanation-btn', 'year': year},
                    color="primary",
                    size="sm",
                    className="w-100"
                ),
                className="text-center"
            ),
        ]))
    
    table_body = html.Tbody(table_rows)
    
    table = html.Table(
        [table_header, table_body],
        className="table table-striped table-hover table-bordered"
    )
    
    return table


@app.callback(
    Output('explanation-modal', 'is_open'),
    Output('modal-title', 'children'),
    Output('modal-explanation', 'children'),
    Output('modal-indicators', 'children'),
    Input({'type': 'view-explanation-btn', 'year': dash.dependencies.ALL}, 'n_clicks'),
    Input('gdp-chart', 'clickData'),
    Input('close-modal', 'n_clicks'),
    State('explanation-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_modal(btn_clicks, click_data, close_clicks, is_open):
    """Handle modal open/close and populate with anomaly explanation"""
    
    # Determine which input triggered the callback
    try:
        triggered_id = ctx.triggered_id
    except:
        # Fallback for older Dash versions or Django-Plotly-Dash compatibility
        if not dash.callback_context.triggered:
            return False, "", "", ""
        triggered_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    # Close modal
    if triggered_id == 'close-modal':
        return False, "", "", ""
    
    # Determine which year to show
    year_to_show = None
    
    # Check if triggered by table button
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'view-explanation-btn':
        year_to_show = triggered_id['year']
    
    # Check if triggered by chart click
    elif triggered_id == 'gdp-chart' and click_data:
        if 'points' in click_data and len(click_data['points']) > 0:
            point = click_data['points'][0]
            if 'customdata' in point:
                year_to_show = int(point['customdata'])
    
    # If no year determined, don't open modal
    if year_to_show is None:
        return is_open, "", "", ""
    
    # Load data for this year
    df = load_data()
    
    if df.empty or year_to_show not in df['year'].values:
        return False, "Error", html.P("Year data not found"), ""
    
    year_data = df[df['year'] == year_to_show].iloc[0]
    
    # Get explanation from database
    explanation = get_anomaly_explanation(year_to_show)
    
    # Format title
    title = f"🚨 Economic Anomaly Analysis: {year_to_show}"
    
    # Format explanation
    explanation_content = html.Div([
        html.P(explanation, style={'whiteSpace': 'pre-wrap'}),
    ])
    
    # Format indicators
    indicators_content = html.Div([
        html.H6("📊 Economic Indicators:", className="fw-bold mb-3"),
        html.Div([
            html.Div([
                html.Strong("GDP Growth: "),
                html.Span(f"{year_data['gdp_growth_rate']:.2f}%" if pd.notna(year_data.get('gdp_growth_rate')) else "N/A")
            ], className="mb-2"),
            html.Div([
                html.Strong("Inflation: "),
                html.Span(f"{year_data['inflation_rate']:.2f}%" if pd.notna(year_data.get('inflation_rate')) else "N/A")
            ], className="mb-2"),
            html.Div([
                html.Strong("Unemployment: "),
                html.Span(f"{year_data['unemployment_rate']:.2f}%" if pd.notna(year_data.get('unemployment_rate')) else "N/A")
            ], className="mb-2"),
            html.Div([
                html.Strong("Anomaly Score: "),
                html.Span(f"{year_data['anomaly_score']:.3f}", className="text-danger fw-bold")
            ], className="mb-2"),
        ])
    ])
    
    return True, title, explanation_content, indicators_content