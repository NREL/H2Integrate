import copy
import os
import sys
import warnings

import hopp.simulation.technologies.hydrogen.electrolysis.run_h2_PEM as run_h2_PEM
import matplotlib.pyplot as plt
import numpy as np
import numpy_financial as npf
import pandas as pd
from dotenv import load_dotenv
from hopp.simulation.technologies.sites import SiteInfo
from hopp.simulation.technologies.sites import flatirons_site as sample_site
from hopp.utilities.keys import set_developer_nrel_gov_key
from lcoe.lcoe import lcoe as lcoe_calc

from greenheart.to_organize.H2_Analysis.hopp_for_h2 import hopp_for_h2
from greenheart.to_organize.H2_Analysis.hopp_for_h2 import \
    run_h2a as run_h2a  # no h2a function
from greenheart.to_organize.H2_Analysis.simple_cash_annuals import \
    simple_cash_annuals
from greenheart.to_organize.H2_Analysis.simple_dispatch import SimpleDispatch

sys.path.append('')
warnings.filterwarnings("ignore")



"""
Perform a LCOH analysis for an offshore wind + Hydrogen PEM system

1. Offshore wind site locations and cost details (4 sites, $1300/kw capex + BOS cost which will come from Orbit Runs)~
2. Cost Scaling Based on Year (Have Weiser et. al report with cost scaling for fixed and floating tech, will implement)
3. Cost Scaling Based on Plant Size (Shields et. Al report)
4. Future Model Development Required:
- Floating Electrolyzer Platform (per turbine vs. centralized)
"""
