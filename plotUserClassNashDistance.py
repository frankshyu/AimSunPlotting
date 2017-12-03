import sqlite3
import sys
import os
import re
import csv
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from os import walk

def output2CSV(percentage, appTTime, nonAppTTime, totalTTime, csvFileName): 
  #----------------------------------------------------------#
  # Helper function to dump all results in a .csv file       #
  #----------------------------------------------------------#
  f = open(csvFileName, 'w')
  writer = csv.writer(f)
  writer.writerow(['Percentage', 'avg app travel time', 'avg non-app travel time', 'avg overall travel time'])
  for i in xrange(len(percentage)):
    writer.writerow([percentage[i], appTTime[i], nonAppTTime[i], totalTTime[i]])
  f.close()

def getAllFilenames(dirName):
  #----------------------------------------------------------#
  # Helper function to traverse the given directory, returns #
  # a list of filenames                                      #
  #----------------------------------------------------------#
  f = []
  cwd = os.getcwd()
  for (dirpath, dirnames, filenames) in walk(dirName):
    f.extend(filenames)
  for i in range(len(f)):
    f[i] = dirName + f[i]
  return f

def getPercentage(fileName):
  percentage = int(re.search(r'\d+', fileName).group())
  return percentage

def getNumVehicles(fileName):
  #----------------------------------------------------------#
  # Get the number of vehicles in a database                 #
  #----------------------------------------------------------#
  # 862 = car_app class id, 863 = car_nonapp class id, this  #
  # part is incomplete because the classes are hard-coded,   #
  # should find way to solve this TODO Frank commented on 11/#
  # 17/2017                                                  #
  appClassId    = 862
  nonAppClassId = 863
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  # oid = object id, sid = class
  cur.execute('SELECT oid, sid FROM MIVEHTRAJECTORY WHERE (entranceTime > 0 AND exitTime > 0 AND entranceTime < 3600)')
  rows = cur.fetchall()
  con.close()
  appCount    = 0
  nonAppCount = 0
  for row in rows:
    if row[1] == appClassId:
      appCount += 1
    else:
      nonAppCount += 1
  return appCount, nonAppCount

def extractSingleDB(fileName, thisPercentage, debug):
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
  numApp, numNonApp = getNumVehicles(fileName)
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, sid, entranceTime, exitTime, origin, destination FROM MIVEHTRAJECTORY WHERE (entranceTime > 0 AND exitTime > 0 AND entranceTime < 3600)')
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

def traverseMultiDB(fileList, debug):
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
      = extractSingleDB(filename, thisPercentage, debug)
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
  fig, ax1 = plt.subplots()
  ax1.set_xlabel('Percentage of app users (%)')
  ax1.set_ylabel('Average travel time / Absolute Nash Distance (sec)')
  ax1.plot(percentage, absND, color = (0, 0, 0), label = 'Absolute Nash Distance', dashes = [2,2], linewidth = 3.0)
  ax2      = ax1.twinx()
  ax2.set_ylabel('Relative Nash Distance (%)')
  ax2.plot(percentage, rltND, color = (0, 0, 0), label = 'Relative Nash Distance', dashes = [10, 5, 2, 5], linewidth = 3.0)
  lineApp,    = ax1.plot(percentage, appTTime, 'r', label = 'mean app travel time')
  lineNonApp, = ax1.plot(percentage, nonAppTTime, 'g', label = 'mean non-app travel time')
  lineAll,    = ax1.plot(percentage, totalTTime, 'b', label = 'mean overall travel time')
  plt.title('Path flow / Travel time v.s. Percentage of App Users')
  hand1, lab1 = ax1.get_legend_handles_labels()
  hand2, lab2 = ax2.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 1)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.legend(handles = hand2, loc = 2)
  plt.show()

def getCsvOutputName(dirName):
  #-----------------------------------------------------------#
  # Helper function to generate the output csv filename based #
  # on the current date                                       #
  #-----------------------------------------------------------#
  dirNames = dirName.split('/')
  print(dirNames)
  now      = datetime.datetime.now()
  thisName = 'outputCsvfiles/' + dirNames[len(dirNames) - 2] + '_user_' + str(now.month) + str(now.day) + '.csv'
  return thisName

def printUsage(): 
  print('usage: \n python extractMultiSQLite.py directoryName showAllMessages')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('system exiting...')
  sys.exit() 

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 3:
    printUsage()
  dirName  = sys.argv[1]
  debug    = sys.argv[2]
  outName  = getCsvOutputName(dirName)
  fileList = getAllFilenames(dirName)
  dm.printObjFiles(fileList, debug)
  percentage, appTTime, nonAppTTime, totalTTime, absND, rltND = traverseMultiDB(fileList, debug)
  dm.printTraverseResults(percentage, appTTime, nonAppTTime, debug)
  output2CSV(percentage, appTTime, nonAppTTime, totalTTime, outName)
  generatePlot(percentage, appTTime, nonAppTTime, totalTTime, absND, rltND)
