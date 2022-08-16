# IndexBasedStatArb
                      ETF Arbitrage / Statistical Arbitrage 
                        based Automated Algorithmic Trading Program



      Project Description
                      
The goal of this project was to produce two main components:
1. A trading strategy that would prove to be profitable(disregarding level of profitability, due to the nature of the project being aimed toward personal educational purposes) in the South Korean stock market
2. A software environment that can support such a strategy(in both backtesting and real-time)


The trading strategy used in this project is based on Statistical Arbitrage/Pairs Trading, a method of trading that aims to capture "spreads" formed in the movement of financial products that should theoretically move in sync. 

Two financial products that are extremely similar, if not identical, in nature should theoretically always move in the same direction. However, this is not always the case due to various reasons including but not limited to: 
- people may favor one financial product over the other due to emotional reasons, causing a difference in the general supply/demand of each product
- companies that manage financial products do not always do so perfectly, which may cause "movement errors" in financial products, leading to an overall correct trajectory, but with small "bumps" at various points in time


When these financial products move out of sync, i.e. in differing directions, time to time as explained above, the relatively expensive product can be shorted(i.e. bet that the price will fall) while the relatively inexpensive product can be bought, with expectations of profit if its price rises. This way, since the two products price movements should converge at some point in time, if both prices fall, the shorted product will prove profitable, while if both prices rise, the simply bought product will prove profitable, theoretically providing a risk free way of trading.



The software environment was developed in Python, mainly using libraries Pandas, NumPy, and MatPlotLib to clean up then model and analyze numerical financial data procurred from brokerage companies in South Korea. 




      Project Organization
             
Within the src folder are two folders, Back-Test and Deploy

Back-Test contains code and data files to run a simulation of the trading strategy with historical data.
Deploy contains code that can be run in during market hours to deply the strategy in real-time.




CleanMinData.py   
- takes in raw data and cleans it

StatArb.py    
- the actual strategy

BackTesterMinData.py    
- runs StatArb.py on the historical prices of two ETPs

minDataUncleaned     
- raw data(price per minute)

minData   
- cleaned data(price per minute)

DataGather.py    
- code for gathering(and recording) real-time data

StatArb.py (Deploy)   
- code to deploy trading strategy in real-time


        
              
                
                  

      How to run this Project

Back-Test     
Running CleanMinData.py takes the csv data files in the uncleanedMinData folder and cleans the data. The cleaned data files are then saved into the minData folder.
The csv data files in the minData folder are used when running BackTesterMinData.py which runs the trading strategy, StatArb.py, printing out the results of the simulated run at the end.

Deploy  
DataGather.py - DataGather.py can be used independently by creating instances of the DataGather class, which would allow the user to simply gather real time data of the input financial product.
StatArb.py - StatArb.py within the Deploy folder contains the class StatArb the live trading program portion of this project. Executing the code in the file will deploy the trading strategy in real-time(assuming the account it is run under has sufficient cash).











