import os
import shutil
from pathlib import Path

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.core.inputs.validation import load_driver_yaml


TEST_RECORDER_OUTPUT_DIR = "testingtesting_output_dir"
TEST_RECORDER_OUTPUT_FILE0 = "testingtesting_filename.sql"
TEST_RECORDER_OUTPUT_FILE1 = "testingtesting_filename0.sql"
TEST_RECORDER_OUTPUT_FILE2 = "testingtesting_filename1.sql"


def test_cleanup_from_past_tests(subtests):
    """This function just removes any left over files if they
    were not properly cleaned up in the last test run. The other
    tests are interdependent via output files, so it is possible
    to have tests fail because of previous failures.
    """

    os.chdir(EXAMPLE_DIR / "05_wind_h2_opt")

    dirs_to_remove = [
        "wind_plant_run",
        TEST_RECORDER_OUTPUT_DIR,
    ]

    for d in dirs_to_remove:
        p = Path(d)  # relative to cwd set above
        if p.exists():
            shutil.rmtree(p)
        with subtests.test(f"{d} does not exist"):
            assert not p.exists()


def test_output_folder_creation_first_run(subtests):
    # Test that the sql file is written to the output folder
    # with the specified name

    # change to example dir
    os.chdir(EXAMPLE_DIR / "05_wind_h2_opt")

    # initialize H2I using non-optimization config
    input_file = EXAMPLE_DIR / "05_wind_h2_opt" / "wind_plant_electrolyzer0.yaml"
    h2i = H2IntegrateModel(input_file)

    # load driver config for optimization run
    driver_config = load_driver_yaml(EXAMPLE_DIR / "05_wind_h2_opt" / "driver_config.yaml")

    # update driver config params with test variables
    new_output_folder = TEST_RECORDER_OUTPUT_DIR
    filename_initial = TEST_RECORDER_OUTPUT_FILE0
    driver_config["general"]["folder_output"] = new_output_folder
    driver_config["recorder"]["file"] = filename_initial
    driver_config["driver"]["optimization"]["max_iter"] = 5  # to prevent tests taking too long

    # reset the driver config in H2I
    h2i.driver_config = driver_config

    # reinitialize the driver model
    h2i.create_driver_model()

    # check if output folder and output files exist
    output_folder_exists = (EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder).exists()
    output_file_exists_prerun = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_initial
    ).exists()

    with subtests.test("Run 0: output folder exists"):
        assert output_folder_exists is True
    with subtests.test("Run 0: recorder output file does not exist yet"):
        assert output_file_exists_prerun is False

    # run the model
    h2i.run()

    # check that recorder file was created
    output_file_exists_postrun = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_initial
    ).exists()
    with subtests.test("Run 0: recorder output file exists after run"):
        assert output_file_exists_postrun is True


def test_output_new_recorder_filename_second_run(subtests):
    # Test that the sql file is written to the output folder
    # with the specified base name and an appended 0
    # change to example dir
    os.chdir(EXAMPLE_DIR / "05_wind_h2_opt")

    # initialize H2I using non-optimization config
    input_file = EXAMPLE_DIR / "05_wind_h2_opt" / "wind_plant_electrolyzer0.yaml"
    h2i = H2IntegrateModel(input_file)

    # load driver config for optimization run
    driver_config = load_driver_yaml(EXAMPLE_DIR / "05_wind_h2_opt" / "driver_config.yaml")

    # update driver config params with test variables
    new_output_folder = TEST_RECORDER_OUTPUT_DIR
    filename_initial = TEST_RECORDER_OUTPUT_FILE0
    filename_expected = TEST_RECORDER_OUTPUT_FILE1

    driver_config["general"]["folder_output"] = new_output_folder
    driver_config["recorder"]["file"] = filename_initial
    driver_config["driver"]["optimization"]["max_iter"] = 5  # to prevent tests taking too long

    # reset the driver config in H2I
    h2i.driver_config = driver_config

    # reinitialize the driver model
    h2i.create_driver_model()

    # check if output folder and output files exist
    output_folder_exists = (EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder).exists()
    output_file_exists_prerun = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_initial
    ).exists()

    with subtests.test("Run 1: output folder exists"):
        assert output_folder_exists is True
    with subtests.test("Run 1: initial recorder output file exists"):
        assert output_file_exists_prerun is True

    # run the model
    h2i.run()

    # check that the new recorder file was created
    new_output_file_exists = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_expected
    ).exists()
    with subtests.test("Run 1: new recorder output file was made"):
        assert new_output_file_exists is True


def test_output_new_recorder_overwrite_first_run(subtests):
    # change to example dir
    os.chdir(EXAMPLE_DIR / "05_wind_h2_opt")

    # initialize H2I using non-optimization config
    input_file = EXAMPLE_DIR / "05_wind_h2_opt" / "wind_plant_electrolyzer0.yaml"
    h2i = H2IntegrateModel(input_file)

    # load driver config for optimization run
    driver_config = load_driver_yaml(EXAMPLE_DIR / "05_wind_h2_opt" / "driver_config.yaml")

    # update driver config params with test variables
    new_output_folder = TEST_RECORDER_OUTPUT_DIR
    filename_initial = TEST_RECORDER_OUTPUT_FILE0
    filename_exists_if_failed = TEST_RECORDER_OUTPUT_FILE2
    driver_config["general"]["folder_output"] = new_output_folder
    driver_config["recorder"]["file"] = filename_initial

    # specify that we want the previous file overwritten rather
    # than create a new file
    driver_config["recorder"].update({"overwrite_recorder": True})
    driver_config["driver"]["optimization"]["max_iter"] = 5  # to prevent tests taking too long

    # reset the driver config in H2I
    h2i.driver_config = driver_config

    # reinitialize the driver model
    h2i.create_driver_model()

    # check if output folder and output files exist
    output_folder_exists = (EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder).exists()
    output_file_exists_prerun = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_initial
    ).exists()

    with subtests.test("Run 2: output folder exists"):
        assert output_folder_exists is True
    with subtests.test("Run 2: initial recorder output file exists"):
        assert output_file_exists_prerun is True

    # run the model
    h2i.run()

    # check that recorder file was overwritten
    new_output_file_exists = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_exists_if_failed
    ).exists()
    with subtests.test("Run 2: initial output file was overwritten"):
        assert new_output_file_exists is False


def test_output_new_recorder_filename_third_run(subtests):
    # change to example dir
    os.chdir(EXAMPLE_DIR / "05_wind_h2_opt")

    # initialize H2I using non-optimization config
    input_file = EXAMPLE_DIR / "05_wind_h2_opt" / "wind_plant_electrolyzer0.yaml"
    h2i = H2IntegrateModel(input_file)

    # load driver config for optimization run
    driver_config = load_driver_yaml(EXAMPLE_DIR / "05_wind_h2_opt" / "driver_config.yaml")

    # update driver config params with test variables
    new_output_folder = TEST_RECORDER_OUTPUT_DIR
    filename_initial = TEST_RECORDER_OUTPUT_FILE0
    filename_second = TEST_RECORDER_OUTPUT_FILE1
    filename_expected = TEST_RECORDER_OUTPUT_FILE2
    driver_config["general"]["folder_output"] = new_output_folder
    driver_config["recorder"]["file"] = filename_initial
    driver_config["driver"]["optimization"]["max_iter"] = 5  # to prevent tests taking too long

    # reset the driver config in H2I
    h2i.driver_config = driver_config

    # reinitialize the driver model
    h2i.create_driver_model()

    # check if output folder and output files exist
    output_folder_exists = (EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder).exists()
    output_file_exists_prerun = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_initial
    ).exists()
    run1_output_file_exists_prerun = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_second
    ).exists()
    with subtests.test("Run 3: output folder exists"):
        assert output_folder_exists is True
    with subtests.test("Run 3: initial recorder output file exists"):
        assert output_file_exists_prerun is True
    with subtests.test("Run 3: second recorder output file exists"):
        assert run1_output_file_exists_prerun is True

    # run the model
    h2i.run()

    # check that the new recorder file was created
    new_output_file_exists = (
        EXAMPLE_DIR / "05_wind_h2_opt" / new_output_folder / filename_expected
    ).exists()
    with subtests.test("Run 3: new recorder output file was made"):
        assert new_output_file_exists is True
