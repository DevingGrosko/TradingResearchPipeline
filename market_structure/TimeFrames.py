import pandas as pd
import numpy as np

class TimeFrames:
    def __init__(self, df:pd.DataFrame):
        self.dataFrame = df

    def H1Timeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts_plus_1h = ts + pd.Timedelta(hours=1)
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)

        rows = []
        i = 0
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)
        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_1h)
                & (self.dataFrame.index < lastDate)
                ]
            if not TempDataFrame.empty:
                max_val = TempDataFrame["high"].max()
                min_val = TempDataFrame["low"].min()
                open_val = TempDataFrame["open"].iloc[0]
                close_val = TempDataFrame["close"].iloc[-1]

                row = {
                    "ts_event": TempDataFrame.index[0],
                    "open": open_val,
                    "high": max_val,
                    "low": min_val,
                    "close": close_val
                }
                rows.append(row)
            ts = ts + pd.Timedelta(hours=1)
            ts_plus_1h = ts + pd.Timedelta(hours=1)
            i += 1

        htf_df = pd.DataFrame(rows).set_index("ts_event")
        return htf_df

    def H4Timeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)

        ts_plus_1h = ts + pd.Timedelta(hours=4)

        rows = []
        i = 0
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)
        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_1h)
                & (self.dataFrame.index < lastDate)
                ]
            if not TempDataFrame.empty:
                max_val = TempDataFrame["high"].max()
                min_val = TempDataFrame["low"].min()
                open_val = TempDataFrame["open"].iloc[0]
                close_val = TempDataFrame["close"].iloc[-1]

                row = {
                    "ts_event": TempDataFrame.index[0],
                    "open": open_val,
                    "high": max_val,
                    "low": min_val,
                    "close": close_val
                }
                rows.append(row)
            ts = ts + pd.Timedelta(hours=4)
            ts_plus_1h = ts + pd.Timedelta(hours=4)
            i += 1

        htf_df = pd.DataFrame(rows).set_index("ts_event")
        return htf_df

    def H6Timeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)

        ts_plus_1h = ts + pd.Timedelta(hours=6)
        rows = []
        i = 0
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)
        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_1h)
                & (self.dataFrame.index < lastDate)
                ]
            if not TempDataFrame.empty:
                max_val = TempDataFrame["high"].max()
                min_val = TempDataFrame["low"].min()
                open_val = TempDataFrame["open"].iloc[0]
                close_val = TempDataFrame["close"].iloc[-1]

                row = {
                    "ts_event": TempDataFrame.index[0],
                    "open": open_val,
                    "high": max_val,
                    "low": min_val,
                    "close": close_val
                }
                rows.append(row)
            ts = ts + pd.Timedelta(hours=6)
            ts_plus_1h = ts + pd.Timedelta(hours=6)
            i += 1

        htf_df = pd.DataFrame(rows).set_index("ts_event")
        return htf_df

    def M15Timeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts_plus_15m = ts + pd.Timedelta(minutes=15)
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)

        rows = []
        i = 0
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)
        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_15m)
                & (self.dataFrame.index < lastDate)
                ]
            if not TempDataFrame.empty:
                max_val = TempDataFrame["high"].max()
                min_val = TempDataFrame["low"].min()
                open_val = TempDataFrame["open"].iloc[0]
                close_val = TempDataFrame["close"].iloc[-1]

                row = {
                    "ts_event": TempDataFrame.index[0],
                    "open": open_val,
                    "high": max_val,
                    "low": min_val,
                    "close": close_val
                }
                rows.append(row)
            ts = ts + pd.Timedelta(minutes=15)
            ts_plus_15m = ts + pd.Timedelta(minutes=15)
            i += 1

        htf_df = pd.DataFrame(rows).set_index("ts_event")
        return htf_df

    def M5Timeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)
        ts_plus_5m = ts + pd.Timedelta(minutes=5)
        rows = []
        i = 0
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)
        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_5m)
                & (self.dataFrame.index < lastDate)
                ]
            if not TempDataFrame.empty:
                max_val = TempDataFrame["high"].max()
                min_val = TempDataFrame["low"].min()
                open_val = TempDataFrame["open"].iloc[0]
                close_val = TempDataFrame["close"].iloc[-1]

                row = {
                    "ts_event": TempDataFrame.index[0],
                    "open": open_val,
                    "high": max_val,
                    "low": min_val,
                    "close": close_val
                }
                rows.append(row)
            ts = ts + pd.Timedelta(minutes=5)
            ts_plus_5m = ts + pd.Timedelta(minutes=5)
            i += 1

        htf_df = pd.DataFrame(rows).set_index("ts_event")
        return htf_df

    def M90Timeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)
        ts_plus_90m = ts + pd.Timedelta(minutes=90)
        rows = []
        i = 0
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)
        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_90m)
                & (self.dataFrame.index < lastDate)
                ]
            if not TempDataFrame.empty:
                max_val = TempDataFrame["high"].max()
                min_val = TempDataFrame["low"].min()
                open_val = TempDataFrame["open"].iloc[0]
                close_val = TempDataFrame["close"].iloc[-1]

                row = {
                    "ts_event": TempDataFrame.index[0],
                    "open": open_val,
                    "high": max_val,
                    "low": min_val,
                    "close": close_val
                }
                rows.append(row)
            ts = ts + pd.Timedelta(minutes=90)
            ts_plus_90m = ts + pd.Timedelta(minutes=90)
            i += 1

        htf_df = pd.DataFrame(rows).set_index("ts_event")
        return htf_df

    def DailyTimeframe(self) -> pd.DataFrame:
        ts = self.dataFrame.index[0]
        ts = ts.replace(hour=18, minute=0, second=0, microsecond=0)
        ts_plus_1D = ts + pd.Timedelta(days=1)
        lastDate = self.dataFrame.index[-1]
        lastDate = lastDate.replace(hour=18, minute=0, second=0, microsecond=0)

        rows = []

        while ts < self.dataFrame.index[-1]:
            TempDataFrame = self.dataFrame[
                (self.dataFrame.index >= ts) &
                (self.dataFrame.index < ts_plus_1D)
                & (self.dataFrame.index < lastDate)
                ]

            if not TempDataFrame.empty:
                row = {
                    "ts_event": TempDataFrame.index[-1],  # FIX
                    "open": TempDataFrame["open"].iloc[0],
                    "high": TempDataFrame["high"].max(),
                    "low": TempDataFrame["low"].min(),
                    "close": TempDataFrame["close"].iloc[-1],
                }
                rows.append(row)

            ts = ts_plus_1D
            ts_plus_1D = ts + pd.Timedelta(days=1)

        return pd.DataFrame(rows).set_index("ts_event")

