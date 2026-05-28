import databento as db
import pandas as pd
from RollingContracts import ContinuousFuturesBuilder
from TimeFrames import TimeFrames
from SwingPoint import SwingPoint
from SMT import SMT

# test2 = SwingPoint("MNQ contracts/MNQZ_Nov_2025.csv")
# print(test2.DailyPartial("2025-11-19 9:59:00-05:00"))

test = SMT("jul")
print(test.M5SMT_high("2025-07-14 5:41:00-04:00"))

#for the trend class, need to input a dataframe that is just that time, so would be a
#data frame that is only overnight data, but would need to take the general dataframe
#and pull out only the data needed

#Also need to create micro cycle in the SMT class

