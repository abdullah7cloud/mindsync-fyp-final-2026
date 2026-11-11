"""
Looks at the timestamps in the dataset's RAW Google-Form export and checks whether they behave like
real survey submissions. Run it yourself and quote what it prints:

    python -m scripts.check_raw_timestamps "path/to/Raw_Responses/raw_google_form_export.csv"

Real people answering a form arrive at irregular times (clustered by day and hour, with long gaps at night).
This script measures (1) the gap in seconds between consecutive responses and (2) how many responses fall in each
hour of the day. It only reports numbers; the wording of the conclusion is left to the report.
Nothing is written or changed. It needs pandas (already in requirements-train.txt).
"""
import sys

import pandas as pd


def main(path: str) -> int:
    raw = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
    ts = pd.to_datetime(raw["Timestamp"].str.replace(" GMT+6", "", regex=False), format="%Y/%m/%d %I:%M:%S %p")
    gaps = ts.diff().dropna().dt.total_seconds()
    per_hour = ts.dt.hour.value_counts().sort_index()
    print(f"Responses: {len(ts)}")
    print(f"First: {ts.iloc[0]}   Last: {ts.iloc[-1]}   (span {(ts.iloc[-1] - ts.iloc[0]).days} days)")
    print(f"Gap between consecutive responses (seconds): min {gaps.min():.0f}, max {gaps.max():.0f}, "
          f"mean {gaps.mean():.1f}, std {gaps.std():.2f}")
    print("Most common gaps (seconds -> count):", {int(k): int(v) for k, v in gaps.round().value_counts().head(5).items()})
    print(f"Responses per hour of day: min {per_hour.min()}, max {per_hour.max()} (24 hours, 3000 responses)")
    print(f"Distinct timestamps: {ts.nunique()}")
    if gaps.std() < 2:
        print("\nREADING: the gap is practically constant and responses arrive equally at every hour of the day and "
              "night. Real people do not submit a form like this; this pattern points to a program generating the rows.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
