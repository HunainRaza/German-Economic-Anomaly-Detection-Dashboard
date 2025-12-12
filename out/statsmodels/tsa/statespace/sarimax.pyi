from .initialization import Initialization as Initialization
from .mlemodel import MLEModel as MLEModel, MLEResults as MLEResults, MLEResultsWrapper as MLEResultsWrapper
from .tools import companion_matrix as companion_matrix, constrain_stationary_univariate as constrain_stationary_univariate, diff as diff, is_invertible as is_invertible, prepare_exog as prepare_exog, prepare_trend_data as prepare_trend_data, prepare_trend_spec as prepare_trend_spec, unconstrain_stationary_univariate as unconstrain_stationary_univariate
from _typeshed import Incomplete
from statsmodels.compat.pandas import Appender as Appender
from statsmodels.tools.decorators import cache_readonly as cache_readonly
from statsmodels.tools.tools import Bunch as Bunch
from statsmodels.tsa.arima.params import SARIMAXParams as SARIMAXParams
from statsmodels.tsa.arima.specification import SARIMAXSpecification as SARIMAXSpecification
from statsmodels.tsa.tsatools import lagmat as lagmat

class SARIMAX(MLEModel):
    order: Incomplete
    seasonal_order: Incomplete
    seasonal_periods: Incomplete
    measurement_error: Incomplete
    time_varying_regression: Incomplete
    mle_regression: Incomplete
    simple_differencing: Incomplete
    enforce_stationarity: Incomplete
    enforce_invertibility: Incomplete
    hamilton_representation: Incomplete
    concentrate_scale: Incomplete
    use_exact_diffuse: Incomplete
    polynomial_ar: Incomplete
    polynomial_ma: Incomplete
    polynomial_seasonal_ar: Incomplete
    polynomial_seasonal_ma: Incomplete
    trend: Incomplete
    trend_offset: Incomplete
    k_ar: Incomplete
    k_ar_params: Incomplete
    k_diff: Incomplete
    k_ma: Incomplete
    k_ma_params: Incomplete
    k_seasonal_ar: Incomplete
    k_seasonal_ar_params: Incomplete
    k_seasonal_diff: Incomplete
    k_seasonal_ma: Incomplete
    k_seasonal_ma_params: Incomplete
    k_exog: Incomplete
    state_regression: Incomplete
    state_error: Incomplete
    k_params: Incomplete
    orig_endog: Incomplete
    orig_exog: Incomplete
    orig_k_diff: Incomplete
    orig_k_seasonal_diff: Incomplete
    nobs: Incomplete
    k_states: Incomplete
    k_posdef: Incomplete
    def __init__(self, endog, exog=None, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0), trend=None, measurement_error: bool = False, time_varying_regression: bool = False, mle_regression: bool = True, simple_differencing: bool = False, enforce_stationarity: bool = True, enforce_invertibility: bool = True, hamilton_representation: bool = False, concentrate_scale: bool = False, trend_offset: int = 1, use_exact_diffuse: bool = False, dates=None, freq=None, missing: str = 'none', validate_specification: bool = True, **kwargs) -> None: ...
    def prepare_data(self): ...
    transition_ar_params_idx: Incomplete
    selection_ma_params_idx: Incomplete
    design_ma_params_idx: Incomplete
    def initialize(self) -> None: ...
    loglikelihood_burn: Incomplete
    def initialize_default(self, approximate_diffuse_variance=None) -> None: ...
    @property
    def initial_design(self): ...
    @property
    def initial_state_intercept(self): ...
    @property
    def initial_transition(self): ...
    @property
    def initial_selection(self): ...
    def clone(self, endog, exog=None, **kwargs): ...
    @property
    def start_params(self): ...
    @property
    def endog_names(self, latex: bool = False): ...
    params_complete: Incomplete
    @property
    def param_terms(self): ...
    @property
    def param_names(self): ...
    @property
    def state_names(self): ...
    @property
    def model_orders(self): ...
    @property
    def model_names(self): ...
    @property
    def model_latex_names(self): ...
    def transform_params(self, unconstrained): ...
    def untransform_params(self, constrained): ...
    def update(self, params, transformed: bool = True, includes_fixed: bool = False, complex_step: bool = False): ...

class SARIMAXResults(MLEResults):
    df_resid: Incomplete
    specification: Incomplete
    polynomial_trend: Incomplete
    polynomial_ar: Incomplete
    polynomial_ma: Incomplete
    polynomial_seasonal_ar: Incomplete
    polynomial_seasonal_ma: Incomplete
    polynomial_reduced_ar: Incomplete
    polynomial_reduced_ma: Incomplete
    model_orders: Incomplete
    param_terms: Incomplete
    def __init__(self, model, params, filter_results, cov_type=None, **kwargs) -> None: ...
    def extend(self, endog, exog=None, **kwargs): ...
    @cache_readonly
    def arroots(self): ...
    @cache_readonly
    def maroots(self): ...
    @cache_readonly
    def arfreq(self): ...
    @cache_readonly
    def mafreq(self): ...
    @cache_readonly
    def arparams(self): ...
    @cache_readonly
    def seasonalarparams(self): ...
    @cache_readonly
    def maparams(self): ...
    @cache_readonly
    def seasonalmaparams(self): ...
    def summary(self, alpha: float = 0.05, start=None): ...

class SARIMAXResultsWrapper(MLEResultsWrapper): ...
