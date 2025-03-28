from pytest import approx

from h2integrate.simulation.technologies.hydrogen.electrolysis.PEM_costs_custom import (
    calc_custom_electrolysis_capex_fom,
)


TOL = 1e-6

electrolyzer_size_MW = 1
electrolyzer_size_kW = electrolyzer_size_MW * 1e3
fom_usd_pr_kW = 10.0
capex_usd_pr_kW = 15.0
elec_config = {"electrolyzer_capex": capex_usd_pr_kW, "fixed_om_per_kw": fom_usd_pr_kW}


def test_custom_capex():
    capex, fom = calc_custom_electrolysis_capex_fom(electrolyzer_size_kW, elec_config)
    assert capex == approx(capex_usd_pr_kW * electrolyzer_size_kW, TOL)


def test_custom_fixed_om():
    capex, fom = calc_custom_electrolysis_capex_fom(electrolyzer_size_kW, elec_config)
    assert fom == approx(fom_usd_pr_kW * electrolyzer_size_kW, TOL)
