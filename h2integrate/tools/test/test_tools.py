import os
from pathlib import Path

import pytest

from h2integrate import EXAMPLE_DIR
from h2integrate.tools.run_cases import modify_tech_config, load_tech_config_cases
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_tech_config_modifier(subtests):
    """Test cases for modifiying and running tech_config from csv.
    Using 01 example as test case
    """

    # Make an H2I model from the 01 example
    os.chdir(EXAMPLE_DIR / "01_onshore_steel_mn")
    example_yaml = "01_onshore_steel_mn.yaml"
    model = H2IntegrateModel(example_yaml)

    # Modify using csv
    case_file = Path(__file__).resolve().parent / "test_inputs.csv"
    cases = load_tech_config_cases(case_file)
    with subtests.test("float"):
        case = cases["Float Test"]
        model = modify_tech_config(model, case)
        model.run()
        assert pytest.approx(model.prob.get_val("steel.LCOS")[0], rel=1e-3) == 1036.6771578253597
    with subtests.test("bool"):
        case = cases["Bool Test"]
        model = modify_tech_config(model, case)
        model.run()
        assert pytest.approx(model.prob.get_val("steel.LCOS")[0], rel=1e-3) == 1214.1874646965953
    with subtests.test("int"):
        case = cases["Int Test"]
        model = modify_tech_config(model, case)
        model.run()
        assert pytest.approx(model.prob.get_val("steel.LCOS")[0], rel=1e-3) == 1190.9501717506432
    with subtests.test("str"):
        case = cases["Str Test"]
        model = modify_tech_config(model, case)
        model.run()
        assert pytest.approx(model.prob.get_val("steel.LCOS")[0], rel=1e-3) == 1208.0782566057335
