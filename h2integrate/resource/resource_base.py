from pathlib import Path

import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig
from h2integrate.resource.utilities.file_tools import check_resource_dir
from h2integrate.resource.utilities.download_tools import download_from_api


@define
class ResourceBaseAPIConfig(BaseConfig):
    """Base configuration class for resource data downloaded from an API.

    Subclasses should include the following attributes that are not set in this BaseConfig:

        - **resource_year** (*int*): Year to download resource data for.
            Recommended to have a range_val validator.
        - **resource_data** (*dict*, optional): Dictionary of user-provided resource data.
            Defaults to {}.
        - **resource_dir** (*str | Path*, optional): Folder to save resource files to or
            load resource files from. Defaults to "".
        - **resource_filename** (*str*, optional): Filename to save resource data to or load
            resource data from. Defaults to None.
        - **valid_intervals** (*list[int]*): time interval(s) in minutes that resource data can be
            downloaded in.

    Note:
        Attributes should be updated in subclasses and should not be modifiable by the user.
        These should be inherit attributes of the subclass.

    Args:
        latitude (float): latitude to download resource data for.
        longitude (float): longitude to download resource data for.
        timezone (float | int): timezone to output data in. May be used to determine whether
            to download data in UTC or local timezone. This should be populated by the value
            in sim_config['timezone']

    Attributes:
        dataset_desc (str): description of the dataset, used in file naming.
            Should be updated in a subclass.
        resource_type (str): type of resource data downloaded, used in folder naming.
            Should be updated in a subclass.



    """

    latitude: float = field()
    longitude: float = field()

    timezone: int | float = field()

    dataset_desc: str = field(default="default", init=False)
    resource_type: str = field(default="none", init=False)


class ResourceBaseAPIModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("resource_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        # create attributes that will be commonly used for resource classes.
        self.site_config = self.options["plant_config"]["site"]
        self.sim_config = self.options["plant_config"]["plant"]["simulation"]
        self.n_timesteps = int(self.sim_config["n_timesteps"])
        self.dt = self.sim_config["dt"]
        self.start_time = self.sim_config["start_time"]

    def create_filename(self):
        """Create default filename to save downloaded data to. Suggested filename formatting is:

        "{latitude}_{longitude}_{resource_year}_{dataset_desc}_{interval}min_{tz_desc}_tz.csv"
        where "tz_desc" is "utc" if the timezone is zero, or "local" otherwise.

        Returns:
            str: filename for resource data to be saved to or loaded from.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")

    def create_url(self):
        """Create url for data download.

        Returns:
            str: url to use for API call.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")

    def download_data(self, url, fpath):
        """Download data from url to a file.

        Args:
            url (str): url to call to access data.
            fpath (Path | str): filepath to save data to.

        Returns:
            bool: True if data was downloaded successfully, False if error was encountered.
        """

        success = download_from_api(url, fpath)
        return success

    def load_data(self, fpath):
        """Loads data from a file, reformats data to follow a standardized naming convention,
        converts data to standardized units, and creates a data time profile.

        Args:
            fpath (str | fpath): filepath to load the data from.

        Raises:
            NotImplementedError: this method should be implemented in a subclass.

        Returns:
            dict: dictionary of data that follows the corresponding standardized
                naming convention and is in standardized units.
                The time profile created should be found in the 'time' key.
        """
        raise NotImplementedError("This method should be implemented in a subclass.")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # resource data should not be modified after setup(),
        # so this method can be empty
        pass

    def get_data(self):
        """Get resource data to handle any of the expected inputs. This method does the following:

        1) check if resource data was input. If not, continue to Step 2.
        2) Get valid resource_dir with the method `check_resource_dir()`
        3) Create a filename if resource_filename was not input with the method `create_filename()`.
            Otherwise, use resource_filename as the filename.
        4) If the resulting resource_dir and filename from Steps 2 and 3 make a valid filepath,
            load data using `load_data()`. Otherwise, continue to Step 5.
        5) Create the url to download data using `create_url()` and continue to Step 6.
        6) Download data from the url created in Step 5 and save to a filepath created from the
            resulting resource_dir and filename from Steps 2 and 3. Continue to Step 7.
        7) Load data from the file created in Step 6 using `load_data()`

        Raises:
            ValueError: If data was not successfully downloaded from the API
            ValueError: An unexpected case was encountered in handling data

        Returns:
            Any: resource data in the format expected by the subclass.
        """
        data = None

        # 1) check if user provided data
        if bool(self.config.resource_data):
            # check that data has correct interval and timezone
            data = self.config.resource_data
            return data

        # 2) check if user provided directory or filename
        if data is None:
            provided_filename = False if self.config.resource_filename == "" else True
            provided_dir = False if self.config.resource_dir is None else True
            if (
                provided_dir
                and Path(self.config.resource_dir).parts[-1] == self.config.resource_type
            ):
                resource_dir = check_resource_dir(resource_dir=self.config.resource_dir)
            else:
                resource_dir = check_resource_dir(
                    resource_dir=self.config.resource_dir, resource_subdir=self.config.resource_type
                )
            if provided_filename:
                filepath = resource_dir / self.config.resource_filename
            else:
                filename = self.create_filename()
                filepath = resource_dir / filename
            if filepath.is_file():
                self.filepath = filepath
                data = self.load_data(filepath)
                return data

        # 3) download data if not found in file or not provided
        if data is None:
            self.filepath = filepath
            url = self.create_url()
            success = self.download_data(url, filepath)
            if not success:
                raise ValueError("Did not successfully download data")
            data = self.load_data(filepath)
            return data

        self.filepath = filepath

        if data is None:
            raise ValueError("Unexpected situation occurred while trying to load data")
