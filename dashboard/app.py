# dashboard/app.py
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from database.db_handler import db
from ta_engine.indicators import TAEngine
from backtest.engine import BacktestEngine

# Initialize the App with the professional DARKLY theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "APEX // QUANT TERMINAL"

# --- Reusable UI Elements ---
def make_metric_card(title, value, text_color="white"):
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="card-title text-muted mb-1", style={"fontSize": "12px", "fontWeight": "bold", "letterSpacing": "1px"}),
            html.H4(value, style={"color": text_color, "fontWeight": "bold", "marginBottom": "0"})
        ]),
        className="mb-3", style={"backgroundColor": "#222", "border": "1px solid #333"}
    )

# --- Top Navigation & Tabs ---
navbar = dbc.NavbarSimple(
    brand="APEX QUANTITATIVE TERMINAL",
    brand_style={"fontWeight": "bold", "letterSpacing": "2px"},
    color="#111", dark=True, className="mb-4", style={"borderBottom": "2px solid #00bc8c"}
)

tabs = dbc.Tabs([
    dbc.Tab(label="LIVE MARKET", tab_id="tab-overview"),
    dbc.Tab(label="BACKTEST ANALYTICS", tab_id="tab-backtest"),
    dbc.Tab(label="SYSTEM PARAMS", tab_id="tab-logic"),
    dbc.Tab(label="EXECUTION HUB", tab_id="tab-execution"),
], id="tabs", active_tab="tab-overview", className="mb-4")

# --- Main Layout ---
app.layout = dbc.Container([
    navbar,
    tabs,
    html.Div(id="tab-content")
], fluid=True, style={"backgroundColor": "#111", "minHeight": "100vh", "paddingBottom": "50px"})

# --- Callbacks ---

@app.callback(Output("tab-content", "children"), [Input("tabs", "active_tab")])
def render_tab_content(active_tab):
    if active_tab == "tab-overview":
        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    id='live-symbol-dropdown',
                    options=[{'label': s, 'value': s} for s in config.SYMBOLS],
                    value=config.SYMBOLS[0],
                    style={"color": "#000"} 
                ), width=3)
            ], className="mb-3"),
            dcc.Loading(dcc.Graph(id='live-candlestick-chart', style={'height': '70vh'}), type="dot"),
            dcc.Interval(id='interval-component', interval=15 * 1000, n_intervals=0)
        ])
        
    elif active_tab == "tab-backtest":
        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    options=[{'label': s, 'value': s} for s in config.SYMBOLS], 
                    value=config.SYMBOLS[0], id='bt-symbol', style={"color": "#000"}
                ), width=3),
                dbc.Col(dbc.Button("RUN BACKTEST", id="btn-run-bt", color="success", className="fw-bold"), width=2),
            ], className="mb-4"),
            dcc.Loading(html.Div(id="bt-results-container"), type="dot", color="#00bc8c")
        ])

    elif active_tab == "tab-logic":
        return dbc.Card(dbc.CardBody([
            html.H4("Current Strategy Parameters", className="text-info"),
            html.Hr(style={"borderColor": "#444"}),
            html.P(f"Risk Per Trade: {config.RISK_PER_TRADE_PCT * 100}%"),
            html.P(f"Risk/Reward Ratio: 1 : {config.DEFAULT_RR_RATIO}"),
            html.P(f"Minimum Confluence Score: {config.MIN_CONFIDENCE_SCORE}/100"),
            html.P(f"Max Trades Per Day: {config.MAX_TRADES_PER_DAY}"),
        ]), style={"backgroundColor": "#222", "border": "1px solid #333", "maxWidth": "600px"})

    elif active_tab == "tab-execution":
        # Default to "PAPER" if TRADING_MODE isn't set in config yet
        current_mode = getattr(config, 'TRADING_MODE', 'PAPER')
        return dbc.Card(dbc.CardBody([
            html.H4("Execution Engine & Credentials", className="text-warning mb-3"),
            html.P("Switching to LIVE mode will allow the terminal to execute real trades via the CCXT engine using your Delta API keys. Ensure risk parameters are double-checked.", className="text-muted"),
            html.Hr(style={"borderColor": "#444"}),
            
            html.H5("Trading Mode", className="text-info mt-3"),
            dbc.RadioItems(
                options=[
                    {"label": "🟢 PAPER TRADING (Simulated Execution)", "value": "PAPER"},
                    {"label": "🔴 LIVE TRADING (Real Capital Risk)", "value": "LIVE"},
                ],
                value=current_mode,
                id="trading-mode-toggle",
                className="mb-4"
            ),
            
            html.H5("Delta Exchange API Credentials", className="text-info"),
            dbc.Input(id="api-key-input", type="password", placeholder="Enter Delta API Key", value=getattr(config, 'DELTA_API_KEY', ''), className="mb-2", style={"backgroundColor": "#111", "color": "white", "borderColor": "#333", "fontFamily": "monospace"}),
            dbc.Input(id="api-secret-input", type="password", placeholder="Enter Delta API Secret", value=getattr(config, 'DELTA_API_SECRET', ''), className="mb-3", style={"backgroundColor": "#111", "color": "white", "borderColor": "#333", "fontFamily": "monospace"}),
            
            dbc.Button("SAVE & AUTHENTICATE", id="btn-save-api", color="warning", className="fw-bold mt-2"),
            html.Div(id="api-save-status", className="mt-3 fw-bold")
        ]), style={"backgroundColor": "#222", "border": "1px solid #333", "maxWidth": "700px"})


@app.callback(
    Output('live-candlestick-chart', 'figure'),
    [Input('interval-component', 'n_intervals'), Input('live-symbol-dropdown', 'value')]
)
def update_live_chart(n, symbol):
    df = db.get_historical_data(symbol, timeframe='15m', limit=150)
    if df.empty: return go.Figure()

    df = TAEngine.apply_all(df)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price')])
    
    if 'ema_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='yellow', width=1), name='EMA 20'))
    if 'ema_50' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], line=dict(color='blue', width=1), name='EMA 50'))
    
    fig.update_layout(template="plotly_dark", title=f"{symbol} Live Action", margin=dict(l=40, r=40, t=40, b=40), xaxis_rangeslider_visible=False, paper_bgcolor="#111", plot_bgcolor="#111")
    return fig


@app.callback(
    Output("bt-results-container", "children"),
    [Input("btn-run-bt", "n_clicks")],
    [State("bt-symbol", "value")],
    prevent_initial_call=True
)
def run_historical_backtest(n_clicks, symbol):
    engine = BacktestEngine(initial_capital=config.PAPER_TRADING_BALANCE, risk_pct=config.RISK_PER_TRADE_PCT)
    res = engine.run(symbol, timeframe='15m')

    if "error" in res: return html.Div(res["error"], className="text-danger mt-3")

    is_prof = res['net_profit'] > 0
    pnl_color = "#00bc8c" if is_prof else "#E74C3C"

    highlights = dbc.Row([
        dbc.Col(make_metric_card("NET PROFIT", f"${res['net_profit']}", pnl_color), width=3),
        dbc.Col(make_metric_card("WIN RATE", f"{res['win_rate']}%", "#3498DB"), width=3),
        dbc.Col(make_metric_card("TOTAL TRADES", res['total_trades']), width=3),
        dbc.Col(make_metric_card("MAX DRAWDOWN", f"{res['max_drawdown']}%", "#E74C3C"), width=3),
    ])

    context_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Data Period", className="text-info mb-3"),
            html.P(f"Start: {res['start_date']}"),
            html.P(f"End: {res['end_date']}"),
            html.P(f"Duration: {res['total_days']} Days"),
            html.P(f"Frequency: {res['trades_per_day']} Trades / Day"),
        ]), style={"backgroundColor": "#222", "border": "1px solid #333", "height": "100%"}), width=4),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Trade Averages", className="text-info mb-3"),
            html.P(["Avg Winning Trade: ", html.Span(f"+${res['avg_win']}", style={"color": "#00bc8c"})]),
            html.P(["Avg Losing Trade: ", html.Span(f"-${res['avg_loss']}", style={"color": "#E74C3C"})]),
            html.P(f"Profit Factor: {res['profit_factor']}"),
        ]), style={"backgroundColor": "#222", "border": "1px solid #333", "height": "100%"}), width=4),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Recent Trade Log", className="text-info mb-3"),
            dash_table.DataTable(
                data=res['recent_trades'],
                style_header={'backgroundColor': '#333', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'backgroundColor': '#222', 'color': 'white', 'textAlign': 'left', 'border': '1px solid #444', 'fontSize': '12px'},
                style_as_list_view=True,
                page_size=5
            )
        ]), style={"backgroundColor": "#222", "border": "1px solid #333", "height": "100%"}), width=4),
    ], className="mb-4")

    equity_fig = go.Figure()
    equity_fig.add_trace(go.Scatter(y=res['equity_curve'], mode='lines', line=dict(color=pnl_color, width=2), fill='tozeroy', fillcolor='rgba(0, 188, 140, 0.1)' if is_prof else 'rgba(231, 76, 60, 0.1)'))
    equity_fig.update_layout(template="plotly_dark", title=f"Account Equity ({res['start_date']} to {res['end_date']})", paper_bgcolor="#222", plot_bgcolor="#222", margin=dict(l=40, r=40, t=40, b=40))

    return html.Div([highlights, context_row, dcc.Graph(figure=equity_fig)])


@app.callback(
    Output("api-save-status", "children"),
    Output("api-save-status", "className"),
    [Input("btn-save-api", "n_clicks")],
    [State("trading-mode-toggle", "value"),
     State("api-key-input", "value"),
     State("api-secret-input", "value")],
    prevent_initial_call=True
)
def save_execution_settings(n_clicks, mode, api_key, api_secret):
    if mode == "LIVE" and (not api_key or not api_secret):
        return "❌ ERROR: API Key and Secret are required for LIVE trading.", "mt-3 text-danger"
    
    # Update global config state
    config.TRADING_MODE = mode
    config.DELTA_API_KEY = api_key
    config.DELTA_API_SECRET = api_secret
    
    msg = f"✅ SUCCESS: Mode set to {mode}."
    if mode == "LIVE":
        msg += " Credentials loaded into active memory. (Reminder: Add to .env for deployment)."
        
    return msg, "mt-3 text-success"

if __name__ == "__main__":
    app.run(debug=True, port=8050)