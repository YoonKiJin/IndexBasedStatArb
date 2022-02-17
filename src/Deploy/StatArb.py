import ctypes
import sys
import win32com.client

from datetime import datetime
import time
import csv
import pandas as pd
import math

from DataGather import DataGather


objTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')
orderObj = win32com.client.Dispatch('CpTrade.CpTd0311')  
objStockMst = win32com.client.Dispatch("DsCbo1.StockMst")
status = win32com.client.Dispatch('CpUtil.CpCybos')
cpBalance = win32com.client.Dispatch('CpTrade.CpTd6033')
cpCash = win32com.client.Dispatch('CpTrade.CpTdNew5331A')
objCancelOrder = win32com.client.Dispatch("CpTrade.CpTd0314")
objRq = win32com.client.Dispatch("CpTrade.CpTd5339")

class StatArb:

    numAllocationsOfCash = 3 # set before trading begins

    currentCashAllocationPerTrade = 0

    numTradesCurrentlyOpen = 0

    def __init__(self, invCode, normCode, minStdSpread=3, minPriceSpread=30):
                
        # codes with A or Q (product type)
        self.invCode = invCode
        self.normCode = normCode

        self.prevDayMean = 0
        self.prevDayStd = 0

        self.minPriceSpread = minPriceSpread

        self.minStdSpread = minStdSpread # minimum number of standard deviations from previous day mean


        self.invCurrentAsk = 0
        self.invPrevAsk = 0

        self.invCurrentBid = 0

        self.invAskVol = 0
        self.invBidVol = 0
        

        self.normCurrentAsk = 0
        self.normPrevAsk = 0

        self.normCurrentBid = 0

        self.normAskVol = 0
        self.normBidVol = 0


        self.invEtfcurrentPctMvt = 0
        self.normEtfcurrentPctMvt = 0

        self.currentSpread = 0


        self.tradeIsOpen = False

        self.tradeOpenTime = ""

        self.invShareNum = 0
        self.normShareNum = 0       


        self.updateNewDay()

    def updateNewDay(self):

        invPrevDayData = pd.read_csv("PrevDayData/" + self.invCode + "prev.csv")
        normPrevDayData = pd.read_csv("PrevDayData/" + self.normCode + "prev.csv")

        # handling of recorded data is all done in DataGather, not in StatArb

        invPrevDayPctMvt = invPrevDayData["PctMvtSummed"]
        invPrevDayPctMvtInverted = invPrevDayPctMvt * -1
        normPrevDayPctMvt = normPrevDayData["PctMvtSummed"]

        prevDaySpreads = invPrevDayPctMvtInverted - normPrevDayPctMvt
        prevDaySpreadsMinusFirst15Min = prevDaySpreads.loc[28:len(prevDaySpreads) - 1]

        # calculate mean and std of previous day spreads of current pair - do so excluding the first 15 min(amount of time is up to user's discretion)

        self.prevDayMean = prevDaySpreadsMinusFirst15Min.mean()
        self.prevDayStd = prevDaySpreadsMinusFirst15Min.std()

        self.invCurrentAsk = invPrevDayData["AskPrice"].iloc[-1]
        self.normCurrentAsk = normPrevDayData["AskPrice"].iloc[-1]

        self.invEtfcurrentPctMvt = invPrevDayPctMvtInverted.iloc[-1]
        self.normEtfcurrentPctMvt = normPrevDayPctMvt.iloc[-1]

        currentSpread = prevDaySpreads.iloc[-1]
        self.currentSpread = currentSpread - self.prevDayMean

        print("invCode", self.invCode, "normCode", self.normCode, "prevDayStd*minStdSpread", self.prevDayStd * self.minStdSpread)

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



    def updatePairState(self):

        StatArb.checkConnectionWithCreon()

        StatArb.checkRemainingSignalCount()


        self.updateInvEtfInfo()

        self.updateNormEtfInfo()


        self.getCurrentSpreadZeroed()

        print(self.currentSpread, status.GetLimitRemainCount(0), "Order Requests Left")
    


        if self.tradeIsOpen == False:

            if datetime.now().hour < 14:

                if self.currentSpread >= self.prevDayStd * self.minStdSpread:      

                    if self.currentSpread * self.invCurrentAsk >= self.minPriceSpread:
                        if self.currentSpread * self.normCurrentAsk >= self.minPriceSpread:                    

                            if self.enoughCashToOpenTrade() == True:

                                if self.normAskVol > self.normShareNum:
                                    if self.invAskVol > self.invShareNum:

                                        self.openPairTrade()

                                        StatArb.positionsView()

                                        return
 

        if self.tradeIsOpen == True:

            if self.normBidVol > self.normShareNum:
                if self.invBidVol > self.invShareNum:

                            if self.currentSpread <= self.prevDayStd * -0.5: 

                                tradeReturn = self.getTradeReturn()
                                if tradeReturn > 0: # close trade if profitable

                                    self.closePairTrade(tradeReturn)

                                    StatArb.positionsView()

                                    return

                            holdingPeriodInSec = (datetime.now() - self.tradeOpenTime).seconds
                            holdingPeriodInMin = holdingPeriodInSec / 60

                            if holdingPeriodInMin >= 30:
                                print("================== TRADE HOLDING PERIOD OVER 30 MIN ==================")

                                tradeReturn = self.getTradeReturn()
                                if tradeReturn > 0: # close trade if profitable:

                                    self.closePairTrade(tradeReturn)

                                    StatArb.positionsView()

                                    return

            if datetime.now().hour >= 15:

                holdingPeriodInSec = (datetime.now() - self.tradeOpenTime).seconds
                holdingPeriodInMin = holdingPeriodInSec / 60

                self.closeAllPositionsForCurrentPairAtMarketPrice()

                filePath = "DayTradeData.csv"
                with open(filePath, 'a', newline="") as csvfile: 
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow(["--------------------------------------------------------------"])
                    csvwriter.writerow(["TRADE CLOSE - EMERGENCY EXIT - past 15:00"])
                    csvwriter.writerow(["Time", datetime.now()])
                    csvwriter.writerow(["invCode", self.invCode, "| normCode", self.normCode])
                    csvwriter.writerow(["currentSpread", round(self.currentSpread, 5), "| holdingPeriodInMin", holdingPeriodInMin])
                    csvwriter.writerow(["invCurrentAsk", self.invCurrentAsk, "| invCurrentBid", self.invCurrentBid, "| invShareNum", self.invShareNum, "| invAskVol", self.invAskVol, "| invBidVol", self.invBidVol])
                    csvwriter.writerow(["normCurrentAsk", self.normCurrentAsk, "| normCurrentBid", self.normCurrentBid,"| normShareNum", self.normShareNum, "| normAskVol", self.normAskVol, "| normBidVol", self.normBidVol])
                    csvwriter.writerow(["--------------------------------------------------------------"])
                

                StatArb.positionsView()

                return

        if datetime.now().minute == 30 and datetime.now().second < 30:
            """
            regularly check for wrongly opened positions
            may happen due to issues with network connections of the machine the code is run on
            """
            self.cancelAnyWronglyOpenPositions()
        

    def updateInvEtfInfo(self):
        objStockMst.SetInputValue(0, self.invCode) 
        objStockMst.BlockRequest()

        askPrice = objStockMst.GetHeaderValue(16)
        bidPrice = objStockMst.GetHeaderValue(17)

        askVol = objStockMst.GetDataValue(2, 0)
        bidVol = objStockMst.GetDataValue(3, 0)

        self.invPrevAsk = self.invCurrentAsk

        if askPrice != 0:
            self.invCurrentAsk = askPrice

        self.invCurrentBid = bidPrice

        self.invAskVol = askVol
        self.invBidVol = bidVol

        print(self.invCode, "| bidAskSpread", askPrice - bidPrice, "| askVol", askVol, "bidVol", bidVol, "| askPrice:", self.invCurrentAsk, "bidPrice:", bidPrice)
    
    def updateNormEtfInfo(self):
        objStockMst.SetInputValue(0, self.normCode)
        objStockMst.BlockRequest()

        askPrice = objStockMst.GetHeaderValue(16)
        bidPrice = objStockMst.GetHeaderValue(17)

        askVol = objStockMst.GetDataValue(2, 0)
        bidVol = objStockMst.GetDataValue(3, 0)

        self.normPrevAsk = self.normCurrentAsk

        if askPrice != 0:
            self.normCurrentAsk = askPrice

        self.normCurrentBid = bidPrice

        self.normAskVol = askVol
        self.normBidVol = bidVol

        print(self.normCode, "| bidAskSpread", askPrice - bidPrice, "| askVol", askVol, "bidVol", bidVol, "| askPrice:", self.normCurrentAsk, "bidPrice:", bidPrice)


    def getCurrentSpreadZeroed(self):
        self.invEtfcurrentPctMvt += self.getPricePctChange(self.invPrevAsk, self.invCurrentAsk) * -1
        self.normEtfcurrentPctMvt += self.getPricePctChange(self.normPrevAsk, self.normCurrentAsk)

        currentSpreadNotZeroed = self.invEtfcurrentPctMvt - self.normEtfcurrentPctMvt

        self.currentSpread = currentSpreadNotZeroed - self.prevDayMean

    def getPricePctChange(self, prevPrice, currentPrice):
        priceChange = currentPrice - prevPrice
        pctChange = priceChange / prevPrice
        return pctChange


    def enoughCashToOpenTrade(self):

        if StatArb.numTradesCurrentlyOpen >= StatArb.numAllocationsOfCash:
            return False

        self.invShareNum = round(self.normCurrentAsk/self.invCurrentAsk)
        self.normShareNum = 1
        print("invShareNum", self.invShareNum, "normShareNum", self.normShareNum)

        totalChargesBuying = 0.000192

        minimumCashNeeded = (self.invCurrentAsk * self.invShareNum * (1 + totalChargesBuying)) + (self.normCurrentAsk * self.normShareNum * (1 + totalChargesBuying))

        tradeSizeMultiplier = math.floor(StatArb.currentCashAllocationPerTrade / minimumCashNeeded)

        if tradeSizeMultiplier > 0:
            self.invShareNum *= tradeSizeMultiplier
            self.normShareNum *= tradeSizeMultiplier
            return True
        else:
            return False


    @classmethod
    def calculateCashToAllocatePerTrade(cls):
        numPositionsOpen = StatArb.getNumPositionsCurrentlyOpen()
        if numPositionsOpen == 0:
            currentTotalCash = StatArb.getCurrentCash()
            StatArb.currentCashAllocationPerTrade = currentTotalCash / StatArb.numAllocationsOfCash


    def openPairTrade(self):
        """
        the logic is that illiquid norm such as TREX or POWER may be more difficult to get orders filled for
        so, we first open a position for the more liquid inv, then we attempt to open a position for the norm
        in the case that the norm position can't be filled, we'd immediately exit the position opened for the inv, in the process we would lose out on the bidAskSpread of 5
        whereas if we were to open for the norm first then have to exit it due to inv not being filled, the spread we would have to pay for may be 50 or so
       
        if the first position is not opened properly, we simply don't enter the trade at all
        """

        StatArb.openPositionAtGivenPrice(self.invCode, self.invShareNum, self.invCurrentAsk)
        time.sleep(0.05) # required due to connection issues - this number should be tweaked at discretion of user

        if StatArb.positionIsCurrentlyOpen(self.invCode) == False:

            StatArb.cancelAnyUnfilledOrders()

            filePath = "DayTradeData.csv"
            with open(filePath, 'a', newline="") as csvfile: 
                csvwriter = csv.writer(csvfile) 
                csvwriter.writerow(["--------------------------------------------------------------"])
                csvwriter.writerow(["Failed to open trade - inv POSITION NOT OPENED PROPERLY", self.invCode, self.normCode])
                csvwriter.writerow(["--------------------------------------------------------------"])
            return


        StatArb.openPositionAtGivenPrice(self.normCode, self.normShareNum, self.normCurrentAsk)
        time.sleep(0.05) # required due to connection issues - this number should be tweaked at discretion of user

        if StatArb.positionIsCurrentlyOpen(self.normCode) == False:

            StatArb.cancelAnyUnfilledOrders()

            self.closeAllPositionsForCurrentPairAtMarketPrice()

            filePath = "DayTradeData.csv"
            with open(filePath, 'a', newline="") as csvfile: 
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(["--------------------------------------------------------------"])
                csvwriter.writerow(["Failed to open trade - norm POSITION NOT OPENED PROPERLY - inv POSITION EMERGENCY EXIT"])
                csvwriter.writerow(["Time", datetime.now()])
                csvwriter.writerow(["invCode", self.invCode, "| normCode", self.normCode])
                csvwriter.writerow(["currentSpread", round(self.currentSpread, 5)])
                csvwriter.writerow(["invCurrentAsk", self.invCurrentAsk, "| invCurrentBid", self.invCurrentBid, "| invShareNum", self.invShareNum, "| invAskVol", self.invAskVol, "| invBidVol", self.invBidVol])
                csvwriter.writerow(["normCurrentAsk", self.normCurrentAsk, "| normCurrentBid", self.normCurrentBid,"| normShareNum", self.normShareNum, "| normAskVol", self.normAskVol, "| normBidVol", self.normBidVol])
                csvwriter.writerow(["--------------------------------------------------------------"])
            

            return


        self.tradeIsOpen = True

        StatArb.numTradesCurrentlyOpen += 1
        
        self.tradeOpenTime = datetime.now()

        filePath = "DayTradeData.csv"
        with open(filePath, 'a', newline="") as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(["--------------------------------------------------------------"])
            csvwriter.writerow(["TRADE OPEN"])
            csvwriter.writerow(["Time", self.tradeOpenTime])
            csvwriter.writerow(["invCode", self.invCode, "| normCode", self.normCode])
            csvwriter.writerow(["currentSpread", round(self.currentSpread, 5), "| invEtfPriceSpread", round(self.currentSpread * self.invCurrentAsk, 5)])
            csvwriter.writerow(["invCurrentAsk", self.invCurrentAsk, "| invShareNum", self.invShareNum, "| invAskVol", self.invAskVol, "| invBidVol", self.invBidVol])
            csvwriter.writerow(["normCurrentAsk", self.normCurrentAsk, "| normShareNum", self.normShareNum, "| normAskVol", self.normAskVol, "| normBidVol", self.normBidVol])
            csvwriter.writerow(["--------------------------------------------------------------"])

    def closePairTrade(self, tradeReturn):
        """
        the logic here is similar to the case of entering a trade
        because the bidAskSpread of illiquid norm is often greater we grab the offered bidAskSpread spread when we can
        losing out on the targeted bidAskSpread of inv would only result in losing out by 5 or 10(roughly) while losing out on the norm's may require an extra 20 or more
        thus, when entering a trade, inv is opened first, but here, when exiting a trade, norm is exited first
        
        if the first position is not closed properly, we simply don't exit the trade at all
        """

        StatArb.closePositionAtGivenPrice(self.normCode, self.normShareNum, self.normCurrentBid)
        time.sleep(0.05) # required due to connection issues - this number should be tweaked at discretion of user

        if StatArb.positionIsCurrentlyOpen(self.normCode) == True:

            StatArb.cancelAnyUnfilledOrders()

            filePath = "DayTradeData.csv"
            with open(filePath, 'a', newline="") as csvfile: 
                csvwriter = csv.writer(csvfile) 
                csvwriter.writerow(["--------------------------------------------------------------"])
                csvwriter.writerow(["Failed to close trade - norm POSITION NOT CLOSED PROPERLY"])
                csvwriter.writerow(["--------------------------------------------------------------"])
            return


        StatArb.closePositionAtGivenPrice(self.invCode, self.invShareNum, self.invCurrentBid)
        time.sleep(0.05) # required due to connection issues - this number should be tweaked at discretion of user

        if StatArb.positionIsCurrentlyOpen(self.invCode) == True:

            StatArb.cancelAnyUnfilledOrders()

            holdingPeriodInSec = (datetime.now() - self.tradeOpenTime).seconds
            holdingPeriodInMin = holdingPeriodInSec / 60

            self.closeAllPositionsForCurrentPairAtMarketPrice()

            filePath = "DayTradeData.csv"
            with open(filePath, 'a', newline="") as csvfile: 
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(["--------------------------------------------------------------"])
                csvwriter.writerow(["Failed to properly close trade - inv POSITION NOT CLOSED PROPERLY - inv POSITION EMERGENCY EXIT"])
                csvwriter.writerow(["Time", datetime.now()])
                csvwriter.writerow(["invCode", self.invCode, "| normCode", self.normCode])
                csvwriter.writerow(["currentSpread", round(self.currentSpread, 5), "| holdingPeriodInMin", holdingPeriodInMin])
                csvwriter.writerow(["invCurrentAsk", self.invCurrentAsk, "| invCurrentBid", self.invCurrentBid, "| invShareNum", self.invShareNum, "| invAskVol", self.invAskVol, "| invBidVol", self.invBidVol])
                csvwriter.writerow(["normCurrentAsk", self.normCurrentAsk, "| normCurrentBid", self.normCurrentBid,"| normShareNum", self.normShareNum, "| normAskVol", self.normAskVol, "| normBidVol", self.normBidVol])
                csvwriter.writerow(["--------------------------------------------------------------"])
            

            return


        self.tradeIsOpen = False

        StatArb.numTradesCurrentlyOpen -= 1

        holdingPeriodInSec = (datetime.now() - self.tradeOpenTime).seconds
        holdingPeriodInMin = holdingPeriodInSec / 60

        filePath = "DayTradeData.csv"
        with open(filePath, 'a', newline="") as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(["--------------------------------------------------------------"])
            csvwriter.writerow(["TRADE CLOSE"])
            csvwriter.writerow(["Time", datetime.now()])
            csvwriter.writerow(["invCode", self.invCode, "| normCode", self.normCode])
            csvwriter.writerow(["currentSpread", round(self.currentSpread, 5), "| holdingPeriodInMin", holdingPeriodInMin])
            csvwriter.writerow(["invCurrentAsk", self.invCurrentAsk, "| invCurrentBid", self.invCurrentBid, "| invShareNum", self.invShareNum, "| invAskVol", self.invAskVol, "| invBidVol", self.invBidVol])
            csvwriter.writerow(["normCurrentAsk", self.normCurrentAsk, "| normCurrentBid", self.normCurrentBid,"| normShareNum", self.normShareNum, "| normAskVol", self.normAskVol, "| normBidVol", self.normBidVol])
            csvwriter.writerow(["tradeReturn", tradeReturn])
            csvwriter.writerow(["--------------------------------------------------------------"])
        

    def getTradeReturn(self):

        allPositions = StatArb.getOpenPositions()

        invPositionCurrent = self.invCurrentBid * self.invShareNum
        normPositionCurrent = self.normCurrentBid * self.normShareNum

        invPositionBreakEven = 0
        normPositionBreakEven = 0

        for position in allPositions:
            if position["stockCode"] == self.invCode:
                invPositionBreakEven = position["breakEvenPrice"] * self.invShareNum
            if position["stockCode"] == self.normCode:
                normPositionBreakEven = position["breakEvenPrice"] * self.normShareNum
                
        if invPositionBreakEven == 0:
            self.closeAllPositionsForCurrentPairAtMarketPrice()
            return 0
        if normPositionBreakEven == 0:
            self.closeAllPositionsForCurrentPairAtMarketPrice()
            return 0

        invPositionReturn = invPositionCurrent - invPositionBreakEven
        normPositionReturn = normPositionCurrent - normPositionBreakEven

        tradeReturn = invPositionReturn + normPositionReturn

        return tradeReturn


    @classmethod
    def openPositionAtGivenPrice(cls, stockCode, numShares, price):        
        objTrade.TradeInit(0)
        accountNum = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(accountNum, 1)               
    
        orderObj.SetInputValue(0, "2")
        orderObj.SetInputValue(1, accountNum)
        orderObj.SetInputValue(2, accFlag[0])
        orderObj.SetInputValue(3, stockCode)
        orderObj.SetInputValue(4, numShares)
        orderObj.SetInputValue(5, price)
        orderObj.SetInputValue(7, "0")
        orderObj.SetInputValue(8, "01")
        orderObj.BlockRequest()

    @classmethod
    def closePositionAtGivenPrice(cls, stockCode, numShares, price):
        objTrade.TradeInit(0)
        accountNum = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(accountNum, 1)         

        orderObj.SetInputValue(0, "1")
        orderObj.SetInputValue(1, accountNum)
        orderObj.SetInputValue(2, accFlag[0])
        orderObj.SetInputValue(3, stockCode)
        orderObj.SetInputValue(4, numShares)
        orderObj.SetInputValue(5, price)
        orderObj.SetInputValue(7, "0")
        orderObj.SetInputValue(8, "01")
        orderObj.BlockRequest()


    def cancelAnyWronglyOpenPositions(self):
        StatArb.checkRemainingSignalCount()

        if self.tradeIsOpen == False:

            if StatArb.positionIsCurrentlyOpen(self.invCode) == True or StatArb.positionIsCurrentlyOpen(self.normCode) == True:

                self.closeAllPositionsForCurrentPairAtMarketPrice()

                StatArb.cancelAnyUnfilledOrders()

                StatArb.checkRemainingSignalCount()

                filePath = "DayTradeData.csv"
                with open(filePath, 'a', newline="") as csvfile: 
                    csvwriter = csv.writer(csvfile) 
                    csvwriter.writerow(["--------------------------------------------------------------"])
                    csvwriter.writerow(["cancelAnyWronglyOpenPositions", self.invCode, self.normCode])
                    csvwriter.writerow(["--------------------------------------------------------------"])
        
    
    def closeAllPositionsForCurrentPairAtMarketPrice(self):

        StatArb.cancelAnyUnfilledOrders()

        positions = StatArb.getOpenPositions()

        for position in positions:

            if position["stockCode"] == self.normCode or position["stockCode"] == self.invCode:
                StatArb.closePositionAtMarketPrice(position["stockCode"], position["numShares"])

            StatArb.checkRemainingSignalCount()

        self.tradeIsOpen = False

        StatArb.calculateCashToAllocatePerTrade()

    @classmethod
    def closePositionAtMarketPrice(cls, stockCode, numShares):
        objTrade.TradeInit(0)
        accountNum = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(accountNum, 1)
        
        orderObj.SetInputValue(0, "1")
        orderObj.SetInputValue(1, accountNum)
        orderObj.SetInputValue(2, accFlag[0])
        orderObj.SetInputValue(3, stockCode)
        orderObj.SetInputValue(4, numShares)
        orderObj.SetInputValue(7, "1") # 1 - IOC
        orderObj.SetInputValue(8, "03") # 03 - market price 시장가
        orderObj.BlockRequest()
    

    @classmethod
    def positionIsCurrentlyOpen(cls, stockCode):
        allPositions = StatArb.getOpenPositions()

        for position in allPositions:
            if position["stockCode"] == stockCode:
                return True

        return False
        

    @classmethod
    def getOpenPositions(cls):
        objTrade.TradeInit(0)
        accountNum = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(accountNum, 1)

        cpBalance.SetInputValue(0, accountNum)
        cpBalance.SetInputValue(1, accFlag[0])
        cpBalance.SetInputValue(2, 50)
        cpBalance.BlockRequest()

        positions = []

        numPositions = cpBalance.GetHeaderValue(7)
        for i in range(0, numPositions):
            stockCode = cpBalance.GetDataValue(12, i)
            numShares = cpBalance.GetDataValue(15, i)
            breakEvenPrice = cpBalance.GetDataValue(18, i)
            positions.append({"stockCode": stockCode, "numShares": numShares, "breakEvenPrice": breakEvenPrice})

        return positions
 
    @classmethod
    def getNumPositionsCurrentlyOpen(cls):
        objTrade.TradeInit(0)
        accountNum = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(accountNum, 1)

        cpBalance.SetInputValue(0, accountNum)
        cpBalance.SetInputValue(1, accFlag[0])
        cpBalance.SetInputValue(2, 50)
        cpBalance.BlockRequest()

        numPositions = cpBalance.GetHeaderValue(7) 

        return numPositions


    @classmethod
    def cancelAnyUnfilledOrders(cls):

        unfilledOrders = StatArb.getUnfilledOrders()

        StatArb.checkRemainingSignalCount()
        
        for item in unfilledOrders:

            StatArb.cancelUnfilledOrder(item["orderNum"], item["code"])

            StatArb.checkRemainingSignalCount()

    @classmethod
    def cancelUnfilledOrder(cls, orderNum, stockCode):
        objTrade.TradeInit(0)
        acc = objTrade.AccountNumber[0] 
        accFlag = objTrade.GoodsList(acc, 1) 

        objCancelOrder.SetInputValue(1, orderNum) 
        objCancelOrder.SetInputValue(2, acc) 
        objCancelOrder.SetInputValue(3, accFlag[0]) 
        objCancelOrder.SetInputValue(4, stockCode)
        objCancelOrder.SetInputValue(5, 0) 
        objCancelOrder.BlockRequest()

    @classmethod
    def getUnfilledOrders(cls):
        objTrade.TradeInit(0)
        acc = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(acc, 1)

        objRq.SetInputValue(0, acc)
        objRq.SetInputValue(1, accFlag[0])
        objRq.SetInputValue(4, "0")
        objRq.SetInputValue(5, "1")
        objRq.SetInputValue(6, "0")
        objRq.SetInputValue(7, 20)
        objRq.BlockRequest()

        numUnfilledOrders = objRq.GetHeaderValue(5)

        unfilledOrders = []

        for i in range(0, numUnfilledOrders):
            orderNum = objRq.GetDataValue(1, i)
            code  = objRq.GetDataValue(3, i)  # 종목코드

            unfilledOrders.append({"orderNum": orderNum, "code": code})

        return unfilledOrders




    @classmethod
    def closeAllPositions(cls):

        StatArb.cancelAnyUnfilledOrders()

        StatArb.checkRemainingSignalCount()
        
        while StatArb.getNumPositionsCurrentlyOpen() > 0:

            positions = StatArb.getOpenPositions()

            for position in positions:

                StatArb.closePositionAtMarketPrice(position["stockCode"], position["numShares"])
                
                StatArb.checkRemainingSignalCount()
                
            time.sleep(0.05)

    @classmethod
    def getCurrentCash(cls):

        objTrade.TradeInit(0)
        accountNum = objTrade.AccountNumber[0]
        accFlag = objTrade.GoodsList(accountNum, 1)           
    
        cpCash.SetInputValue(0, accountNum)
        cpCash.SetInputValue(1, accFlag[0])
        cpCash.BlockRequest()

        return cpCash.GetHeaderValue(9)k


    @classmethod
    def checkRemainingSignalCount(cls):
        if status.GetLimitRemainCount(0) <= 5 or status.GetLimitRemainCount(1) <= 5:
            print(status.GetLimitRemainCount(0), "Order Requests Left", status.GetLimitRemainCount(1), "Signal Requests Left")
            time.sleep(15)



if __name__ == '__main__':

    # If we don't have a file for an ETF or previous data, we must gather data on it first (we don't have the code to handle it any other way for now)
        # DataGather instances
            # we create DataGather objects first, so that upon initialization, previous day data is moved into prevDay data files as intended

    StatArb.checkConnectionWithCreon()

    StatArb.checkRemainingSignalCount()

    # kospi inv
    DataGather1   = DataGather(stockCode="A145670")
    DataGather2   = DataGather(stockCode="A252410")
    DataGather3   = DataGather(stockCode="Q530092")
    DataGather4   = DataGather(stockCode="Q500061")

    # kospi norm
    DataGather5   = DataGather(stockCode="Q530091")
    DataGather6   = DataGather(stockCode="Q550067")
    DataGather7   = DataGather(stockCode="Q570067")
    DataGather8   = DataGather(stockCode="Q500060")

    # kosdaq inv
    DataGather9   = DataGather(stockCode="Q530094")
    DataGather10  = DataGather(stockCode="Q500063")
    DataGather11  = DataGather(stockCode="A301410")

    # kosdaq norm
    DataGather12  = DataGather(stockCode="Q500062")
    DataGather13  = DataGather(stockCode="Q570068")
    DataGather14  = DataGather(stockCode="Q530093")

        # StatArb instances - KOSPI200 / KOSPI

    Pair1  = StatArb(invCode="A145670", normCode="Q570067")
    Pair2  = StatArb(invCode="A252410", normCode="Q550067")
    Pair3  = StatArb(invCode="Q530092", normCode="Q530091")
    Pair4  = StatArb(invCode="Q500061", normCode="Q500060")

        # StatArb instances - KOSDAQ150

    Pair5  = StatArb(invCode="Q530094", normCode="Q500062")
    Pair6  = StatArb(invCode="Q500063", normCode="Q570068")
    Pair7  = StatArb(invCode="A301410", normCode="Q530093")

    StatArb.calculateCashToAllocatePerTrade()


    filePath = "DayTradeData.csv"
    with open(filePath, 'a', newline="") as csvfile: 
        csvwriter = csv.writer(csvfile) 
        csvwriter.writerow(["--------------------------------------------------------------"])
        csvwriter.writerow([datetime.now().date()])
        csvwriter.writerow(["DayStartCash", StatArb.getCurrentCash()])
        csvwriter.writerow(["--------------------------------------------------------------"])

    marketOpenTime = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    marketCloseTime = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)  

    while True:

        if datetime.now() > marketOpenTime:

            if datetime.now().second % 30 == 0:

                startTime = time.time()

                print(datetime.now())
                print(status.GetLimitRemainCount(0), "Order Requests Left", status.GetLimitRemainCount(1), "Signal Requests Left")

                    # DataGathering
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

                    # TradablePairInstances
                Pair1.updatePairState()
                Pair2.updatePairState()
                Pair3.updatePairState()
                Pair4.updatePairState()
                Pair5.updatePairState()
                Pair6.updatePairState()      
                Pair7.updatePairState()          

                endTime = time.time()

                print("runTime", endTime - startTime)
                print(status.GetLimitRemainCount(0), "Order Requests Left", status.GetLimitRemainCount(1), "Signal Requests Left")
                time.sleep(1)
                print()

        if datetime.now() > marketCloseTime:

            filePath = "DayTradeData.csv"
            with open(filePath, 'a', newline="") as csvfile: 
                csvwriter = csv.writer(csvfile) 
                csvwriter.writerow(["--------------------------------------------------------------"])
                csvwriter.writerow([datetime.now().date()])
                csvwriter.writerow(["DayEndCash", StatArb.getCurrentCash()])
                csvwriter.writerow(["--------------------------------------------------------------"])


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



