from h2integrate.finances.profast_financial import ProFastComp


class ProFASTNPV(ProFastComp):
    def add_model_specific_outputs(self):
        self.add_output(
            f"NPV_{self.output_txt}",
            val=0.0,
            units="USD",
        )

        return

    def setup(self):
        self.commodity_sell_price = self.options["plant_config"]["finance_parameters"][
            "model_inputs"
        ].get("commodity_sell_price", None)

        if self.commodity_sell_price is None:
            raise ValueError("commodity_sell_price is missing as an input")

        super().setup()

        self.add_input(
            f"sell_price_{self.output_txt}",
            val=self.commodity_sell_price,
            units=self.lco_units,
        )

    def compute(self, inputs, outputs):
        pf = self.populate_profast(inputs)

        outputs[f"NPV_{self.output_txt}"] = pf.cash_flow(
            price=inputs[f"sell_price_{self.output_txt}"][0]
        )
