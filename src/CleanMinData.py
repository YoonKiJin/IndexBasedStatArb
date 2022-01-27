import pandas as pd
import numpy as np
import os


class MinDataCleaner:

    def __init__(self, startDate="", endDate=""):
        self.startDate = startDate
        self.endDate = endDate

    def cleanDataForAllStocksAndSaveAsCsv(self):
        uncleanedCsvDataFilesFolderName = "minDataUncleaned"
        csvFileNames = list(os.listdir(uncleanedCsvDataFilesFolderName))
        for fileName in csvFileNames:
            if ".csv" in fileName:
                stockCode = fileName[0:7]
                uncleanedDataAsList = self.getUncleanedDataAsListForSingleStock(stockCode)
                cleanedDataAsDf = self.cleanAndModifyData(uncleanedDataAsList)
                self.saveCleanedDataAsCsv(cleanedDataAsDf, stockCode)

    def getUncleanedDataAsListForSingleStock(self, stockCode):
        uncleanedMinDataAsCsv = pd.read_csv("minDataUncleaned/" + str(stockCode) + "MinData.csv")

        uncleanedMinDataAsList = uncleanedMinDataAsCsv.values.tolist()

        uncleanedMinDataAsList.reverse()

        return uncleanedMinDataAsList

    def cleanAndModifyData(self, minDataAsList):

        self.dropRowsOfTimeAfter1520(minDataAsList)

        self.fillInMissingRows(minDataAsList)

        minDataDf = self.turnListDataIntoPandasDf(minDataAsList)

        # set time filter if start/end dates are specified
        if self.startDate != "":
            minDataDf = self.addTimeFilterToMinDataDf(minDataDf, startDate=self.startDate, endDate=self.endDate)

        self.addMoreTypesOfDataToDf(minDataDf)

        return minDataDf

    def dropRowsOfTimeAfter1520(self, minDataAsList):
        # standardize data by using time period from 901 to 1520
        index = 0
        while index < len(minDataAsList):
            currentRow = minDataAsList[index]
            currentRowTime = int(currentRow[1])
            if currentRowTime > 1520:
                minDataAsList.pop(index)
                continue
            index += 1

    def fillInMissingRows(self, minDataAsList):

        # handle very first row of data
        if int(minDataAsList[0][1]) != 901:
            firstRow = minDataAsList[0].copy()
            firstRow[1] = 901
            firstRow[6] = 0
            minDataAsList.insert(0, firstRow)

        # Date changes are signaled by comparing current and next row
        # placeHolderRow at the end helps avoid index out of bounds error
        # placeHolderRow requirements:
        #   - minimum length 2
        #   - first element must be a different value from the date of the very last row of the data (thus, 0 is used)
        placeHolderRow = [0, 0]
        minDataAsList.append(placeHolderRow)

        correctTime = 902
        index = 1
        while index < (len(minDataAsList) - 1):
            if correctTime == 960:
                correctTime = 1000
            elif correctTime == 1060:
                correctTime = 1100
            elif correctTime == 1160:
                correctTime = 1200
            elif correctTime == 1260:
                correctTime = 1300
            elif correctTime == 1360:
                correctTime = 1400
            elif correctTime == 1460:
                correctTime = 1500
            elif correctTime == 1521:
                correctTime = 901

            currentRow = minDataAsList[index]
            currentRowTime = int(currentRow[1])
            currentRowDate = currentRow[0]

            nextRow = minDataAsList[index + 1]
            nextRowDate = nextRow[0]

            prevRow = minDataAsList[index - 1]
            prevRowDate = prevRow[0]

            if currentRowTime != correctTime:
                if currentRowDate != prevRowDate:  # current row is the first row of the day but time is not 901
                    newRow = currentRow.copy()
                    newRow[1] = correctTime
                    newRow[6] = 0  # trading volume = 0
                    minDataAsList.insert(index, newRow)
                else:
                    newRow = prevRow.copy()
                    newRow[1] = correctTime
                    newRow[6] = 0
                    minDataAsList.insert(index, newRow)
            elif currentRowDate != nextRowDate:
                if correctTime != 1520:
                    newRow = currentRow.copy()
                    newRow[1] = 1520
                    newRow[6] = 0
                    minDataAsList.insert(index + 1, newRow)

            index += 1
            correctTime += 1

        minDataAsList.pop()  # delete placeHolderRow once missing rows are filled

    def turnListDataIntoPandasDf(self, minDataAsList):
        minDataDf = pd.DataFrame(minDataAsList, columns=["Date", "Time", "Open", "High", "Low", "Close", "Volume"])

        minDataDf["Date"] = minDataDf["Date"].apply(str)
        minDataDf["Date"] = minDataDf["Date"].apply(lambda x: x[0:4] + "-" + x[4:6] + "-" + x[6:])
        minDataDf["Date"] = pd.to_datetime(minDataDf["Date"], format="%Y-%m-%d")

        minDataDf["Open"] = minDataDf["Open"].apply(int)
        minDataDf["High"] = minDataDf["High"].apply(int)
        minDataDf["Low"] = minDataDf["Low"].apply(int)
        minDataDf["Close"] = minDataDf["Close"].apply(int)
        minDataDf["Volume"] = minDataDf["Volume"].apply(int)
        minDataDf["Time"] = minDataDf["Time"].apply(int)

        return minDataDf

    def addTimeFilterToMinDataDf(self, minDataDf, startDate, endDate):

        timeFilt = (minDataDf["Date"] >= pd.to_datetime(startDate)) & (minDataDf["Date"] <= pd.to_datetime(endDate))

        minDataDf = minDataDf[timeFilt]

        minDataDf.reset_index(inplace=True)

        return minDataDf

    def addMoreTypesOfDataToDf(self, minDataDf):
        pctChangeIndexPeriod = 1
        minDataDf["OpenPctChangeSummed"] = np.cumsum(minDataDf["Open"].pct_change(periods=pctChangeIndexPeriod))
        # first value for ClosePctChangeSummed will be NaN because the very first values has no value
        # before it to calculate a pct change from
        minDataDf.loc[0, "OpenPctChangeSummed"] = 0

        pctChangeIndexPeriod = 1
        minDataDf["ClosePctChangeSummed"] = np.cumsum(minDataDf["Close"].pct_change(periods=pctChangeIndexPeriod))
        # first value for ClosePctChangeSummed will be NaN because the very first values has no value
        # before it to calculate a pct change from
        minDataDf.loc[0, "ClosePctChangeSummed"] = 0

    def saveCleanedDataAsCsv(self, cleanedDataDf, stockCode):
        cleanedDataDf.to_csv("minData/" + str(stockCode) + ".csv", index = False)



def main():
    MinDataCleanerInstance = MinDataCleaner()
    MinDataCleanerInstance.cleanDataForAllStocksAndSaveAsCsv()

if __name__ == '__main__':
    main()
