"""
Data cleaning module for network anomaly analysis.
Provides reusable cleaning functions with configurable strategies.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import hashlib
import logging
from typing import Tuple, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

ALLOWED_TS_START = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
ALLOWED_TS_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")

REJECTION_REASONS = {
    "INVALID_TIMESTAMP": "Invalid timestamp format",
    "TIMESTAMP_OUT_OF_RANGE": "Timestamp outside allowed range",
    "MISSING_REQUIRED_FIELD": "Missing src_ip, dst_ip, or port",
    "INVALID_IP": "Invalid IP address format",
    "INVALID_PORT": "Port outside 1-65535 range",
    "NEGATIVE_BYTES": "Negative bytes value",
    "DUPLICATE_RECORD": "Duplicate by composite key",
}

@dataclass
class CleaningStats:
    """Statistics from cleaning process."""
    total_input: int
    total_clean: int
    total_quarantined: int
    rejection_counts: Dict[str, int]
    clean_ratio: float
    warnings: list

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of file for batch_id."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]

def validate_ip(ip: str) -> bool:
    """Validate IPv4 address format."""
    if not ip or pd.isna(ip):
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False

def validate_port(port) -> bool:
    """Validate port number."""
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (ValueError, TypeError):
        return False

def parse_timestamp(ts: str) -> pd.Timestamp:
    """Parse timestamp with multiple format attempts."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return pd.Timestamp(ts, tz="UTC")
        except (ValueError, TypeError):
            continue
    return pd.NaT

def clean_network_logs(
    df: pd.DataFrame,
    batch_id: str,
    bytes_impute_strategy: str = "median",
    bytes_impute_value: Optional[float] = None,
    drop_duplicates: bool = True,
    duplicate_subset: Optional[list] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, CleaningStats]:
    """
    Clean network logs and return (clean_df, quarantine_df, stats).

    Args:
        df: Raw dataframe from CSV
        batch_id: Unique batch identifier
        bytes_impute_strategy: "median", "mean", "zero", or "custom"
        bytes_impute_value: Custom value if strategy="custom"
        drop_duplicates: Whether to drop duplicates
        duplicate_subset: Columns for duplicate detection (default: timestamp, src_ip, dst_ip, port)

    Returns:
        Tuple of (clean_dataframe, quarantine_dataframe, cleaning_stats)
    """
    logger.info(f"Starting cleaning for batch {batch_id}, input rows: {len(df)}")

    df = df.copy()
    df["source_record_id"] = range(1, len(df) + 1)

    quarantine_rows = []
    clean_mask = pd.Series(True, index=df.index)

    # 1. Parse timestamps
    df["timestamp_parsed"] = df["timestamp"].apply(parse_timestamp)

    # Invalid timestamps
    invalid_ts_mask = df["timestamp_parsed"].isna()
    if invalid_ts_mask.any():
        for idx in df[invalid_ts_mask].index:
            quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "INVALID_TIMESTAMP"))
        clean_mask &= ~invalid_ts_mask

    # 2. Timestamp range check
    oob_mask = (df["timestamp_parsed"] < ALLOWED_TS_START) | (df["timestamp_parsed"] > ALLOWED_TS_END)
    if oob_mask.any():
        for idx in df[oob_mask].index:
            quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "TIMESTAMP_OUT_OF_RANGE"))
        clean_mask &= ~oob_mask

    # 3. Missing required fields
    missing_ip = df["src_ip"].isna() | (df["src_ip"] == "") | df["dst_ip"].isna() | (df["dst_ip"] == "")
    missing_port = df["port"].isna() | (df["port"] == "")
    missing_required = missing_ip | missing_port
    if missing_required.any():
        for idx in df[missing_required].index:
            quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "MISSING_REQUIRED_FIELD"))
        clean_mask &= ~missing_required

    # 4. Invalid IPs
    invalid_src_ip = ~df["src_ip"].apply(validate_ip)
    invalid_dst_ip = ~df["dst_ip"].apply(validate_ip)
    invalid_ip = invalid_src_ip | invalid_dst_ip
    if invalid_ip.any():
        for idx in df[invalid_ip].index:
            quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "INVALID_IP"))
        clean_mask &= ~invalid_ip

    # 5. Invalid ports
    invalid_port = ~df["port"].apply(validate_port)
    if invalid_port.any():
        for idx in df[invalid_port].index:
            quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "INVALID_PORT"))
        clean_mask &= ~invalid_port

    # 6. Negative bytes
    df["bytes_numeric"] = pd.to_numeric(df["bytes"], errors="coerce")
    neg_bytes = df["bytes_numeric"] < 0
    if neg_bytes.any():
        for idx in df[neg_bytes].index:
            quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "NEGATIVE_BYTES"))
        clean_mask &= ~neg_bytes

    # 7. Duplicates
    if drop_duplicates:
        subset = duplicate_subset or ["timestamp_parsed", "src_ip", "dst_ip", "port"]
        df["composite_key"] = df[subset].astype(str).agg("|".join, axis=1)
        dup_mask = df.duplicated(subset=["composite_key"], keep="first")
        if dup_mask.any():
            for idx in df[dup_mask].index:
                quarantine_rows.append(_make_quarantine_row(df, idx, batch_id, "DUPLICATE_RECORD"))
            clean_mask &= ~dup_mask

    # Build clean dataframe
    clean_df = df[clean_mask].copy()

    # Impute missing bytes
    valid_bytes = clean_df.loc[clean_df["bytes_numeric"] >= 0, "bytes_numeric"]
    if bytes_impute_strategy == "median":
        bytes_fill = valid_bytes.median() if len(valid_bytes) > 0 else 0
    elif bytes_impute_strategy == "mean":
        bytes_fill = valid_bytes.mean() if len(valid_bytes) > 0 else 0
    elif bytes_impute_strategy == "zero":
        bytes_fill = 0
    elif bytes_impute_strategy == "custom":
        bytes_fill = bytes_impute_value if bytes_impute_value is not None else 0
    else:
        bytes_fill = 0

    logger.info(f"Bytes imputation value ({bytes_impute_strategy}): {bytes_fill}")

    clean_df["bytes_clean"] = clean_df["bytes_numeric"].fillna(bytes_fill)
    clean_df.loc[clean_df["bytes_clean"] < 0, "bytes_clean"] = bytes_fill

    # Handle missing status
    clean_df["status_clean"] = clean_df["status"].fillna("UNKNOWN")
    clean_df.loc[clean_df["status_clean"] == "", "status_clean"] = "UNKNOWN"

    # Clean timestamp column
    clean_df["event_timestamp"] = clean_df["timestamp_parsed"]

    # Drop helper columns
    drop_cols = ["timestamp_parsed", "bytes_numeric", "source_record_id"]
    if "composite_key" in clean_df.columns:
        drop_cols.append("composite_key")
    clean_df = clean_df.drop(columns=drop_cols, errors="ignore")

    # Build quarantine dataframe
    quarantine_df = pd.DataFrame(quarantine_rows) if quarantine_rows else pd.DataFrame(
        columns=["batch_id", "source_record_id", "rejection_reason", "rejected_at", "original_record"]
    )

    # Statistics
    rejection_counts = quarantine_df["rejection_reason"].value_counts().to_dict() if len(quarantine_df) > 0 else {}
    stats = CleaningStats(
        total_input=len(df),
        total_clean=len(clean_df),
        total_quarantined=len(quarantine_df),
        rejection_counts=rejection_counts,
        clean_ratio=len(clean_df) / len(df) if len(df) > 0 else 0,
        warnings=[]
    )

    if stats.clean_ratio < 0.5:
        stats.warnings.append(f"Clean ratio below 50%: {stats.clean_ratio:.2%}")
        logger.warning(stats.warnings[-1])

    logger.info(f"Cleaning complete: {len(clean_df)} clean, {len(quarantine_df)} quarantined")
    return clean_df, quarantine_df, stats

def _make_quarantine_row(df: pd.DataFrame, idx: int, batch_id: str, reason: str) -> dict:
    """Create a quarantine row."""
    return {
        "batch_id": batch_id,
        "source_record_id": df.loc[idx, "source_record_id"],
        "rejection_reason": reason,
        "rejected_at": pd.Timestamp.now(tz="UTC"),
        "original_record": df.loc[idx].to_json(),
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = pd.read_csv("network_logs_dirty.csv")
    batch_id = compute_file_hash(Path("network_logs_dirty.csv"))
    clean, quarantine, stats = clean_network_logs(df, batch_id)
    print(f"Clean: {len(clean)}, Quarantine: {len(quarantine)}")
    print(f"Stats: {stats}")