"""
Dash Dashboard Application - PROPER DATA-DRIVEN VERSION
No hardcoded years! Fetches real data from database.
"""

from django.conf import settings
from django_plotly_dash import DjangoDash
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from dash import dash_table


def get_year_range():
    """
    Get actual year range from database.
    Returns (min_year, max_year) or None if no data.
    """
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
    """
    Load data from database - called during callbacks, not module load!
    """
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
            'is_anomaly',
            'anomaly_score'
        ))
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"⚠️ Warning: Could not load data: {e}")
        return pd.DataFrame()


# =============================================================================
# Create Dash App - NO DATABASE QUERIES, NO HARDCODED YEARS!
# =============================================================================

app = DjangoDash(
    'EconomicDashboard',
    external_stylesheets=[
        'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css'
    ]
)

# Initial layout with loading state - NO hardcoded years!
# pylint: disable=attribute-defined-outside-init
app.layout = html.Div([
    # Store for year range
    dcc.Store(id='year-range-store'),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # 30 seconds
        n_intervals=0
    ),
    
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
# Callbacks - All database queries happen HERE!
# =============================================================================

@app.callback(
    Output('year-range-store', 'data'),
    Input('interval-component', 'n_intervals')
)
def fetch_year_range(n):
    """
    Fetch actual year range from database.
    This is the FIRST callback that runs - it gets real data!
    """
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
    """
    Render the entire dashboard ONLY after we know the actual year range.
    This ensures we NEVER show hardcoded values!
    """
    # If no data yet, show loading
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
    
    # Now create the actual dashboard with REAL year range
    return html.Div([
        # Header
        html.Div([
            html.H1("🇩🇪 German Economic Dashboard", className="text-center mb-4 mt-4"),
            html.P(
                f"Real-time monitoring of German economic indicators ({min_year}-{max_year})",
                className="text-center mb-4", style={'color': '#DFD3E3'}
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
        
        # Year Range Slider - NOW with REAL data!
        html.Div([
            html.Div([
                html.Label(f"Select Year Range ({min_year}-{max_year}):", className="form-label fw-bold"),
                dcc.RangeSlider(
                    id='year-slider',
                    min=min_year,  # ✅ REAL data from database!
                    max=max_year,  # ✅ REAL data from database!
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
                        html.H5("GDP Growth Rate (%)", className="card-title"),
                        dcc.Graph(id='gdp-chart')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
            # Inflation Chart
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("Inflation Rate (%)", className="card-title"),
                        dcc.Graph(id='inflation-chart')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
            # Unemployment Chart
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("Unemployment Rate (%)", className="card-title"),
                        dcc.Graph(id='unemployment-chart')
                    ], className="card-body")
                ], className="card shadow-sm mb-4")
            ], className="col-md-12"),
            
            # Anomaly Table
            html.Div([
                html.Div([
                    html.Div([
                        html.H5("🔍 Detected Anomalies", className="card-title"),
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
    """Update GDP chart with selected year range"""
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
        marker=dict(size=10)
    ))
    
    # Highlight anomalies
    if 'is_anomaly' in filtered.columns:
        anomalies = filtered[filtered['is_anomaly'] == True]
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies['year'],
                y=anomalies['gdp_growth_rate'],
                mode='markers',
                name='Anomaly',
                marker=dict(
                    size=15,
                    color='red',
                    symbol='x',
                    line=dict(width=2, color='darkred')
                )
            ))
    
    fig.update_layout(
        title='GDP Growth Rate Over Time',
        xaxis_title='Year',
        yaxis_title='GDP Growth Rate (%)',
        template='plotly_white',
        hovermode='x unified'
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
    """Update anomaly detection table"""
    df = load_data()
    
    if df.empty or 'is_anomaly' not in df.columns:
        return html.P("No anomaly data available", className="text-muted")
    
    anomalies = df[df['is_anomaly'] == True].sort_values('year', ascending=False)
    
    if anomalies.empty:
        return html.P("✅ No anomalies detected in the current dataset", className="text-success")
    
    # Create table rows
    table_header = html.Thead(html.Tr([
        html.Th('Year', className="fw-bold"),
        html.Th('GDP Growth (%)', className="fw-bold"),
        html.Th('Inflation (%)', className="fw-bold"),
        html.Th('Unemployment (%)', className="fw-bold"),
        html.Th('Anomaly Score', className="fw-bold"),
    ]))
    
    table_rows = []
    for _, row in anomalies.iterrows():
        table_rows.append(html.Tr([
            html.Td(str(int(row['year'])), className="text-center"),
            html.Td(f"{row['gdp_growth_rate']:.2f}" if pd.notna(row.get('gdp_growth_rate')) else "N/A", 
                   className="text-center"),
            html.Td(f"{row['inflation_rate']:.2f}" if pd.notna(row.get('inflation_rate')) else "N/A",
                   className="text-center"),
            html.Td(f"{row['unemployment_rate']:.2f}" if pd.notna(row.get('unemployment_rate')) else "N/A",
                   className="text-center"),
            html.Td(f"{row['anomaly_score']:.3f}" if pd.notna(row.get('anomaly_score')) else "N/A",
                   className="text-center text-danger fw-bold"),
        ]))
    
    table_body = html.Tbody(table_rows)
    
    table = html.Table(
        [table_header, table_body],
        className="table table-striped table-hover table-bordered"
    )
    
    return table