from h2integrate.postprocess.mapping import (
    plot_geospatial_point_heat_map,
    plot_straight_line_shipping_routes,
)
from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create H2Integrate model
# NOTE:
# This example has already been run and the cases.csv and cases.sql file is saved in ./ex_26_out.
# You may comment out the following two lines to avoid long runtimes
model = H2IntegrateModel("iron_map.yaml")
model.run()

# Plot the LCOI results with geopandas and contextily
# NOTE: you can swap './ex_26_out/cases.sql' with './ex_26_out/cases.csv' to read results from csv
fig, ax, lcoi_layer_gdf = plot_geospatial_point_heat_map(
    case_results_fpath="./ex_26_out/cases.sql",
    metric_to_plot="iron.LCOI (USD/kg)",
    map_preferences={"figsize": (10, 8), "colorbar_label": "Levelized Cost of\nIron [$/tonne-Fe]"},
    save_sql_file_to_csv=True,
)

# Add a layer for example ore cost prices from select mines
fig, ax, ore_cost_layer_gdf = plot_geospatial_point_heat_map(
    case_results_fpath="./example_ore_prices.csv",
    metric_to_plot="ore_cost",
    map_preferences={
        "colormap": "Greens",
        "marker": "o",
        "colorbar_bbox_to_anchor": (0.025, 0.97, 1, 1),
        "colorbar_label": "Levelized Cost of\nIron Ore Pellets\n[$/tonne ore]",
    },
    fig=fig,
    ax=ax,
    base_layer_gdf=lcoi_layer_gdf,
)

# Add a layer for example waterway shipping cost from select mines to select ports
fig, ax, shipping_cost_layer_gdf = plot_geospatial_point_heat_map(
    case_results_fpath="./example_shipping_prices.csv",
    metric_to_plot="shipping_cost",
    map_preferences={
        "colormap": "Greys",
        "marker": "d",
        "markersize": 80,
        "colorbar_bbox_to_anchor": (0.4, 0.97, 1, 1),
        "colorbar_label": "Waterway Shipping Cost\n[$/tonne ore]",
    },
    fig=fig,
    ax=ax,
    base_layer_gdf=[lcoi_layer_gdf, ore_cost_layer_gdf],
)

# Define example water way shipping routes for plotting straight line transport
cleveland_route = [
    "Duluth",
    "Keweenaw",
    "Sault St Marie",
    "De Tour",
    "Lake Huron",
    "Port Huron",
    "Erie",
    "Cleveland",
]

buffalo_route = [
    "Duluth",
    "Keweenaw",
    "Sault St Marie",
    "De Tour",
    "Lake Huron",
    "Port Huron",
    "Erie",
    "Cleveland",
    "Buffalo",
]

chicago_route = [
    "Duluth",
    "Keweenaw",
    "Sault St Marie",
    "De Tour",
    "Mackinaw",
    "Manistique",
    "Chicago",
]

# Add cleveland route as layer
fig, ax, transport_layer1_gdf = plot_straight_line_shipping_routes(
    shipping_coords_fpath="./example_shipping_coords.csv",
    shipping_route=cleveland_route,
    map_preferences={},
    fig=fig,
    ax=ax,
    base_layer_gdf=[lcoi_layer_gdf, ore_cost_layer_gdf, shipping_cost_layer_gdf],
)

# Add buffalo route as layer
fig, ax, transport_layer2_gdf = plot_straight_line_shipping_routes(
    shipping_coords_fpath="./example_shipping_coords.csv",
    shipping_route=buffalo_route,
    map_preferences={},
    fig=fig,
    ax=ax,
    base_layer_gdf=[
        lcoi_layer_gdf,
        ore_cost_layer_gdf,
        shipping_cost_layer_gdf,
        transport_layer1_gdf,
    ],
)

# Add chicago route as layer
fig, ax, transport_layer3_gdf = plot_straight_line_shipping_routes(
    shipping_coords_fpath="./example_shipping_coords.csv",
    shipping_route=chicago_route,
    map_preferences={"figure_title": "Example H2 DRI Iron Costs"},
    fig=fig,
    ax=ax,
    base_layer_gdf=[
        lcoi_layer_gdf,
        ore_cost_layer_gdf,
        shipping_cost_layer_gdf,
        transport_layer1_gdf,
        transport_layer2_gdf,
    ],
    show_plot=True,
    save_plot_fpath="./ex_26_out/example_26_iron_map.png",
)
