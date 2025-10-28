# Specifying Filepaths in H2I

Filepaths in H2I can be specified in a number of ways. Files are looked for using the `find_file()` method, which looks for files in the following order:
1. With respect to a specified root folder
2. With respect to the current working directory (cwd)
3. With respect to the H2Integrate package root. This folder includes subdirectories of `examples`, `resource_files`, `docs` and `h2integrate`.
4. As an absolute filepath

## Main Input Files
The main input files to H2Integrate (`plant_config`, `tech_config` and `driver_config`) are defined in a top-level config file. In many examples, these files live in the same folder as the python run script.

The main input files are searched for H2I in the following order:
1. Relative to the folder containing the top-level config file
    ```yaml
    plant_config: "plant_config.yaml"
    technology_config: "tech_config.yaml"
    driver_config: "driver_config.yaml"
    ```
2. Relative to the current working directory (suppose our cwd is `examples/14_wind_hydrogen_dispatch`):
    ```yaml
    plant_config: "inputs/plant_config.yaml"
    technology_config: "inputs/tech_config.yaml"
    driver_config: "inputs/driver_config.yaml"
    ```
3. Relative to the H2Integrate root directory
    ```yaml
    plant_config: "examples/01_onshore_steel_mn/plant_config.yaml"
    technology_config: "examples/01_onshore_steel_mn/tech_config.yaml"
    driver_config: "examples/01_onshore_steel_mn/driver_config.yaml"
    ```
4. As an absolute filepath.
    ```yaml
    plant_config: "/Users/myname/H2Integrate/examples/01_onshore_steel_mn/plant_config.yaml"
    technology_config: "/Users/myname/H2Integrate/examples/01_onshore_steel_mn/tech_config.yaml"
    driver_config: "/Users/myname/H2Integrate/examples/01_onshore_steel_mn/driver_config.yaml"
    ```

## Recommendations
1. Change your current working directory to the folder containing your input files, this is how most examples are set-up.
    ```bash
    cd examples/01_onshore_steel_mn
    python run_onshore_steel_mn.py
    ```
2. Specify full filepaths instead of relative filepaths
3. Use unique filenames if specifying filepaths relative to the H2Integrate package root.
4. Check the filepaths are correct:
    ```python
    model = H2IntegrateModel(Path.cwd()/"01_onshore_steel_mn.yaml")
    print(f"Driver config file: {model.driver_config_path}")
    print(f"Tech config file: {model.tech_config_path}")
    print(f"Plant config file: {model.plant_config_path}")
    ```
