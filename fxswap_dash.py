import pandas as pd
from dash import Dash, dcc, html, Input, Output, ctx, Patch
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta

# ── 데이터 로드 ──────────────────────────────────────────────────────────────
STR_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRfNroFE_THBtcNXvqGmIjAznHFN7d7J_oaBaUWbuGwCnpifPfAcDWDZJcgRsJ13efcmQu1LcNeXCmq"
    "/pub?output=xlsx"
)

print("데이터 로딩 중... (Google Sheets 다운로드)")
data = pd.read_excel(STR_URL, sheet_name="Market_Data", index_col="DATE").sort_index()
print("데이터 로딩 완료.")

TENORS = ["ON", "1W", "1M", "3M", "6M", "1Y"]
FXSWR_COLS = [f"FXSWR_{t}" for t in TENORS]
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
POSITIONS = [(1, 1), (1, 2), (2, 1), (2, 2), (3, 1), (3, 2)]
YAXIS_KEYS = ["yaxis", "yaxis2", "yaxis3", "yaxis4", "yaxis5", "yaxis6"]

df = data[FXSWR_COLS].dropna(how="all").sort_index()

DATE_MIN = df.index.min().date()
DATE_MAX = df.index.max().date()
DEFAULT_START = max(DATE_MIN, DATE_MAX - timedelta(days=365))

PRESET_BUTTONS = [
    {"label": "1M",  "days": 30},
    {"label": "3M",  "days": 90},
    {"label": "6M",  "days": 180},
    {"label": "1Y",  "days": 365},
    {"label": "2Y",  "days": 730},
    {"label": "ALL", "days": None},
]


def get_yrange(series, x0, x1, pad=0.05):
    visible = series.loc[x0:x1].dropna()
    if len(visible) == 0:
        return None
    mn, mx = visible.min(), visible.max()
    margin = (mx - mn) * pad if mx != mn else (abs(mn) * pad if mn != 0 else 0.1)
    return [mn - margin, mx + margin]


def build_figure(dff):
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=TENORS,
        shared_xaxes=True,
        vertical_spacing=0.08,
        horizontal_spacing=0.08,
    )

    for col, (row, c), tenor, color in zip(FXSWR_COLS, POSITIONS, TENORS, COLORS):
        series = dff[col].dropna()
        fig.add_trace(
            go.Scatter(
                x=series.index, y=series.values,
                name=tenor, mode="lines",
                line=dict(color=color, width=1.5),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.4f}%<extra>" + tenor + "</extra>",
            ),
            row=row, col=c,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="rgba(150,150,150,0.5)", line_width=1, row=row, col=c)

    fig.update_layout(
        height=900,
        showlegend=False,
        hovermode="x unified",
        margin=dict(t=60, b=40, l=60, r=20),
        plot_bgcolor="#fafafa",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=3,  label="3M",  step="month", stepmode="backward"),
                    dict(count=6,  label="6M",  step="month", stepmode="backward"),
                    dict(count=1,  label="1Y",  step="year",  stepmode="backward"),
                    dict(count=2,  label="2Y",  step="year",  stepmode="backward"),
                    dict(step="all", label="ALL"),
                ]
            ),
            rangeslider=dict(visible=True, thickness=0.04),
            type="date",
        ),
    )
    fig.update_xaxes(matches="x", showgrid=True, gridcolor="#e0e0e0")
    fig.update_yaxes(ticksuffix="%", showgrid=True, gridcolor="#e0e0e0")
    return fig


# ── 앱 ───────────────────────────────────────────────────────────────────────
app = Dash(__name__, title="FX Swap Dashboard")

app.layout = html.Div(
    style={"fontFamily": "sans-serif", "maxWidth": "1400px", "margin": "0 auto", "padding": "20px"},
    children=[
        html.H2("FX Swap Rate (FXSWR) Dashboard", style={"marginBottom": "16px"}),
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "16px", "flexWrap": "wrap", "marginBottom": "16px"},
            children=[
                html.Div(
                    style={"display": "flex", "gap": "6px"},
                    children=[
                        html.Button(
                            btn["label"],
                            id=f"preset-{btn['label']}",
                            n_clicks=0,
                            style={"padding": "6px 12px", "cursor": "pointer",
                                   "border": "1px solid #aaa", "borderRadius": "4px", "background": "#f5f5f5"},
                        )
                        for btn in PRESET_BUTTONS
                    ],
                ),
                dcc.DatePickerRange(
                    id="date-range",
                    min_date_allowed=DATE_MIN,
                    max_date_allowed=DATE_MAX,
                    start_date=DEFAULT_START,
                    end_date=DATE_MAX,
                    display_format="YYYY-MM-DD",
                ),
            ],
        ),
        dcc.Graph(id="fxswr-chart", style={"height": "900px"}),
    ],
)


# ── 프리셋 버튼 → DatePickerRange ────────────────────────────────────────────
@app.callback(
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    [Input(f"preset-{btn['label']}", "n_clicks") for btn in PRESET_BUTTONS],
    prevent_initial_call=True,
)
def apply_preset(*_):
    if not ctx.triggered_id:
        return DEFAULT_START, DATE_MAX
    for btn in PRESET_BUTTONS:
        if ctx.triggered_id == f"preset-{btn['label']}":
            if btn["days"] is None:
                return DATE_MIN, DATE_MAX
            return max(DATE_MIN, DATE_MAX - timedelta(days=btn["days"])), DATE_MAX
    return DEFAULT_START, DATE_MAX


# ── 차트: 날짜 변경 시 전체 재빌드 / x축 zoom 시 y축만 업데이트 ──────────────
@app.callback(
    Output("fxswr-chart", "figure"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("fxswr-chart", "relayoutData"),
)
def update_chart(start_date, end_date, relayout_data):
    # 날짜 피커 변경 → 전체 재빌드
    if ctx.triggered_id != "fxswr-chart":
        dff = df.loc[start_date:end_date] if start_date and end_date else df
        return build_figure(dff)

    # zoom/pan 이벤트가 없으면 무시
    if not relayout_data:
        raise PreventUpdate

    # 더블클릭 리셋 → 전체 재빌드
    if relayout_data.get("xaxis.autorange") or relayout_data.get("autosize"):
        dff = df.loc[start_date:end_date] if start_date and end_date else df
        return build_figure(dff)

    # x 범위 변경 → y축 범위만 Patch로 업데이트
    if "xaxis.range[0]" not in relayout_data:
        raise PreventUpdate

    x0 = pd.Timestamp(relayout_data["xaxis.range[0]"])
    x1 = pd.Timestamp(relayout_data["xaxis.range[1]"])
    dff = df.loc[start_date:end_date] if start_date and end_date else df

    patch = Patch()
    for col, ykey in zip(FXSWR_COLS, YAXIS_KEYS):
        yr = get_yrange(dff[col], x0, x1)
        if yr:
            patch["layout"][ykey]["range"] = yr
            patch["layout"][ykey]["autorange"] = False

    return patch


if __name__ == "__main__":
    app.run(debug=True, port=8050)