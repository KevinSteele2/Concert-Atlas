import pandas as pd

from visualize_prices import plot_price_snapshot


def _sample_df():
    return pd.DataFrame(
        [
            {
                "event_id": "e1",
                "artist": "The Testers",
                "venue": "Test Arena",
                "city": "Austin",
                "event_date": pd.Timestamp("2026-10-01"),
                "price_min": 45.0,
                "price_max": 250.0,
                "snapshot_date": pd.Timestamp("2026-09-03T12:00:00Z"),
                "first_seen_date": pd.Timestamp("2026-09-03T12:00:00Z"),
            }
        ]
    )


def test_plot_creates_nonempty_png(tmp_path):
    output_path = tmp_path / "chart.png"

    plot_price_snapshot(_sample_df(), output_path=output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_empty_dataframe_does_not_crash_or_create_file(tmp_path):
    output_path = tmp_path / "chart.png"

    plot_price_snapshot(pd.DataFrame(columns=["event_id", "artist", "venue", "price_min", "price_max", "snapshot_date"]), output_path=output_path)

    assert not output_path.exists()
