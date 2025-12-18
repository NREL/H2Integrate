import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from xyzservices import TileProvider
import numpy as np
import math

from attrs import field, define

from pathlib import Path
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from shapely.geometry import LineString

from h2integrate.core.utilities import BaseConfig
from h2integrate.postprocess.sql_to_csv import convert_sql_to_csv_summary
from h2integrate.core.utilities import find_file

@define
class GeospatialMapConfig(BaseConfig):
    """
    Configuration class for plot_geospatial_point_heat_map() Arg: map_preferences.
    Represents necessary paramaters for formatting and plotting a geospatial point heat map with GeoPandas, matplotlib, and contextily

    Args:
        lat_long_crs (str, optional): A string representing the CRS of the (longitude,latitude) data used to plot points. Defaults to 'EPSG:4326'.
        web_map_crs (str, optional): A string representing the Web Mercator projection CRS used to convert the (longitude,latitude) data for plotting. Defaults to 'EPSG:3857'.
        figsize (tuple, optional): A tuple of floats used to set the matplotlib.pyplot.subplots() figsize parameter. Defaults to (10.0,8.0).
        constrained_layout (bool, optional): A boolean used to set the matplotlib.pyplot.subplots() constrained_layout parameter. Defaults to True.
        figure_title (str, optional): A string used to set the matplotlib.pyplot figure title. Defaults to 'UPDATE TITLE'.
        colormap (str, optional): A string used to set the gpd.GeoDataFrame.plot() cmap parameter. Defaults to 'plasma_r'.
        alpha (float, optional): A float used to set the gpd.GeoDataFrame.plot() alpha parameter. Defaults to 0.8.
        marker (str, optional): A string used to set the gpd.GeoDataFrame.plot() marker parameter. Defaults to 's' == 'square'.
        markersize (float, optional): A float used to set the gpd.GeoDataFrame.plot() markersize parameter. Defaults to 36.0.
        edgecolor (str, optional): A string used to set the gpd.GeoDataFrame.plot() edgecolor parameter. Defaults to 'black'.
        colorbar_label (str, optional): A string used to set the colorbar label text. Defaults to 'UPDATE LABEL'.
        colorbar_label_font_size (float, optional): A float used to set the colorbar label font size. Defaults to 8.0.
        colorbar_labelpad (float, optional): A float used to set the pad / spacing between the colorbar and the label text. Defaults to 7.5.
        colorbar_label_bbox_facecolor (str, optional): A string used to set the color of the bounding box which holds the colorbar label text. Defaults to 'white'.
        colorbar_label_bbox_alpha (float, optional): A float used to set the opacity / transparency of the colorbar label bounding box. Defaults to 0.75.
        colorbar_width (str, optional): A string used to set the width of the colorbar as a percentage of the figure width. Defaults to '20%'.
        colorbar_height (str, optional): A string used to set the height of the colorbar as a percentage of the figure height. Defaults to '2.5%'.
        colorbar_location (str, optional): A string used to set the location of the colorbar in conjunction with the colorbar_bbox_to_anchor. See mpl_toolkits.axes_grid1.inset_locator.inset_axes() documentation for additional details. Defaults to 'lower_left'
        colorbar_bbox_to_anchor (tuple, optional): A tuple of floats used to set the location of the bounding box to anchor the colorbar. Defaults to (0.75, 0.97, 1.0, 1.0) == top right corner.
            The values represent normalized coordinates relative to the parent figure where.
            Example: (0,0,1,1) would be the bottom left corner and (1,1,1,1) would be the top right corner.
            See mpl_toolkits.axes_grid1.inset_locator.inset_axes() documentation for additional details. 
        colorbar_borderpad (float, optional): A float used to fine tune the padding and location of the colorbar. Defaults to 0.0.
        colorbar_orientation (str, optional): A string used to set the orientation of the colorbar. Defaults to 'horizontal'.
            See matplotlib.pyplot.colorbar() orientation parameter documentation for additional details.
        colorbar_tick_location (str, optional): A string used to set the location of the tick marks for the colorbar. Defaults to 'bottom'.
            See matplotlib.pyplot.colorbar() ticklocation parameter documentation for additional details.
        colorbar_tick_direction (str, optional): A string used to set if the colorbar ticks appear inside the colorbar, outside, or both. Default 'inout' == both.
            See matplotlib.axes.Axes.tick_params() direction parameter documentation for additional details.
        colorbar_tick_label_font_size (float, optional): A float used to set the fontsize of the colorbar tick labels. Defaults to 8.0.
            See matplotlib.axes.Axes.tick_params() labelsize parameter documentation for additional details.
        colorbar_tick_label_use_exp_notation (bool, optional): A boolean used to format the colorbar tick labels in exponential notation. Defaults to True.
        colorbar_tick_label_exp_notation_decimal_limit (tuple, optional): A tuple of integers to set the decimal size threshold to switch to expontential notation. Defaults to (-3,4).
            See matplotlib.ticker.ScalarFormatter.set_powerlimits() lim parameter documentation for additional details.
        basemap_leftpad (float, optional): A float used to set the extent the basemap will show beyond the left / western most data point in the plot. Defaults to 0.05.
            The value represents a fraction of the width, or longitude range, the data points cover.
            Example: if the data points span a distance of 1000 meters East-West, the basemap will extend an additional (1000*0.05) = 50 meters to the left / west.
        basemap_rightpad (float, optional): A float used to set the extent the basemap will show beyond the right / eastern most data point in the plot. Defaults to 0.05.
            The value represents a fraction of the width, or longitude range, the data points cover.
            Example: if the data points span a distance of 1000 meters East-West, the basemap will extend an additional (1000*0.05) = 50 meters to the right / east.
        basemap_upperpad (float, optional): A float used to set the extent the basemap will show beyond the upper / northern most data point in the plot. Defaults to 0.2125.
            The value represents a fraction of the height, or latitude range, the data points cover.
            Example: if the data points span a distance of 1000 meters North-South, the basemap will extend an additional (1000*0.2125) = 212.5 meters up / north.
        basemap_lowerpad (float, optional): A float used to set the extent the basemap will show beyond the lower / southern most data point in the plot. Defaults to 0.05.
            The value represents a fraction of the height, or latitude range, the data points cover.
            Example: if the data points span a distance of 1000 meters North-South, the basemap will extend an additional (1000*0.05) = 50 meters down / south.
        basemap_provider (xyzservices.TileProvider, optional): An xyzservices.TileProvider option used to set which basemap to plot with contextily. Defaults to ctx.providers.OpenStreetMap.Mapnik.
            See contextily.providers object documentation for additional details. 
        basemap_zoom (int, optional): An integer that sets the basemap tile zoom level, controls the level of detail and resolution of the map tiles. Defaults to 6.
            Higher values correspond to higher resolution, each tile provider has a maximum available zoom level.
        zorder (int, optional): An integer that sets the order of layers when plotting multiple layers. Default = 1.
        linestyle (str, optional): A string used to set the gpd.GeoDataFrame.plot() linestyle parameter. Defaults to '--'.
        linecolor (str, optional): A string used to set the gpd.GeoDataFrame.plot() color parameter. Defaults to 'black'.
        linewidth (float, optional): A float used to set the gpd.GeoDataFrame.plot() linewidth parameter. Defaults to 1.5.

    """

    lat_long_crs: str = field(default='EPSG:4326')
    web_map_crs: str = field(default='EPSG:3857')
    figsize: tuple[float, ...] = field(default=(10.0, 8.0))
    constrained_layout: bool = field(default=True)
    figure_title: str = field(default='UPDATE TITLE')
    colormap: str = field(default='plasma_r')
    alpha: float = field(default=0.8)
    marker: str = field(default='s')
    markersize: float = field(default=36.0)
    edgecolor: str = field(default='black')
    colorbar_label: str = field(default='UPDATE LABEL')
    colorbar_label_font_size: float = field(default=8.0)
    colorbar_labelpad: float = field(default=7.5)
    colorbar_label_bbox_facecolor: str = field(default='white')
    colorbar_label_bbox_alpha: float = field(default=0.75)
    colorbar_width: str = field(default='20%')
    colorbar_height: str = field(default='2.5%')
    colorbar_location: str = field(default='lower left')
    colorbar_bbox_to_anchor: tuple[float, ...] = field(default=(0.75, 0.97, 1.0, 1.0))
    colorbar_borderpad: float = field(default=0.0)
    colorbar_orientation: str = field(default='horizontal')
    colorbar_tick_location: str = field(default='bottom')
    colorbar_tick_direction: str = field(default='inout')
    colorbar_tick_label_font_size: float = field(default=8.0)
    colorbar_tick_label_use_exp_notation: bool = field(default=True)
    colorbar_tick_label_exp_notation_decimal_limit: tuple[int, ...] = field(default=(-3, 4))
    basemap_leftpad: float = field(default=0.05)
    basemap_rightpad: float = field(default=0.05)
    basemap_upperpad: float = field(default=0.2125)
    basemap_lowerpad: float = field(default=0.05)
    basemap_provider: TileProvider = field(default=ctx.providers.OpenStreetMap.Mapnik)
    basemap_zoom: int = field(default=6)
    zorder: int = field(default=1)
    linestyle: str = field(default='--')
    linecolor: str = field(default='black')
    linewidth: float = field(default=1.5)

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
    save_plot_fpath: Path | str | None = None,
    map_preferences: dict | GeospatialMapConfig | None = {},
    save_sql_file_to_csv: bool = False,
):
    """
    Plot a geospatial point heat map for a metric of interest (ie:  AEP, LCOE, LCOI, etc.) across multiple site locations (latitude, longitude) 
    from data stored in a single cases.sql recorder file (if ran in serial), a set of cases.sql recorder files (if ran in parallel), or a .csv file.

    Allows plotting of additional layers on an existing map if the plt.figure, plt.axes, and the previous gpd.GeoDataFrame object(s)
    used to create the existing map are passed in as arguments to the function.

    Args:
        case_results_fpath (Path | str): A string or Path object to the .csv or cases.sql file(s) where results are stored
        metric_to_plot (str): A string representing the column / variable name of the metric of interest to plot as heat map points as defined in the .csv or cases.sql file.
        latitude_var_name (str, optional): A string representing the column / variable name of the latitude data as defined in the .csv or cases.sql file. Defaults to None.
            The code will attempt to automatically detect this column if no string is provided and will raise an error if unable to resolve to one column.
        longitude_var_name (str, optional): A string representing the column / variable name of the longitude data as defined in the .csv or cases.sql file. Defaults to None.
            The code will attempt to automatically detect this column if no string is provided and will raise an error if unable to resolve to one column.
        fig (plt.Figure, optional): A plt.Figure object of an existing map on which to add layers. Defaults to None.
        ax (plt.Axes, optional): A plt.Axes object of an existing map on which to add layers. Defaults to None.
        base_layer_gdf (
            gpd.GeoDataFrame | list[gpd.GeoDataFrame] | tuple[gpd.GeoDataFrame, ...],
            optional
        ):
            One or more GeoDataFrame objects previously used to create the base map. These are used to validate CRS consistency and to calculate
            map bounds when adding new layers. Defaults to None.
        show_plot (bool, optional): A boolean to control whether the plot is displayed. When adding multiple layers to the same figure, this should be set to False until the final layer
            is added. Defaults to True.
        save_plot_fpath (Path | str, optional): A string or Path object specifying where to save the generated plot. If None, the plot is not saved. Defaults to None.
        map_preferences (dict | GeospatialMapConfig, optional): A dictionary or GeospatialMapConfig object defining formatting and plotting preferences for GeoPandas, matplotlib, and contextily.
            Defaults to {}.
        save_sql_file_to_csv (bool, optional): A boolean used to save the results from cases.sql files into a csv file. passed into the convert_sql_to_csv_summary() function.
            Defaults to False.
    
    Returns:
        fig (plt.Figure): The plt.Figure object for the current plot. This can be passed back into the function to add additional layers.
        ax (plt.Axes): The plt.Axes object for the current plot. This can be passed back into the function to add additional layers.
        results_gdf (gpd.GeoDataFrame): The gpd.GeoDataFrame object created from the parsed results. This can be passed back into the function to add additional layers.

    Raises:
        TypeError: If the provided case_results_fpath is of the wront type (not .csv or .sql)
        ValueError: If only a subset of fig, ax, and base_layer_gdf is provided.
    """
    # Check if map_preferences is a dictionary and load as GeospatialMapConfig.from_dict()
    # Loads default values and checks for any erroneous / extraneous keys
    if isinstance(map_preferences, dict):
        map_preferences = GeospatialMapConfig.from_dict(
            map_preferences,
            strict=True
        )

    # Load data
    case_results_fpath = find_file(case_results_fpath)

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
            crs=map_preferences.lat_long_crs,
        ),
        crs=map_preferences.lat_long_crs,
    )

    # Convert coordinates to typical Web Mercator project CRS (EPSG:3857) for plotting
    results_gdf = results_gdf.to_crs(map_preferences.web_map_crs)

    # Check if fig, ax, and base_layer_gdf are all provided together 
    if len({fig is None, ax is None, base_layer_gdf is None}) != 1:
        raise ValueError("The fig, ax, and base_layer_gdf arguments must be provided together to add a layer to an existing plot or all must be omitted/None to create a new plot")

    # Create figure and axis objects if none are provided = creating base map
    elif fig is None:
        fig, ax = plt.subplots(
            1,
            figsize=map_preferences.figsize,
            constrained_layout=map_preferences.constrained_layout,
        )
    else: # Else fig and ax and base_layer_gdf are all not None:
        # set figure and axes as current fig,ax objects
        plt.figure(fig.number)
        plt.sca(ax)

        # Validate base_layer_gdf(s) is in the same CRS as the results_gdf
        base_layer_gdf = validate_gdfs_are_same_crs(base_layer_gdf, results_gdf)

    # Plot point heat map layer
    results_gdf.plot(
        ax=ax,
        column=metric_to_plot,
        cmap=map_preferences.colormap,
        alpha=map_preferences.alpha,
        marker=map_preferences.marker,
        markersize=map_preferences.markersize,
        edgecolor=map_preferences.edgecolor,
        # zorder=1,
    )

    # Create inset axis for color bar legend 
    inset_ax = inset_axes(
        ax,
        width=map_preferences.colorbar_width,
        height=map_preferences.colorbar_height,
        loc=map_preferences.colorbar_location,
        bbox_to_anchor=map_preferences.colorbar_bbox_to_anchor,
        bbox_transform=ax.transAxes,
        borderpad=map_preferences.colorbar_borderpad,
    )

    # Create scalar mappable object for color bar legend normalized between min and max value of metric_to_plot
    sm = plt.cm.ScalarMappable(
        cmap=map_preferences.colormap,
        norm=plt.Normalize(
            vmin=math.floor(results_gdf[metric_to_plot].min() / 100) * 100,
            vmax=math.ceil(results_gdf[metric_to_plot].max() / 100) * 100,
        ),
    )

    # plot the color bar legend
    cbar = plt.colorbar(
        sm,
        cax=inset_ax,
        ticklocation=map_preferences.colorbar_tick_location,
        orientation=map_preferences.colorbar_orientation,
    )

    # set color bar legend label
    cbar.set_label(
        map_preferences.colorbar_label,
        bbox=dict(
            facecolor=map_preferences.colorbar_label_bbox_facecolor,
            alpha=map_preferences.colorbar_label_bbox_alpha,
        ),
        size=map_preferences.colorbar_label_font_size,
        labelpad=map_preferences.colorbar_labelpad,
    )

    # format tick marks on colorbar
    inset_ax.tick_params(
        direction=map_preferences.colorbar_tick_direction,
        labelsize=map_preferences.colorbar_tick_label_font_size,
    )

    # format color bar legend offset text and position (scientific notation for values if applicable)
    # By default, this is set such that if the values of the colorbar legend are larger or smaller than 4 decimal places (0.0001-9999) then use exponential notation
    cbar.formatter.set_scientific(
        map_preferences.colorbar_tick_label_use_exp_notation
    )
    cbar.formatter.set_powerlimits(
        map_preferences.colorbar_tick_label_exp_notation_decimal_limit
    )

    offset_text = cbar.ax.xaxis.get_offset_text()
    offset_text.set_fontsize(map_preferences.colorbar_tick_label_font_size)
    
    # Dynamically set the exponential notation text x position based on the colorbar's width
    # Defaults to +2.5% relative to the colorbar width, normalized to the inset axis of the colorbar
    # Ex: colorbar_width = 20%, dynamic offset = (22.5/20) = 1.125
    # NOTE: hardcoding this for ease of handling and reducing inputs, can be changed if needed
    colorbar_width = float(map_preferences.colorbar_width[:-1])
    dyn_exp_notation_x_offset = (colorbar_width + 2.5) / colorbar_width
    offset_text.set_position(
        (dyn_exp_notation_x_offset, np.nan)
    )
    # Set the expontential notation y position centered on the colorbar
    # NOTE: hardcoding this for ease of handling and reducing inputs, can be changed if needed
    cbar.ax.xaxis.OFFSETTEXTPAD = -24

    # Calculate appropriate bounds for map based on coordinates of data used in plots
    gdfs_for_bounds = [results_gdf]
    if base_layer_gdf is not None:
        gdfs_for_bounds.extend(base_layer_gdf)

    coord_range_dict = calculate_geodataframe_total_bounds(*gdfs_for_bounds)

    left_pad = coord_range_dict['x_range'] * map_preferences.basemap_leftpad
    right_pad = coord_range_dict['x_range'] * map_preferences.basemap_rightpad
    upper_pad = coord_range_dict['y_range'] * map_preferences.basemap_upperpad
    lower_pad = coord_range_dict['y_range'] * map_preferences.basemap_lowerpad

    ax.set_xlim(coord_range_dict['min_x'] - left_pad, coord_range_dict['max_x'] + right_pad)
    ax.set_ylim(coord_range_dict['min_y'] - lower_pad, coord_range_dict['max_y'] + upper_pad)
    ax.set_axis_off()
    ax.set_title(map_preferences.figure_title)

    # Plot basemap with contextily
    ctx.add_basemap(
        ax,
        crs=map_preferences.web_map_crs,
        source=map_preferences.basemap_provider,
        zoom=map_preferences.basemap_zoom
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
        save_plot_fpath: Path | str | None = None,
        map_preferences: dict | GeospatialMapConfig | None = {},
):
    """
    Plot straight-line shipping or transport routes between a sequence of locations using latitude and longitude coordinates provided in a CSV file.

    Allows plotting of additional route layers on an existing map if the plt.figure, plt.axes, and the previous gpd.GeoDataFrame object(s)
    used to create the existing map are passed in as arguments to the function

    NOTE:
        This function currently plots simple straight-line connections between locations and is intended for proof-of-concept and early-stage analysis.
        Future versions may incorporate more advanced routing logic.

    Args:
        shipping_coords_fpath (Path | str): A string or Path object pointing to a CSV file containing location names and their corresponding latitude and longitude coordinates.
        shipping_route (list[str]): An ordered list of location identifiers defining the shipping or transport route. 
            Each identifier must correspond to an index entry in the provided CSV file.
        latitude_var_name (str, optional): A string representing the column / variable name of the latitude data as defined in the .csv file. Defaults to None.
            The code will attempt to automatically detect this column if no string is provided and will raise an error if unable to resolve to one column.
        longitude_var_name (str, optional): A string representing the column / variable name of the longitude data as defined in the .csv file. Defaults to None.
            The code will attempt to automatically detect this column if no string is provided and will raise an error if unable to resolve to one column.
        fig (plt.Figure, optional):A plt.Figure object of an existing map on which to add the shipping route. Defaults to None.
        ax (plt.Axes, optional): A plt.Axes object of an existing map on which to add the shipping route. Defaults to None.
        base_layer_gdf (
            gpd.GeoDataFrame | list[gpd.GeoDataFrame] | tuple[gpd.GeoDataFrame, ...],
            optional
        ):
            One or more GeoDataFrame objects previously used to create the base map. These are used to validate CRS consistency and to calculate
            map bounds when adding new layers. Defaults to None.
        show_plot (bool, optional): A boolean to control whether the plot is displayed. When adding multiple layers to the same figure, this should be set to False until the final layer
            is added. Defaults to True.
        save_plot_fpath (Path | str, optional): A string or Path object specifying where to save the generated plot. If None, the plot is not saved. Defaults to None.
        map_preferences (dict | GeospatialMapConfig, optional): A dictionary or GeospatialMapConfig object defining formatting and plotting preferences for GeoPandas, matplotlib, and contextily.
            Defaults to {}.

    Returns:
        fig (plt.Figure): The plt.Figure object for the current plot. This can be passed back into the function to add additional layers.
        ax (plt.Axes): The plt.Axes object for the current plot. This can be passed back into the function to add additional layers.
        shipping_route_gdf (gpd.GeoDataFrame): The gpd.GeoDataFrame containing the plotted shipping route geometry. This can be passed back into the function to add additional layers.
            

    Raises:
        TypeError: If the provided shipping_coords_fpath is not a CSV file.
        ValueError: If only a subset of fig, ax, and base_layer_gdf is provided.
    
    """



    # Check if map_preferences is a dictionary and load as GeospatialMapConfig.from_dict()
    # Loads default values and checks for any erroneous / extraneous keys
    if isinstance(map_preferences, dict):
        map_preferences = GeospatialMapConfig.from_dict(
            map_preferences,
            strict=True
        )

    # Load data
    shipping_coords_fpath = find_file(shipping_coords_fpath)

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
    shipping_route_gdf = gpd.GeoDataFrame(geometry=[LineString(shipping_route_coords)], crs=map_preferences.lat_long_crs)

    # Convert coordinates to typical Web Mercator project CRS (EPSG:3857) for plotting
    shipping_route_gdf = shipping_route_gdf.to_crs(map_preferences.web_map_crs)

    # Check if fig, ax, and base_layer_gdf are all provided together 
    if len({fig is None, ax is None, base_layer_gdf is None}) != 1:
        raise ValueError("The fig, ax, and base_layer_gdf arguments must be provided together to add a layer to an existing plot or all must be omitted/None to create a new plot")

    # Create figure and axis objects if none are provided = creating base map
    elif fig is None:
        fig, ax = plt.subplots(
            1,
            figsize=map_preferences.figsize,
            constrained_layout=map_preferences.constrained_layout,
        )
    else: # Else fig and ax and base_layer_gdf are all not None:
        # set figure and axes as current fig,ax objects
        plt.figure(fig.number)
        plt.sca(ax)

        # Validate base_layer_gdf(s) is in the same CRS as the results_gdf
        base_layer_gdf = validate_gdfs_are_same_crs(base_layer_gdf, shipping_route_gdf)

    # Plot straight line shipping layer
    shipping_route_gdf.plot(
        ax=ax,
        linestyle=map_preferences.linestyle,
        color=map_preferences.linecolor,
        linewidth=map_preferences.linewidth,
        zorder=map_preferences.zorder
    )    

    # Calculate appropriate bounds for map based on coordinates of data used in plots
    gdfs_for_bounds = [shipping_route_gdf]
    if base_layer_gdf is not None:
        gdfs_for_bounds.extend(base_layer_gdf)

    coord_range_dict = calculate_geodataframe_total_bounds(*gdfs_for_bounds)

    left_pad = coord_range_dict['x_range'] * map_preferences.basemap_leftpad
    right_pad = coord_range_dict['x_range'] * map_preferences.basemap_rightpad
    upper_pad = coord_range_dict['y_range'] * map_preferences.basemap_upperpad
    lower_pad = coord_range_dict['y_range'] * map_preferences.basemap_lowerpad


    ax.set_xlim(coord_range_dict['min_x'] - left_pad, coord_range_dict['max_x'] + right_pad)
    ax.set_ylim(coord_range_dict['min_y'] - lower_pad, coord_range_dict['max_y'] + upper_pad)
    ax.set_axis_off()
    ax.set_title(map_preferences.figure_title)

    # Add basemap tiles with contextily
    ctx.add_basemap(
        ax,
        crs=map_preferences.web_map_crs,
        source=map_preferences.basemap_provider,
        zoom=map_preferences.basemap_zoom,
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

def calculate_geodataframe_total_bounds(*gdfs: gpd.GeoDataFrame | list[gpd.GeoDataFrame]):
    """
    Calculate the combined spatial bounds for one or more GeoDataFrames.

    Computes the minimum and maximum X and Y coordinates across all provided GeoDataFrames and returns both the absolute bounds and the corresponding
    coordinate ranges. All GeoDataFrames must share the same coordinate reference system (CRS).

    Args:
        *gdfs (gpd.GeoDataFrame | list[gpd.GeoDataFrame]): One or more GeoDataFrame objects for which to compute the combined spatial extent.

    Returns:
        coord_range_dict (dict): A dictionary containing the combined bounds and coordinate ranges with the following keys:

            - ``min_x``: Minimum X coordinate across all GeoDataFrames
            - ``min_y``: Minimum Y coordinate across all GeoDataFrames
            - ``max_x``: Maximum X coordinate across all GeoDataFrames
            - ``max_y``: Maximum Y coordinate across all GeoDataFrames
            - ``x_range``: Total range in the X direction (max_x - min_x)
            - ``y_range``: Total range in the Y direction (max_y - min_y)

    Raises:
        ValueError: If no GeoDataFrames are provided or if the GeoDataFrames do not all share the same CRS.
    
    """

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
    Auto detect latitude and longitude column names in a pandas DataFrame.

    Searches the DataFrame’s column names using case-insensitive keyword matching to identify a single latitude column and a single longitude column. 
    If the detection is ambiguous or unsuccessful, an error is raised and the user must explicitly specify the column names.

    Args:
        results_df (pd.DataFrame): A pandas DataFrame containing latitude and longitude information within its columns.

    Returns:
        latitude_var_name (str): The detected column name corresponding to latitude values.
        longitude_var_name (str): The detected column name corresponding to longitude values.

    Raises:
        KeyError: If no latitude or longitude column can be detected, or if multiple possible columns are found for either coordinate, resulting in an ambiguous match.
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

def validate_gdfs_are_same_crs(base_layer_gdf: gpd.GeoDataFrame | list[gpd.GeoDataFrame] | tuple[gpd.GeoDataFrame, ...],
                               results_gdf:gpd.GeoDataFrame):
    """
    Validate that one or more GeoDataFrames share the same CRS as a reference GeoDataFrame.

    Ensures that all provided base-layer GeoDataFrames use the same coordinate reference system (CRS) as the results GeoDataFrame used for plotting.
    If a single GeoDataFrame is provided, it is normalized to a list to simplify downstream processing.

    Args:
        base_layer_gdf (
            gpd.GeoDataFrame | list[gpd.GeoDataFrame] | tuple[gpd.GeoDataFrame, ...]
        ):
            A GeoDataFrame or collection of GeoDataFrames representing existing map layers to which additional data will be added.

        results_gdf (gpd.GeoDataFrame): The GeoDataFrame defining the CRS to be used for validation.

    Returns:
        base_layer_gdf (list[gpd.GeoDataFrame]): A list of GeoDataFrames validated to share the same CRS as ``results_gdf``. 
        If a single GeoDataFrame was provided, it is returned as a one-element list.

    Raises:
        ValueError: If any provided GeoDataFrame does not share the same CRS as ``results_gdf``.
    """

    # Validate base_layer_gdf(s) is in the same CRS as the results_gdf
    if isinstance(base_layer_gdf, (list, tuple)):
        for gdf in base_layer_gdf:
            if gdf.crs != results_gdf.crs:
                raise ValueError(f"base_layer_gdf(s) CRS ({gdf.crs}) must match the new layers plotting CRS ({results_gdf.crs})")
    else: # single GeoDataFrame
        if base_layer_gdf.crs != results_gdf.crs:
                raise ValueError(f"base_layer_gdf(s) CRS ({base_layer_gdf.crs}) must match the new layers plotting CRS ({results_gdf.crs})")
        base_layer_gdf = [base_layer_gdf]

    return base_layer_gdf