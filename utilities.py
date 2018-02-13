import re
import os
from os import walk
import sqlite3
#---------------------------------------------------#
# File name in the following list will be neglected #
#---------------------------------------------------#
unwantedFileNames = ['hohoho.txt']

def getPercentage(longFileName):
  fileName = longFileName.split('/')
  fileName = fileName[-1]
  percentage = int(re.search(r'\d+', fileName).group())
  return percentage

def getNumVehicles(fileName, maxTime):
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
  cur.execute('SELECT oid, sid FROM MIVEHTRAJECTORY WHERE (entranceTime > 0 AND exitTime > 0 AND entranceTime < {})'.format(maxTime))
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

def getAllFilenames(dirName):
  #----------------------------------------------------------#
  # Helper function to traverse the given directory, returns #
  # a list of filenames                                      #
  #----------------------------------------------------------#
  f = []
  cwd = os.getcwd()
  for (dirpath, dirnames, filenames) in walk(dirName):
    f.extend(filenames)
  for i in range(len(unwantedFileNames)):
    if unwantedFileNames[i] in f:
      f.remove(unwantedFileNames[i])
  for i in range(len(f)):
    f[i] = dirName + f[i]
  return f

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
    print("\tOD: {}, corresponding number: {}".format(key, value))
  desiredId = input("please enter the corresponding number of your desired O/D\n")
  print("desired od is {}, {}".format(idODict[desiredId], idDDict[desiredId]))
  return idODict[desiredId], idDDict[desiredId]

