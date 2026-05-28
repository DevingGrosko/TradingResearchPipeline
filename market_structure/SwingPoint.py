from datetime import timedelta

import pandas as pd

from TimeFrames import TimeFrames

class SwingPoint:
    def __init__(self, month):
        self.month_data = pd.read_csv(
            month,
            parse_dates=["ts_event"],
            index_col="ts_event"
        )

        timeframe = TimeFrames(self.month_data)
        self.H6Chart = timeframe.H6Timeframe()
        self.H4Chart = timeframe.H4Timeframe()
        self.H1Chart = timeframe.H1Timeframe()
        self.M90Chart = timeframe.M90Timeframe()
        self.M15Chart = timeframe.M15Timeframe()
        self.M5Chart = timeframe.M5Timeframe()
        self.DailyChart = timeframe.DailyTimeframe()

    # def weeklyCycle(self, current_date):
    #     target_day = pd.to_datetime(current_date).date()
    #     current_rows = self.DailyChart[
    #         self.DailyChart.index.date == target_day
    #         ]
    #
    #     if current_rows.empty:
    #         return  False
    #
    #     current = current_rows.iloc[0]  # Series
    #     pos = self.DailyChart.index.get_loc(current.name)
    #
    #     prev_day = self.DailyChart.iloc[pos - 1] if pos > 0 else None
    #     next_day = (
    #         self.DailyChart.iloc[pos + 1]
    #         if pos < len(self.DailyChart) - 1
    #         else None
    #     )
    #     print("Current:")
    #     print(current)
    #     print("\nPrevious:")
    #     print(prev_day)
    #     print("\nNext:")
    #     print(next_day)
    #     return current,prev_day,next_day
    #
    # def M15SD(self,current_date):
    #     target_time = pd.to_datetime(current_date)
    #     if target_time.tzinfo is None:
    #         target_time = target_time.tz_localize(self.M15Chart.index.tz)
    #
    #     current_rows = self.M15Chart[
    #         self.M15Chart.index == target_time
    #         ]
    #
    #     if current_rows.empty:
    #         return False
    #
    #     current = current_rows.iloc[0]  # Series
    #     pos = self.M15Chart.index.get_loc(current.name)
    #
    #     prev_day = self.M15Chart.iloc[pos - 1] if pos > 0 else None
    #     next_day = (
    #         self.M15Chart.iloc[pos + 1]
    #         if pos < len(self.M15Chart) - 1
    #         else None
    #     )
    #     print("Current:")
    #     print(current)
    #     print("\nPrevious:")
    #     print(prev_day)
    #     print("\nNext:")
    #     print(next_day)
    #     return current, prev_day, next_day
    #
    # def M5SD(self,current_date):
    #     target_time = pd.to_datetime(current_date)
    #     if target_time.tzinfo is None:
    #         target_time = target_time.tz_localize(self.M5Chart.index.tz)
    #
    #     current_rows = self.M5Chart[
    #         self.M5Chart.index == target_time
    #         ]
    #
    #     if current_rows.empty:
    #         return False
    #
    #     current = current_rows.iloc[0]  # Series
    #     pos = self.M5Chart.index.get_loc(current.name)
    #
    #     prev_day = self.M5Chart.iloc[pos - 1] if pos > 0 else None
    #     next_day = (
    #         self.M5Chart.iloc[pos + 1]
    #         if pos < len(self.M5Chart) - 1
    #         else None
    #     )
    #     print("Current:")
    #     print(current)
    #     print("\nPrevious:")
    #     print(prev_day)
    #     print("\nNext:")
    #     print(next_day)
    #     return current, prev_day, next_day
    #
    # def M90SD(self,current_date):
    #     target_time = pd.to_datetime(current_date)
    #     if target_time.tzinfo is None:
    #         target_time = target_time.tz_localize(self.M90Chart.index.tz)
    #
    #     current_rows = self.M90Chart[
    #         self.M90Chart.index == target_time
    #         ]
    #
    #     if current_rows.empty:
    #         return False
    #
    #     current = current_rows.iloc[0]  # Series
    #     pos = self.M90Chart.index.get_loc(current.name)
    #
    #     prev_day = self.M90Chart.iloc[pos - 1] if pos > 0 else None
    #     next_day = (
    #         self.M90Chart.iloc[pos + 1]
    #         if pos < len(self.M90Chart) - 1
    #         else None
    #     )
    #     print("Current:")
    #     print(current)
    #     print("\nPrevious:")
    #     print(prev_day)
    #     print("\nNext:")
    #     print(next_day)
    #     return current, prev_day, next_day
    #
    # def H4SD(self,current_date):
    #     target_time = pd.to_datetime(current_date)
    #     if target_time.tzinfo is None:
    #         target_time = target_time.tz_localize(self.H4Chart.index.tz)
    #
    #     current_rows = self.H4Chart[
    #         self.H4Chart.index == target_time
    #         ]
    #
    #     if current_rows.empty:
    #         return False
    #
    #     current = current_rows.iloc[0]  # Series
    #     pos = self.H4Chart.index.get_loc(current.name)
    #
    #     prev_day = self.H4Chart.iloc[pos - 1] if pos > 0 else None
    #     next_day = (
    #         self.H4Chart.iloc[pos + 1]
    #         if pos < len(self.H4Chart) - 1
    #         else None
    #     )
    #     print("Current:")
    #     print(current)
    #     print("\nPrevious:")
    #     print(prev_day)
    #     print("\nNext:")
    #     print(next_day)
    #     return current, prev_day, next_day
    #
    # def H6SD(self,current_datetime):
    #     ts = pd.to_datetime(current_datetime)
    #
    #     if ts.tzinfo is None:
    #         ts = ts.tz_localize(self.month_data.index.tz)
    #
    #     # --- find current 6H block start (anchored at 18:00) ---
    #     anchor = ts.replace(hour=18, minute=0, second=0, microsecond=0)
    #     if ts.hour < 18:
    #         anchor -= pd.Timedelta(days=1)
    #
    #     delta_hours = int((ts - anchor).total_seconds() // 3600)
    #     block_start = anchor + pd.Timedelta(hours=(delta_hours // 6) * 6)
    #     prev_block_start = block_start - pd.Timedelta(hours=6)
    #
    #     # --- current partial 6H candle ---
    #     cur_df = self.month_data[
    #         (self.month_data.index >= block_start) &
    #         (self.month_data.index <= ts)
    #         ]
    #
    #     if cur_df.empty:
    #         return False
    #
    #     current = pd.Series({
    #         "open": cur_df["open"].iloc[0],
    #         "high": cur_df["high"].max(),
    #         "low": cur_df["low"].min(),
    #         "close": cur_df["close"].iloc[-1],
    #     }, name=ts)
    #
    #     # --- previous full 6H candle ---
    #     prev_df = self.month_data[
    #         (self.month_data.index >= prev_block_start) &
    #         (self.month_data.index < block_start)
    #         ]
    #
    #     prev_day = (
    #         pd.Series({
    #             "open": prev_df["open"].iloc[0],
    #             "high": prev_df["high"].max(),
    #             "low": prev_df["low"].min(),
    #             "close": prev_df["close"].iloc[-1],
    #         }, name=prev_block_start)
    #         if not prev_df.empty
    #         else None
    #     )
    #
    #     return current, prev_day, None
    #     # target_time = pd.to_datetime(current_date)
    #     # if target_time.tzinfo is None:
    #     #     target_time = target_time.tz_localize(self.H6Chart.index.tz)
    #     #
    #     # current_rows = self.H6Chart[
    #     #     self.H6Chart.index == target_time
    #     #     ]
    #     #
    #     # if current_rows.empty:
    #     #     return False
    #     #
    #     # current = current_rows.iloc[0]  # Series
    #     # pos = self.H6Chart.index.get_loc(current.name)
    #     #
    #     # prev_day = self.H6Chart.iloc[pos - 1] if pos > 0 else None
    #     # next_day = (
    #     #     self.H6Chart.iloc[pos + 1]
    #     #     if pos < len(self.H6Chart) - 1
    #     #     else None
    #     # )
    #     # print("Current:")
    #     # print(current)
    #     # print("\nPrevious:")
    #     # print(prev_day)
    #     # print("\nNext:")
    #     # print(next_day)
    #     # return current, prev_day, next_day
    #
    # def H1SD(self,current_date):
    #     target_time = pd.to_datetime(current_date)
    #     if target_time.tzinfo is None:
    #         target_time = target_time.tz_localize(self.H1Chart.index.tz)
    #
    #     current_rows = self.H1Chart[
    #         self.H1Chart.index == target_time
    #         ]
    #
    #     if current_rows.empty:
    #         return False
    #
    #     current = current_rows.iloc[0]  # Series
    #     pos = self.H1Chart.index.get_loc(current.name)
    #
    #     prev_day = self.H1Chart.iloc[pos - 1] if pos > 0 else None
    #     next_day = (
    #         self.H1Chart.iloc[pos + 1]
    #         if pos < len(self.H1Chart) - 1
    #         else None
    #     )
    #     print("Current:")
    #     print(current)
    #     print("\nPrevious:")
    #     print(prev_day)
    #     print("\nNext:")
    #     print(next_day)
    #     return current, prev_day, next_day

    def SwingHigh(self,current_date,function):
        current,prev_day,next_day = function(current_date)
        if current["high"] > prev_day["high"] and current["high"] > next_day["high"]:
            print("True")
            return True
        print("False")
        return False

    def SwingLow(self, current_date, function):
        current, prev_day, next_day = function(current_date)
        if current["low"] < prev_day["low"] and current["low"] < next_day["low"]:
            print("True")
            return True
        print("False")
        return False

    def HigherHigh(self,current_date,function):
        current, prev_day, next_day = function(current_date)
        if current["high"] > prev_day["high"]:
            print("Higher high")
            return True
        print("Lower high")
        return False

    def LowerLow(self,current_date,function):
        current, prev_day, next_day = function(current_date)
        if current["low"] < prev_day["low"]:
            print("Lower low")
            return True
        print("Higher low")
        return False

    def weeklyCycle(self, current_datetime):
        current_ts = pd.to_datetime(current_datetime)

        # Ensure timezone consistency
        if current_ts.tzinfo is None:
            current_ts = current_ts.tz_localize(self.month_data.index.tz)

        # Determine session start (18:00)
        session_start = current_ts.replace(
            hour=18, minute=0, second=0, microsecond=0
        )
        if current_ts.hour < 18:
            session_start -= pd.Timedelta(days=1)

        # Slice intraday data from session start → now
        intraday = self.month_data[
            (self.month_data.index >= session_start) &
            (self.month_data.index <= current_ts)
            ]

        if intraday.empty:
            return False

        # Build partial daily candle
        current = pd.Series({
            "open": intraday["open"].iloc[0],
            "high": intraday["high"].max(),
            "low": intraday["low"].min(),
            "close": intraday["close"].iloc[-1],
        }, name=current_ts)

        # Get previous full daily candle
        daily_idx = self.DailyChart.index
        prev_days = daily_idx[daily_idx < session_start]

        prev_day = (
            self.DailyChart.loc[prev_days[-1]]
            if len(prev_days) > 0
            else None
        )

        return current, prev_day, None

    def _BlockPartial(self, current_datetime, block_minutes):
        ts = pd.to_datetime(current_datetime)

        if ts.tzinfo is None:
            ts = ts.tz_localize(self.month_data.index.tz)

        # Anchor at 18:00
        anchor = ts.replace(hour=18, minute=0, second=0, microsecond=0)
        if ts.hour < 18:
            anchor -= pd.Timedelta(days=1)

        # Compute block boundaries
        delta_minutes = int((ts - anchor).total_seconds() // 60)
        block_start = anchor + pd.Timedelta(
            minutes=(delta_minutes // block_minutes) * block_minutes
        )
        prev_block_start = block_start - pd.Timedelta(minutes=block_minutes)

        # -------- current partial candle --------
        cur_df = self.month_data[
            (self.month_data.index >= block_start) &
            (self.month_data.index <= ts)
            ]

        if cur_df.empty:
            return False

        current = pd.Series({
            "open": cur_df["open"].iloc[0],
            "high": cur_df["high"].max(),
            "low": cur_df["low"].min(),
            "close": cur_df["close"].iloc[-1],
        }, name=ts)

        # -------- previous full candle --------
        prev_df = self.month_data[
            (self.month_data.index >= prev_block_start) &
            (self.month_data.index < block_start)
            ]

        prev_day = (
            pd.Series({
                "open": prev_df["open"].iloc[0],
                "high": prev_df["high"].max(),
                "low": prev_df["low"].min(),
                "close": prev_df["close"].iloc[-1],
            }, name=prev_block_start)
            if not prev_df.empty
            else None
        )

        return current, prev_day, None

    # ---------------------------------------------------------
    # Timeframe-specific wrappers
    # ---------------------------------------------------------
    def M5SD(self, current_datetime):
        return self._BlockPartial(current_datetime, 5)

    def M15SD(self, current_datetime):
        return self._BlockPartial(current_datetime, 15)

    def M90SD(self, current_datetime):
        return self._BlockPartial(current_datetime, 90)

    def H1SD(self, current_datetime):
        return self._BlockPartial(current_datetime, 60)

    def H4SD(self, current_datetime):
        return self._BlockPartial(current_datetime, 240)

    def H6SD(self, current_datetime):
        return self._BlockPartial(current_datetime, 360)

