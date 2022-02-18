# IndexBasedStatArb
Statistical Arbitrage based automated algorithmic trading program


Within the src folder are two folders, Back-Test and Deploy

Back-Test contains code and data files to run a simulation of the trading strategy with historical data.
Deply contains code that can be run in during market hours to deply the strategy in real-time.

CleanMinData.py
takes in raw data and cleans it

StatArb.py
the actual strategy

BackTesterMinData.py
runs StatArb.py on the historical prices of two ETPs

minDataUncleaned
raw data(price per minute)
  
minData
cleaned data(price per minute)


Introduction
The goal of this project was to produce two main components:
1. A trading strategy that would prove to be profitable(regardless of how much) in the South Korean stock market
2. A software environment that can support such a strategy(in both backtesting and real time)

The trading strategy used in this project is based on Statistical Arbitrage/Pairs Trading, a method of trading that aims to capture "spreads" formed in the movement of financial products that should theoretically move in sync. 










