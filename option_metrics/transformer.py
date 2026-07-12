"""Pandas transformations for option metric calculations."""

import numpy as np
import pandas as pd
from scipy.stats import norm


class OptionMetricsTransformer:
    """Append implied volatility and Greek columns to option contract rows."""

    METRIC_COLUMNS = [
        "calculatedImpliedVolatility",
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
    ]

    REQUIRED_COLUMNS = {
        "timeToExpiryYears",
        "strike",
        "ask",
        "direction",
        "lastStockPrice",
        "riskFreeRate",
        "dividendYield",
    }

    @classmethod
    def transform(cls, options: pd.DataFrame) -> pd.DataFrame:
        """Return option rows enriched with metrics.

        :param options: DataFrame loaded from ``options_last.parquet``.
        :returns: Copy of ``options`` with appended metric columns.
        :raises ValueError: If required input columns are missing.
        """

        cls._validate_columns(options)
        base_options = options.drop(columns=cls.METRIC_COLUMNS, errors="ignore")
        metrics = cls._calculate_metrics(base_options)
        return pd.concat(
            [base_options.reset_index(drop=True), metrics.reset_index(drop=True)],
            axis=1,
        )

    @classmethod
    def _calculate_metrics(cls, options: pd.DataFrame) -> pd.DataFrame:
        """Calculate metric columns with vectorized pandas and NumPy operations.

        :param options: DataFrame loaded from ``options_last.parquet``.
        :returns: DataFrame containing only the metric columns.
        """

        time_to_expiry = pd.to_numeric(options["timeToExpiryYears"], errors="coerce").to_numpy(dtype=float)
        spot = pd.to_numeric(options["lastStockPrice"], errors="coerce").to_numpy(dtype=float)
        strike = pd.to_numeric(options["strike"], errors="coerce").to_numpy(dtype=float)
        market_price = pd.to_numeric(options["ask"], errors="coerce").to_numpy(dtype=float)
        risk_free_rate = pd.to_numeric(options["riskFreeRate"], errors="coerce").to_numpy(dtype=float)
        dividend_yield = pd.to_numeric(options["dividendYield"], errors="coerce").to_numpy(dtype=float)
        directions = options["direction"].astype(str).str.upper().to_numpy()
        is_call = directions == "CALL"
        is_put = directions == "PUT"

        metrics = pd.DataFrame(
            np.nan,
            index=options.index,
            columns=cls.METRIC_COLUMNS,
            dtype=float,
        )
        discounted_spot, discounted_strike = cls._discounted_values(
            spot,
            strike,
            time_to_expiry,
            risk_free_rate,
            dividend_yield,
        )
        intrinsic_value = np.where(
            is_call,
            np.maximum(0.0, discounted_spot - discounted_strike),
            np.maximum(0.0, discounted_strike - discounted_spot),
        )
        max_price = np.where(is_call, discounted_spot, discounted_strike)
        valid = (
            np.isfinite(time_to_expiry)
            & np.isfinite(spot)
            & np.isfinite(strike)
            & np.isfinite(market_price)
            & np.isfinite(risk_free_rate)
            & np.isfinite(dividend_yield)
            & (time_to_expiry > 0.0)
            & (spot > 0.0)
            & (strike > 0.0)
            & (market_price > 0.0)
            & (is_call | is_put)
            & (market_price >= intrinsic_value - 1e-9)
            & (market_price <= max_price + 1e-9)
        )

        if not valid.any():
            return metrics

        iv = cls._solve_implied_volatility(
            is_call=is_call[valid],
            market_price=market_price[valid],
            spot=spot[valid],
            strike=strike[valid],
            time_to_expiry=time_to_expiry[valid],
            risk_free_rate=risk_free_rate[valid],
            dividend_yield=dividend_yield[valid],
        )
        greeks = cls._calculate_greeks(
            is_call=is_call[valid],
            spot=spot[valid],
            strike=strike[valid],
            time_to_expiry=time_to_expiry[valid],
            volatility=iv,
            risk_free_rate=risk_free_rate[valid],
            dividend_yield=dividend_yield[valid],
        )

        metrics.loc[valid, "calculatedImpliedVolatility"] = iv
        for column, values in greeks.items():
            metrics.loc[valid, column] = values
        return metrics

    @staticmethod
    def _solve_implied_volatility(
        is_call: np.ndarray,
        market_price: np.ndarray,
        spot: np.ndarray,
        strike: np.ndarray,
        time_to_expiry: np.ndarray,
        risk_free_rate: np.ndarray,
        dividend_yield: np.ndarray,
        lower_bound: float = 1e-6,
        upper_bound: float = 5.0,
        max_upper_bound: float = 80.0,
        iterations: int = 80,
    ) -> np.ndarray:
        """Solve implied volatility for many option rows using bisection.

        The solver expands each row's upper volatility bound until the
        Black-Scholes price reaches the market price or ``max_upper_bound``.
        It then bisects the bracketed interval, moving the lower bound up when
        the model price is too low and the upper bound down otherwise.
        Unbracketed rows return ``NaN``.

        :param is_call: Boolean array identifying call rows.
        :param market_price: Observed option prices.
        :param spot: Current underlying prices.
        :param strike: Option strike prices.
        :param time_to_expiry: Times to expiry in years.
        :param risk_free_rate: Continuously compounded risk-free rates.
        :param dividend_yield: Continuously compounded dividend yields.
        :param lower_bound: Lower volatility search bound.
        :param upper_bound: Initial upper volatility search bound.
        :param max_upper_bound: Maximum volatility tested while searching for an interval containing the solution.
        :param iterations: Number of bisection iterations.
        :returns: Annualized implied volatility array.
        """

        lower = np.full_like(market_price, lower_bound, dtype=float)
        upper = np.full_like(market_price, upper_bound, dtype=float)

        upper_price = OptionMetricsTransformer._black_scholes_prices(
            is_call,
            spot,
            strike,
            time_to_expiry,
            upper,
            risk_free_rate,
            dividend_yield,
        )
        while True:
            expand = (upper_price < market_price) & (upper < max_upper_bound)
            if not expand.any():
                break
            upper = np.where(
                expand,
                np.minimum(upper * 2.0, max_upper_bound),
                upper,
            )
            upper_price = OptionMetricsTransformer._black_scholes_prices(
                is_call,
                spot,
                strike,
                time_to_expiry,
                upper,
                risk_free_rate,
                dividend_yield,
            )

        bracketed = upper_price >= market_price
        result = np.full_like(market_price, np.nan, dtype=float)
        if not bracketed.any():
            return result

        lower = lower[bracketed]
        upper = upper[bracketed]
        is_call = is_call[bracketed]
        market_price = market_price[bracketed]
        spot = spot[bracketed]
        strike = strike[bracketed]
        time_to_expiry = time_to_expiry[bracketed]
        risk_free_rate = risk_free_rate[bracketed]
        dividend_yield = dividend_yield[bracketed]

        for _ in range(iterations):
            midpoint = (lower + upper) / 2.0
            price = OptionMetricsTransformer._black_scholes_prices(
                is_call,
                spot,
                strike,
                time_to_expiry,
                midpoint,
                risk_free_rate,
                dividend_yield,
            )
            too_low = price < market_price
            lower = np.where(too_low, midpoint, lower)
            upper = np.where(too_low, upper, midpoint)

        result[bracketed] = (lower + upper) / 2.0
        return result

    @staticmethod
    def _black_scholes_prices(
        is_call: np.ndarray,
        spot: np.ndarray,
        strike: np.ndarray,
        time_to_expiry: np.ndarray,
        volatility: np.ndarray,
        risk_free_rate: np.ndarray,
        dividend_yield: np.ndarray,
    ) -> np.ndarray:
        """Return vectorized Black-Scholes-Merton option prices.

        :param is_call: Boolean array identifying call rows.
        :param spot: Current underlying prices.
        :param strike: Option strike prices.
        :param time_to_expiry: Times to expiry in years.
        :param volatility: Annualized volatility values as decimals.
        :param risk_free_rate: Continuously compounded risk-free rates.
        :param dividend_yield: Continuously compounded dividend yields.
        :returns: Theoretical option price array.
        """

        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            d1, d2 = OptionMetricsTransformer._d1_d2(
                spot,
                strike,
                time_to_expiry,
                volatility,
                risk_free_rate,
                dividend_yield,
            )
            discounted_spot, discounted_strike = OptionMetricsTransformer._discounted_values(
                spot,
                strike,
                time_to_expiry,
                risk_free_rate,
                dividend_yield,
            )
            call = discounted_spot * norm.cdf(d1) - discounted_strike * norm.cdf(d2)
            put = discounted_strike * norm.cdf(-d2) - discounted_spot * norm.cdf(-d1)
            return np.where(is_call, call, put)

    @staticmethod
    def _calculate_greeks(
        is_call: np.ndarray,
        spot: np.ndarray,
        strike: np.ndarray,
        time_to_expiry: np.ndarray,
        volatility: np.ndarray,
        risk_free_rate: np.ndarray,
        dividend_yield: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """Return vectorized Black-Scholes-Merton Greek arrays.

        Theta is returned per calendar day. Vega and rho are returned per one
        percentage point move.

        :param is_call: Boolean array identifying call rows.
        :param spot: Current underlying prices.
        :param strike: Option strike prices.
        :param time_to_expiry: Times to expiry in years.
        :param volatility: Annualized volatility values as decimals.
        :param risk_free_rate: Continuously compounded risk-free rates.
        :param dividend_yield: Continuously compounded dividend yields.
        :returns: Mapping from Greek column names to NumPy arrays.
        """

        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            d1, d2 = OptionMetricsTransformer._d1_d2(
                spot,
                strike,
                time_to_expiry,
                volatility,
                risk_free_rate,
                dividend_yield,
            )
            sqrt_t = np.sqrt(time_to_expiry)
            pdf_d1 = norm.pdf(d1)
            discount_q, discount_r = OptionMetricsTransformer._discount_factors(
                time_to_expiry,
                risk_free_rate,
                dividend_yield,
            )
            gamma = discount_q * pdf_d1 / (spot * volatility * sqrt_t)
            vega = spot * discount_q * pdf_d1 * sqrt_t / 100.0
            call_delta = discount_q * norm.cdf(d1)
            put_delta = discount_q * (norm.cdf(d1) - 1.0)
            call_theta_year = (
                -(spot * discount_q * pdf_d1 * volatility) / (2.0 * sqrt_t)
                - risk_free_rate * strike * discount_r * norm.cdf(d2)
                + dividend_yield * spot * discount_q * norm.cdf(d1)
            )
            put_theta_year = (
                -(spot * discount_q * pdf_d1 * volatility) / (2.0 * sqrt_t)
                + risk_free_rate * strike * discount_r * norm.cdf(-d2)
                - dividend_yield * spot * discount_q * norm.cdf(-d1)
            )
            call_rho = strike * time_to_expiry * discount_r * norm.cdf(d2) / 100.0
            put_rho = -strike * time_to_expiry * discount_r * norm.cdf(-d2) / 100.0

        return {
            "delta": np.where(is_call, call_delta, put_delta),
            "gamma": gamma,
            "theta": np.where(is_call, call_theta_year, put_theta_year) / 365.0,
            "vega": vega,
            "rho": np.where(is_call, call_rho, put_rho),
        }

    @staticmethod
    def _d1_d2(
        spot: np.ndarray,
        strike: np.ndarray,
        time_to_expiry: np.ndarray,
        volatility: np.ndarray,
        risk_free_rate: np.ndarray,
        dividend_yield: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return vectorized Black-Scholes-Merton ``d1`` and ``d2`` terms.

        :param spot: Current underlying prices.
        :param strike: Option strike prices.
        :param time_to_expiry: Times to expiry in years.
        :param volatility: Annualized volatility values as decimals.
        :param risk_free_rate: Continuously compounded risk-free rates.
        :param dividend_yield: Continuously compounded dividend yields.
        :returns: Tuple containing ``d1`` and ``d2`` arrays.
        """

        sqrt_t = np.sqrt(time_to_expiry)
        d1 = (
            np.log(spot / strike)
            + (risk_free_rate - dividend_yield + 0.5 * volatility * volatility)
            * time_to_expiry
        ) / (volatility * sqrt_t)
        return d1, d1 - volatility * sqrt_t

    @staticmethod
    def _discount_factors(
        time_to_expiry: np.ndarray,
        risk_free_rate: np.ndarray,
        dividend_yield: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return vectorized dividend and risk-free discount factors.

        :param time_to_expiry: Times to expiry in years.
        :param risk_free_rate: Continuously compounded risk-free rates.
        :param dividend_yield: Continuously compounded dividend yields.
        :returns: Tuple containing dividend and risk-free discount factor arrays.
        """

        return (
            np.exp(-dividend_yield * time_to_expiry),
            np.exp(-risk_free_rate * time_to_expiry),
        )

    @staticmethod
    def _discounted_values(
        spot: np.ndarray,
        strike: np.ndarray,
        time_to_expiry: np.ndarray,
        risk_free_rate: np.ndarray,
        dividend_yield: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return vectorized discounted underlying and strike values.

        :param spot: Current underlying prices.
        :param strike: Option strike prices.
        :param time_to_expiry: Times to expiry in years.
        :param risk_free_rate: Continuously compounded risk-free rates.
        :param dividend_yield: Continuously compounded dividend yields.
        :returns: Tuple containing discounted spot and strike arrays.
        """

        discount_q, discount_r = OptionMetricsTransformer._discount_factors(
            time_to_expiry,
            risk_free_rate,
            dividend_yield,
        )
        return spot * discount_q, strike * discount_r

    @classmethod
    def _validate_columns(cls, options: pd.DataFrame) -> None:
        """Validate that input data contains required option fields.

        :param options: Candidate input DataFrame.
        :raises ValueError: If one or more required columns are missing.
        """

        missing_columns = sorted(cls.REQUIRED_COLUMNS - set(options.columns))
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
