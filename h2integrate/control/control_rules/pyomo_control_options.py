import numpy as np
from attrs import field, define

from h2integrate.core.utilities import BaseConfig
from h2integrate.core.validators import gt_zero, contains, gte_zero, range_val


@define
class PyomoControlOptions(BaseConfig):
    """
    Configuration class for setting dispatch options.

    This class inherits from BaseConfig and uses attrs for field definition and validation.
    Configuration can be set by passing a dictionary to the from_dict() class method or by
    providing values directly to the constructor.

    Attributes:
        - **solver** (str, default='cbc'): MILP solver used for dispatch optimization problem.
        Options are `('glpk', 'cbc', 'xpress', 'xpress_persistent', 'gurobi_ampl', 'gurobi')`.

        - **solver_options** (dict): Dispatch solver options.

        - **include_lifecycle_count** (bool, default=True): Should battery lifecycle counting
        be included.

        - **lifecycle_cost_per_kWh_cycle** (float, default=0.0265): If include_lifecycle_count,
        cost per kWh cycle.

        - **max_lifecycle_per_day** (int, default=None): If include_lifecycle_count, how many
        cycles allowed per day.

        - **n_look_ahead_periods** (int, default=48): Number of time periods dispatch
        looks ahead.

        - **n_roll_periods** (int, default=24): Number of time periods simulation rolls forward
        after each dispatch.

        - **time_weighting_factor** (float, default=0.995): Discount factor for the time periods
        in the look ahead period.

        - **log_name** (str, default=''): Dispatch log file name, empty str will result in no
        log (for development).

        - **use_clustering** (bool, default=False): If True, the simulation will be run for a
        selected set of "exemplar" days.

        - **n_clusters** (int, default=30).

        - **clustering_weights** (dict, default={}): Custom weights used for classification
        metrics for data clustering. If empty, default weights will be used.

        - **clustering_divisions** (dict, default={}): Custom number of averaging periods for
        classification metrics for data clustering. If empty, default values will be used.

        - **use_higher_hours** bool (default = False): if True, the simulation will run extra
        hours analysis (must be used with load following)

        - **higher_hours** (dict, default = {}): Higher hour count parameters: the value of
        power that must be available above the schedule and the number of hours in a row

    """

    solver: str = field(
        default="glpk",
        validator=contains(["glpk", "cbc", "xpress", "xpress_persistent", "gurobi_ampl", "gurobi"]),
    )
    solver_options: dict = field(default_factory=dict)
    include_lifecycle_count: bool = field(default=True)
    lifecycle_cost_per_kWh_cycle: float = field(default=0.0265, validator=gte_zero)
    max_lifecycle_per_day: int | float = field(default=np.inf, validator=gt_zero)
    n_look_ahead_periods: int = field(default=48, validator=gt_zero)
    time_weighting_factor: float = field(default=0.995, validator=range_val(0, 1))
    n_roll_periods: int = field(default=24, validator=gt_zero)
    log_name: str = field(default="")
    use_clustering: bool = field(default=False)
    n_clusters: int = field(default=30, validator=gt_zero)
    clustering_weights: dict = field(default_factory=dict)
    clustering_divisions: dict = field(default_factory=dict)
    use_higher_hours: bool = field(default=False)
    higher_hours: dict = field(default_factory=dict)
