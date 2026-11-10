"""
Feature engineering module for network anomaly detection.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import LabelEncoder
import joblib

logger = logging.getLogger(__name__)

FEATURE_VERSION = "1.0.0"
CATEGORICAL_COLS = ["protocol", "status_clean"]
TARGET_COL = "label"
TARGET_MAP = {"benign": 0, "malicious": 1}
ANOMALY_TYPES = ["port_scan", "ddos", "brute_force", "data_exfil"]
ROLLING_WINDOWS = ["5min", "1H", "24H"]

META_COLS = {
    "timestamp", "event_timestamp", "src_ip", "dst_ip",
    "protocol", "status", "status_clean", "label",
    "anomaly_type", "target", "anomaly_type_target",
    "source_record_id", "composite_key", "prev_ts",
}


def create_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ts = df["event_timestamp"]
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = ts.dt.month
    df["day_of_month"] = ts.dt.day
    return df


def create_frequency_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["src_ip_freq"] = df["src_ip"].map(df["src_ip"].value_counts())
    df["dst_ip_freq"] = df["dst_ip"].map(df["dst_ip"].value_counts())
    df["port_freq"] = df["port"].map(df["port"].value_counts())
    df["protocol_freq"] = df["protocol"].map(df["protocol"].value_counts())
    return df


def create_rolling_features(df, windows=None, groupby_col="src_ip",
                            value_col="bytes_clean", time_col="event_timestamp"):
    if windows is None:
        windows = ROLLING_WINDOWS
    df = df.copy().sort_values([groupby_col, time_col]).reset_index(drop=True)
    for window in windows:
        if window.endswith("min"):
            period = pd.Timedelta(minutes=int(window[:-3]))
        elif window.endswith("H"):
            period = pd.Timedelta(hours=int(window[:-1]))
        else:
            continue
        suffix = window
        for stat in ["mean", "std", "min", "max", "count", "median"]:
            df[f"{value_col}_{stat}_{suffix}"] = np.nan
        for _, grp in df.groupby(groupby_col, sort=False):
            g = grp.set_index(time_col)[value_col].sort_index()
            rolled = g.rolling(window=period, closed="left")
            positions = grp.index.values
            df.loc[positions, f"{value_col}_mean_{suffix}"]   = rolled.mean().values
            df.loc[positions, f"{value_col}_std_{suffix}"]    = rolled.std().values
            df.loc[positions, f"{value_col}_min_{suffix}"]    = rolled.min().values
            df.loc[positions, f"{value_col}_max_{suffix}"]    = rolled.max().values
            df.loc[positions, f"{value_col}_count_{suffix}"]  = rolled.count().values
            df.loc[positions, f"{value_col}_median_{suffix}"] = rolled.median().values
    return df


# def create_connection_features(df: pd.DataFrame) -> pd.DataFrame:
#     df = df.copy().sort_values(["src_ip", "event_timestamp"]).reset_index(drop=True)
#     df["prev_ts"] = df.groupby("src_ip")["event_timestamp"].shift(1)
#     df["time_since_last_conn"] = (
#         df["event_timestamp"] - df["prev_ts"]
#     ).dt.total_seconds().fillna(-1)
#     df = df.drop(columns=["prev_ts"])
#     df["conn_count_cum"] = df.groupby("src_ip").cumcount() + 1
#     df["unique_ports_cum"] = df.groupby("src_ip")["port"].transform(
#         lambda x: x.expanding().apply(lambda s: s.nunique(), raw=False))
#     df["unique_dst_cum"] = df.groupby("src_ip")["dst_ip"].transform(
#         lambda x: x.expanding().apply(lambda s: s.nunique(), raw=False))
#     return df


def create_connection_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create connection-based behavioral features (string-safe)."""
    df = df.copy().sort_values(["src_ip", "event_timestamp"]).reset_index(drop=True)

    df["prev_ts"] = df.groupby("src_ip")["event_timestamp"].shift(1)
    df["time_since_last_conn"] = (
        df["event_timestamp"] - df["prev_ts"]
    ).dt.total_seconds().fillna(-1)
    df = df.drop(columns=["prev_ts"])

    df["conn_count_cum"] = df.groupby("src_ip").cumcount() + 1

    def expanding_nunique(series):
        """Cumulative count of unique values (works for any dtype)."""
        seen = set()
        out = []
        for v in series:
            seen.add(v)
            out.append(len(seen))
        return pd.Series(out, index=series.index)

    df["unique_ports_cum"] = df.groupby("src_ip")["port"].transform(expanding_nunique)
    df["unique_dst_cum"] = df.groupby("src_ip")["dst_ip"].transform(expanding_nunique)
    return df

def create_port_entropy_features(df: pd.DataFrame, window: str = "1H") -> pd.DataFrame:
    df = df.copy().sort_values(["src_ip", "event_timestamp"]).reset_index(drop=True)

    def entropy(ports):
        if len(ports) == 0:
            return 0.0
        vc = pd.Series(ports).value_counts(normalize=True)
        return float(-(vc * np.log2(vc)).sum())

    period = pd.Timedelta(hours=1)
    col = f"port_entropy_{window}"
    df[col] = 0.0

    for _, grp in df.groupby("src_ip", sort=False):
        g = grp.sort_values("event_timestamp")
        ts = g["event_timestamp"].values
        ports = g["port"].values
        orig_idx = g.index.values
        for i in range(1, len(g)):
            lo = ts[i] - np.timedelta64(int(period.total_seconds() * 1e9), "ns")
            mask = (ts[:i] >= lo) & (ts[:i] < ts[i])
            if mask.any():
                df.at[orig_idx[i], col] = entropy(ports[:i][mask])
    return df


def encode_categorical(df, cols=None, encoders=None, fit=False):
    if cols is None:
        cols = CATEGORICAL_COLS
    df = df.copy()
    encoders = encoders or {}
    for col in cols:
        if col not in df.columns:
            continue
        if fit or col not in encoders:
            le = LabelEncoder()
            values = df[col].fillna("UNKNOWN").astype(str).unique().tolist()
            if "UNKNOWN" not in values:
                values.append("UNKNOWN")
            le.fit(values)
            encoders[col] = le
        le = encoders[col]
        mapping = {cls: i for i, cls in enumerate(le.classes_)}
        unknown_val = mapping.get("UNKNOWN", 0)
        df[f"{col}_encoded"] = (
            df[col].fillna("UNKNOWN").astype(str).map(mapping).fillna(unknown_val).astype(int))
    return df, encoders


def prepare_target(df: pd.DataFrame, target_col: str = TARGET_COL) -> pd.DataFrame:
    df = df.copy()
    if target_col in df.columns:
        df["target"] = df[target_col].map(TARGET_MAP).fillna(0).astype(int)
        if "anomaly_type" in df.columns:
            df["anomaly_type_target"] = df["anomaly_type"].map(
                {t: i for i, t in enumerate(ANOMALY_TYPES + ["benign"])}
            ).fillna(len(ANOMALY_TYPES)).astype(int)
    return df


def temporal_split(df, time_col="event_timestamp"):
    """Month-based split: Train=Jan-Aug, Val=Sep-Oct, Test=Nov-Dec 2024."""
    df = df.sort_values(time_col).reset_index(drop=True)
    ts = df[time_col]
    train_df = df[ts < pd.Timestamp("2024-09-01", tz="UTC")].copy()
    val_df = df[(ts >= pd.Timestamp("2024-09-01", tz="UTC")) &
                (ts < pd.Timestamp("2024-11-01", tz="UTC"))].copy()
    test_df = df[ts >= pd.Timestamp("2024-11-01", tz="UTC")].copy()
    if len(train_df) == 0 or len(val_df) == 0 or len(test_df) == 0:
        logger.warning("Month-based split empty; using percentage split.")
        n = len(df)
        train_df = df.iloc[: int(n * 0.70)].copy()
        val_df = df.iloc[int(n * 0.70): int(n * 0.85)].copy()
        test_df = df.iloc[int(n * 0.85):].copy()
    logger.info(f"Split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")
    return train_df, val_df, test_df


def select_model_features(df, exclude_cols=None):
    if exclude_cols is None:
        exclude_cols = META_COLS
    cols = []
    for col in df.columns:
        if col in exclude_cols:
            continue
        if df[col].dtype in ["object", "datetime64[ns, UTC]", "datetime64[ns]"]:
            continue
        cols.append(col)
    return cols


def build_feature_pipeline(clean_df, fit_encoders=True, encoders=None):
    logger.info("Starting feature engineering...")
    df = clean_df.copy()
    df = create_temporal_features(df)
    df = create_frequency_features(df)
    df = create_rolling_features(df)
    df = create_connection_features(df)
    df = create_port_entropy_features(df)
    df = prepare_target(df)
    df, encoders = encode_categorical(df, encoders=encoders, fit=fit_encoders)

    train_df, val_df, test_df = temporal_split(df)
    feature_cols = select_model_features(train_df)

    def split_xy(sdf):
        X = sdf[feature_cols].fillna(0).reset_index(drop=True)
        y = sdf["target"].reset_index(drop=True)
        return X, y

    X_train, y_train = split_xy(train_df)
    X_val, y_val = split_xy(val_df)
    X_test, y_test = split_xy(test_df)

    return {
        "X_train": X_train, "y_train": y_train,
        "X_val": X_val, "y_val": y_val,
        "X_test": X_test, "y_test": y_test,
        "train_df": train_df.reset_index(drop=True),
        "val_df": val_df.reset_index(drop=True),
        "test_df": test_df.reset_index(drop=True),
        "encoders": encoders,
        "feature_cols": feature_cols,
        "feature_version": FEATURE_VERSION,
    }


def save_features(output_dir: Path, feature_data: Dict):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for split in ["train", "val", "test"]:
        full_df = feature_data[f"{split}_df"].copy()
        if "target" not in full_df.columns:
            full_df["target"] = feature_data[f"y_{split}"].values
        full_df.to_parquet(output_dir / f"{split}.parquet", index=False)
        X = feature_data[f"X_{split}"].copy()
        X["target"] = feature_data[f"y_{split}"].values
        X.to_parquet(output_dir / f"{split}_features_only.parquet", index=False)
    joblib.dump(feature_data["encoders"], output_dir / "encoders.joblib")
    joblib.dump(feature_data["feature_cols"], output_dir / "feature_cols.joblib")
    schema = {
        "version": feature_data["feature_version"],
        "feature_columns": feature_data["feature_cols"],
        "categorical_features": CATEGORICAL_COLS,
        "target_column": "target",
        "target_mapping": TARGET_MAP,
        "anomaly_types": ANOMALY_TYPES,
    }
    with open(output_dir / "FEATURE_SCHEMA.json", "w") as f:
        json.dump(schema, f, indent=2)
    logger.info(f"Features saved to {output_dir}")
