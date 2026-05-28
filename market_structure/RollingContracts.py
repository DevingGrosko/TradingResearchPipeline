import pandas as pd
from pathlib import Path
import databento as db

class ContinuousFuturesBuilder:
    def __init__(self, base_folder,old_contract_path,new_contract_path,outPutName,timestamp,extraAdjustment: float = 0.0):
        # Create folder only if it does not exist
        self.base_dir = Path(base_folder)
        self.base_dir.mkdir(exist_ok=True)

        self.df_old = db.read_dbn(old_contract_path).to_df()
        self.df_new = db.read_dbn(new_contract_path).to_df()

        self.roll_ts = pd.Timestamp(timestamp, tz="US/Eastern")

        # Convert to Eastern Time
        self.df_old = self.df_old.tz_convert("US/Eastern")
        self.df_new = self.df_new.tz_convert("US/Eastern")

        # Keep only what you actually care about
        self.cols = ["open", "high", "low", "close", "volume"]
        self.df_old = self.df_old[self.cols]
        self.df_new = self.df_new[self.cols]

        self.outPutName = outPutName
        self.extraAdjustment = extraAdjustment


    def build(self):
        self.build_continuous(
            df_old=self.df_old,
            df_new=self.df_new,
            roll_ts=self.roll_ts,
            output_name=self.outPutName
        )


    def _compute_adjustment(
        self,
        df_old: pd.DataFrame,
        df_new: pd.DataFrame,
        roll_ts: pd.Timestamp
    ) -> float:
        old_close = df_old.loc[roll_ts, "close"]
        new_close = df_new.loc[roll_ts, "close"]
        print(old_close)
        print(new_close)
        print(new_close - old_close)
        return new_close - old_close

    def apply_adjustment(
        self,
        df: pd.DataFrame,
        adjustment: float,
        extraAdjustment: float = 0.0
    ) -> pd.DataFrame:

        df_adj = df.copy()
        price_cols = ["open", "high", "low", "close"]
        df_adj[price_cols] = df_adj[price_cols] + adjustment + extraAdjustment
        return df_adj

    def build_continuous(
        self,
        df_old: pd.DataFrame,
        df_new: pd.DataFrame,
        roll_ts: pd.Timestamp,
        output_name: str
    ) -> pd.DataFrame:

        if roll_ts not in df_old.index:
            raise ValueError("Roll timestamp missing in OLD contract")

        if roll_ts not in df_new.index:
            raise ValueError("Roll timestamp missing in NEW contract")

        # Compute price adjustment
        adjustment = self._compute_adjustment(df_old, df_new, roll_ts)

        # Split data
        old_part = df_old[df_old.index < roll_ts]
        new_part = df_new[df_new.index >= roll_ts]

        # Adjust old contract
        old_adj = self.apply_adjustment(old_part, adjustment,self.extraAdjustment)

        # Merge into continuous contract
        continuous_df = pd.concat([old_adj, new_part]).sort_index()


        # Save result
        save_path = self.base_dir / f"{output_name}.csv"
        rollingContracts = self.base_dir / f"RollingContractsChange.txt"

        with open(rollingContracts, "a") as f:
            f.write(f"{output_name}\n{adjustment}\n")

        continuous_df.to_csv(save_path)

        return continuous_df

    def adjustNonRollingMonth(self,monthContract,monthName:str,contractIndex:str,adjustAmount:float):
        # builder.build()
        df_old = db.read_dbn(monthContract).to_df()
        # FOR ADJUSTING ONE MONTH
        df_old = df_old.tz_convert("US/Eastern")

        end = self.apply_adjustment(df_old, adjustAmount)

        save_path = f"{contractIndex} contracts/{monthName}.csv"
        end.to_csv(save_path)
