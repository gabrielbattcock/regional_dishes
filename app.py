#!/usr/bin/env python3
"""
Regional Dishes Explorer — Plotly Dash App
==========================================
Run from the backend/ directory:

    pip install -r requirements.txt
    python app.py

Then open: http://127.0.0.1:8050
"""

import json
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, no_update

# ── Data Loading ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

with open(DATA_DIR / "recipes.json") as f:
    recipes: list[dict] = json.load(f)

with open(DATA_DIR / "regions.json") as f:
    regions: list[dict] = json.load(f)

with open(DATA_DIR / "clusters.json") as f:
    clusters_data: dict = json.load(f)

# Lookup helpers
recipe_by_id   = {r["id"]: r for r in recipes}
region_by_id   = {r["id"]: r for r in regions}
recipes_by_region: dict[str, list[dict]] = {}
for _r in recipes:
    recipes_by_region.setdefault(_r["region"], []).append(_r)

# ── Palette ───────────────────────────────────────────────────────────────────
CLUSTER_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
COUNTRY_COLORS = {"UK": "#4ECDC4", "Italy": "#FF6B6B", "USA": "#E8293F"}
COUNTRY_FLAGS  = {"UK": "🇬🇧", "Italy": "🇮🇹", "USA": "🇺🇸"}
BG_DARK  = "#0f0f1a"
BG_CARD  = "#16213e"
ACCENT   = "#4ECDC4"
MUTED    = "#8a8fa8"

# ── Map figure ────────────────────────────────────────────────────────────────

def build_map() -> go.Figure:
    """One scatter trace per region — clicking gives us the region id via customdata."""
    fig = go.Figure()

    for region in regions:
        color  = COUNTRY_COLORS.get(region["country"], "#888")
        lat, lon = region["coordinates"]
        dish_names = [
            recipe_by_id[rid]["name"]
            for rid in region.get("recipe_ids", [])
            if rid in recipe_by_id
        ]
        flag  = COUNTRY_FLAGS.get(region["country"], "")
        hover = (
            f"<b>{flag} {region['name']}</b><br>"
            f"<span style='color:{MUTED}'>{region['country']}</span><br>"
            f"{''.join(f'<br>• {d}' for d in dish_names)}"
        )

        fig.add_trace(go.Scattermap(
            lat=[lat], lon=[lon],
            mode="markers+text",
            marker=dict(size=16, color=color, opacity=0.92),
            text=[f"{flag} {region['name']}"],
            textfont=dict(color="white", size=11),
            textposition="top right",
            hovertemplate=hover + "<extra></extra>",
            customdata=[region["id"]],
            name=region["country"],
            showlegend=False,
        ))

    # Invisible legend entries per country
    for country, color in COUNTRY_COLORS.items():
        flag = COUNTRY_FLAGS.get(country, "")
        fig.add_trace(go.Scattermap(
            lat=[None], lon=[None],
            mode="markers",
            marker=dict(size=10, color=color),
            name=f"{flag}  {country}",
            showlegend=True,
        ))

    fig.update_layout(
        map=dict(
            style="carto-darkmatter",
            center=dict(lat=40.0, lon=-30.0),
            zoom=2,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            x=0.02, y=0.03,
            bgcolor="rgba(22,33,62,0.85)",
            bordercolor="rgba(255,255,255,0.15)",
            borderwidth=1,
            font=dict(color="white", size=12),
        ),
        uirevision="constant",  # preserves zoom/pan on callbacks
    )
    return fig


# ── Connections network figure ────────────────────────────────────────────────

def build_connections() -> go.Figure:
    dishes      = clusters_data["dishes"]
    connections = clusters_data["connections"]
    dish_pos    = {d["id"]: d for d in dishes}
    cluster_meta = {c["id"]: c for c in clusters_data["clusters"]}

    fig = go.Figure()

    # ── Edges
    for conn in connections:
        s = dish_pos.get(conn["source"])
        t = dish_pos.get(conn["target"])
        if not s or not t:
            continue
        alpha = 0.10 + conn["similarity"] * 0.65
        width = 0.5 + conn["similarity"] * 2.5
        fig.add_trace(go.Scatter(
            x=[s["tsne_x"], t["tsne_x"], None],
            y=[s["tsne_y"], t["tsne_y"], None],
            mode="lines",
            line=dict(width=width, color=f"rgba(180,190,220,{alpha:.2f})"),
            hoverinfo="none",
            showlegend=False,
        ))

    # ── Nodes grouped by cluster
    by_cluster: dict[int, list[dict]] = {}
    for dish in dishes:
        by_cluster.setdefault(dish["cluster"], []).append(dish)

    for cid, members in sorted(by_cluster.items()):
        color = CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]
        label = cluster_meta.get(cid, {}).get("label", f"Cluster {cid}")
        fig.add_trace(go.Scatter(
            x=[d["tsne_x"] for d in members],
            y=[d["tsne_y"] for d in members],
            mode="markers+text",
            marker=dict(
                size=22, color=color,
                line=dict(width=1.5, color="rgba(255,255,255,0.4)"),
                opacity=0.92,
            ),
            text=[d["name"] for d in members],
            textposition="top center",
            textfont=dict(size=9, color="rgba(255,255,255,0.8)"),
            customdata=[d["id"] for d in members],
            hovertemplate=(
                "<b>%{text}</b><br>"
                + "<br>".join(
                    f"{d['country']} · {d['region'].title()}<br>"
                    f"<span style='color:{MUTED}'>{d['cooking_method']}</span>"
                    for d in members[:1]
                )
                + "<extra></extra>"
            ),
            name=label,
        ))

    fig.update_layout(
        paper_bgcolor=BG_DARK,
        plot_bgcolor=BG_DARK,
        font=dict(color="white"),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showline=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showline=False),
        margin=dict(l=20, r=20, t=50, b=20),
        title=dict(
            text="Dish Connections — grouped by shared ingredients & cooking method",
            font=dict(size=13, color=MUTED),
            x=0.5,
        ),
        legend=dict(
            bgcolor="rgba(22,33,62,0.85)",
            bordercolor="rgba(255,255,255,0.15)",
            borderwidth=1,
            font=dict(size=11),
            itemclick=False,
        ),
        hovermode="closest",
        uirevision="constant",
    )
    return fig


# ── Recipe offcanvas content ──────────────────────────────────────────────────

def recipe_offcanvas_content(recipe: dict) -> html.Div:

    meta = []
    if recipe.get("prep_time_mins"):
        meta.append(dbc.Badge(f"Prep {recipe['prep_time_mins']} min", color="secondary", className="me-1 mb-1"))
    if recipe.get("cook_time_mins"):
        meta.append(dbc.Badge(f"Cook {recipe['cook_time_mins']} min", color="secondary", className="me-1 mb-1"))
    if recipe.get("serves"):
        meta.append(dbc.Badge(f"Serves {recipe['serves']}", color="secondary", className="me-1 mb-1"))

    def section(emoji, title, content):
        return html.Details([
            html.Summary(
                f"{emoji}  {title}",
                style={"cursor": "pointer", "fontWeight": "600",
                       "color": "#FFEAA7", "padding": "6px 0", "fontSize": "0.93rem"},
            ),
            html.Div(content, style={"paddingTop": "8px"}),
        ], open=True, style={"marginBottom": "14px",
                              "borderBottom": "1px solid rgba(255,255,255,0.06)",
                              "paddingBottom": "6px"})

    ingredients_ul = html.Ul([
        html.Li(
            " ".join(filter(None, [
                str(ing.get("amount") or ""),
                str(ing.get("unit") or ""),
                ing["item"],
            ])).strip(),
            style={"marginBottom": "5px", "fontSize": "0.87rem", "color": "#ccc"}
        )
        for ing in recipe.get("ingredients", [])
    ], style={"paddingLeft": "18px", "margin": "0"})

    steps_ol = html.Ol([
        html.Li(
            step["instruction"],
            style={"marginBottom": "9px", "fontSize": "0.87rem",
                   "color": "#ddd", "lineHeight": "1.55"}
        )
        for step in recipe.get("steps", [])
    ], style={"paddingLeft": "18px", "margin": "0"})

    return html.Div([
        # Title
        html.H4(recipe["name"],
                style={"color": ACCENT, "fontWeight": "700", "marginBottom": "3px"}),
        html.P(f"{recipe['region'].title()} · {recipe['country']}",
               style={"color": MUTED, "fontSize": "0.83rem", "marginBottom": "8px"}),
        # Short description
        html.P(recipe.get("short_description", ""),
               style={"color": "#ccc", "fontStyle": "italic",
                      "fontSize": "0.9rem", "lineHeight": "1.5", "marginBottom": "10px"}),
        # Meta badges
        html.Div(meta, style={"marginBottom": "14px"}),
        # Sections
        section("📜", "History",
                html.P(recipe.get("history", ""),
                       style={"fontSize": "0.87rem", "color": "#ccc", "lineHeight": "1.65", "margin": "0"})),
        section("🧅", "Ingredients", ingredients_ul),
        section("👨‍🍳", "Method", steps_ol),
    ], style={"padding": "4px 0"})


def region_picker_content(region: dict) -> html.Div:
    """Show buttons for each dish in a region when multiple recipes exist."""
    dishes = [recipe_by_id[rid] for rid in region.get("recipe_ids", []) if rid in recipe_by_id]
    return html.Div([
        html.H5(region["name"],
                style={"color": ACCENT, "fontWeight": "700", "marginBottom": "4px"}),
        html.P(f"{region['country']} · {len(dishes)} traditional dish{'es' if len(dishes) != 1 else ''}",
               style={"color": MUTED, "fontSize": "0.85rem", "marginBottom": "16px"}),
        html.P("Choose a dish to explore:", style={"color": "#ccc", "fontSize": "0.88rem", "marginBottom": "10px"}),
        *[dbc.Button(
            [html.Span("🍽  "), dish["name"]],
            id={"type": "dish-btn", "index": dish["id"]},
            color="outline-light",
            className="mb-2 w-100 text-start",
            style={"borderColor": "rgba(255,255,255,0.2)", "fontSize": "0.9rem"},
        ) for dish in dishes],
    ])


# ── Welcome panel (map sidebar) ───────────────────────────────────────────────

def welcome_hint() -> html.Div:
    uk_count    = sum(1 for r in recipes if r["country"] == "UK")
    italy_count = sum(1 for r in recipes if r["country"] == "Italy")
    usa_count   = sum(1 for r in recipes if r["country"] == "USA")
    return html.Div([
        html.Div("🗺️", style={"fontSize": "2.8rem", "textAlign": "center", "marginBottom": "14px"}),
        html.H5("Explore Regional Dishes",
                style={"color": ACCENT, "textAlign": "center", "fontWeight": "700", "marginBottom": "6px"}),
        html.P("Click any pin on the map to discover traditional dishes from that region.",
               style={"color": MUTED, "textAlign": "center", "fontSize": "0.88rem",
                      "lineHeight": "1.6", "marginBottom": "20px"}),
        html.Hr(style={"borderColor": "rgba(255,255,255,0.08)"}),
        dbc.Row([
            dbc.Col(html.Div([
                html.Div("🇬🇧", style={"fontSize": "1.8rem", "textAlign": "center"}),
                html.P("United Kingdom", style={"textAlign": "center", "color": "#4ECDC4",
                                                "fontSize": "0.85rem", "margin": "4px 0 2px"}),
                html.P(f"{uk_count} dishes", style={"textAlign": "center", "color": MUTED, "fontSize": "0.8rem"}),
            ])),
            dbc.Col(html.Div([
                html.Div("🇮🇹", style={"fontSize": "1.8rem", "textAlign": "center"}),
                html.P("Italy", style={"textAlign": "center", "color": "#FF6B6B",
                                       "fontSize": "0.85rem", "margin": "4px 0 2px"}),
                html.P(f"{italy_count} dishes", style={"textAlign": "center", "color": MUTED, "fontSize": "0.8rem"}),
            ])),
            dbc.Col(html.Div([
                html.Div("🇺🇸", style={"fontSize": "1.8rem", "textAlign": "center"}),
                html.P("USA", style={"textAlign": "center", "color": "#E8293F",
                                     "fontSize": "0.85rem", "margin": "4px 0 2px"}),
                html.P(f"{usa_count} dishes", style={"textAlign": "center", "color": MUTED, "fontSize": "0.8rem"}),
            ])),
        ]),
        html.Hr(style={"borderColor": "rgba(255,255,255,0.08)"}),
        html.P("💡 Switch to the Connections tab to see how dishes across countries share ingredients and cooking techniques.",
               style={"color": MUTED, "fontSize": "0.82rem", "textAlign": "center",
                      "lineHeight": "1.55", "marginTop": "12px"}),
    ], style={"padding": "24px 16px"})


# ── App & Layout ──────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Regional Dishes Explorer",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

SIDEBAR_STYLE = {
    "height": "calc(100vh - 108px)",
    "overflowY": "auto",
    "backgroundColor": BG_CARD,
    "borderLeft": "1px solid rgba(255,255,255,0.07)",
}

OFFCANVAS_STYLE = {
    "backgroundColor": BG_CARD,
    "borderLeft": "1px solid rgba(255,255,255,0.1)",
    "color": "white",
    "width": "430px",
}

_map_fig  = build_map()
_conn_fig = build_connections()

app.layout = html.Div([
    # ── Header ────────────────────────────────────────────────────────────────
    html.Div([
        dbc.Row([
            dbc.Col([
                html.H3("🍽️  Regional Dishes Explorer",
                        style={"color": "white", "margin": "0", "fontWeight": "700",
                               "letterSpacing": "0.4px", "fontSize": "1.25rem"}),
                html.P("Traditional recipes from the UK, Italy & USA",
                       style={"color": MUTED, "margin": "0", "fontSize": "0.8rem"}),
            ], width="auto"),
        ], align="center"),
    ], style={"padding": "12px 20px", "backgroundColor": BG_DARK,
              "borderBottom": "1px solid rgba(255,255,255,0.08)"}),

    # ── Tabs ──────────────────────────────────────────────────────────────────
    dbc.Tabs([
        dbc.Tab(label="🗺️   Map",         tab_id="tab-map",
                label_style={"color": MUTED, "padding": "10px 20px"},
                active_label_style={"color": "white", "fontWeight": "600"}),
        dbc.Tab(label="🔗   Connections", tab_id="tab-connections",
                label_style={"color": MUTED, "padding": "10px 20px"},
                active_label_style={"color": "white", "fontWeight": "600"}),
    ], id="tabs", active_tab="tab-map",
       style={"backgroundColor": BG_DARK, "borderBottom": "1px solid rgba(255,255,255,0.08)"}),

    # ── Tab content ───────────────────────────────────────────────────────────
    html.Div(id="tab-content"),

    # ── Offcanvas for recipe detail ────────────────────────────────────────────
    dbc.Offcanvas(
        id="recipe-offcanvas",
        title="",
        is_open=False,
        placement="end",
        style=OFFCANVAS_STYLE,
        children=[html.Div(id="offcanvas-body")],
        backdrop=False,
        scrollable=True,
    ),

    # ── Stores ────────────────────────────────────────────────────────────────
    dcc.Store(id="selected-region"),
    dcc.Store(id="selected-recipe"),

], style={"backgroundColor": BG_DARK, "minHeight": "100vh"})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
)
def render_tab(active_tab: str):
    if active_tab == "tab-map":
        return dbc.Row([
            dbc.Col([
                dcc.Graph(
                    id="world-map",
                    figure=_map_fig,
                    style={"height": "calc(100vh - 108px)"},
                    config={"scrollZoom": True, "displayModeBar": False},
                ),
            ], width=8, style={"padding": "0"}),
            dbc.Col([
                html.Div(id="map-panel", children=welcome_hint(), style=SIDEBAR_STYLE),
            ], width=4, style={"padding": "0"}),
        ], style={"margin": "0"})

    elif active_tab == "tab-connections":
        cluster_legend = []
        for c in clusters_data["clusters"]:
            color = CLUSTER_COLORS[c["id"] % len(CLUSTER_COLORS)]
            names = [recipe_by_id[did]["name"] for did in c["dish_ids"] if did in recipe_by_id]
            cluster_legend.append(html.Div([
                html.Div([
                    html.Span("●", style={"color": color, "fontSize": "1.1rem", "marginRight": "7px"}),
                    html.Span(c["label"], style={"fontWeight": "600", "fontSize": "0.88rem"}),
                ], style={"marginBottom": "4px"}),
                html.P(", ".join(names),
                       style={"color": MUTED, "fontSize": "0.77rem", "marginLeft": "18px",
                              "lineHeight": "1.45", "marginBottom": "0"}),
            ], style={"marginBottom": "14px"}))

        return dbc.Row([
            dbc.Col([
                dcc.Graph(
                    id="connections-graph",
                    figure=_conn_fig,
                    style={"height": "calc(100vh - 108px)"},
                    config={"displayModeBar": False},
                ),
            ], width=9, style={"padding": "0"}),
            dbc.Col([
                html.Div([
                    html.H6("Clusters", style={"color": ACCENT, "fontWeight": "700", "marginBottom": "14px"}),
                    *cluster_legend,
                    html.Hr(style={"borderColor": "rgba(255,255,255,0.08)"}),
                    html.P(
                        "Edge thickness represents similarity strength. "
                        "Dishes with thick edges share core ingredients or cooking technique.",
                        style={"color": MUTED, "fontSize": "0.82rem", "lineHeight": "1.5"},
                    ),
                    html.Hr(style={"borderColor": "rgba(255,255,255,0.08)"}),
                    html.P("Click any dish node to open its full recipe →",
                           style={"color": MUTED, "fontSize": "0.82rem", "lineHeight": "1.5"}),
                ], style=SIDEBAR_STYLE | {"padding": "20px"}),
            ], width=3, style={"padding": "0"}),
        ], style={"margin": "0"})

    return html.Div()


@callback(
    Output("map-panel",       "children"),
    Output("selected-region", "data"),
    Input("world-map",        "clickData"),
    prevent_initial_call=True,
)
def handle_map_click(click_data):
    if not click_data:
        return no_update, no_update
    region_id = click_data["points"][0].get("customdata")
    if not region_id or region_id not in region_by_id:
        return no_update, no_update
    region = region_by_id[region_id]
    dishes = [recipe_by_id[rid] for rid in region.get("recipe_ids", []) if rid in recipe_by_id]

    if len(dishes) == 1:
        # Single dish — go straight to recipe view
        panel = html.Div([
            dbc.Button("← Back to regions", id="back-btn", color="link",
                       style={"color": MUTED, "padding": "0 0 12px", "fontSize": "0.82rem"}),
            recipe_offcanvas_content(dishes[0]),
        ], style={"padding": "16px"})
    else:
        panel = html.Div(region_picker_content(region), style={"padding": "16px"})

    return panel, region_id


@callback(
    Output("map-panel",       "children", allow_duplicate=True),
    Input({"type": "dish-btn", "index": dash.ALL}, "n_clicks"),
    State("selected-region",  "data"),
    prevent_initial_call=True,
)
def show_dish_from_region(n_clicks_list, region_id):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return no_update
    # Which button was clicked?
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    import json as _json
    dish_id = _json.loads(triggered_id)["index"]
    if dish_id not in recipe_by_id:
        return no_update
    recipe = recipe_by_id[dish_id]
    region = region_by_id.get(region_id, {})
    panel = html.Div([
        dbc.Button(
            f"← Back to {region.get('name', 'region')}",
            id="back-btn",
            color="link",
            style={"color": MUTED, "padding": "0 0 12px", "fontSize": "0.82rem"},
        ),
        recipe_offcanvas_content(recipe),
    ], style={"padding": "16px"})
    return panel


@callback(
    Output("map-panel", "children", allow_duplicate=True),
    Input("back-btn", "n_clicks"),
    State("selected-region", "data"),
    prevent_initial_call=True,
)
def go_back_to_region(n_clicks, region_id):
    if not n_clicks or not region_id or region_id not in region_by_id:
        return no_update
    region = region_by_id[region_id]
    return html.Div(region_picker_content(region), style={"padding": "16px"})


@callback(
    Output("recipe-offcanvas", "is_open"),
    Output("offcanvas-body",   "children"),
    Input("connections-graph", "clickData"),
    State("recipe-offcanvas",  "is_open"),
    prevent_initial_call=True,
)
def open_offcanvas_from_network(click_data, is_open):
    if not click_data:
        return no_update, no_update
    dish_id = click_data["points"][0].get("customdata")
    if not dish_id or dish_id not in recipe_by_id:
        return no_update, no_update
    return True, recipe_offcanvas_content(recipe_by_id[dish_id])


if __name__ == "__main__":
    app.run(debug=True, port=8050)
