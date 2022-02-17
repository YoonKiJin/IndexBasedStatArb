import ctypes
import sys
import win32com.client

from datetime import datetime
import time
import csv
import pandas as pd
import numpy as np
import os


objTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')
orderObj = win32com.client.Dispatch('CpTrade.CpTd0311')  
objStockMst = win32com.client.Dispatch("DsCbo1.StockMst")
status = win32com.client.Dispatch('CpUtil.CpCybos')
cpBalance = win32com.client.Dispatch('CpTrade.CpTd6033')
cpCash = win32com.client.Dispatch('CpTrade.CpTdNew5331A')

class DataGather:

    def __init__(self, stockCode):

        self.stockCode = stockCode
    
        self.askPrice = 0
        self.bidPrice = 0

        self.askVol = 0
        self.bidVol = 0

        marketOpenTime = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        if datetime.now() < marketOpenTime:
            self.updateNewDay()

    def updateNewDay(self):

        filePath = "CurrDayData/" + self.stockCode + "curr.csv"
        fileExists = os.path.isfile(filePath)
        
        if fileExists == True:
            prevDayData = pd.read_csv("CurrDayData/" + self.stockCode + "curr.csv")
        else:
            prevDayData = pd.DataFrame(columns = ["Date", "Time", "AskPrice", "BidPrice", "AskVol", "BidVol"])

        prevDayData.to_csv("PrevDayData/" + self.stockCode + "prev.csv", index = False)

        currDayDataTemplate = pd.DataFrame(columns = ["Date", "Time", "AskPrice", "BidPrice", "AskVol", "BidVol"])

        currDayDataTemplate.to_csv("CurrDayData/" + self.stockCode + "curr.csv", index = False)

        try:
            self.askPrice = prevDayData["AskPrice"].iloc[-1]
        except:
            self.askPrice = 0


    def updateData(self):

        DataGather.checkConnectionWithCreon()

        DataGather.checkRemainingSignalCount()


        objStockMst.SetInputValue(0, self.stockCode) 
        objStockMst.BlockRequest()

        currentAskPrice = objStockMst.GetHeaderValue(16)
        currentBidPrice = objStockMst.GetHeaderValue(17)

        if currentAskPrice != 0:
            self.askPrice = currentAskPrice

        if currentBidPrice != 0:
            self.bidPrice = currentBidPrice  

        self.askVol = objStockMst.GetDataValue(2, 0)
        self.bidVol = objStockMst.GetDataValue(3, 0)

        self.recordData()    

    def recordData(self):

        hour = str(datetime.now().hour)
        minute = str(datetime.now().minute)
        second = str(datetime.now().second)
        time = hour + " " + minute + " " + second

        filePath = "CurrDayData/" + self.stockCode + "curr.csv"
        with open(filePath, 'a', newline="") as csvfile: 
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow([datetime.now().date(), time, self.askPrice, self.bidPrice, self.askVol, self.bidVol])


    def dayEndDataCalculations(self):

        prevDayData = pd.read_csv("PrevDayData/" + self.stockCode + "prev.csv")
        currDayData = pd.read_csv("CurrDayData/" + self.stockCode + "curr.csv")

        currAndPrevData = prevDayData.append(currDayData, ignore_index=True)


        currAndPrevData["PctChange"] = currAndPrevData["AskPrice"].pct_change(periods=1)
        currAndPrevData.loc[0, "PctChange"] = 0
        currAndPrevData["PctMvtSummed"] = np.cumsum(currAndPrevData["PctChange"])

        currAndPrevData.to_csv("TodayYesterdayData/" + self.stockCode + "both.csv", index = False)


        currDayData["PctChange"] = currDayData["AskPrice"].pct_change(periods=1)
        currDayData.loc[0, "PctChange"] = 0
        currDayData["PctMvtSummed"] = np.cumsum(currDayData["PctChange"])

        currDayData.to_csv("CurrDayData/" + self.stockCode + "curr.csv", index = False)


    @classmethod
    def checkConnectionWithCreon(cls): 

        # connection status check
        if status.IsConnect == 0:
            print("CREON PLUS not properly connected")
            sys.exit()

        # Program must be run as Administrator
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Program not run as Administrator")
            sys.ext()

        # objTrade must be initialized before placing trades - check if initialization is done properly
        if (objTrade.TradeInit(0) != 0):
            print("objTrade not initialized properly")
            sys.ext()

        print("Connection Secure")

    @classmethod
    def checkRemainingSignalCount(cls):
        if status.GetLimitRemainCount(0) <= 5 or status.GetLimitRemainCount(1) <= 5:
            print(status.GetLimitRemainCount(0), "Order Requests Left", status.GetLimitRemainCount(1), "Signal Requests Left")
            time.sleep(15)


if __name__ == '__main__': 

    DataGather.checkConnectionWithCreon()

    # kospi inv - main
    DataGather1   = DataGather(stockCode="A145670")
    DataGather2   = DataGather(stockCode="A252410")
    DataGather3   = DataGather(stockCode="Q530092")
    DataGather4   = DataGather(stockCode="Q500061")

    # kospi norm - main
    DataGather5   = DataGather(stockCode="Q530091")
    DataGather6   = DataGather(stockCode="Q550067")
    DataGather7   = DataGather(stockCode="Q570067")
    DataGather8   = DataGather(stockCode="Q500060")

    # kosdaq inv - main
    DataGather9   = DataGather(stockCode="Q530094")
    DataGather10  = DataGather(stockCode="Q500063")
    DataGather11  = DataGather(stockCode="A301410")

    # kosdaq norm - main
    DataGather12  = DataGather(stockCode="Q500062")
    DataGather13  = DataGather(stockCode="Q570068")
    DataGather14  = DataGather(stockCode="Q530093")

    marketOpenTime = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    marketCloseTime = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)

    while True:

        if datetime.now() > marketOpenTime:

            if datetime.now().second % 30 == 0:

                print(status.GetLimitRemainCount(0), "Order Requests Left", status.GetLimitRemainCount(1), "Signal Requests Left")
                
                start = time.time()

                DataGather1.updateData()
                DataGather2.updateData()
                DataGather3.updateData()
                DataGather4.updateData()
                DataGather5.updateData()
                DataGather6.updateData()
                DataGather7.updateData()
                DataGather8.updateData()
                DataGather9.updateData()
                DataGather10.updateData()
                DataGather11.updateData()
                DataGather12.updateData()
                DataGather13.updateData()
                DataGather14.updateData()

                end = time.time()

                print(status.GetLimitRemainCount(0), "Order Requests Left", status.GetLimitRemainCount(1), "Signal Requests Left")

                print("runtime", end - start)

                time.sleep(1)

        if datetime.now() > marketCloseTime:

            DataGather1.dayEndDataCalculations()
            DataGather2.dayEndDataCalculations()
            DataGather3.dayEndDataCalculations()
            DataGather4.dayEndDataCalculations()
            DataGather5.dayEndDataCalculations()
            DataGather6.dayEndDataCalculations()
            DataGather7.dayEndDataCalculations()
            DataGather8.dayEndDataCalculations()
            DataGather9.dayEndDataCalculations()
            DataGather10.dayEndDataCalculations()
            DataGather11.dayEndDataCalculations()
            DataGather12.dayEndDataCalculations()
            DataGather13.dayEndDataCalculations()
            DataGather14.dayEndDataCalculations()

            sys.exit()
