from h2integrate.finances.profast_financial import ProFastComp


class ProFASTNPV(ProFastComp):
    def setup(self):
        self.commodity_sell_price = self.options["plant_config"]["finance_parameters"][
            "model_inputs"
        ].get("commodity_sell_price", None)

        if self.commodity_sell_price is None:
            raise ValueError("commodity_sell_price is missing as an input")

        super().setup()
        self.add_input(
            "commodity_sell_price",
            val=self.commodity_sell_price,
            units=self.lco_units,
        )

        self.output_txt = self.options["commodity_type"].lower()
        if self.options["description"] != "":
            desc_str = self.options["description"].strip().strip("_()-")
            if desc_str != "":
                self.output_txt = f"{self.options['commodity_type'].lower()}_{desc_str}"

        self.add_output(
            f"NPV_{self.output_txt}",
            val=0.0,
            units="USD",  # TODO: check units
        )

    def compute(self, inputs, outputs):
        pf = self.populate_profast(inputs)

        outputs[f"NPV_{self.output_txt}"] = pf.cash_flow(price=inputs["commodity_sell_price"][0])
