import sqlite3
import sys
import os
import csv
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from os import walk
from utilities import getPercentage, getNumVehicles, getAllFilenames
#---------------------------------------------------------------------#
# This python file takes in multiple sqlite DBs created by AimSun and #
# plot how the Average Travel Time of Different Users changes with the#
# percentage of app users. The main executable lines are at the very  #
# bottom of this file.                                                #
# Last modified by Frank Feb. 12, 2018                                #
#---------------------------------------------------------------------#

def extractSingleDB(fileName, thisPercentage, debug, maxTime):
  #----------------------------------------------------------#
  # Helper function to traverse single SQLite DB and return  #
  # the average travel time of app users and non-app users   #
  #----------------------------------------------------------#
  # Extracting the interested columns from the database, the #
  # columns of the extracted data are                        #
  # (0) oid, the object id for the generated vehicles        #
  # (1) sid, the class of the car, sid = 862 stands for app  #
  #     users, sid = 863 stands for nonapp users. This part  #
  #     should be fixed later since it's hard coded TODO     #
  #     Frank commented on 11/17/2017                        #
  # (2) entranceTime, the entrance time                      #
  # (3) exitTime, the exit time                              #
  numApp, numNonApp = getNumVehicles(fileName, maxTime)
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, sid, entranceTime, exitTime FROM MIVEHTRAJECTORY WHERE (entranceTime > 0 AND exitTime > 0 AND entranceTime < {})'.format(maxTime))
  rows = cur.fetchall()
  con.close()
  appId       = 862
  nonAppId    = 863
  totalTTime  = 0
  appTTime    = 0
  nonAppTTime = 0
  for row in rows:
    if row[1] == appId:
      appTTime += (row[3] - row[2])
    else: 
      nonAppTTime += (row[3] - row[2])
    totalTTime += (row[3] - row[2])
  appTTime    /= numApp
  nonAppTTime /= numNonApp
  totalTTime  /= (numApp + numNonApp)
  dm.printTraverseSingleDB(thisPercentage, appTTime, numApp, nonAppTTime, numNonApp, totalTTime, (numApp + numNonApp), debug)
  return appTTime, nonAppTTime, totalTTime

def sortBasedOnPercentage(percentage, appTTime, nonAppTTime, totalTTime):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = zip(percentage, appTTime, nonAppTTime, totalTTime)
  zipped.sort()
  unzip  = zip(*zipped)
  sPercentage, sAppTTime, sNonAppTTime, sTotalTTime = map(list, unzip)
  return sPercentage, sAppTTime, sNonAppTTime, sTotalTTime

def traverseMultiDB(fileList, debug, maxTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
  percentage = []
  appTTime   = []
  nonAppTTime= []
  totalTTime = []
  for filename in fileList:
    thisPercentage = getPercentage(filename)
    thisAppTTime, thisNonAppTTime, thisTotalTTime = extractSingleDB(filename, thisPercentage, debug, maxTime)
    percentage.append(thisPercentage)
    appTTime.append(thisAppTTime)
    nonAppTTime.append(thisNonAppTTime)
    totalTTime.append(thisTotalTTime)
  percentage, appTTime, nonAppTTime, totalTTime = sortBasedOnPercentage(percentage, appTTime, nonAppTTime, totalTTime)
  return percentage, appTTime, nonAppTTime, totalTTime

def generatePlot(percentage, appTTime, nonAppTTime, totalTTime):
  #-----------------------------------------------------------#
  # Helper function for generating a plot that compares the   #
  # travel time of App users and non-App users with respect to#
  # the percentage of App users in the network                #
  #-----------------------------------------------------------#
  font = {'family':'normal',
          'weight':'bold',
          'size':24}
  plt.rc('font', **font)
  fig, ax1 = plt.subplots(figsize = (24, 14), dpi = 100)
  lineApp,    = plt.plot(percentage, appTTime, 'r', label = 'average app travel time', linewidth = 5.0)
  lineNonApp, = plt.plot(percentage, nonAppTTime, 'g', label = 'average non-app travel time', linewidth = 5.0)
  lineAll,    = plt.plot(percentage, totalTTime, 'b', label = 'average overall travel time', linewidth = 5.0)
  plt.grid(color = 'b', linestyle = '--', linewidth = 2)
  plt.legend(handles = [lineApp, lineNonApp, lineAll])
  plt.ylabel('Average Travel Time (sec)')
  plt.xlabel('Percentage of App Users (%)')
  plt.title('Percentage of App Users - Average Travel Time of Different User Classes')
  plt.savefig('outputFigures/percentage-traveltime.png', dpi = 'figure')
  print('plotting complete, results saved under ./outputFigures/\n')

def printUsage(): 
  print('usage: \n\t python extractMultiSQLite.py directoryName showAllMessages maxEntranceTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('system exiting...')
  sys.exit() 

def std2Call(dirName, maxTime):
  print('---------------------------------------')
  print('       executing std2 plots            ')
  print('---------------------------------------')
  fileList = getAllFilenames(dirName)
  percentage, appTTime, nonAppTTime, totalTTime = traverseMultiDB(fileList, True, maxTime)
  generatePlot(percentage, appTTime, nonAppTTime, totalTTime)
  

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  dirName  = sys.argv[1]
  debug    = sys.argv[2]
  maxTime  = int(sys.argv[3])
  fileList = getAllFilenames(dirName)
  dm.printObjFiles(fileList, debug)
  percentage, appTTime, nonAppTTime, totalTTime = traverseMultiDB(fileList, debug, maxTime)
  dm.printTraverseResults(percentage, appTTime, nonAppTTime, debug)
  generatePlot(percentage, appTTime, nonAppTTime, totalTTime)
