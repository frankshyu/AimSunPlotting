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

def output2CSV(percentage, pathAvgTime, pathFlow, commonKeys, csvFileName): 
  #----------------------------------------------------------#
  # Helper function to dump all results in a .csv file       #
  # TODO: Extend to write pathFlow as well, Frank on 1125    #
  #----------------------------------------------------------#
  f = open(csvFileName, 'w')
  writer = csv.writer(f)
  firstRow = ['Path Name']
  # Write all the travel time for common keys (i.e paths)    #
  for i in xrange(len(percentage)):
    firstRow.append(percentage[i])
  writer.writerow(firstRow)
  for commonKey in commonKeys:
    thisRow = [commonKey]
    for i in xrange(len(pathAvgTime)):
      thisRow.append(pathAvgTime[i][commonKey])
    writer.writerow(thisRow)
    del thisRow
  # Write travel time for each percentage of app user         #
  writer.writerow(['Percentage', 'Path Set', 'Path AvgTime'])
  for i in xrange(len(percentage)):
    writer.writerow([percentage[i], 'N/A','N/A'])
    for key, value in pathAvgTime[i].items():
      writer.writerow(['N/A', key, value])
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
  cur.execute('SELECT oid, sid FROM MIVEHTRAJECTORY WHERE (entranceTime > 0 AND exitTime > 0)')
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

def extractSingleDB(fileName, thisPercentage, debug, oriId, desId):
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
  numApp, numNonApp = getNumVehicles(fileName)
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
      pathSet = frozenset(pathList)
      vehPathDict[thisOid] = pathSet
    elif lastOid != thisOid:
  # Completed finding the path for 1 single car, record the results #
      pathSet = frozenset(pathList)
      vehPathDict[lastOid] = pathSet
      del pathList
      del pathSet
      pathList = []
      pathList.append(rows[i][2])
      lastOid  = thisOid
    else:
  # Add a new section to the path of this car                       #
      pathList.append(rows[i][2])

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND entranceTime > 0 AND origin = {} AND destination = {}'.format(oriId, desId))
  vehTTime = cur.fetchall()
  con.close()
  # Then, for each car, we lookup the travel time and add the result#
  # to the corresponding path                                       #
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
  #pathAccumTime, pathAccumCount = removeSubsetPaths(pathAccumTime, pathAccumCount)
  for key, value in pathAccumCount.items():
    pathAvgTime[key] = pathAccumTime[key]/pathAccumCount[key]
    countArrived += value
    print('path: {}, vehicles count: {}'.format( key, pathAccumCount[key]))

  # We are also interested in the vehicles that have alread entered  #
  # the network but has not finished the trip yet                    #
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT COUNT(oid) FROM MIVEHTRAJECTORY WHERE exitTime = -1.0 AND entranceTime > 0')
  vehStuck = cur.fetchall()
  con.close()
  countStuck = vehStuck[0][0]
  # dirty code beneath!!
  countNonEnter = 10000 - countStuck - countArrived
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
  commonKeys = set(sPathAvgTime[0].keys())
  for i in xrange(len(sPathAvgTime)):
    commonKeys.intersection_update(sPathAvgTime[i].keys())
  print('===========The Common Keys Are:===========')
  print(commonKeys)
  print('==========================================')
  return sPercentage, sPathAvgTime, sPathFlow, commonKeys, sCountNonEnter, sCountStuck

def getODPair(fileName):
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT origin, destination FROM MIVEHTRAJECTORY')
  rows = cur.fetchall()
  con.close()
  currId  = 0
  idOdDict= {}
  idODict = {}
  idDDict = {}
  for row in rows:
    thisSet = frozenset([row[0], row[1]])
    if thisSet not in idOdDict.values():
      idOdDict[currId] = thisSet
      idODict[currId]  = row[0]
      idDDict[currId]  = row[1]
      currId += 1
    del thisSet
  for key, value in idOdDict.items():
    print("{}, {}".format(key, value))
  desiredId = input("please enter your desired O/D\n")
  print("desired od is {}, {}".format(idODict[desiredId], idDDict[desiredId]))
  return idODict[desiredId], idDDict[desiredId]

def traverseMultiDB(fileList, debug):
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
      extractSingleDB(filename, thisPercentage, debug, oriId, desId)
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
          'size':14}
  plt.rc('font', **font)
  colorChoices, startingColor = getColorChoices()
  fig, ax1 = plt.subplots()
  ax1.set_xlabel('Percentage of app users (%)')
  ax1.set_ylabel('Average travel time (sec)')
  ax2      = ax1.twinx()
  ax2.set_ylabel('Cumulative flow (#)')
  ax2.plot(percentage, countNonEnter, color = (0, 0, 0), label = 'vehicles failed to enter network', dashes = [10, 5, 2, 5], linewidth = 3.0)
  ax2.plot(percentage, countStuck, color = (0, 0, 0), label = 'vehicles stuck in network', dashes = [2,2], linewidth = 3.0)
  for key in commonKeys:
    avgPathTTime  = []
    localPathFlow = []
    for i in xrange(len(pathAvgTime)):
      avgPathTTime.append(pathAvgTime[i][key])
      localPathFlow.append(pathFlow[i][key])
    ax1.plot(percentage, avgPathTTime, colorChoices[startingColor % 8], label = ('travel time of path ' + str(key)))
    ax2.plot(percentage, localPathFlow, colorChoices[startingColor % 8], label = ('vehicles arrived by taking path '+ str(key)), dashes = [10,5])
    startingColor += 1
    if startingColor == 8:
      print('WARNING: number of paths plotted is more than the choice of colors, may need to manually add in more colors!')
  #lineAll,    = plt.plot(percentage, totalTTime, 'b', label = 'mean overall travel time')
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
  thisName = 'outputCsvfiles/' + dirNames[len(dirNames) - 2] + '_path_' + str(now.month) + str(now.day) + '.csv'
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
  percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck = traverseMultiDB(fileList, debug)
  output2CSV(percentage, pathAvgTime, pathFlow, commonKeys, outName)
  generatePlot(percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck)
