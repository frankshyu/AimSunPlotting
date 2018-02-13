import sqlite3
import sys
import os
import csv
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from utilities import getNumVehicles, getPercentage, getAllFilenames
#---------------------------------------------------------------------#
# This python file takes in multiple sqlite DBs created by AimSun and #
# plot how the Relative and Absolute Nash Distances changes with the  #
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
  cur.execute('SELECT oid, sid, entranceTime, exitTime, origin, destination FROM MIVEHTRAJECTORY WHERE (entranceTime > 0 AND exitTime > 0 AND entranceTime < {})'.format(maxTime))
  rows = cur.fetchall()
  con.close()
  appId       = 862
  nonAppId    = 863
  totalTTime  = 0
  appTTime    = 0
  nonAppTTime = 0
  minTTime    = float(1000000000)
  for row in rows:
    thisTTime = float((row[3] - row[2]))
    if thisTTime < minTTime:
      minTTime = thisTTime
    if row[1] == appId:
      appTTime += thisTTime
    else: 
      nonAppTTime += (row[3] - row[2])
    totalTTime += thisTTime
  absNashDistance = totalTTime/(numApp + numNonApp) - minTTime
  rltNashDistance = 100*absNashDistance/minTTime
  appTTime    /= numApp
  nonAppTTime /= numNonApp
  totalTTime  /= (numApp + numNonApp)
  dm.printTraverseSingleDB(thisPercentage, appTTime, numApp, nonAppTTime, numNonApp, totalTTime, (numApp + numNonApp), debug)
  return appTTime, nonAppTTime, totalTTime, absNashDistance, rltNashDistance

def sortBasedOnPercentage(percentage, appTTime, nonAppTTime, totalTTime, absND, rltND):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = zip(percentage, appTTime, nonAppTTime, totalTTime, absND, rltND)
  zipped.sort()
  unzip  = zip(*zipped)
  sPercentage, sAppTTime, sNonAppTTime, sTotalTTime, sAbsND, sRltND = map(list, unzip)
  return sPercentage, sAppTTime, sNonAppTTime, sTotalTTime, sAbsND, sRltND

def traverseMultiDB(fileList, debug, maxTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
  percentage = []
  appTTime   = []
  nonAppTTime= []
  totalTTime = []
  absNashDistance = []
  rltNashDistance = []
  for filename in fileList:
    thisPercentage = getPercentage(filename)
    thisAppTTime, thisNonAppTTime, thisTotalTTime, thisAbsNashDistance, thisRltNashDistance \
      = extractSingleDB(filename, thisPercentage, debug, maxTime)
    percentage.append(thisPercentage)
    appTTime.append(thisAppTTime)
    nonAppTTime.append(thisNonAppTTime)
    totalTTime.append(thisTotalTTime)
    absNashDistance.append(thisAbsNashDistance)
    rltNashDistance.append(thisRltNashDistance)
  percentage, appTTime, nonAppTTime, totalTTime, absNashDistance, rltNashDistance \
    = sortBasedOnPercentage(percentage, appTTime, nonAppTTime, totalTTime, absNashDistance, rltNashDistance)
  return percentage, appTTime, nonAppTTime, totalTTime, absNashDistance, rltNashDistance

def generatePlot(percentage, appTTime, nonAppTTime, totalTTime, absND, rltND):
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
  ax1.set_xlabel('Percentage of App Users (%)')
  ax1.set_ylabel('Absolute Nash Distance (sec)')
  ax1.plot(percentage, absND, color = (0, 0, 0), label = 'Absolute Nash Distance', dashes = [2,2], linewidth = 5.0)
  ax1.grid(color = 'b', linestyle = '--', linewidth = 2)
  ax2      = ax1.twinx()
  ax2.set_ylabel('Relative Nash Distance (%)')
  ax2.plot(percentage, rltND, color = (0, 0, 0), label = 'Relative Nash Distance', dashes = [10, 5, 2, 5], linewidth = 5.0)
  ax2.set_yticks(np.linspace(ax2.get_yticks()[0], ax2.get_yticks()[-1], len(ax1.get_yticks())))
  plt.title('Percentage of App Users - Absolute/Relative Nash Distance')
  hand1, lab1 = ax1.get_legend_handles_labels()
  hand2, lab2 = ax2.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 3)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.legend(handles = hand2, loc = 1)
  plt.savefig('outputFigures/percentage-ND.png', dpi = 'figure')
  print('plotting complete, results saved under ./outputFigures/\n')

def printUsage(): 
  print('usage: \n\t python extractMultiSQLite.py directoryName showAllMessages maxEntranceTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('system exiting...')
  sys.exit() 

def std1Call(dirName, maxTime):
  print('---------------------------------------')
  print('       executing std1 plots            ')
  print('---------------------------------------')
  fileList = getAllFilenames(dirName)
  percentage, appTTime, nonAppTTime, totalTTime, absND, rltND = traverseMultiDB(fileList, True, maxTime)
  generatePlot(percentage, appTTime, nonAppTTime, totalTTime, absND, rltND)

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  dirName  = sys.argv[1]
  debug    = sys.argv[2]
  maxTime  = int(sys.argv[3])
  fileList = getAllFilenames(dirName)
  dm.printObjFiles(fileList, debug)
  percentage, appTTime, nonAppTTime, totalTTime, absND, rltND = traverseMultiDB(fileList, debug, maxTime)
  dm.printTraverseResults(percentage, appTTime, nonAppTTime, debug)
  generatePlot(percentage, appTTime, nonAppTTime, totalTTime, absND, rltND)
