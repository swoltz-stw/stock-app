import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# =========================
# Data + Feature Functions (NO RSI)
# =========================

def get_price_history(ticker: str, lookback_years: int = 3) -> pd.DataFrame:
    """Download historical daily OHLC data for a ticker using yfinance."""
    end = datetime.today()
    start = end - timedelta(days=365 * lookback_years)
    data = yf.download(ticker, start=start, end=end)

    # 🔧 IMPORTANT: handle duplicate/multi-level columns (e.g., multiple "Close")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(-1)

    data = data.loc[:, ~data.columns.duplicated()]
    data.dropna(inplace=True)
    return data


def build_features(data: pd.DataFrame):
    """Build feature set and target for the ML model.
    Target: 1 if next day's close > today's close, else 0.
    """
    df = data.copy()

    # 🔧 Ensure "Close" is a single Series (not a DataFrame)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    df["Close"] = close

    # Daily returns
    df["ret_1d"] = df["Close"].pct_change(1)
    df["ret_3d"] = df["Close"].pct_change(3)
    df["ret_5d"] = df["Close"].pct_change(5)

    # Moving averages
    df["SMA_10"] = df["Close"].rolling(window=10).mean()
    df["SMA_30"] = df["Close"].rolling(window=30).mean()
    df["SMA_ratio_10_30"] = df["SMA_10"] / (df["SMA_30"] + 1e-9)

    # Rolling volatility
    df["vol_10d"] = df["ret_1d"].rolling(window=10).std()
    df["vol_60d"] = df["ret_1d"].rolling(window=60).std()

    # 52-week high drawdown
    window_52w = 252
    df["52w_high"] = df["Close"].rolling(window=window_52w).max()

    dd = (df["Close"] - df["52w_high"]) / (df["52w_high"] + 1e-9)
    # 🔧 If dd somehow ends up as DataFrame, reduce to first column
    if isinstance(dd, pd.DataFrame):
        dd = dd.iloc[:, 0]
    df["dd_52w"] = dd

    # Target: 1 if next day's close > today's close, else 0
    df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    # Drop rows with NaNs (from rolling / shift)
    df.dropna(inplace=True)

    feature_cols = [
        "ret_1d", "ret_3d", "ret_5d",
        "SMA_10", "SMA_30", "SMA_ratio_10_30",
        "vol_10d", "vol_60d", "dd_52w"
    ]

    X = df[feature_cols]
    y = df["target"]

    return df, X, y, feature_cols


# =========================
# Fundamental Factor Scoring
# =========================

def safe_get(info: dict, key: str, default=None):
    """Safe dictionary access for yfinance .info."""
    try:
        value = info.get(key, default)
        if value is None:
            return default
        if isinstance(value, float) and np.isnan(value):
            return default
        return value
    except Exception:
        return default


def score_pe(pe: float) -> float:
    if pe is None or pe <= 0:
        return 50.0
    if pe < 10:
        return 90.0
    if pe < 20:
        return 80.0
    if pe < 30:
        return 65.0
    if pe < 50:
        return 50.0
    if pe < 80:
        return 40.0
    return 30.0


def score_margin(margin: float) -> float:
    if margin is None:
        return 50.0
    margin = max(min(margin, 0.4), -0.4)
    return (margin + 0.4) / 0.8 * 100.0


def score_growth(growth: float) -> float:
    if growth is None:
        return 50.0
    growth = max(min(growth, 0.5), -0.5)
    return (growth + 0.5) / 1.0 * 100.0


def score_debt_to_equity(de: float) -> float:
    if de is None or de < 0:
        return 50.0
    if de < 0.5:
        return 85.0
    if de < 1.0:
        return 75.0
    if de < 2.0:
        return 60.0
    if de < 3.0:
        return 45.0
    return 30.0


def score_roe(roe: float) -> float:
    if roe is None:
        return 50.0
    roe = max(min(roe, 0.3), -0.1)
    return (roe + 0.1) / 0.4 * 100.0


def score_roa(roa: float) -> float:
    if roa is None:
        return 50.0
    roa = max(min(roa, 0.2), -0.05)
    return (roa + 0.05) / 0.25 * 100.0


def score_dividend_yield(dy: float) -> float:
    if dy is None or dy < 0:
        return 50.0
    if dy < 0.01:
        return 40.0
    if dy < 0.05:
        return 85.0
    if dy < 0.10:
        return 60.0
    return 40.0


def score_payout_ratio(pr: float) -> float:
    if pr is None or pr < 0:
        return 50.0
    if pr < 0.2:
        return 60.0
    if pr < 0.6:
        return 85.0
    if pr < 1.0:
        return 50.0
    return 40.0


def get_fundamental_factor_scores(ticker: str):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
    except Exception:
        info = {}

    trailing_pe = safe_get(info, "trailingPE")
    forward_pe = safe_get(info, "forwardPE")
    profit_margin = safe_get(info, "profitMargins")
    revenue_growth = safe_get(info, "revenueGrowth")
    debt_to_equity = safe_get(info, "debtToEquity")
    roe = safe_get(info, "returnOnEquity")
    roa = safe_get(info, "returnOnAssets")
    dividend_yield = safe_get(info, "dividendYield")
    payout_ratio = safe_get(info, "payoutRatio")

    free_cashflow = safe_get(info, "freeCashflow")
    total_revenue = safe_get(info, "totalRevenue")
    if free_cashflow is not None and total_revenue:
        fcf_margin = free_cashflow / total_revenue
    else:
        fcf_margin = None

    factors = {}

    factors["trailingPE"] = {"raw": trailing_pe, "score": score_pe(trailing_pe)}
    factors["forwardPE"] = {"raw": forward_pe, "score": score_pe(forward_pe)}
    factors["profitMargins"] = {"raw": profit_margin, "score": score_margin(profit_margin)}
    factors["revenueGrowth"] = {"raw": revenue_growth, "score": score_growth(revenue_growth)}
    factors["debtToEquity"] = {"raw": debt_to_equity, "score": score_debt_to_equity(debt_to_equity)}
    factors["ROE"] = {"raw": roe, "score": score_roe(roe)}
    factors["ROA"] = {"raw": roa, "score": score_roa(roa)}
    factors["FCF_margin"] = {"raw": fcf_margin, "score": score_margin(fcf_margin)}
    factors["dividendYield"] = {"raw": dividend_yield, "score": score_dividend_yield(dividend_yield)}
    factors["payoutRatio"] = {"raw": payout_ratio, "score": score_payout_ratio(payout_ratio)}

    valid_scores = [d["score"] for d in factors.values() if d["score"] is not None]
    fundamental_score = float(np.mean(valid_scores)) if valid_scores else 50.0

    return fundamental_score, factors


# =========================
# Technical Factor Scoring
# =========================

def score_return(r: float) -> float:
    if r is None or np.isnan(r):
        return 50.0
    r = max(min(r, 0.1), -0.1)
    return (r + 0.1) / 0.2 * 100.0


def score_vol(vol: float, low: float = 0.005, high: float = 0.05) -> float:
    if vol is None or np.isnan(vol):
        return 50.0
    vol = max(min(vol, high), low)
    return (high - vol) / (high - low) * 100.0


def score_sma_ratio(ratio: float) -> float:
    if ratio is None or np.isnan(ratio):
        return 50.0
    ratio = max(min(ratio, 1.2), 0.8)
    return (ratio - 0.8) / 0.4 * 100.0


def score_drawdown(dd: float) -> float:
    if dd is None or np.isnan(dd):
        return 50.0
    dd = max(min(dd, 0.0), -0.8)
    return (abs(dd) / 0.8) * 100.0


def get_technical_factor_scores(df: pd.DataFrame):
    latest = df.iloc[-1]

    factors = {}
    factors["ret_1d"] = {"raw": latest["ret_1d"], "score": score_return(latest["ret_1d"])}
    factors["ret_3d"] = {"raw": latest["ret_3d"], "score": score_return(latest["ret_3d"])}
    factors["ret_5d"] = {"raw": latest["ret_5d"], "score": score_return(latest["ret_5d"])}
    factors["SMA_10"] = {"raw": latest["SMA_10"], "score": 50.0}
    factors["SMA_30"] = {"raw": latest["SMA_30"], "score": 50.0}
    factors["SMA_ratio_10_30"] = {
        "raw": latest["SMA_ratio_10_30"],
        "score": score_sma_ratio(latest["SMA_ratio_10_30"]),
    }
    factors["vol_10d"] = {"raw": latest["vol_10d"], "score": score_vol(latest["vol_10d"])}
    factors["vol_60d"] = {"raw": latest["vol_60d"], "score": score_vol(latest["vol_60d"])}
    factors["dd_52w"] = {"raw": latest["dd_52w"], "score": score_drawdown(latest["dd_52w"])}

    valid_scores = [d["score"] for d in factors.values() if d["score"] is not None]
    technical_score = float(np.mean(valid_scores)) if valid_scores else 50.0

    return technical_score, factors


# =========================
# Macro / Context Factor Scoring
# =========================

SECTOR_ETF_MAP = {
    "Information Technology": "XLK",
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Healthcare": "XLV",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Materials": "XLB",
    "Communication Services": "XLC",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}


def score_market_regime(spy_ratio: float) -> float:
    if spy_ratio is None or np.isnan(spy_ratio):
        return 50.0
    spy_ratio = max(min(spy_ratio, 1.2), 0.8)
    return (spy_ratio - 0.8) / 0.4 * 100.0


def score_sector_relative(rel: float) -> float:
    if rel is None or np.isnan(rel):
        return 50.0
    rel = max(min(rel, 0.1), -0.1)
    return (rel + 0.1) / 0.2 * 100.0


def score_vol_regime(vix_level: float) -> float:
    if vix_level is None or np.isnan(vix_level):
        return 50.0
    vix_level = max(min(vix_level, 40.0), 10.0)
    return (40.0 - vix_level) / 30.0 * 100.0


def get_macro_factor_scores(ticker: str):
    spy_data = get_price_history("SPY", lookback_years=1)
    spy_data["SMA_50"] = spy_data["Close"].rolling(window=50).mean()
    spy_data["SMA_200"] = spy_data["Close"].rolling(window=200).mean()
    spy_data.dropna(inplace=True)
    if not spy_data.empty:
        latest_spy = spy_data.iloc[-1]
        spy_ratio = latest_spy["SMA_50"] / (latest_spy["SMA_200"] + 1e-9)
    else:
        spy_ratio = None

    try:
        sector = yf.Ticker(ticker).info.get("sector", None)
    except Exception:
        sector = None
    sector_etf = SECTOR_ETF_MAP.get(sector, "SPY")

    lookback_days = 60
    sector_data = yf.download(sector_etf, period=f"{lookback_days}d")
    spy_short = yf.download("SPY", period=f"{lookback_days}d")

    if not sector_data.empty and not spy_short.empty:
        sector_ret_1m = sector_data["Close"].iloc[-1] / sector_data["Close"].iloc[0] - 1
        spy_ret_1m = spy_short["Close"].iloc[-1] / spy_short["Close"].iloc[0] - 1
        rel_strength = sector_ret_1m - spy_ret_1m
    else:
        rel_strength = None

    vix_data = yf.download("^VIX", period="60d")
    if not vix_data.empty:
        vix_level = float(vix_data["Close"].iloc[-1])
    else:
        vix_level = None

    factors = {}
    factors["market_regime_SPY_50_200"] = {
        "raw": spy_ratio,
        "score": score_market_regime(spy_ratio),
    }
    factors["sector_relative_strength"] = {
        "raw": rel_strength,
        "score": score_sector_relative(rel_strength),
    }
    factors["volatility_regime_VIX"] = {
        "raw": vix_level,
        "score": score_vol_regime(vix_level),
    }

    valid_scores = [d["score"] for d in factors.values() if d["score"] is not None]
    macro_score = float(np.mean(valid_scores)) if valid_scores else 50.0

    return macro_score, factors


# =========================
# ML Training (reference)
# =========================

def train_model(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=5,
        random_state=random_state,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_test_1d = np.ravel(y_test)
    y_pred_1d = np.ravel(y_pred)

    acc = accuracy_score(y_test_1d, y_pred_1d)

    proba_test = model.predict_proba(X_test)[:, 1]
    proba_test_1d = np.ravel(proba_test)

    brier = float(np.mean((proba_test_1d - y_test_1d) ** 2))

    return model, acc, brier


def predict_next_day(model, X: pd.DataFrame):
    latest_features = X.iloc[[-1]]
    proba = model.predict_proba(latest_features)[0]

    p_down, p_up = proba[0], proba[1]
    direction = "UP" if p_up >= p_down else "DOWN"
    confidence = max(p_up, p_down)

    return direction, confidence, p_up, p_down


# =========================
# Streamlit App
# =========================

def main():
    st.set_page_config(page_title="Hybrid Stock Predictor (No RSI)", page_icon="📈")
    st.title("Hybrid Stock Predictor (ML + Fundamentals + Macro)")

    st.sidebar.header("Configuration")

    default_ticker = "SPY"
    ticker = st.sidebar.text_input("Ticker symbol", value=default_ticker).upper()

    lookback_years = st.sidebar.slider(
        "Years of history to use (for training)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Number of past years of daily data to pull for model training."
    )

    test_size = st.sidebar.slider(
        "Test size (for backtest split)",
        min_value=0.1,
        max_value=0.5,
        value=0.2,
        step=0.05,
        help="Fraction of the most recent data used as a hold-out test set."
    )

    show_category_summary = st.sidebar.checkbox("Summarize by category", value=True)
    show_factor_details = st.sidebar.checkbox("Show individual factor scores", value=False)

    if st.sidebar.button("Run Prediction"):
        if not ticker:
            st.error("Please enter a ticker symbol.")
            return

        with st.spinner(f"Fetching data and computing scores for {ticker}..."):
            try:
                data = get_price_history(ticker, lookback_years=lookback_years)
                if data.empty:
                    st.error("No data returned. Please check the ticker symbol.")
                    return

                df, X, y, feature_cols = build_features(data)

                if len(df) < 150:
                    st.warning(
                        "Not much historical data available after feature engineering. "
                        "Predictions and calibration may be less reliable."
                    )

                model, acc, brier = train_model(X, y, test_size=test_size)
                direction_ml, confidence_ml, p_up, p_down = predict_next_day(model, X)

                technical_score, tech_factors = get_technical_factor_scores(df)
                fundamental_score, fund_factors = get_fundamental_factor_scores(ticker)
                macro_score, macro_factors = get_macro_factor_scores(ticker)

                final_factor_score = (
                    0.4 * technical_score
                    + 0.4 * fundamental_score
                    + 0.2 * macro_score
                )
                final_factor_score = float(np.clip(final_factor_score, 0.0, 100.0))

                direction_final = "UP" if final_factor_score > 50.0 else "DOWN"
                distance_from_50 = abs(final_factor_score - 50.0) / 50.0
                confidence_pct = float(np.clip(distance_from_50 * 100.0, 0.0, 100.0))

                latest_row = df.iloc[-1]
                last_date = latest_row.name.date()
                last_close = float(latest_row["Close"])

                factor_rows = []
                for name, d in tech_factors.items():
                    factor_rows.append({
                        "factor": name,
                        "category": "Technical",
                        "raw_value": d["raw"],
                        "score_0_100": d["score"],
                    })
                for name, d in fund_factors.items():
                    factor_rows.append({
                        "factor": name,
                        "category": "Fundamental",
                        "raw_value": d["raw"],
                        "score_0_100": d["score"],
                    })
                for name, d in macro_factors.items():
                    factor_rows.append({
                        "factor": name,
                        "category": "Macro",
                        "raw_value": d["raw"],
                        "score_0_100": d["score"],
                    })

                factors_df = pd.DataFrame(factor_rows)

                category_rows = [
                    {
                        "category": "Technical",
                        "score": technical_score,
                        "weight": 0.4,
                        "weighted_contribution": 0.4 * technical_score,
                    },
                    {
                        "category": "Fundamental",
                        "score": fundamental_score,
                        "weight": 0.4,
                        "weighted_contribution": 0.4 * fundamental_score,
                    },
                    {
                        "category": "Macro",
                        "score": macro_score,
                        "weight": 0.2,
                        "weighted_contribution": 0.2 * macro_score,
                    },
                ]
                category_df = pd.DataFrame(category_rows)
                category_df.loc["Total", "category"] = "Total"
                category_df.loc["Total", "score"] = None
                category_df.loc["Total", "weight"] = 1.0
                category_df.loc["Total", "weighted_contribution"] = (
                    0.4 * technical_score + 0.4 * fundamental_score + 0.2 * macro_score
                )

            except Exception as e:
                import traceback
                st.error(f"Something went wrong: {e}")
                st.code(traceback.format_exc())
                return

        st.subheader(f"Results for {ticker}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Last close date", str(last_date))
            st.metric("Last close price", f"${last_close:,.2f}")
        with col2:
            st.metric("Final factor score (1–100)", f"{final_factor_score:.1f}")
            st.metric("Predicted direction (1-day)", direction_final)
        with col3:
            st.metric("Confidence % (factor-based)", f"{confidence_pct:.1f}%")
            st.metric("ML backtest accuracy", f"{acc:.3f}")

        st.markdown("---")
        st.subheader("ML Probability (reference)")
        st.write(f"P(UP) from ML model: `{p_up * 100:.1f}%`")
        st.write(f"P(DOWN) from ML model: `{p_down * 100:.1f}%`")

        if show_category_summary:
            st.markdown("### Category scores (Technical / Fundamental / Macro)")
            st.dataframe(category_df)

        if show_factor_details:
            st.markdown("### Individual factor scores (0–100)")
            st.dataframe(factors_df)

        st.markdown("---")
        st.subheader("Price History (Close)")
        price_to_show = pd.DataFrame({"Close": list(df["Close"].astype(float))})
        st.line_chart(price_to_show)

        st.subheader("Recent Features Snapshot (Last 10 Days)")
        st.dataframe(df[feature_cols + ["target"]].tail(10))

        st.markdown("---")
        st.subheader("Export Prediction Summary")
        summary_row = {
            "ticker": ticker,
            "last_date": last_date,
            "last_close": last_close,
            "final_factor_score_1d": final_factor_score,
            "direction_1d": direction_final,
            "confidence_pct_factor": confidence_pct,
            "technical_score": technical_score,
            "fundamental_score": fundamental_score,
            "macro_score": macro_score,
            "ml_p_up_1d": p_up,
            "ml_p_down_1d": p_down,
            "ml_backtest_accuracy": acc,
            "ml_brier_score": brier,
        }
        summary_df = pd.DataFrame([summary_row])
        csv_bytes = summary_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download 1-day factor prediction as CSV",
            data=csv_bytes,
            file_name=f"{ticker}_factor_prediction_1d.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
