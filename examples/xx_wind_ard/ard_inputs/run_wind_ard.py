import pprint as pp

import numpy as np
import openmdao.api as om
from ard.api import set_up_ard_model
from ard.utils.io import load_yaml
from ard.viz.layout import plot_layout


def run_example():
    # load input
    input_dict = load_yaml("./inputs/ard_system.yaml")

    # set up system
    prob = set_up_ard_model(input_dict=input_dict, root_data_path="inputs")

    if False:
        # visualize model
        om.n2(prob)

    # run the model
    prob.run_model()

    # collapse the test result data
    test_data = {
        "AEP_val": float(prob.get_val("AEP_farm", units="GW*h")[0]),
        "CapEx_val": float(prob.get_val("tcc.tcc", units="MUSD")[0]),
        "BOS_val": float(prob.get_val("landbosse.total_capex", units="MUSD")[0]),
        "OpEx_val": float(prob.get_val("opex.opex", units="MUSD/yr")[0]),
        "LCOE_val": float(prob.get_val("financese.lcoe", units="USD/MW/h")[0]),
        "area_tight": float(prob.get_val("landuse.area_tight", units="km**2")[0]),
        "coll_length": float(prob.get_val("total_length_cables", units="km")[0]),
        "turbine_spacing": float(
            np.min(prob.get_val("spacing_constraint.turbine_spacing", units="km"))
        ),
    }

    print("\n\nRESULTS:\n")
    pp.pprint(test_data)
    print("\n\n")
    plot_layout(
        prob,
        input_dict=input_dict,
        show_image=True,
        include_cable_routing=True,
        save_path="initial_wind_farm_layout.png",
        save_kwargs={"transparent": True},
    )

    optimize = True  # set to False to skip optimization

    if optimize:
        # run the optimization
        prob.run_driver()
        prob.cleanup()

        # collapse the test result data
        test_data = {
            "AEP_val": float(prob.get_val("AEP_farm", units="GW*h")[0]),
            "CapEx_val": float(prob.get_val("tcc.tcc", units="MUSD")[0]),
            "BOS_val": float(prob.get_val("landbosse.total_capex", units="MUSD")[0]),
            "OpEx_val": float(prob.get_val("opex.opex", units="MUSD/yr")[0]),
            "LCOE_val": float(prob.get_val("financese.lcoe", units="USD/MW/h")[0]),
            "area_tight": float(prob.get_val("landuse.area_tight", units="km**2")[0]),
            "coll_length": float(prob.get_val("total_length_cables", units="km")[0]),
            "turbine_spacing": float(
                np.min(prob.get_val("spacing_constraint.turbine_spacing", units="km"))
            ),
        }

        # clean up the recorder
        prob.cleanup()

        # print the results
        print("\n\nRESULTS (opt):\n")
        pp.pprint(test_data)
        print("\n\n")

        plot_layout(
            prob,
            input_dict=input_dict,
            show_image=True,
            include_cable_routing=True,
            save_path="final_wind_farm_layout.png",
            save_kwargs={"transparent": True},
        )


if __name__ == "__main__":
    run_example()
    # update_layout(65, "inputs/windio.yaml", xlim=[-3000, 3000], ylim=[-3000, 3000])
