from pathlib import Path

from h2integrate import EXAMPLE_DIR
from h2integrate.tools.run_cases import modify_tech_config, load_tech_config_cases
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_tech_config_modifier(subtests):
    """Test cases for modifiying and running tech_config from csv.
    Using 01 example as test case
    """

    # Make an H2I model from the 01 example
    orig_highlevel_yaml = EXAMPLE_DIR / "01_onshore_steel_mn" / "01_onshore_steel_mn.yaml"
    model = H2IntegrateModel(orig_highlevel_yaml)

    # Modify using csv
    case_file = Path(__file__).resolve().parent / "test_inputs.csv"
    cases = load_tech_config_cases(case_file)
    with subtests.test("float"):
        case = cases["Float Test"]
        model = modify_tech_config(model, case)
        model.run()
