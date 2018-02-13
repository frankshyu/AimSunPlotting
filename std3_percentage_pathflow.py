import sqlite3
import sys
import os
import csv
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from os import walk
from utilities import getAllFilenames, getPercentage, getNumVehicles, getODPair

#---------------------------------------------------#
# The total demand of the network has to be manually#
# keyed in. This is because there will be cars that #
# fail to enter the network.                        #
#---------------------------------------------------#
totalDemand = 10000

def removeSubsetPaths(pathAccumTime, pathAccumCount):
  #----------------------------------------------------------#
  # Helper function to remove paths that are subsets of other#
  # paths. For example, if a path contains sections (1, 2, 3)#
  # and there is another path that contains sections (1, 2), #
  # the latter one will be removed                           #
  # ---------------------------------------------------------#
  newPathAccumTime = {} 
  newPathAccumCount= {}
  for key in pathAccumTime.keys():
    isSubset = False
    for compKey in pathAccumTime.keys():
      if (key.issubset(compKey) and key != compKey ):
        isSubset = True
    if (not isSubset):
      newPathAccumTime[key] = pathAccumTime[key]
      newPathAccumCount[key]= pathAccumCount[key]
  return newPathAccumTime, newPathAccumCount

def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxTime):
  #----------------------------------------------------------#
  # Helper function to traverse single SQLite DB and return  #
  # the average travel time of different paths               #
  #----------------------------------------------------------#
  # Extracting the interested columns from the database, the #
  # columns of the extracted data are                        #
  # (0) oid, the object id for the generated vehicles        #
  # (1) end, the order of the section traversal for a vehicle#
  # (2) sectionId, the id for the road section               #
  # (3) travelTime, the travel time on the specific section  #
  print('extracting database:')
  print(fileName)
  numApp, numNonApp = getNumVehicles(fileName, maxTime)
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, ent, sectionId, travelTime FROM MIVEHSECTTRAJECTORY ORDER BY oid ASC, ent ASC')
  rows = cur.fetchall()
  con.close()
  # First we build up the vehicle - path relation for fast lookup   #
  pathList    = []
  lastOid     = rows[0][0]
  vehPathDict = {}
  for i in xrange(len(rows)):
    thisOid = rows[i][0]
    if i == (len(rows) - 1 ):
      pathList.append(rows[i][2])
      pathSet = frozenset(pathList)
      vehPathDict[thisOid] = pathSet
    elif lastOid != thisOid:
  # Completed finding the path for 1 single car, record the results  #
      pathSet = frozenset(pathList)
      vehPathDict[lastOid] = pathSet
      del pathList
      del pathSet
      pathList = []
      pathList.append(rows[i][2])
      lastOid  = thisOid
    else:
  # Add a new section to the path of this car                        #
      pathList.append(rows[i][2])

  # Now we select all cars that succeeded in entering and exiting the#
  # network.                                                         #
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND origin = {} AND destination = {} AND entranceTime < {}'.format(oriId, desId, maxTime))
  vehTTime = cur.fetchall()
  con.close()
  # Then, for each car, we lookup the travel time and add the result #
  # to the corresponding path                                        #
  pathAccumTime = {}
  pathAccumCount= {}
  for i in xrange(len(vehTTime)):
    thisPath = vehPathDict[vehTTime[i][0]]
    if thisPath in pathAccumTime:
      pathAccumTime[thisPath] += vehTTime[i][1]
      pathAccumCount[thisPath]+= 1
    else:
      pathAccumTime[thisPath]  = vehTTime[i][1]
      pathAccumCount[thisPath] = 1
      
  pathAvgTime = {}
  countArrived= 0
  for key, value in pathAccumCount.items():
    pathAvgTime[key] = pathAccumTime[key]/pathAccumCount[key]
    countArrived += value
    print('path: {}, vehicles count: {}'.format( key, pathAccumCount[key]))

  # We are also interested in the vehicles that have alread entered  #
  # the network but has not finished the trip yet                    #
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT COUNT(oid) FROM MIVEHTRAJECTORY WHERE exitTime = -1 AND entranceTime > 0 AND entranceTime < {}'.format(maxTime))
  vehStuck = cur.fetchall()
  con.close()
  countStuck = vehStuck[0][0]
  # Here we aim to get the simulation length, denoted simLength. By  #
  # combining simLenght, maxTIme, and totolDemand, we can know how   #
  # many cars fail to enter the network, assuming that the cars are  #
  # generated in a uniform manner                                    # 
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT MAX(entranceTime) FROM MIVEHTRAJECTORY WHERE entranceTime > 0')
  simLength = cur.fetchall()
  con.close()
  simLength = simLength[0][0]
  countNonEnter = (totalDemand * maxTime / simLength) - (numApp + numNonApp + countStuck)
  print('{} distinct vehicles are stuck in the network'.format(countStuck))
  print('{} distinct vehicles failed to enter the network'.format(countNonEnter))
  return pathAvgTime, pathAccumCount, countNonEnter , countStuck

def sortBasedOnPercentage(percentage, pathAvgTime, pathFlow, countNonEnter, countStuck):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = zip(percentage, pathAvgTime, pathFlow, countNonEnter, countStuck)
  zipped.sort()
  unzip  = zip(*zipped)
  sPercentage, sPathAvgTime, sPathFlow, sCountNonEnter, sCountStuck = map(list, unzip)
  commonKeys = set(sPathAvgTime[len(sPathAvgTime) - 1].keys())
  for i in xrange(len(sPathAvgTime)):
    commonKeys.union(sPathAvgTime[i].keys())
  print('===========The Common Keys Are:===========')
  print(commonKeys)
  print('==========================================')
  return sPercentage, sPathAvgTime, sPathFlow, commonKeys, sCountNonEnter, sCountStuck

def traverseMultiDB(fileList, debug, maxTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
  percentage = []
  pathAvgTime= []
  pathFlow   = []
  countStuck = []
  countNonEnter = []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisPathAvgTime, thisPathFlow, thisNonEnter, thisStuckCount = \
      extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxTime)
    percentage.append(thisPercentage)
    pathAvgTime.append(thisPathAvgTime)
    pathFlow.append(thisPathFlow)
    countStuck.append(thisStuckCount)
    countNonEnter.append(thisNonEnter)
  percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck = \
    sortBasedOnPercentage(percentage, pathAvgTime, pathFlow, countNonEnter, countStuck)
  return percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck

def getColorChoices():
  #-----------------------------------------------------------#
  # Helper function for returning the ten color choices for   #
  # matplotlib, namely 'C0', 'C1', ..., and 'C9'              #
  #-----------------------------------------------------------#
  ret = []
  ret.append('b') 
  ret.append('g') 
  ret.append('r') 
  ret.append('c') 
  ret.append('m') 
  ret.append('y') 
  ret.append('k') 
  ret.append('w')
  return ret, 0

def generatePlot(percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck):
  #-----------------------------------------------------------#
  # Helper function for generating a plot that compares the   #
  # travel time of App users and non-App users with respect to#
  # the percentage of App users in the network                #
  #-----------------------------------------------------------#
  font = {'family':'normal',
          'weight':'bold',
          'size':24}
  plt.rc('font', **font)
  colorChoices, startingColor = getColorChoices()
  fig, ax1 = plt.subplots(figsize = (24, 14), dpi = 100)
  ax1.set_xlabel('Percentage of App Users (%)')
  ax1.set_ylabel('Path Flow (#)')
  ax1.grid(color = 'b', linestyle = '--', linewidth = 2)
  #ax1.set_ylim(0, max(max(pathFlow)) * 1.5)
  #ax2      = ax1.twinx()
  #ax2.set_ylabel('Cumulative flow (#)')
  ax1.plot(percentage, countNonEnter, color = (0, 0, 0), label = 'vehicles failed to enter network', dashes = [10, 5, 2, 5], linewidth = 5.0)
  ax1.plot(percentage, countStuck, color = (0, 0, 0), label = 'vehicles stuck in network', dashes = [2,2], linewidth = 5.0)
  for key in commonKeys:
    avgPathTTime  = []
    localPathFlow = []
    for i in xrange(len(pathAvgTime)):
      if key in pathAvgTime[i].keys():
        avgPathTTime.append(pathAvgTime[i][key])
        localPathFlow.append(pathFlow[i][key])
      else:
        avgPathTTime.append(0)
        localPathFlow.append(0)
    #ax1.plot(percentage, avgPathTTime, colorChoices[startingColor % 8], label = ('travel time of path ' + str(key)))
    ax1.plot(percentage, localPathFlow, colorChoices[startingColor % 8], label = ('vehicles arrived by taking path '+ str(startingColor)), linewidth = 5.0)
    startingColor += 1
    if startingColor == 8:
      print('WARNING: number of paths plotted is more than the choice of colors, may need to manually add in more colors!')
  #lineAll,    = plt.plot(percentage, totalTTime, 'b', label = 'mean overall travel time')
  plt.title('Percentage of App Users - Path Flow')
  hand1, lab1 = ax1.get_legend_handles_labels()
  #hand2, lab2 = ax2.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 1)
  dummy       = plt.gca().add_artist(firstLegend)
  #plt.legend(handles = hand2, loc = 2)
  plt.savefig('outputFigures/percentage-pathflow.png', dpi = 'figure')
  print('plotting complete, results saved under ./outputFigures/\n')

def getCsvOutputName(dirName):
  #-----------------------------------------------------------#
  # Helper function to generate the output csv filename based #
  # on the current date                                       #
  #-----------------------------------------------------------#
  dirNames = dirName.split('/')
  print(dirNames)
  now      = datetime.datetime.now()
  thisName = 'outputCsvfiles/' + dirNames[len(dirNames) - 2] + '_path_' + str(now.month) + str(now.day) + '.csv'
  return thisName

def printUsage(): 
  print('usage: \n\t python extractMultiSQLite.py directoryName showAllMessages maxTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('system exiting...')
  sys.exit()

def std3Call(dirName, maxTime):
  print('---------------------------------------')
  print('       executing std3 plots            ')
  print('---------------------------------------')
  fileList = getAllFilenames(dirName)
  percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck = traverseMultiDB(fileList, True, maxTime)
  generatePlot(percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck)

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  dirName  = sys.argv[1]
  debug    = sys.argv[2]
  maxTime  = int(sys.argv[3])
  fileList = getAllFilenames(dirName)
  dm.printObjFiles(fileList, debug)
  percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck = traverseMultiDB(fileList, debug, maxTime)
  generatePlot(percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck)
