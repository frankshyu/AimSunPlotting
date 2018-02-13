import sqlite3
import sys
import os
import csv
import math
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from os import walk
from utilities import getPercentage, getNumVehicles, getAllFilenames, getODPair

#------------------------------------------------------------#
# Global variables to plot additional lines to describe when #
# an event (i.e., an accident) starts.                       #
#------------------------------------------------------------#
plotEvent = True
eventStart= 30
eventEnd  = 60

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
    thisTStep, thisAbsNash, thisRltNash = extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxT)
    percentage.append(thisPercentage)
    absNash.append(thisAbsNash)
    rltNash.append(thisRltNash)
    tStep = thisTStep
  percentage, absNash, rltNash = sortBasedOnPercentage(percentage, absNash, rltNash)
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
  '''
  font = {'family':'normal',
          'weight':'bold',
          'size':6}
  plt.rc('font', **font)
  # Plot multiple figures                                     #
  plt.figure(1, figsize = (24, 14), dpi = 100)
  for i in xrange(len(percentage)):
    thisAx = plt.subplot(5, 4, i + 1)
    thisAx.set_xlabel('Time Step (#)')
    thisAx.set_ylabel('Absolute Nash Distance (sec)')
    thisAx.plot(timeStep, absNash[i], color = (0,0,1), label = 'Abs Nash Distance', dashes = [10, 5], linewidth = 2.0)
    thisAx.set_ylim(0, max(absNash[i])*1.1)
    # THIS LINE IS ONLY FOR PLOTTING A SINGLE LINE THAT REPRESENTS THE #
    # START OF THE ACCIDENT, THIS IS NOT FOR ANY GENERALIZED PLOTTING! #
    #thisAx.plot([30, 30], [0, max(absNash[i])*1.1], color = (0,0,0), dashes = [2, 2], linewidth = 2.0)
    #thisAx.plot([60, 60], [0, max(absNash[i])*1.1], color = (0,0,0), dashes = [2, 2], linewidth = 2.0)
    #------------------------------------------------------------------#
    thisAx2 = thisAx.twinx()
    thisAx2.set_ylabel('Relative Nash Distance (%)')
    thisAx2.plot(timeStep, rltNash[i], color = (1,0,0), label = 'Rlt Nash Distance', dashes = [10, 5], linewidth = 2.0)
    thisAx.set_title('Nash Distance for app user percentage {}%'.format(percentage[i]))
    hand1, lab1 = thisAx.get_legend_handles_labels()
    hand2, lab2 = thisAx2.get_legend_handles_labels()
    firstLegend = plt.legend(handles = hand1, loc = 1)
    dummy       = plt.gca().add_artist(firstLegend)
    plt.legend(handles = hand2, loc = 2)
  plt.savefig('outputFigures/single_timestep_ND.png')
  '''
  # For plotting the timestep - abs Nash Distance graph #
  font = {'family':'normal',
          'weight':'bold',
          'size':20}
  plt.rc('font', **font)
  fig, ax = plt.subplots(figsize = (24, 14), dpi = 100)
  for i in xrange(len(percentage)):
    ax.plot(timeStep, absNash[i], color = (1 - float(percentage[i])/100, 0, float(percentage[i])/100), \
            label = 'Abs Nash Distance of percentage {}'.format(percentage[i]), \
            linewidth = 4.0)
    hand, lab = ax.get_legend_handles_labels()
    plt.legend(handles = hand, loc = 1)
  ax.set_ylim(0, max(max(absNash)) * 2)
  ax.set_xlabel('Time Step (#)')
  ax.set_ylabel('Absolute Nash Distance (sec)')
  ax.set_title('Absolute Nash Distance for Different App User Percentages')
  if plotEvent:
    ax.plot([eventStart, eventStart], [0, max(max(absNash)) * 2], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
    ax.plot([eventEnd, eventEnd], [0, max(max(absNash)) * 2], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
  plt.savefig('outputFigures/absND.png', dpi = 'figure')

  # For plotting the timestep - rlt Nash Distance graph #
  font = {'family':'normal',
          'weight':'bold',
          'size':20}
  plt.rc('font', **font)
  fig, ax = plt.subplots(figsize = (24, 14), dpi = 100)
  for i in xrange(len(percentage)):
    ax.plot(timeStep, rltNash[i], color = (0, 1 - float(percentage[i])/100, float(percentage[i])/100), \
            label = 'Rlt Nash Distance of percentage {}'.format(percentage[i]), \
            linewidth = 4.0)
    hand, lab = ax.get_legend_handles_labels()
    plt.legend(handles = hand, loc = 1)
  ax.set_ylim(0, max(max(rltNash)) * 2)
  ax.set_xlabel('Time Step (#)')
  ax.set_ylabel('Relative Nash Distance (sec)')
  ax.set_title('Relative Nash Distance for Different App User Percentages')
  if plotEvent:
    ax.plot([eventStart, eventStart], [0, max(max(absNash)) * 2], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
    ax.plot([eventEnd, eventEnd], [0, max(max(absNash)) * 2], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
  plt.savefig('outputFigures/rltND.png', dpi = 'figure')
  
  print('plotting complete, results saved under ./outputFigures/\n')

def printUsage(): 
  print('usage: \n python extractMultiSQLite.py directoryName showAllMessages maxEntranceTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('maxEntranceTime: the maximum time cars are allowed to enter the network')
  print('system exiting...')
  sys.exit()

def std4Call(dirName, maxTime):
  print('---------------------------------------')
  print('       executing std4 plots            ')
  print('---------------------------------------')
  fileList = getAllFilenames(dirName)
  percentage, timeStep, absNash, rltNash = traverseMultiDB(fileList, True, maxTime)
  generatePlot(percentage, timeStep, absNash, rltNash)

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  dirName  = sys.argv[1]
  debug    = sys.argv[2]
  maxEntranceTime = float(sys.argv[3])
  fileList = getAllFilenames(dirName)
  dm.printObjFiles(fileList, debug)
  percentage, timeStep, absNash, rltNash = traverseMultiDB(fileList, debug, maxEntranceTime)
  generatePlot(percentage, timeStep, absNash, rltNash)
