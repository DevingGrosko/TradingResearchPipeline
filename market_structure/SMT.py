from pathlib import Path
from SwingPoint import SwingPoint
class SMT:
    def __init__(self, month: str):
        self.month = month.lower()[:3]

    def _get_month_file(self, symbol: str):
        folder = Path(f"{symbol} contracts")

        for file in folder.iterdir():
            if file.suffix == ".csv" and self.month in file.name.lower():
                return file

        raise FileNotFoundError(
            f"No CSV found for {symbol} in month {self.month}"
        )

    def ES_month_file(self):
        return self._get_month_file("ES")

    def MNQ_month_file(self):
        return self._get_month_file("MNQ")

    def YM_month_file(self):
        return self._get_month_file("YM")

    def _swing(self, month_file, date_time, attr, side):
        sp = SwingPoint(month_file)
        dataset = getattr(sp, attr)

        if side == "low":
            return sp.LowerLow(date_time, dataset)
        elif side == "high":
            return sp.HigherHigh(date_time, dataset)
        else:
            raise ValueError(f"Invalid side: {side}")

    def _SMT(self, attr, date_time, side):
        swings = [
            self._swing(self.MNQ_month_file(), date_time, attr, side),
            self._swing(self.ES_month_file(), date_time, attr, side),
            self._swing(self.YM_month_file(), date_time, attr, side),
        ]
        return not (swings[0] == swings[1] == swings[2])

    def weeklyCycleSMT_low(self, date_time):
        return self._SMT("weeklyCycle", date_time, "low")

    def dailyCycleSMT_low(self, date_time):
        return self._SMT("H6SD", date_time, "low")

    def H4SMT_low(self, date_time):
        return self._SMT("H4SD", date_time, "low")

    def H1SMT_low(self, date_time):
        return self._SMT("H1SD", date_time, "low")

    def M90SMT_low(self, date_time):
        return self._SMT("M90SD", date_time, "low")

    def M15SMT_low(self, date_time):
        return self._SMT("M15SD", date_time, "low")

    def M5SMT_low(self, date_time):
        return self._SMT("M5SD", date_time, "low")

    def weeklyCycleSMT_high(self, date_time):
        return self._SMT("weeklyCycle", date_time, "high")

    def dailyCycleSMT_high(self, date_time):
        return self._SMT("H6SD", date_time, "high")

    def H4SMT_high(self, date_time):
        return self._SMT("H4SD", date_time, "high")

    def H1SMT_high(self, date_time):
        return self._SMT("H1SD", date_time, "high")

    def M90SMT_high(self, date_time):
        return self._SMT("M90SD", date_time, "high")

    def M15SMT_high(self, date_time):
        return self._SMT("M15SD", date_time, "high")

    def M5SMT_high(self, date_time):
        return self._SMT("M5SD", date_time, "high")

