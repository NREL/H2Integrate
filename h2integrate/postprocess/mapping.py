import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import numpy as np
import math

from pathlib import Path
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from shapely.geometry import LineString

from h2integrate.postprocess.sql_to_csv import convert_sql_to_csv_summary


def plot_geospatial_point_heat_map(
    case_results_fpath: Path | str,
    metric_to_plot: str,
    latitude_var_name: str | None = None,
    longitude_var_name: str | None = None,
    *,
    fig: plt.Figure | None = None,
    ax: plt.Axes | None = None,
    base_layer_gdf: gpd.GeoDataFrame | list[gpd.GeoDataFrame] | tuple[gpd.GeoDataFrame, ...] | None = None,
    show_plot: bool = True,
    save_plot_fpath: Path | str | None,
    map_preferences: dict | None = None,
    save_sql_file_to_csv: bool = False,
):
    """Plot a geospatial point heat map for a metric of interest (ie:  AEP, LCOE, LCOI, etc.)
    across multiple site locations (latitude, longitude) from data stored in a 
    single cases.sql recorder file (if ran in serial), set of cases.sql recorder files (if ran in parallel),
    or a .csv file.

    
    """
    # Default map preferences
    map_preferences_default = {
        'lat_long_crs': 'EPSG:4326',
        'web_map_crs': 'EPSG:3857',
        'figsize': (10, 8),
        'constrained_layout': True,
        'figure_title': 'UPDATE TITLE',
        'colormap': 'plasma_r',
        'alpha': 0.8,
        'marker': 's',
        'markersize':36,
        'edgecolor': 'black',
        'colorbar_label': 'UPDATE LABEL',
        'colorbar_label_font_size': 8,
        'colorbar_labelpad': 7.5,
        'colorbar_label_bbox_facecolor': 'white',
        'colorbar_label_bbox_alpha': 0.75,
        'colorbar_width': '20%',
        'colorbar_height': '2.5%',
        'colorbar_location': 'lower left',
        'colorbar_bbox_to_anchor': (0.75, 0.97, 1, 1),
        'colorbar_borderpad': 0,
        'colorbar_orientation': 'horizontal',
        'colorbar_tick_location': 'bottom',
        'colorbar_tick_direction': 'inout',
        'colorbar_tick_label_font_size': 8,
        'colorbar_tick_label_use_exp_notation': True,
        'colorbar_tick_label_exp_notation_decimal_limit': (-3, 3),
        'colorbar_tick_label_exp_notation_x_position': (1.125, np.nan),
        'colorbar_tick_label_exp_notation_y_pad': -24,
        'basemap_leftpad': 0.05,
        'basemap_rightpad': 0.05,
        'basemap_upperpad': 0.2125,
        'basemap_lowerpad': 0.05,
        'basemap_provider': ctx.providers.OpenStreetMap.DE,
        'basemap_zoom': 6,
    }

    # Dynamic colorbar offset
    # If the user has overwritten colorbar_width but has not adjusted the colorbar_tick_label_exp_notation_x_position
    # Then update dynamically as +2.5% relative to the colorbar width, normalized to the inset axis of the colorbar
    # Ex: colorbar_width = 20%, colorbar_tick_label_exp_notation_x_position = (22.5/20) = 1.125
    # NOTE: colorbar_tick_label_exp_notation_x_position is required to be a tuple of 2 values, the 2nd value is negligible
    if (
        map_preferences.get('colorbar_width') is not None
        and map_preferences.get('colorbar_tick_label_exp_notation_x_position') is None
    ):
        width = float(map_preferences['colorbar_width'][:-1])
        map_preferences['colorbar_tick_label_exp_notation_x_position'] = (
            (width + 2.5) / width,
            np.nan
        )

    # Merge the default map preferences with user defined map preference in case the user does not specify all required
    map_preferences = {**map_preferences_default, **(map_preferences or {})}

    # Load data
    # If case_results_fpath = str, convert to Path object
    if isinstance(case_results_fpath, str):
        case_results_fpath = Path(case_results_fpath)

    # If case_results_fpath is a .csv file read in with pandas
    if (".csv") in case_results_fpath.suffix:
        results_df = pd.read_csv(case_results_fpath)
    # Else if case_results_fpath is a path to the SQL recorder(s) (H2IntegrateModel.recorder_path) defined in the driver_config.yaml, read in with convert_sql_to_csv_summary()
    elif (".sql") in case_results_fpath.suffix:
        results_df = convert_sql_to_csv_summary(
            case_results_fpath, save_sql_file_to_csv
        )
    else:
        raise TypeError(
            f"The provided filepath {case_results_fpath} is of the wrong type, must be a .csv or the .sql file defined in the driver_config.yaml (H2IntegrateModel.recorder_path)")

    # Auto detect latitude and longitude column names if not provided as argument
    if latitude_var_name is None:
        latitude_var_name, _ = auto_detect_lat_long_columns(results_df)

    if longitude_var_name is None:
        _, longitude_var_name = auto_detect_lat_long_columns(results_df)

    # Create GeoDataFrame with results_df
    results_gdf = gpd.GeoDataFrame(
        results_df,
        geometry=gpd.points_from_xy(
            results_df[longitude_var_name],
            results_df[latitude_var_name],
            crs=map_preferences['lat_long_crs'],
        ),
        crs=map_preferences['lat_long_crs'],
    )

    # Convert coordinates to typical Web Mercator project CRS (EPSG:3857) for plotting
    results_gdf = results_gdf.to_crs(map_preferences['web_map_crs'])

    # Validate base_layer_gdf(s), if provided, is in the same CRS as the results_gdf
    if base_layer_gdf is not None:
        if isinstance(base_layer_gdf, (list, tuple)):
            for gdf in base_layer_gdf:
                if gdf.crs != results_gdf.crs:
                    raise ValueError(f"base_layer_gdf(s) CRS ({gdf.crs}) must match the new layers plotting CRS ({results_gdf.crs})")
        else: # single GeoDataFrame
            if base_layer_gdf.crs != results_gdf.crs:
                    raise ValueError(f"base_layer_gdf(s) CRS ({base_layer_gdf.crs}) must match the new layers plotting CRS ({results_gdf.crs})")
            base_layer_gdf = [base_layer_gdf]

    # Check if both fig and ax provided together (XOR condition)
    if (fig is None) ^ (ax is None):
        raise ValueError("The fig and ax arguments must be provided together to add a layer to an existing plot or both must be omitted/None to create a new plot")

    # Create plot figure and axis objects if none are provided = creating base map
    elif fig is None and ax is None:
        fig, ax = plt.subplots(
            1,
            figsize=map_preferences['figsize'],
            constrained_layout=map_preferences['constrained_layout'],
        )
    else:
        plt.figure(fig.number)
        plt.sca(ax)

    # Plot point heat map layer
    results_gdf.plot(
        ax=ax,
        column=metric_to_plot,
        cmap=map_preferences['colormap'],
        alpha=map_preferences['alpha'],
        marker=map_preferences['marker'],
        markersize=map_preferences['markersize'],
        edgecolor=map_preferences['edgecolor'],
        label=map_preferences['colorbar_label'],
        # zorder=1,
    )

    # Create inset axis for color bar legend 
    inset_ax = inset_axes(
        ax,
        width=map_preferences['colorbar_width'],
        height=map_preferences['colorbar_height'],
        loc=map_preferences['colorbar_location'],
        bbox_to_anchor=map_preferences['colorbar_bbox_to_anchor'],
        bbox_transform=ax.transAxes,
        borderpad=map_preferences['colorbar_borderpad'],
    )

    # Create scalar mappable object for color bar legend normalized between min and max value of metric_to_plot
    sm = plt.cm.ScalarMappable(
        cmap=map_preferences['colormap'],
        norm=plt.Normalize(
            vmin=math.floor(results_gdf[metric_to_plot].min() / 100) * 100,
            vmax=math.ceil(results_gdf[metric_to_plot].max() / 100) * 100,
        ),
    )

    # plot the color bar legend
    cbar = plt.colorbar(
        sm,
        cax=inset_ax,
        ticklocation=map_preferences['colorbar_tick_location'],
        orientation=map_preferences['colorbar_orientation'],
    )

    # set color bar legend label
    cbar.set_label(
        map_preferences['colorbar_label'],
        bbox=dict(
            facecolor=map_preferences['colorbar_label_bbox_facecolor'],
            alpha=map_preferences['colorbar_label_bbox_alpha'],
        ),
        size=map_preferences['colorbar_label_font_size'],
        labelpad=map_preferences['colorbar_labelpad'],
    )

    # format tick marks on colorbar
    inset_ax.tick_params(
        direction=map_preferences['colorbar_tick_direction'],
        labelsize=map_preferences['colorbar_tick_label_font_size'],
    )

    # format color bar legend offset text and position (scientific notation for values if applicable)
    # By default, this is set such that if the values of the colorbar legend are larger or smaller than 4 decimal places (0.0001-9999) then use exponential notation
    cbar.formatter.set_scientific(
        map_preferences['colorbar_tick_label_use_exp_notation']
    )
    cbar.formatter.set_powerlimits(
        map_preferences['colorbar_tick_label_exp_notation_decimal_limit']
    )

    offset_text = cbar.ax.xaxis.get_offset_text()
    offset_text.set_fontsize(map_preferences['colorbar_tick_label_font_size'])
    offset_text.set_position(
        map_preferences['colorbar_tick_label_exp_notation_x_position']
    )
    cbar.ax.xaxis.OFFSETTEXTPAD = map_preferences[
        'colorbar_tick_label_exp_notation_y_pad'
    ]

    # Calculate appropriate bounds for map based on coordinates of data used in plots
    gdfs_for_bounds = [results_gdf]
    if base_layer_gdf is not None:
        gdfs_for_bounds.extend(base_layer_gdf)

    coord_range_dict = calculate_geodataframe_total_bounds(*gdfs_for_bounds)

    left_pad = coord_range_dict['x_range'] * map_preferences['basemap_leftpad']
    right_pad = coord_range_dict['x_range'] * map_preferences['basemap_rightpad']
    upper_pad = coord_range_dict['y_range'] * map_preferences['basemap_upperpad']
    lower_pad = coord_range_dict['y_range'] * map_preferences['basemap_lowerpad']

    ax.set_xlim(coord_range_dict['min_x'] - left_pad, coord_range_dict['max_x'] + right_pad)
    ax.set_ylim(coord_range_dict['min_y'] - lower_pad, coord_range_dict['max_y'] + upper_pad)
    ax.set_axis_off()
    ax.set_title(map_preferences['figure_title'])

    # Plot basemap with contextily
    ctx.add_basemap(
        ax,
        crs=map_preferences['web_map_crs'],
        source=map_preferences['basemap_provider'],
        zoom=map_preferences['basemap_zoom'],
    )

    #NOTE: when plotting multiple layers, set this to True only when plotting the last layer
    if show_plot:
        plt.show()

    # Save figure if save_plot_fpath is present
    if save_plot_fpath is not None:
        if isinstance(save_plot_fpath, str):
            save_plot_fpath = Path(save_plot_fpath)
        fig.savefig(save_plot_fpath)
        

    return fig, ax, results_gdf

def plot_straight_line_shipping_routes(
        shipping_coords_fpath: Path | str,
        shipping_route: list[str],
        latitude_var_name: str | None = None,
        longitude_var_name: str | None = None,
        *,
        fig: plt.Figure | None = None,
        ax: plt.Axes | None = None,
        base_layer_gdf: gpd.GeoDataFrame | list[gpd.GeoDataFrame] | tuple[gpd.GeoDataFrame, ...] | None = None,
        show_plot: bool = True,
        save_plot_fpath: Path | str | None,
        map_preferences: dict | None = None,
):
    """
    Plot simple straight line shipping / transport routes.
    
    NOTE: this function will likely be altered as more shipping / transport functionality becomes available in H2I
    This was developed for ITO Iron Electrowinning proof of concept work"""

    # Default map preferences
    map_preferences_default = {
        'lat_long_crs': 'EPSG:4326',
        'web_map_crs': 'EPSG:3857',
        'figsize': (10, 8),
        'constrained_layout': True,
        'figure_title': 'UPDATE TITLE',
        'linestyle':'--',
        'linecolor':'black',
        'linewidth':1.5,
        'zorder':1,
        'basemap_leftpad': 0.05,
        'basemap_rightpad': 0.05,
        'basemap_upperpad': 0.2125,
        'basemap_lowerpad': 0.05,
        'basemap_provider': ctx.providers.OpenStreetMap.DE,
        'basemap_zoom': 6,
    }

    # Merge the default map preferences with user defined map preference in case the user does not specify all required
    map_preferences = {**map_preferences_default, **(map_preferences or {})}

    # Load data
    # If case_results_fpath = str, convert to Path object
    if isinstance(shipping_coords_fpath, str):
        shipping_coords_fpath = Path(shipping_coords_fpath)

    # If case_results_fpath is a .csv file read in with pandas
    if (".csv") in shipping_coords_fpath.suffix:
        shipping_coords_df = pd.read_csv(shipping_coords_fpath,index_col=0)

        # Auto detect latitude and longitude column names if not provided as argument
        if latitude_var_name is None:
            latitude_var_name, _ = auto_detect_lat_long_columns(shipping_coords_df)

        if longitude_var_name is None:
            _, longitude_var_name = auto_detect_lat_long_columns(shipping_coords_df)
        
        # Order columns so tuples created in dict below are (long,lat) ordered pairs
        shipping_coords_df = shipping_coords_df[[longitude_var_name,latitude_var_name]]
        shipping_coords_dict = {index: tuple(row.values()) for index, row in shipping_coords_df.to_dict(orient='index').items()}
    else:
        raise TypeError(
            f"The provided filepath {shipping_coords_fpath} is of the wrong type, must be a .csv")

    # Create list of coordinates to trace shipping route
    shipping_route_coords = []
    for city in shipping_route:
        shipping_route_coords.append(shipping_coords_dict[str(city)])
    
    # Create GeoDataFrame with shipping_route_coords
    shipping_route_gdf = gpd.GeoDataFrame(geometry=[LineString(shipping_route_coords)], crs=map_preferences['lat_long_crs'])

    # Convert coordinates to typical Web Mercator project CRS (EPSG:3857) for plotting
    shipping_route_gdf = shipping_route_gdf.to_crs(map_preferences['web_map_crs'])

    # Validate base_layer_gdf(s), if provided, is in the same CRS as the results_gdf
    if base_layer_gdf is not None:
        if isinstance(base_layer_gdf, (list, tuple)):
            for gdf in base_layer_gdf:
                if gdf.crs != shipping_route_gdf.crs:
                    raise ValueError(f"base_layer_gdf(s) CRS ({gdf.crs}) must match the new layers plotting CRS ({shipping_route_gdf.crs})")
        else: # single GeoDataFrame
            if base_layer_gdf.crs != shipping_route_gdf.crs:
                    raise ValueError(f"base_layer_gdf(s) CRS ({base_layer_gdf.crs}) must match the new layers plotting CRS ({shipping_route_gdf.crs})")
            base_layer_gdf = [base_layer_gdf]

    # Check if both fig and ax provided together (XOR condition)
    if (fig is None) ^ (ax is None):
        raise ValueError("The fig and ax arguments must be provided together to add a layer to an existing plot or both must be omitted/None to create a new plot")

    # Create plot figure and axis objects if none are provided = creating base map
    if fig is None and ax is None:
        fig, ax = plt.subplots(
            1,
            figsize=map_preferences['figsize'],
            constrained_layout=map_preferences['constrained_layout'],
        )
    else:
        plt.figure(fig.number)
        plt.sca(ax)

    # Plot straight line shipping layer
    shipping_route_gdf.plot(
        ax=ax,
        linestyle=map_preferences['linestyle'],
        color=map_preferences['linecolor'],
        linewidth=map_preferences['linewidth'],
        zorder=map_preferences['zorder']
    )    

    # Calculate appropriate bounds for map based on coordinates of data used in plots
    gdfs_for_bounds = [shipping_route_gdf]
    if base_layer_gdf is not None:
        gdfs_for_bounds.extend(base_layer_gdf)

    coord_range_dict = calculate_geodataframe_total_bounds(*gdfs_for_bounds)

    left_pad = coord_range_dict['x_range'] * map_preferences['basemap_leftpad']
    right_pad = coord_range_dict['x_range'] * map_preferences['basemap_rightpad']
    upper_pad = coord_range_dict['y_range'] * map_preferences['basemap_upperpad']
    lower_pad = coord_range_dict['y_range'] * map_preferences['basemap_lowerpad']


    ax.set_xlim(coord_range_dict['min_x'] - left_pad, coord_range_dict['max_x'] + right_pad)
    ax.set_ylim(coord_range_dict['min_y'] - lower_pad, coord_range_dict['max_y'] + upper_pad)
    ax.set_axis_off()
    ax.set_title(map_preferences['figure_title'])

    # Add basemap tiles with contextily
    ctx.add_basemap(
        ax,
        crs=map_preferences['web_map_crs'],
        source=map_preferences['basemap_provider'],
        zoom=map_preferences['basemap_zoom'],
    )

    #NOTE: when plotting multiple layers, set this to True only when plotting the last layer
    if show_plot:
        plt.show()

    # Save figure if save_plot_fpath is present
    if save_plot_fpath is not None:
        if isinstance(save_plot_fpath, str):
            save_plot_fpath = Path(save_plot_fpath)
        fig.savefig(save_plot_fpath)
        

    return fig, ax, shipping_route_gdf

def calculate_geodataframe_total_bounds(*gdfs: gpd.GeoDataFrame):
    """Calculate combined bounds for one or more GeoDataFrames."""

    # raise error if no gdf is provided as keyword argument
    if not gdfs:
        raise ValueError("Must provide at least one GeoDataFrame.")

    # Validate all gdfs are in the same CRS
    base_crs = gdfs[0].crs
    for gdf in gdfs:
        if gdf.crs != base_crs:
            raise ValueError("All GeoDataFrames must have the same CRS.")

    # Extract the min and max X (Longitude) and Y (Latitude) from the total bounds of all gdfs
    min_xs, min_ys, max_xs, max_ys = zip(
        *(gdf.total_bounds for gdf in gdfs)
    )

    min_x = min(min_xs)
    min_y = min(min_ys)
    max_x = max(max_xs)
    max_y = max(max_ys)
    x_range = (max_x - min_x) 
    y_range = (max_y - min_y)

    #Construct dictionary with relevant values
    coord_range_dict = {'min_x':min_x,
                        'min_y':min_y,
                        'max_x':max_x,
                        'max_y':max_y,
                        'x_range':x_range,
                        'y_range':y_range}

    return coord_range_dict

def auto_detect_lat_long_columns(results_df: pd.DataFrame):
    """
    Auto detect latitude and longitude column names in a pandas DataFrame
    """

    # regex expression provides case insensitive search of the keywords
    keywords = ['lat','latitude']
    regex = "(?i)" + "|".join(keywords)
    # return dataframe column names that match regex expression
    matching_columns = results_df.filter(regex=regex).columns
    # raise error if unable to detect a singular latitude column
    if len(matching_columns) == 0 or len(matching_columns) > 1:
        raise KeyError("Unable to automatically detect the latitude variable / column in the data. Please specify the exact variable / column name using the latitude_var_name argument")
    latitude_var_name = str(matching_columns[0])

    keywords = ['lon','long','longitude']
    regex = "(?i)" + "|".join(keywords)
    # return dataframe column names that match regex expression
    matching_columns = results_df.filter(regex=regex).columns
    # raise error if unable to detect a singular latitude column
    if len(matching_columns) == 0 or len(matching_columns) > 1:
        raise KeyError("Unable to automatically detect the longitude variable / column in the data. Please specify the exact variable / column name using the longitude_var_name argument")
    longitude_var_name = str(matching_columns[0])

    return latitude_var_name, longitude_var_name