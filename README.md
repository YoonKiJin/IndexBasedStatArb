# IndexBasedStatArb
Statistical Arbitrage based automated algorithmic trading program



To explain the structure of the project early on:
CleanMinData.py
  takes in raw data and 

StatArb.py


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










