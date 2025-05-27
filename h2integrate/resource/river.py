from pathlib import Path

import pandas as pd
import openmdao.api as om


class RiverResource(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("filename", types=str)

    def setup(self):
        # Define inputs and outputs
        self.add_output("discharge", shape=8760, val=0.0, units="ft**3/s")

    def compute(self, inputs, outputs):
        # Read the CSV file
        filename = self.options["filename"]

        # Check if the file exists
        if not Path(filename).is_file():
            raise FileNotFoundError(f"The file '{filename}' does not exist.")

        df = pd.read_csv(
            filename,
            sep="\t",
            comment="#",  # Ignore comment lines starting with #
            skiprows=13,  # Skip top metadata until actual headers
        )

        # Check if the DataFrame is empty or has insufficient data
        if df.empty or len(df) < 8760:
            raise ValueError("Insufficient data for resampling.")

        # Extract the column name for discharge
        with Path.open(filename) as file:
            for line in file:
                if "Discharge, cubic feet per second" in line:
                    # Extract the numeric identifier before "Discharge"
                    parts = line.split()
                    column_identifier = f"{parts[1]}_{parts[2]}"
                    break
            else:
                raise ValueError("Discharge column not found in the file.")

        # Rename the columns to more meaningful names
        df = df.rename(
            columns={
                column_identifier: "discharge_cfs",
            }
        )

        # Drop the first row if it contains unwanted metadata
        df = df.iloc[1:].reset_index(drop=True)

        df = df[["datetime", "discharge_cfs"]]

        # Convert 'discharge_cfs' to numeric, coercing errors to NaN
        df["discharge_cfs"] = pd.to_numeric(df["discharge_cfs"], errors="coerce")

        # Convert datetime column to datetime format
        df["datetime"] = pd.to_datetime(df["datetime"])

        # Set datetime as index (required for resampling)
        df = df.set_index("datetime")

        # Resample to hourly data using mean
        df_hourly = df.resample("1h").mean()

        # Reset index if to use datetime as a column again
        df_hourly = df_hourly.reset_index()

        # Forward fill NaN values with the last valid observation
        df_hourly = df_hourly.ffill(limit=1)

        outputs["discharge"] = df_hourly["discharge_cfs"].values

        df_hourly.to_csv("output.csv", index=False)
