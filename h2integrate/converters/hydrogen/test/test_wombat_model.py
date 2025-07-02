import numpy as np
import openmdao.api as om
from pytest import approx

from h2integrate.converters.hydrogen.wombat_model import WOMBATElectrolyzerModel


def test_wombat_model_outputs(subtests):
    prob = om.Problem()
    prob.model.add_subsystem(
        "wombat_model",
        WOMBATElectrolyzerModel(
            plant_config={
                "plant": {
                    "plant_life": 20,
                },
            },
            tech_config={
                "model_inputs": {
                    "shared_parameters": {
                        "rating": 40.0,
                        "location": "onshore",
                        "electrolyzer_capex": 1295,
                        "sizing": {
                            "resize_for_enduse": False,
                            "size_for": "BOL",
                            "hydrogen_dmd": None,
                        },
                        "cluster_rating_MW": 40,
                        "pem_control_type": "basic",
                        "eol_eff_percent_loss": 13,
                        "uptime_hours_until_eol": 80000.0,
                        "include_degradation_penalty": True,
                        "turndown_ratio": 0.1,
                        "library_path": "resource_files/wombat_library",
                    },
                }
            },
        ),
        promotes=["*"],
    )
    prob.setup()
    prob.set_val("electricity_in", np.ones(8760) * 40.0, units="MW")
    prob.run_model()

    with subtests.test("hydrogen_out"):
        assert np.linalg.norm(prob["hydrogen_out"]) == approx(72653.05815087, rel=1e-2)
    with subtests.test("total_hydrogen_produced"):
        assert prob["total_hydrogen_produced"] == approx(6777348.33570215, rel=1e-2)
    with subtests.test("efficiency"):
        assert prob["efficiency"] == approx(0.76733639, rel=1e-2)
    with subtests.test("rated_h2_production_kg_pr_hr"):
        assert prob["rated_h2_production_kg_pr_hr"] == approx(784.3544736, rel=1e-2)
    with subtests.test("CapEx"):
        assert prob["CapEx"] == approx(51800000.0, rel=1e-2)
    with subtests.test("OpEx"):
        assert prob["OpEx"] == approx(1015899.3984, rel=1e-2)
    with subtests.test("percent_hydrogen_lost"):
        assert prob["percent_hydrogen_lost"] == approx(1.50371, rel=1e-2)
    with subtests.test("electrolyzer_availability"):
        assert prob["electrolyzer_availability"] == approx(0.993379, rel=1e-2)
