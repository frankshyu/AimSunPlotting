import sqlite3
import sys
import os
import re
import csv
import math
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
  cur.execute('SELECT oid, sid FROM MIVEHTRAJECTORY WHERE entranceTime > 0 AND exitTime > 0')
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

def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxT):
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

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, entranceTime, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND entranceTime > 0 AND entranceTime < {} AND origin = {} AND destination = {}'.format(maxT, oriId, desId))
  vehTTime = cur.fetchall()
  con.close()
  # Key: essentially the timestep (tStep below), this is because we are #
  #      targeting a specific O/D pair.                                 #
  tStepAccumTime = {}
  tStepAccumCount= {}
  tStepMinTime   = {}
  for i in xrange(len(vehTTime)):
    thisTStep = math.ceil(vehTTime[i][1]/60)
    if thisTStep in tStepAccumTime:
      tStepAccumTime[thisTStep] += vehTTime[i][2]
      tStepAccumCount[thisTStep]+= 1
      if vehTTime[i][2] < tStepMinTime[thisTStep]:
        tStepMinTime[thisTStep] = vehTTime[i][2]
    else:
      tStepAccumTime[thisTStep]  = vehTTime[i][2]
      tStepAccumCount[thisTStep] = 1
      tStepMinTime[thisTStep]    = vehTTime[i][2]
  tStep   = []
  absNash = []
  rltNash = []
  for key in tStepAccumTime.keys():
    tStep.append(key)
    absNash.append(tStepAccumTime[key]/tStepAccumCount[key] - tStepMinTime[key])
    rltNash.append(tStepAccumTime[key]/(tStepAccumCount[key] * tStepMinTime[key]) - 1)
  zipped = zip(tStep, absNash, rltNash)
  zipped.sort()
  unzip  = zip(*zipped)
  sTStep, sAbsNash, sRltNash = map(list, unzip)
  return sTStep, sAbsNash, sRltNash

def sortBasedOnPercentage(percentage, absNash, rltNash):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = zip(percentage, absNash, rltNash)
  zipped.sort()
  unzip  = zip(*zipped)
  sPercentage, sAbsNash, sRltNash = map(list, unzip)
  return sPercentage, sAbsNash, sRltNash

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

def traverseMultiDB(fileList, debug, maxT):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
  percentage = []
  absNash    = []
  rltNash    = []
  tStep      = []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisTStep, thisAbsNash, thisRltNash = \
      extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxT)
    percentage.append(thisPercentage)
    absNash.append(thisAbsNash)
    rltNash.append(thisRltNash)
    tStep = thisTStep
  percentage, absNash, rltNash = \
    sortBasedOnPercentage(percentage, absNash, rltNash)
  return percentage, tStep, absNash, rltNash

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

def generatePlot(percentage, timeStep, absNash, rltNash):
  #-----------------------------------------------------------#
  # Helper function for generating a plot that compares the   #
  # travel time of App users and non-App users with respect to#
  # the percentage of App users in the network                #
  #-----------------------------------------------------------#
  font = {'family':'normal',
          'weight':'bold',
          'size':6}
  plt.rc('font', **font)
  # Plot multiple figures                                     #
  plt.figure(1)
  for i in xrange(len(percentage)):
    thisAx = plt.subplot(3, 4, i + 1)
    thisAx.set_xlabel('Time Step (#)')
    thisAx.set_ylabel('Absolute Nash Distance (sec)')
    thisAx.plot(timeStep, absNash[i], color = (0,0,1), label = 'Abs Nash Distance', dashes = [10, 5], linewidth = 2.0)
    thisAx.set_ylim(0, max(absNash[i])*1.1)
    # THIS LINE IS ONLY FOR PLOTTING A SINGLE LINE THAT REPRESENTS THE #
    # START OF THE ACCIDENT, THIS IS NOT FOR ANY GENERALIZED PLOTTING! #
    thisAx.plot([30, 30], [0, max(absNash[i])*1.1], color = (1,0,0), dashes = [2, 2], linewidth = 2.0)
    #------------------------------------------------------------------#
    thisAx2 = thisAx.twinx()
    thisAx2.set_ylabel('Relative Nash Distance (%)')
    thisAx2.plot(timeStep, rltNash[i], color = (0,1,0), label = 'Rlt Nash Distance', dashes = [10, 5], linewidth = 2.0)
    thisAx.set_title('Nash Distance for app user percentage {}%'.format(percentage[i]))
    hand1, lab1 = thisAx.get_legend_handles_labels()
    hand2, lab2 = thisAx2.get_legend_handles_labels()
    firstLegend = plt.legend(handles = hand1, loc = 1)
    dummy       = plt.gca().add_artist(firstLegend)
    plt.legend(handles = hand2, loc = 2)
  plt.show()
  font = {'family':'normal',
          'weight':'bold',
          'size':14}
  plt.rc('font', **font)
  fig, ax = plt.subplots()
  for i in xrange(len(percentage)):
    ax.plot(timeStep, absNash[i], color = (1 - float(percentage[i])/100, 0, float(percentage[i])/100), \
             label = 'Abs Nash Distance of percentage {}'.format(percentage[i]), \
             linewidth = 2.0)
    hand, lab = ax.get_legend_handles_labels()
    plt.legend(handles = hand, loc = 1)
  ax.set_ylim(0, max(max(absNash)) * 1.1)
  ax.set_xlabel('Time Step (#)')
  ax.set_ylabel('Absolute Nash Distance (sec)')
  ax.set_title('Absolute Nash Distance for different percentages of app user')
  # THIS LINE IS ONLY FOR PLOTTING A SINGLE LINE THAT REPRESENTS THE #
  # START OF THE ACCIDENT, THIS IS NOT FOR ANY GENERALIZED PLOTTING! #
  ax.plot([30, 30], [0, max(max(absNash)) * 1.1], color = (0, 0, 0), dashes = [2, 2], linewidth = 2.0)
  #------------------------------------------------------------------#
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
  print('usage: \n python extractMultiSQLite.py directoryName showAllMessages maxEntranceTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('maxEntranceTime: the maximum time cars are allowed to enter the network')
  print('system exiting...')
  sys.exit() 

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  dirName  = sys.argv[1]
  debug    = sys.argv[2]
  maxEntranceTime = float(sys.argv[3])
  outName  = getCsvOutputName(dirName)
  fileList = getAllFilenames(dirName)
  dm.printObjFiles(fileList, debug)
  percentage, timeStep, absNash, rltNash = traverseMultiDB(fileList, debug, maxEntranceTime)
  generatePlot(percentage, timeStep, absNash, rltNash)
