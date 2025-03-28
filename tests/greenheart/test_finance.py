from pytest import approx


def test_calc_financial_parameter_weighted_average_by_capex(subtests):
    from h2integrate.tools.eco.finance import calc_financial_parameter_weighted_average_by_capex

    with subtests.test("single value"):
        h2integrate_config = {"finance_parameters": {"discount_rate": 0.1}}

        assert (
            calc_financial_parameter_weighted_average_by_capex(
                "discount_rate", h2integrate_config=h2integrate_config, capex_breakdown={}
            )
            == 0.1
        )

    with subtests.test("weighted average value - all values specified"):
        h2integrate_config = {"finance_parameters": {"discount_rate": {"wind": 0.05, "solar": 0.1}}}

        capex_breakdown = {"wind": 1e9, "solar": 1e8}

        return_value = calc_financial_parameter_weighted_average_by_capex(
            "discount_rate", h2integrate_config=h2integrate_config, capex_breakdown=capex_breakdown
        )

        assert return_value == approx(0.05454545454545454)

    with subtests.test("weighted average value - not all values specified"):
        h2integrate_config = {
            "finance_parameters": {"discount_rate": {"wind": 0.05, "solar": 0.1, "general": 0.15}}
        }

        capex_breakdown = {"wind": 1e9, "solar": 1e8, "electrolyzer": 3e8, "battery": 2e8}

        return_value = calc_financial_parameter_weighted_average_by_capex(
            "discount_rate", h2integrate_config=h2integrate_config, capex_breakdown=capex_breakdown
        )

        assert return_value == approx(0.084375)
