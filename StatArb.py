import math
import numpy as np
import pandas as pd


class IndexBasedStatArb:

    def __init__(self, inv, norm, invBidAskSpread, normBidAskSpread, minPriceSpread, minStd):
        self.inv = inv
        self.norm = norm

        self.invCurrentPctMvt = 0
        self.normCurrentPctMvt = 0
        self.currentSpreadZeroedOut = 0

        self.prevDayMean = 0
        self.prevDayStd = 0

        self.minPriceSpread = minPriceSpread # minimum spread in terms of price
        self.minStd = minStd # minimum spread in terms of number of standard deviations

        self.invBidAskSpread = invBidAskSpread
        self.normBidAskSpread = normBidAskSpread

        self.isTradeOpen = False

        self.invShareNum = 0
        self.normShareNum = 0

        self.cashBeforeTrade = 0
        self.tradeOpenIndex = 0


        self.numTrades = 0
        self.numSuccessfulTrades = 0
        self.allHoldingPeriods = []

    def updatePairState(self, currentIndex, currentCash):

        currentTime = self.inv.minData.loc[currentIndex, "Time"]

        print("INDEX", currentIndex, "- TIME", currentTime, "- CAPITAL", currentCash)

        if currentIndex < 380: # skip day 1
            return currentCash

        if currentTime == 901:
            print("UPDATE")
            self.updateNewDayInfo(currentIndex)

        self.getCurrentSpreadZeroed(currentIndex)

        if self.isTradeOpen == False:

            if 901 <= currentTime and currentTime <= 1400:

                if self.currentSpreadZeroedOut >= self.prevDayStd * self.minStd:

                    if self.currentSpreadZeroedOut * self.inv.minData.loc[currentIndex, "Open"] >= self.minPriceSpread and self.currentSpreadZeroedOut * self.norm.minData.loc[currentIndex, "Open"] >= self.minPriceSpread:

                        currentCash = self.openTrade(currentIndex, currentCash, currentTime)

                        return currentCash


        if self.isTradeOpen == True:

            if self.currentSpreadZeroedOut <= -0.5 * self.prevDayStd:
                if self.isTradeExitProfitable(currentIndex, currentCash):
                    currentCash = self.closeTrade(currentIndex, currentCash, currentTime)
                    return currentCash

            if currentIndex - self.tradeOpenIndex >= 30:
                if self.isTradeExitProfitable(currentIndex, currentCash):
                    print("Profit Capture")
                    currentCash = self.closeTrade(currentIndex, currentCash, currentTime)
                    return currentCash

            if currentTime >= 1500:
                currentCash = self.closeTrade(currentIndex, currentCash, currentTime)
                print("Trade Closed - Over 3:00pm")
                return currentCash

        return currentCash


    def openTrade(self, currentIndex, currentCash, currentTime):

        self.invShareNum = round(self.norm.minData.loc[currentIndex, "Open"] / self.inv.minData.loc[currentIndex, "Open"])
        self.normShareNum = 1

        buyCommission = 0.000192

        invBasePositionSize = self.inv.minData.loc[currentIndex, "Open"] * self.invShareNum * (1 + buyCommission)
        normBasePositionSize = self.norm.minData.loc[currentIndex, "Open"] * self.normShareNum * (1 + buyCommission)

        baseTradeSize = invBasePositionSize + normBasePositionSize

        tradeSizeMultiplier = math.floor(currentCash / baseTradeSize)

        if tradeSizeMultiplier == 0:
            return currentCash

        self.invShareNum *= tradeSizeMultiplier
        self.normShareNum *= tradeSizeMultiplier

        cashBeforeTrade = currentCash

        currentCash -= baseTradeSize * tradeSizeMultiplier

        self.isTradeOpen = True
        self.tradeOpenIndex = currentIndex
        self.cashBeforeTrade = cashBeforeTrade
        self.numTrades += 1

        print("------------------------------")
        print("TRADE OPENED - INDEX:", currentIndex, "TIME", currentTime)
        print(self.inv.stockCode, self.inv.minData.loc[currentIndex, "Open"])
        print(self.inv.stockCode, self.inv.minData.loc[currentIndex, "Open"] * self.invShareNum)
        print(self.norm.stockCode, self.norm.minData.loc[currentIndex, "Open"])
        print("2std", 2 * self.prevDayStd, "currentSpreadZeroedOut", self.currentSpreadZeroedOut, "invPriceSpread", self.currentSpreadZeroedOut * self.inv.minData.loc[currentIndex, "Open"])
        print("------------------------------")

        return currentCash

    def closeTrade(self, currentIndex, currentCash, currentTime):

        sellCommission = 0.000192

        currentCash += (self.inv.minData.loc[currentIndex, "Open"] - self.invBidAskSpread) * self.invShareNum * (1 - sellCommission)
        currentCash += (self.norm.minData.loc[currentIndex, "Open"] - self.normBidAskSpread) * self.normShareNum * (1 - sellCommission)

        print("------------------------------")
        print("TRADE CLOSED - INDEX:", currentIndex, "TIME", currentTime)
        print(self.inv.stockCode, self.inv.minData.loc[currentIndex, "Open"])
        print(self.inv.stockCode, self.inv.minData.loc[currentIndex, "Open"] * self.invShareNum)
        print(self.norm.stockCode, self.norm.minData.loc[currentIndex, "Open"])
        print("2std", 2 * self.prevDayStd, "currentSpreadZeroedOut", self.currentSpreadZeroedOut, "tradeReturn: ", currentCash - self.cashBeforeTrade)
        if currentCash - self.cashBeforeTrade < 0:
            print("LOSS")
        else:
            self.numSuccessfulTrades += 1
        print("------------------------------")

        self.allHoldingPeriods.append(currentIndex - self.tradeOpenIndex)
        self.isTradeOpen = False

        return currentCash

    def isTradeExitProfitable(self, currentIndex, currentCash):

        sellCommission = 0.000192

        cashAfterTrade = currentCash

        cashAfterTrade += (self.inv.minData.loc[currentIndex, "Open"] - self.invBidAskSpread) * self.invShareNum * (1 - sellCommission)
        cashAfterTrade += (self.norm.minData.loc[currentIndex, "Open"] - self.normBidAskSpread) * self.normShareNum * (1 - sellCommission)

        if cashAfterTrade - self.cashBeforeTrade > 0:
            return True

        return False


    def getCurrentSpreadZeroed(self, currentIndex):

        self.invCurrentPctMvt += IndexBasedStatArb.getPricePctChange(self.inv, currentIndex) * -1
        self.normCurrentPctMvt += IndexBasedStatArb.getPricePctChange(self.norm, currentIndex)

        currentSpreadNotZeroed = self.invCurrentPctMvt - self.normCurrentPctMvt

        self.currentSpreadZeroedOut = currentSpreadNotZeroed - self.prevDayMean

    @classmethod
    def getPricePctChange(cls, stockObject, currentIndex):
        prevPrice = stockObject.minData.loc[currentIndex - 1, "Open"]
        currentPrice = stockObject.minData.loc[currentIndex, "Open"]

        priceChange = currentPrice - prevPrice

        pctChange = priceChange / prevPrice

        return pctChange


    def updateNewDayInfo(self, currentIndex):
        # exclude the first 15 min
        start = currentIndex - (380 - 15)
        end = currentIndex - 1
        pastPricesA = self.inv.minData.loc[start:end, "Open"]
        pastPricesB = self.norm.minData.loc[start:end, "Open"]

        pctChangeIndexPeriod = 1
        pctChangesA = pastPricesA.pct_change(periods=pctChangeIndexPeriod)
        pctChangesB = pastPricesB.pct_change(periods=pctChangeIndexPeriod)

        invertedPctChangeSumA = np.cumsum(pctChangesA) * -1
        pctChangeSumB = np.cumsum(pctChangesB)

        self.updatePrevDaySpreadsMeanAndStd(invertedPctChangeSumA, pctChangeSumB)

    def updatePrevDaySpreadsMeanAndStd(self, invPctMvtInverted, normPctMvt):

        invPctMvtInverted = list(invPctMvtInverted)
        normPctMvt = list(normPctMvt)

        spreads = []
        for index in range(len(invPctMvtInverted)):
            spreads.append(invPctMvtInverted[index] - normPctMvt[index])

        spreads = pd.Series(spreads)

        self.prevDayMean = spreads.mean()
        self.prevDayStd = spreads.std()

        self.invCurrentPctMvt = invPctMvtInverted[len(invPctMvtInverted) - 1]
        self.normCurrentPctMvt = normPctMvt[len(normPctMvt) - 1]

