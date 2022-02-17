import os
import pandas as pd
from matplotlib import pyplot as plt

import StatArb


class Stock:

    def __init__(self, stockCode, minDataDf):
        self.stockCode = stockCode
        self.minData = minDataDf



class BackTester:

    def __init__(self, initialCash, invCode, normCode, startDate="", endDate=""):
        self.startDate = startDate
        self.endDate = endDate

        self.invCode = invCode
        self.normCode = normCode

        self.invAsset = None
        self.normAsset = None

        self.stockPair = []
        self.getStockObjects()


        self.currentCash = initialCash

        self.initialCash = initialCash

        self.returnAsCash = 0
        self.returnAsPercent = 0

    def getStockObjects(self):
        csvDataFilesFolderName = "minData"
        csvFileNames = list(os.listdir(csvDataFilesFolderName))
        for fileName in csvFileNames:
            if self.invCode in fileName:
                stockCode = fileName[0:7]
                minDataDf = self.getStockMinDataDf(stockCode)
                self.invAsset = Stock(stockCode, minDataDf)
            if self.normCode in fileName:
                stockCode = fileName[0:7]
                minDataDf = self.getStockMinDataDf(stockCode)
                self.normAsset = Stock(stockCode, minDataDf)

    def getStockMinDataDf(self, stockCode):
        minDataDf = pd.read_csv("minData/" + str(stockCode) + ".csv")
        minDataDf["Date"] = pd.to_datetime(minDataDf["Date"], format="%Y-%m-%d")

        if self.startDate != "":
            minDataDf = self.addTimeFilterToMinDataDf(minDataDf)

        return minDataDf

    def addTimeFilterToMinDataDf(self, minDataDf):
        timeFilt = (pd.to_datetime(self.startDate) <= minDataDf["Date"]) & (minDataDf["Date"] <= pd.to_datetime(self.endDate))

        minDataDf = minDataDf[timeFilt]
        minDataDf.reset_index(inplace=True)

        return minDataDf


    def runBackTest(self):

        StatArbInstance = StatArb.IndexBasedStatArb(inv=self.invAsset, norm=self.normAsset, invBidAskSpread=15, normBidAskSpread=15, minPriceSpread=30, minStd=3)

        for i in range(len(self.invAsset.minData)):
            self.currentCash = StatArbInstance.updatePairState(i, self.currentCash)

        self.printBackTestResults(StatArbInstance)

        self.plotBackTestPeriodAllSpreads()

    def printBackTestResults(self, StatArbInstance):
        print(self.invAsset.stockCode, self.normAsset.stockCode)
        print("Number Trades", StatArbInstance.numTrades)
        print("Number Profit Trades", StatArbInstance.numSuccessfulTrades)
        print("Trade Accuracy(percentage of profit trades)", 100.0 * StatArbInstance.numSuccessfulTrades / StatArbInstance.numTrades, "%")
        print("Avg Holding Period", sum(StatArbInstance.allHoldingPeriods) / (StatArbInstance.numTrades - 1))
        print("Final Cash:", round(self.currentCash), "₩")
        print("Performance(cash):", self.currentCash - self.initialCash, "₩ profit")
        print("Performance(pct):", 100 * (self.currentCash - self.initialCash) / self.initialCash, "%")


    def plotBackTestPeriodAllSpreads(self):

        invPctMvtInverted, normPctMvt = self.getPctMvtData()

        spreads = invPctMvtInverted - normPctMvt

        plt.plot(spreads, color="green", label="spreads")
        plt.plot(list(invPctMvtInverted), color="orange", label=self.invCode + "inverted")
        plt.plot(list(normPctMvt), color="cyan", label=self.normCode)

        plt.axhline(y=0.004, color='blue', linestyle='-') # spreads percent markers
        plt.axhline(y=0.003, color='blue', linestyle='-')
        plt.axhline(y=0.002, color='blue', linestyle='-')
        plt.axhline(y=0.001, color='blue', linestyle='-')
        plt.axhline(y=0, color='red', linestyle='-')

    def getPctMvtData(self):
        invPctMvt = self.invAsset.minData["OpenPctChangeSummed"]
        invPctMvtInverted = invPctMvt * -1

        normPctMvt = self.normAsset.minData["OpenPctChangeSummed"]

        return invPctMvtInverted, normPctMvt



def main():
    Pair1BackTester = BackTester(initialCash=0, invCode="", normCode="", startDate="", endDate="")
    Pair1BackTester.runBackTest()

    """
        inv assets    
    A145670 
    A252410 
    A114800
    A123310
    A253240
    A306520
    
        norm assets
    A069500
    A148020
    A226490
    A337140
    A237350
    A278530
    """

    plt.legend(loc="upper left")
    plt.grid(True)
    plt.grid(which='minor', linestyle=':', linewidth='0.5', color='black')
    plt.minorticks_on()
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()



