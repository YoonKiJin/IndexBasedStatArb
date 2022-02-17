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
        """
        Method that is called at every index of data. Updates the "state" of the pair we are back testing based on
        the price of each ETP/stock at each new index
        :param currentIndex: the current index of data we are at
        :param currentCash: cash we currently have that can be used to open trades
        :return: currentCash after the state of the pair is updated(after change in price, we either open a trade, close a trade, or no action)
        """

        currentTime = self.inv.minData.loc[currentIndex, "Time"]

        print("INDEX", currentIndex, "- TIME", currentTime, "- CAPITAL", currentCash)

        if currentIndex < 380: # skip day 1 - because we need one previous day to update new day info
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

        buyCommission = 0.000192 # commission when a position is opened

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
        """
        Calculate the return of a currently open trade if closed at current index. Used to see if this return is
        greater than 0, i.e. profitable.
        :param currentIndex: the current index of data we are at
        :param currentCash: cash we currently have that can be used to open trades
        :return: returns a boolean value, True if the return of the trade at current index is greater than 0
        """

        sellCommission = 0.000192 # commission when a position is closed

        cashAfterTrade = currentCash

        cashAfterTrade += (self.inv.minData.loc[currentIndex, "Open"] - self.invBidAskSpread) * self.invShareNum * (1 - sellCommission)
        cashAfterTrade += (self.norm.minData.loc[currentIndex, "Open"] - self.normBidAskSpread) * self.normShareNum * (1 - sellCommission)

        if cashAfterTrade - self.cashBeforeTrade > 0:
            return True

        return False


    def getCurrentSpreadZeroed(self, currentIndex):
        """
        Calculates the percent movement of each asset in the pair(starting from the previous day market open) and uses
        this movement to calculate the current spread between these two percent movements
        :param currentIndex: the current index of data we are at
        :return: returns the percent spread between the two assets' percent movements
        """

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
        """
        Method that is called whenever we arrive at a new day.
        Recalculate the
            pct movement of the assets of our pair based on the new day
            and
            previous day's pct spreads standard deviation and mean values by calling updatePrevDaySpreadsMeanAndStd()
        :param currentIndex: the current index of data we are at
        :return:
        """
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

