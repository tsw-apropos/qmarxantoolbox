# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QMarxanToolbox
                                 A QGIS plugin
 Marxan Processing tools for QGIS
                              -------------------
        begin                : 2016-09-02
        copyright            : (C) 2016 by Apropos Information Systems Inc
        email                : tsw@aproposinfosytems.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Apropos Information Systems Inc'
__date__ = '2016-09-02'
__copyright__ = '(C) 2016 by Apropos Information Systems Inc'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from PyQt4 import QtCore, QtGui
from qgis.core import *
from qgis.gui import *
import os, sys, math
from processing.tools import dataobjects, vector
from collections import Counter
import numpy as np
from osgeo import ogr
from osgeo import gdal
import datetime, itertools

#
# qmtCalc - methods to calculate contents of planning units and write results
#

class qmtCalc:

        
    def __init__(self):

        self.wkbTypeGroups = {
            'POINT': (QGis.WKBPoint, QGis.WKBMultiPoint, QGis.WKBPoint25D, QGis.WKBMultiPoint25D,),
            'LINE': (QGis.WKBLineString, QGis.WKBMultiLineString, QGis.WKBLineString25D, QGis.WKBMultiLineString25D,),
            'POLYGON': (QGis.WKBPolygon, QGis.WKBMultiPolygon, QGis.WKBPolygon25D, QGis.WKBMultiPolygon25D,),
        }
        for key, value in self.wkbTypeGroups.items():
            for const in value:
                self.wkbTypeGroups[const] = key
        
    #
    # extract records from pu field
    #
    def puRecordsExtract(self,puLyr,idField,calcField):

        uniqueValues = set([])
        if puLyr.isValid():
            fields  = puLyr.dataProvider().fields()
            puidIdx = fields.indexFromName(idField)
            calcIdx = fields.indexFromName(calcField)
            total = puLyr.featureCount()
            current = 0
            lastPercent = 0.0
            featIter = puLyr.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            results = {}
            for feat in featIter:
                attr = feat.attributes()
                if attr[calcIdx] > 0:
                    if attr[puidIdx] in results:
                        # record exists for this puid
                        if attr[calcIdx] in results[attr[puidIdx]]:
                            # record exits for this puid and this unique value of calcfield value
                            results[attr[puidIdx]][attr[calcIdx]][0] += 1
                            results[attr[puidIdx]][attr[calcIdx]][1] += attr[calcIdx]
                            if attr[calcIdx] > results[attr[puidIdx]][attr[calcIdx]][2]:
                                results[attr[puidIdx]][attr[calcIdx]][2] = attr[calcIdx]
                            if attr[calcIdx] < results[attr[puidIdx]][attr[calcIdx]][3]:
                                results[attr[puidIdx]][attr[calcIdx]][3] = attr[calcIdx]
                        else:
                            # create this unique value of calcfield value within existing puid record
                            results[attr[puidIdx]][attr[calcIdx]] = [1,attr[calcIdx],attr[calcIdx],attr[calcIdx]]
                            if not attr[calcIdx] in uniqueValues:
                                uniqueValues.add(attr[calcIdx])
                    else:
                        # create record for this puid
                        # store array of [count, sum, max, min] for each calcField or unique value
                        results[attr[puidIdx]] = {attr[calcIdx] : [1,attr[calcIdx],attr[calcIdx],attr[calcIdx]]}
                        if not attr[calcIdx] in uniqueValues:
                            uniqueValues.add(attr[calcIdx])
                current += 1
                buildPercent = float(current) / float(total) * 100
        # close layer
        tempLayer = None
        # return results
        return(results,uniqueValues)

    #
    # Summarize Raw Measures and Performing Calculations
    #

    #
    # summarize single values for a pu
    #
    def valuesSummarizeSingle(self,puResults,calcType,intersectOp):

        #
        # Note that puResults looks like either
        # this:
        # {calcField or pixel value : [count, sum, max, min], cpv2 ... n : [count,sum,...]}
        # or this:
        # {0.0 : [count, sum, max, min]}
        # puResults[key][0] == count
        # puResults[key][1] == sum
        # puResults[key][2] == max
        # puResults[key][3] == min
        
        finalValue = None
        cnt = 0
        if calcType == 'measure':
            if intersectOp == 'sum':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][1]
                    else:
                        finalValue += puResults[key][1]
            elif intersectOp == 'mean':
                for key in puResults:
                    if finalValue == None:
                        cnt = puResults[key][0]
                        finalValue = puResults[key][1]
                    else:
                        cnt += puResults[key][0]
                        finalValue += puResults[key][1]
                finalValue = float(finalValue) / cnt
            elif intersectOp == 'max':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][2]
                    else:
                        finalValue += puResults[key][2]
            elif intersectOp == 'min':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][3]
                    else:
                        finalValue += puResults[key][3]
            elif intersectOp == 'count':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][0]
                    else:
                        finalValue += puResults[key][0]
            elif intersectOp == 'presence':
                for key in puResults:
                    if finalValue == None:
                        finalValue = 1
        elif calcType == 'field':
            if intersectOp == 'sum':
                for key in puResults:
                    if finalValue == None:
                        finalValue = float(key)
                    else:
                        finalValue += float(key)
            elif intersectOp == 'mean':
                for key in puResults:
                    if finalValue == None:
                        cnt = puResults[key][0]
                        finalValue = float(key)
                    else:
                        cnt += puResults[key][0]
                        finalValue += float(key)
                finalValue = float(finalValue) / cnt
            elif intersectOp == 'max':
                for key in puResults:
                    if finalValue == None:
                        finalValue = float(key)
                    else:
                        if float(key) > finalValue:
                            finalValue = float(key)
            elif intersectOp == 'min':
                for key in puResults:
                    if finalValue == None:
                        finalValue = float(key)
                    else:
                        if float(key) < finalValue:
                            finalValue = float(key)
            elif intersectOp == 'count':
                for key in puResults:
                    if finalValue == None:
                        finalValue = 1
                    else:
                        finalValue += 1
        else:
            # weighted
            if intersectOp == 'sum':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][1] * float(key)
                    else:
                        finalValue += puResults[key][1] * float(key)
            elif intersectOp == 'mean':
                for key in puResults:
                    if finalValue == None:
                        cnt = puResults[key][0]
                        finalValue = puResults[key][1] * float(key)
                    else:
                        cnt += puResults[key][0]
                        finalValue += puResults[key][1] * float(key)
                finalValue = float(finalValue) / cnt
            elif intersectOp == 'max':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][2] * float(key)
                    else:
                        if puResults[key][2] * float(key) > finalValue:
                            finalValue = puResults[key][2] * float(key)
            elif intersectOp == 'min':
                for key in puResults:
                    if finalValue == None:
                        finalValue = puResults[key][3] * float(key)
                    else:
                        if puResults[key][3] * float(key) < finalValue:
                            finalValue = puResults[key][3] * float(key)
            
        return(finalValue)

    #
    # summarize multiple values for a pu
    #
    def valuesSummarizeMulti(self,puResults,calcType,intersectOp):
        
        #
        # Note that puResults looks like either
        # this:
        # {calcField or pixel value : [count, sum, max, min], cpv2 ... n : [count,sum,...]}
        # or this:
        # {0.0 : [count, sum, max, min]}
        # puResults[key][0] == count
        # puResults[key][1] == sum
        # puResults[key][2] == max
        # puResults[key][3] == min

        finalValues = {}
        cnts = {}
        if calcType == 'measure':
            # multiple field measure only because weighted and field not possible
            if intersectOp == 'sum':
                for key in puResults:
                    if key in finalValues:
                        finalValues[key] += puResults[key][1]
                    else:
                        finalValues[key] = puResults[key][1]
            elif intersectOp == 'mean':
                for key in puResults:
                    if key in finalValues:
                        finalValues[key] += puResults[key][1] 
                        cnts[key] += puResults[key][0]
                    else:
                        finalValues[key] = puResults[key][1]
                        cnts[key] = puResults[key][0]
                for key in finalValues:
                    finalValues[key] = float(finalValues[key]) / cnts[key]
            elif intersectOp == 'max':
                for key in puResults:
                    if key in finalValues:
                        if puResults[key][2] > finalValues[key]:
                            finalValues[key] = puResults[key][2] 
                    else:
                        finalValues[key] = puResults[key][2]
            elif intersectOp == 'min':
                for key in puResults:
                    if key in finalValues:
                        if puResults[key][2] < finalValues[key]:
                            finalValues[key] = puResults[key][2]
                    else:
                        finalValues[key] = puResults[key][2]
            elif intersectOp == 'count':
                for key in puResults:
                    if key in finalValues:
                        finalValues[key] += puResults[key][0]
                    else:
                        finalValues[key] = puResults[key][0]
            elif intersectOp == 'presence':
                for key in puResults:
                    if not key in finalValues:
                        finalValues[key] = 1
                        
        return(finalValues)

    #
    # create attribute map for pu layer

    def valuesCreateAttributeMap(self,puResults,idxDict):

        # summarize by key
        results = {}
        if puResults == None:
            # nothing found so set all to zero
            for dKey, dValue in idxDict.iteritems():
                results[dValue] = 0.0
        else:
            for dKey, dValue in idxDict.iteritems():
                if dKey in puResults:
                    results[dValue] = puResults[dKey]
                else:
                    results[dValue] = 0.0
        return(results)

    #
    # single file output
    #
    def fileSingleOutput(self,progress,progMin,progMax,results,puLyr,idField,destName,calcType,intersectOp):

        # confirm it is valid
        if puLyr.isValid():
            fName = destName + '.qmd'
            f = open(fName,'w')
            f.write('puid,amount\n')
            x = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            featCnt = len(results)
            # 
            # old method didn't sort - made checks difficult
            #
            #for key, value in results.iteritems():
                #updateVal = self.valuesSummarizeSingle(value,calcType,intersectOp)
                #if updateVal <> 0.0:
                    #f.write('%d,%f\n' % (key,updateVal))
                #x += 1
                #progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                #if int(progPct) > lastPct:
                    #progress.setPercentage(progPct)
                    #lastPct = progPct
            # 
            # new method sorts before writing
            #        
            resList = results.items()
            resList.sort()
            for rec in resList:
                updateVal = self.valuesSummarizeSingle(rec[1],calcType,intersectOp)
                if updateVal <> 0.0:
                    f.write('%d,%f\n' % (rec[0],updateVal))
                x += 1
                progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            f.close()
            
    #
    # table file output
    #
    def fileTableOutput(self,progress,progMin,progMax,puLyr,idField,calcField,destName):

        # confirm it is valid
        if puLyr.isValid():
            # get reference information
            fields  = puLyr.dataProvider().fields()
            puidIdx = fields.indexFromName(idField)
            calcIdx = fields.indexFromName(calcField)
            # prepare to track progress
            x = 0
            progPct = progMin
            lastPct = progPct
            progRange = (progMax/2.0) - progMin
            featCnt = puLyr.featureCount()
            results = []
            # get iterator
            featIter = puLyr.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            for feat in featIter:
                attr = feat.attributes()
                if float(attr[calcIdx]) > 0.0:
                    results.append([int(attr[puidIdx]),float(attr[calcIdx])])
                x += 1
                progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            # sort
            results.sort()
            # prepare to write output
            fName = destName + '.qmd'
            f = open(fName,'w')
            f.write('puid,amount\n')
            x = 0
            progRange = progMax - lastPct
            for rec in results:
                f.write('%d,%f\n' % (rec[0],rec[1]))
                x += 1
                progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            f.close()
            
    #
    # multi file output
    #
    def fileMultiOutput(self,progress,progMin,progMax,results,puLyr,idField,destName,calcType,intersectOp,uniqueValues):

        # confirm it is valid
        if puLyr.isValid():
            outFiles = {}
            progress.setPercentage(progMin+1)
            for val in uniqueValues:
                fName = '%s-%03d.qmd' % (destName,int(val))
                outFiles[val] = open(fName,'w')
                outFiles[val].write('puid,amount\n')
            progress.setPercentage(progMin+2)
            for rKey, rValue in results.iteritems():
                updateValues = self.valuesSummarizeMulti(rValue,calcType,intersectOp)
                for cKey, cValue in updateValues.iteritems():
                    if cValue <> 0.0:
                        outFiles[cKey].write('%d,%f\n' % (rKey,cValue))
            x = 0
            progMin += 2
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            featCnt = len(outFiles)
            for fKey,fValue in outFiles.iteritems():
                fValue.close()
                x += 1
                progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct


    #
    # single field update pu layer
    #
    def puLayerSingleUpdate(self,results,puLyr,idField,destName,calcType,intersectOp):

        # confirm it is valid
        if puLyr.isValid():
            fields = puLyr.dataProvider().fields()
            puidIdx = fields.indexFromName(idField)
            destIdx = fields.indexFromName(destName)
            if destIdx == -1:
                try:
                    res = puLyr.dataProvider().addAttributes([QgsField(destName, QtCore.QVariant.Double, "real", 19, 10)])
                    puLyr.updateFields()
                    fields = puLyr.dataProvider().fields()
                    destIdx = fields.indexFromName(destName)
                except:
                    pass 
                if destIdx == -1:
                    return
            total = puLyr.featureCount()
            featIter = puLyr.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            updateMap = {}
            for feat in featIter:
                puid = feat.attributes()[puidIdx]
                if puid in results:
                    updateVal = self.valuesSummarizeSingle(results[puid],calcType,intersectOp)
                    updateMap[feat.id()] = {destIdx : updateVal}
                else:
                    updateMap[feat.id()] = {destIdx : 0.0}
            puLyr.dataProvider().changeAttributeValues(updateMap)

    #
    # multiple field update pu layer
    #
    def puLayerMultiUpdate(self,results,puLyr,idField,destName,calcType,intersectOp,uniqueValues):

        #QgsMessageLog.logMessage(str(uniqueValues))
        maxFields = 254
        # confirm it is valid
        if puLyr.isValid():
            fields = puLyr.dataProvider().fields()
            puidIdx = fields.indexFromName(idField)
            fldCount = len(fields) + len(uniqueValues)
            if fldCount > maxFields:
                self.abort = True
                raise NameError('Too many values to add fields for each')
                return 
            idxDict = {}
            for val in uniqueValues:
                fldName = '%s-%03d' % (destName,int(val))
                destIdx = fields.indexFromName(fldName)
                if destIdx == -1:
                    try:
                        res = puLyr.dataProvider().addAttributes([QgsField(fldName, QtCore.QVariant.Double, "real", 19, 10)])
                        puLyr.updateFields()
                        fields = puLyr.dataProvider().fields()
                        destIdx = fields.indexFromName(fldName)
                        idxDict[val] = destIdx
                    except:
                        pass
                else:
                    idxDict[val] = destIdx
            total = puLyr.featureCount()
            featIter = puLyr.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            updateMap = {}
            for feat in featIter:
                puid = feat.attributes()[puidIdx]
                if puid in results:
                    summarizedValues = self.valuesSummarizeMulti(results[puid],calcType,intersectOp)
                    updateValues = self.valuesCreateAttributeMap(summarizedValues,idxDict)
                else:
                    updateValues = self.valuesCreateAttributeMap(None,idxDict)
                updateMap[feat.id()] = updateValues
            puLyr.dataProvider().changeAttributeValues(updateMap)

#
# qmtGrid - methods to calculate grid cell count and create a grid
#

class qmtGrid:

    def __init__(self):
        pass
        
    #
    # calculate number of square cells
    #
    def calcSquareCount(self,sideLength,xMin,xMax,yMin,yMax):

        xRange = abs(xMax - xMin)
        xRows = xRange / float(sideLength)
        if xRows > int(xRows):
            xRows = int(xRows) + 1
        else:
            xRows = int(xRows)
        yRange = abs(yMax - yMin)
        yRows = yRange / float(sideLength)
        if yRows > int(yRows):
            yRows = int(yRows) + 1
        else:
            yRows = int(yRows)
        cellCount = xRows * yRows
        return(cellCount)

    #
    # calculate square side length based on area
    #
    def calcSquareSideLength(self,unitArea):

        squareSideLength = math.sqrt(unitArea)
        return(squareSideLength)

    #
    # calculate square area based on side length
    #
    def calcSquareArea(self,sideLength):

        squareArea = sideLength * sideLength
        return(squareArea)

    #
    # hexagon trig
    #
    def hexagonTrig(self,sideLength):
        
        # basic trig
        angle_a = math.radians(30)
        hyp = sideLength
        side_a = hyp * math.sin(angle_a)
        side_b = hyp * math.cos(angle_a)
        return(hyp,side_a,side_b)

    #
    # calculate number of hexagon cells
    #
    def calcHexagonCount(self,sideLength,xMin,xMax,yMin,yMax):

        hyp, side_a, side_b = self.hexagonTrig(sideLength)
        xUnits = hyp + side_a
        yUnits = side_b * 2
        xRange = abs(xMax - xMin)
        yRange = abs(yMax - yMin)
        xRows = xRange / float(xUnits)
        if xRows > int(xRows):
            xRows = int(xRows) + 1
        else:
            xRows = int(xRows)
        yRows = yRange / float(yUnits)
        if yRows > int(yRows):
            yRows = int(yRows) + 1
        else:
            yRows = int(yRows)
        cellCount = xRows * yRows
        return(cellCount)

    #
    # calculate hexagon side length based on area
    #
    def calcHexagonSideLength(self,unitArea):   

        triangleArea = unitArea/6.0
        #
        # area of an equilateral triangle = length^2 * sqrt(3)/4 
        # sqrt(3)/4 * area = length^2
        # sqrt( sqrt(3)/4 * area) = length
        #
        hexagonSideLength = math.sqrt( triangleArea / (math.sqrt(3.0)/4.0) )
        return(hexagonSideLength)

    #
    # calcualte hexagon area based on side length
    #
    def calcHexagonArea(self,sideLen):

        #
        # area of an equilateral triangle = length^2 * sqrt(3)/4 
        # sqrt(3)/4 * area = length^2
        # sqrt( sqrt(3)/4 * area) = length
        #
        tarea = float(sideLen)**2 * math.sqrt(3)/4
        return(tarea*6)

    #
    # create hexagon points
    #
    def createHexagon(self,x, y, sideLen):

        hyp, side_a, side_b = self.hexagonTrig(sideLen)
        # create points
        pt1 = QgsPoint(x, y)
        pt2 = QgsPoint(x + hyp, y)
        pt3 = QgsPoint(x + hyp + side_a, y - side_b)
        pt4 = QgsPoint(x + hyp, y - (2 * side_b))
        pt5 = QgsPoint(x, y - (2 * side_b))
        pt6 = QgsPoint(x - side_a, y - side_b)
        pt7 = QgsPoint(x, y)
        hexagon = [[pt1, pt2, pt3, pt4, pt5, pt6, pt7]]
        return(hexagon)

    #
    # create square
    #
    def createSquare(self,x, y, sideLen):

        pt1 = QgsPoint(x,y)
        pt2 = QgsPoint(x+sideLen,y)
        pt3 = QgsPoint(x+sideLen,y-sideLen)
        pt4 = QgsPoint(x,y-sideLen)
        pt5 = QgsPoint(x,y)
        square = [[pt1, pt2, pt3, pt4, pt5]]
        return(square)

#
# qmtSpatial - methods to preform intersections and other spatial calculations
#

class qmtSpatial:
    
    def __init__(self):
        
        self.gridTools = qmtGrid()
        self.wkbTypeGroups = {
            'POINT': (QGis.WKBPoint, QGis.WKBMultiPoint, QGis.WKBPoint25D, QGis.WKBMultiPoint25D,),
            'LINE': (QGis.WKBLineString, QGis.WKBMultiLineString, QGis.WKBLineString25D, QGis.WKBMultiLineString25D,),
            'POLYGON': (QGis.WKBPolygon, QGis.WKBMultiPolygon, QGis.WKBPolygon25D, QGis.WKBMultiPolygon25D,),
        }
        for key, value in self.wkbTypeGroups.items():
            for const in value:
                self.wkbTypeGroups[const] = key
        
    #
    # remove temporary files
    #
    def removeTempFile(self,fName):

        if os.path.exists(fName):
            rFName,ext = os.path.splitext(fName)
            if ext == '.shp':
                QgsVectorFileWriter.deleteShapeFile(fName)
                lfn = rFName + '.cpg'
                if os.path.exists(lfn):
                    os.remove(lfn)
            else:
                os.remove(fName)

    #
    # build squares
    #
    def buildSquares(self,progress,progMin,progMax,makeTemp,bbox,outFName,encoding,crs,puSideLength,tempPrefix,puidFieldName):

        # place squares from top left corner
        xMin = bbox[0]
        yMin = bbox[1]
        xMax = bbox[2]
        yMax = bbox[3]
        xExtra = (xMax - xMin) * 0.01
        yExtra = (yMax - yMin) * 0.01
        xMin = xMin - xExtra
        xMax = xMax + xExtra
        yMin = yMin - yExtra
        yMax = yMax + yExtra
        path,fname = os.path.split(outFName)            
        if makeTemp == True:
            fName = os.path.join(path, tempPrefix + 'grid.shp')
            sideLen = min((xMax -xMin) / 10.0, (yMax - yMin) / 10.0)
        else:
            fName = outFName
            sideLen = puSideLength
        fields = QgsFields()
        fields.append(QgsField(puidFieldName, QtCore.QVariant.Int))
        fields.append(QgsField("pu_status", QtCore.QVariant.Int))
        fields.append(QgsField("bnd_cost", QtCore.QVariant.Double, "real", 19, 10))
        fields.append(QgsField("area", QtCore.QVariant.Double, "real", 19, 10))
        fields.append(QgsField("perimeter", QtCore.QVariant.Double, "real", 19, 10))
        fields.append(QgsField("sidelength", QtCore.QVariant.Double, "real", 19, 10))
        check = QtCore.QFile(fName)
        if check.exists():
            if not QgsVectorFileWriter.deleteShapeFile(fName):
                return
        writer = QgsVectorFileWriter(fName, encoding, fields, QGis.WKBPolygon, crs, 'ESRI Shapefile')
        outFeat = QgsFeature()
        outFeat.setFields(fields)
        outGeom = QgsGeometry()
        idVar = 1
        puArea = float(sideLen)**2
        puPerimeter = float(sideLen)*4
        cellCount = self.gridTools.calcSquareCount(sideLen,xMin,xMax,yMin,yMax)
        # start building
        cnter = 0
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        featCnt = cellCount
        y = yMax
        while y >= yMin:
            x = xMin
            while x < xMax:
                polygon = self.gridTools.createSquare(x, y, sideLen)
                outFeat.setGeometry(outGeom.fromPolygon(polygon))
                outFeat.setAttributes([idVar,0,1.0,puArea,puPerimeter,sideLen])
                writer.addFeature(outFeat)
                idVar = idVar + 1
                x = x + sideLen
                cnter += 1
                progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            y = y - sideLen
        # close writer
        del writer    

    #
    # build hexagons
    #
    def buildHexagons(self,progress,progMin,progMax,bbox,outFName,encoding,crs,puSideLength,puidFieldName):

        fields = QgsFields()
        fields.append(QgsField(puidFieldName, QtCore.QVariant.Int))
        fields.append(QgsField("pu_status", QtCore.QVariant.Int))
        fields.append(QgsField("bnd_cost", QtCore.QVariant.Double, "real", 19, 10))
        fields.append(QgsField("area", QtCore.QVariant.Double, "real", 19, 10))
        fields.append(QgsField("perimeter", QtCore.QVariant.Double, "real", 19, 10))
        fields.append(QgsField("sidelength", QtCore.QVariant.Double, "real", 19, 10))
        check = QtCore.QFile(outFName)
        if check.exists():
            if not QgsVectorFileWriter.deleteShapeFile(outFName):
                return
        writer = QgsVectorFileWriter(outFName, encoding, fields, QGis.WKBPolygon, crs, 'ESRI Shapefile')
        outFeat = QgsFeature()
        outFeat.setFields(fields)
        outGeom = QgsGeometry()
        idVar = 1
        # place hexagons from just above top left corner
        puArea = self.gridTools.calcHexagonArea(puSideLength)
        puPerimeter = float(puSideLength)*6        
        xMin = bbox[0]
        yMin = bbox[1]
        xMax = bbox[2]
        yMax = bbox[3]
        xExtra = (xMax - xMin) * 0.01
        yExtra = (yMax - yMin) * 0.01
        xMin = xMin - xExtra
        xMax = xMax + xExtra
        yMin = yMin - yExtra
        yMax = yMax + yExtra
        cellCount = self.gridTools.calcHexagonCount(puSideLength,xMin,xMax,yMin,yMax)
        hyp,side_a,side_b = self.gridTools.hexagonTrig(puSideLength)
        y = yMax + side_b
        rowType = 'a'
        cnter = 0
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        featCnt = cellCount
        while y >= yMin:
            if rowType == 'a':
                x = xMin
                rowType = 'b'
            else:
                rowType = 'a'
                x = xMin + puSideLength + side_a
            while x < xMax:
                polygon = self.gridTools.createHexagon(x, y, puSideLength)
                outFeat.setGeometry(outGeom.fromPolygon(polygon))
                outFeat.setAttributes([idVar,0,1.0,puArea,puPerimeter,puSideLength])
                writer.addFeature(outFeat)
                idVar = idVar + 1
                x = x + (2 * puSideLength) + (2 * side_a)
                cnter += 1
                progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            y = y - side_b
        # close writer
        del writer    

    #
    # multi to single
    # modified from ftools MutlipartToSingleparts by Victor Olaya
    #
    def multiToSingle(self,progress,progMin,progMax,sourceLayer,outFName,tempPrefix,encoding,crs):

        # create temp filename
        path,fname = os.path.split(outFName)
        tfn = os.path.join(path, tempPrefix + 'single.shp')
        # create fields
        fields = QgsFields()
        fields.append(QgsField("id", QtCore.QVariant.Int))
        # create writer
        writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBPolygon, crs, 'ESRI Shapefile')
        # define variables to hold features
        outFeat = QgsFeature()
        inGeom = QgsGeometry()
        # prepare to loop through features
        features = vector.features(sourceLayer)
        cnter = 0
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        featCnt = len(features)
        for f in features:
            # get geometry
            inGeom = f.geometry()
            # convert to single
            geometries = self.convertToSingle(inGeom)
            outFeat.setAttributes([1])
            # add feature for each part
            for g in geometries:
                outFeat.setGeometry(g)
                writer.addFeature(outFeat)
            cnter += 1
            progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
        # close file
        del writer

    #
    # convert multi geometries to single geometries
    # modified from ftools MutlipartToSingleparts by Victor Olaya
    #
    def convertToSingle(self,geom):

        multiGeom = QgsGeometry()
        geometries = []
        if geom.type() == QGis.Point:
            if geom.isMultipart():
                multiGeom = geom.asMultiPoint()
                for i in multiGeom:
                    geometries.append(QgsGeometry().fromPoint(i))
            else:
                geometries.append(geom)
        elif geom.type() == QGis.Line:
            if geom.isMultipart():
                multiGeom = geom.asMultiPolyline()
                for i in multiGeom:
                    geometries.append(QgsGeometry().fromPolyline(i))
            else:
                geometries.append(geom)
        elif geom.type() == QGis.Polygon:
            if geom.isMultipart():
                multiGeom = geom.asMultiPolygon()
                for i in multiGeom:
                    geometries.append(QgsGeometry().fromPolygon(i))
            else:
                geometries.append(geom)
        return geometries
        
    #
    # intersect layers
    # modified code Intersection.py in ftools by Victor Olaya
    #
    def intersectLayers(self,progress,progMin,progMax,aLayer,bLayer,tfn,geomType,encoding,crs,puidFieldName,calcFieldName):

        # create fields and variables to hold information
        fields = QgsFields()
        fields.append(QgsField("puid", QtCore.QVariant.Int))
        fields.append(QgsField('calcField', QtCore.QVariant.Double))
        if geomType == 'POINT':
            writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBPoint, crs, 'ESRI Shapefile')
        elif geomType == 'LINE':
            writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBLineString, crs, 'ESRI Shapefile')
        else:
            writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBPolygon, crs, 'ESRI Shapefile')
        aFeat = QgsFeature()
        bFeat = QgsFeature()
        outFeat = QgsFeature()
        index = vector.spatialindex(aLayer)
        bFeatures = vector.features(bLayer)
        idIdx = bLayer.dataProvider().fields().indexFromName(puidFieldName)
        if calcFieldName <> '':
            calcIdx = aLayer.dataProvider().fields().indexFromName(calcFieldName)
        else:
            calcIdx = -1
        #QgsMessageLog.logMessage(calcFieldName)
        #QgsMessageLog.logMessage(str(calcIdx))
        featCnt = len(bFeatures)
        x = 0
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for bFeat in bFeatures:
            bGeom = QgsGeometry(bFeat.geometry())
            idVal = bFeat.attributes()[idIdx]
            intersects = index.intersects(bGeom.boundingBox())
            for i in intersects:
                request = QgsFeatureRequest().setFilterFid(i)
                aFeat = aLayer.getFeatures(request).next()
                tmpGeom = QgsGeometry(aFeat.geometry())
                try:
                    if bGeom.intersects(tmpGeom):
                        intGeom = QgsGeometry(bGeom.intersection(tmpGeom))
                        if calcIdx <> -1:
                            calcVal = aFeat.attributes()[calcIdx]
                        else:
                            calcVal = 0.0
                        if intGeom.wkbType() == QGis.WKBUnknown:
                            intCom = bGeom.combine(tmpGeom)
                            intSym = bGeom.symDifference(tmpGeom)
                            intGeom = QgsGeometry(intCom.difference(intSym))
                        try:
                            if intGeom.wkbType() in self.wkbTypeGroups[self.wkbTypeGroups[intGeom.wkbType()]]:
                                outFeat.setGeometry(intGeom)
                                outFeat.setAttributes([idVal,calcVal])
                                writer.addFeature(outFeat)
                        except:
                            continue
                except:
                    break
            x += 1
            progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            
        # close writer
        del writer


    #
    # intersect layers
    # modified code Intersection.py in ftools by Victor Olaya
    #
    def intersectAndMeasureLayers(self,progress,progMin,progMax,aLayer,bLayer,tfn,geomType,encoding,crs,puidFieldName,calcFieldName):

        # create fields and variables to hold information
        #fields = QgsFields()
        #fields.append(QgsField("puid", QtCore.QVariant.Int))
        #fields.append(QgsField('calcField', QtCore.QVariant.Double))
        #if geomType == 'POINT':
        #    writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBPoint, crs, 'ESRI Shapefile')
        #elif geomType == 'LINE':
        #    writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBLineString, crs, 'ESRI Shapefile')
        #else:
        #    writer = QgsVectorFileWriter(tfn, encoding, fields, QGis.WKBPolygon, crs, 'ESRI Shapefile')
        f = open(tfn,'w')
        #f.write('puid,key,measure\n')
        aFeat = QgsFeature()
        bFeat = QgsFeature()
        outFeat = QgsFeature()
        index = vector.spatialindex(aLayer)
        bFeatures = vector.features(bLayer)
        idIdx = bLayer.dataProvider().fields().indexFromName(puidFieldName)
        if calcFieldName <> '':
            calcIdx = aLayer.dataProvider().fields().indexFromName(calcFieldName)
        else:
            calcIdx = -1
        #QgsMessageLog.logMessage(calcFieldName)
        #QgsMessageLog.logMessage(str(calcIdx))
        featCnt = len(bFeatures)
        x = 0
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for bFeat in bFeatures:
            bGeom = QgsGeometry(bFeat.geometry())
            idVal = bFeat.attributes()[idIdx]
            intersects = index.intersects(bGeom.boundingBox())
            for i in intersects:
                request = QgsFeatureRequest().setFilterFid(i)
                aFeat = aLayer.getFeatures(request).next()
                tmpGeom = QgsGeometry(aFeat.geometry())
                try:
                    if bGeom.intersects(tmpGeom):
                        intGeom = QgsGeometry(bGeom.intersection(tmpGeom))
                        if calcIdx <> -1:
                            calcVal = aFeat.attributes()[calcIdx]
                        else:
                            calcVal = 0.0
                        if intGeom.wkbType() == QGis.WKBUnknown:
                            intCom = bGeom.combine(tmpGeom)
                            intSym = bGeom.symDifference(tmpGeom)
                            intGeom = QgsGeometry(intCom.difference(intSym))
                        try:
                            if intGeom.wkbType() in self.wkbTypeGroups[self.wkbTypeGroups[intGeom.wkbType()]]:
                                outFeat.setGeometry(intGeom)
                                #outFeat.setAttributes([idVal,calcVal])
                                #writer.addFeature(outFeat)
                                if geomType == 'POLYGON':
                                    measure = outFeat.geometry().area()
                                elif geomType == 'LINE':
                                    measure = outFeat.geometry().length()
                                else:
                                    measure = 1
                                f.write('%d|%d|%f\n' % (int(idVal),int(calcVal),float(measure)))
                        except:
                            continue
                except:
                    break
            x += 1
            progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            
        # close writer
        #del writer

    #
    # find PUs that overlap with clip layer via vector
    #
    def vectorFindMatchingPUs(self,progress,progMin,progMax,tempLayer):

        # confirm it is valid
        if tempLayer.isValid():
            fields = tempLayer.dataProvider().fields()
            total = tempLayer.featureCount()
            featIter = tempLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            results = set([])
            featCnt = total
            cnter = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            for feat in featIter:
                attr = feat.attributes()
                if not attr[0] in results:
                    results.add(attr[0])
                cnter += 1
                progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
        # return results
        return(results)
    
    #
    # delete cells
    #
    def deleteCells(self,progress,progMin,progMax,matchList,outFName):

        # open layer
        gridLayer = QgsVectorLayer(outFName, 'grid', 'ogr')
        # confirm valid
        if gridLayer.isValid():
            cnter = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            total = gridLayer.featureCount()
            featCnt = total
            # create deletion list
            deleteList = []
            featIter = gridLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            for feat in featIter:
                if not feat.attributes()[0] in matchList:
                    deleteList.append(feat.id())
                cnter += 1
                progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            # if deletion list not empty, delete records
            if len(deleteList) > 0:
                gridLayer.startEditing()
                gridLayer.dataProvider().deleteFeatures(deleteList)
                gridLayer.commitChanges()
        # close layer
        gridLayer = None
            
    #
    # renumber PUs
    #
    def reNumberPUs(self,progress,progMin,progMax,outFName,puidFieldName):

        # open layer
        gridLayer = QgsVectorLayer(outFName, 'grid', 'ogr')
        # confirm it is valid
        if gridLayer.isValid():
            fields = gridLayer.dataProvider().fields()
            idx = fields.indexFromName(puidFieldName)
            total = gridLayer.featureCount()
            cnter = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            featCnt = total
            idVar = 1
            featIter = gridLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            updateMap = {}
            for feat in featIter:
                updateMap[feat.id()] = {idx : idVar}
                idVar += 1
                cnter += 1
                progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
            gridLayer.startEditing()
            gridLayer.dataProvider().changeAttributeValues(updateMap)
            gridLayer.commitChanges()
        # close layer
        gridLayer = None

    #
    # create matching raster
    #
    def rasterCreateMatching(self,trg,puLyr,srcLyr,idField):

        # get parameters
        pixelSize = min(srcLyr.rasterUnitsPerPixelX(),srcLyr.rasterUnitsPerPixelY())
        bbox = srcLyr.extent()
        xMin = bbox.xMinimum()
        yMax = bbox.yMaximum()
        xMax = bbox.xMaximum()
        yMin = bbox.yMinimum()
        xRecs = round((xMax - xMin) / pixelSize)
        yRecs = round((yMax - yMin) / pixelSize)
        transformArray = [xMin,pixelSize,0,yMax,0,-pixelSize]
        self.vectorToRaster(puLyr.source(),trg,xRecs,yRecs,transformArray,idField)
        
    #
    # create matching rasters
    #
    def rasterCreateMatchingPair(self,progress,progMin,progMax,trg,trs,calcField,puLyr,srcLyr,idField,pixelSize,calcType):

        # get parameters
        pixelSize = pixelSize
        bbox = srcLyr.extent()
        xMin = bbox.xMinimum()
        yMax = bbox.yMaximum()
        xMax = bbox.xMaximum()
        yMin = bbox.yMinimum()
        xRecs = round((xMax - xMin) / pixelSize)
        yRecs = round((yMax - yMin) / pixelSize)
        progStep = (progMax - progMin) / 3.0
        progress.setPercentage(int(progStep))
        transformArray = [xMin,pixelSize,0,yMax,0,-pixelSize]
        # transform grid first
        progress.setText('Converting PU Layer')
        self.vectorToRaster(puLyr.source(),trg,xRecs,yRecs,transformArray,idField)
        progress.setPercentage(int(progStep*2))
        progress.setText('Converting Source Layer')
        if calcType == 'calculate':
            self.vectorToRaster(srcLyr.source(),trs,xRecs,yRecs,transformArray,calcField)
        else:
            self.vectorToRaster(srcLyr.source(),trs,xRecs,yRecs,transformArray,None)
        progress.setPercentage(progMax)

    #
    # convert to raster
    #
    def vectorToRaster(self,inFName,outFName,xRecs,yRecs,transformArray,keyField=None):

        sDs = ogr.Open(inFName)
        sLyr = sDs.GetLayer()
        gtDriver = gdal.GetDriverByName('GTiff')
        tDs = gtDriver.Create(outFName, int(xRecs), int(yRecs), 1, gdal.GDT_Int32)
        tDs.SetGeoTransform(transformArray)
        # set options
        if keyField == None:
            #options = ['ALL_TOUCHED=True']
            options = []
        else:
            #options = ['ATTRIBUTE=%s' % keyField,'ALL_TOUCHED=TRUE']
            options = ['ATTRIBUTE=%s' % keyField]
        # rasterize
        #QgsMessageLog.logMessage('rasterize')
        gdal.RasterizeLayer(tDs, [1], sLyr, None, None, [1], options)
        sLyr = None
        sDs = None
        tDs = None
        
    #
    # estimate raster overlaps
    #
    def rasterMeasure(self,progress,progMin,progMax,trg,trs,delSource,srcNDValue,pixelSize):

        #
        # data structure for each record is
        # results[puid][calcField or pixel value] = [count,sum,max,min]
        #
        uniqueValues = set([])
        try:
            gaf = None
            caf = None
            # read grid
            gds = gdal.Open(trg)
            gdBand = gds.GetRasterBand(1)
            # read content layer
            cds = gdal.Open(trs)
            cdBand = cds.GetRasterBand(1)
            ndValue = cdBand.GetNoDataValue()
            nRows = gds.RasterYSize
            nCols = gds.RasterXSize
            # get raster attribute table
            results = {}
            size = pixelSize*pixelSize
            cnter = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            featCnt = nRows
            calcMethod = 1
            methodOneMask = False
            for rowIdx in range(nRows):
                gaf = np.array(gdBand.ReadAsArray(0,rowIdx,nCols,1)).flatten()
                caf = np.array(cdBand.ReadAsArray(0,rowIdx,nCols,1)).flatten()
                #
                puidList = np.unique(gaf).tolist()
                if 0 in puidList:
                    puidList.remove(0)
                unique_gaf = np.array(puidList)
                x,y = np.meshgrid(gaf, unique_gaf)
                caf_stack = np.tile(caf, (unique_gaf.size, 1))
                caf_in_gaf = np.zeros_like(caf_stack)
                caf_in_gaf[x==y] = caf_stack[x==y]
                for idx in range(len(caf_in_gaf)):
                    puid = unique_gaf[idx]
                    newDict = {}
                    puData = np.array(np.unique(caf_in_gaf[idx],return_counts=True)).transpose()
                    if len(puData) > 0:
                        for val in puData:
                            newDict[val[0]] = [val[1], val[1]*size, val[1]*size, val[1]*size]
                        if puid in results:
                            for key,value in newDict.iteritems():
                                if key in results[puid]:
                                    results[puid][key][0] += value[0]
                                    results[puid][key][1] += value[1]
                                    if value[2] > results[puid][key][2]:
                                        results[puid][key][2] = value[2]
                                    if value[3] < results[puid][key][3]:
                                        results[puid][key][3] = value[3]
                                else:
                                    results[puid][key] = value
                                    uniqueValues.add(key)
                        else:
                            results[puid] = newDict
                            uniqueValues = uniqueValues.union(newDict.keys())
                cnter += 1
                progPct = ((float(cnter) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
        except Exception as inst:
            QgsMessageLog.logMessage('Error: %s' % str(inst))
        os.remove(trg)
        if delSource == True:
            os.remove(trs)  
        del gaf
        del caf
        return(results, uniqueValues)
        
    #
    # measure vector features
    #
    def vectorMeasure(self,progress,progMin,progMax,tfn,geomType):

        #
        # data structure for each record is
        # results[puid][calcField or pixel value] = [count,sum,max,min]
        #
        uniqueValues = set([])
        # open layer
        tempLayer = QgsVectorLayer(tfn, 'tempint', 'ogr')
        # confirm it is valid
        if tempLayer.isValid():
            fields = tempLayer.dataProvider().fields()
            featCnt = tempLayer.featureCount()
            if geomType == 'POINT':
                featIter = tempLayer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry))
            else:
                featIter = tempLayer.getFeatures()
            results = {}
            # produce multi dimensional dictionary of puids, calcFieldsValues and counts
            # attr[0] == puid
            # attr[1] === calcField
            x = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            for feat in featIter:
                attr = feat.attributes()
                # determine measure
                if geomType == 'POLYGON':
                    measure = feat.geometry().area()
                elif geomType == 'LINE':
                    measure = feat.geometry().length()
                else:
                    measure = 1
                if attr[0] in results:
                    # record exists for this puid
                    if attr[1] in results[attr[0]]:
                        # record exits for this puid and this unique value of calcfield value
                        results[attr[0]][attr[1]][0] += 1
                        results[attr[0]][attr[1]][1] += measure
                        if measure > results[attr[0]][attr[1]][2]:
                            results[attr[0]][attr[1]][2] = measure
                        if measure < results[attr[0]][attr[1]][3]:
                            results[attr[0]][attr[1]][3] = measure
                    else:
                        # create this unique value of calcfield value within existing puid record
                        results[attr[0]][attr[1]] = [1,measure,measure,measure]
                        if not attr[1] in uniqueValues:
                            uniqueValues.add(attr[1])
                else:
                    # create record for this puid
                    # store array of [count, sum, max, min] for each calcField or unique value
                    results[attr[0]] = {attr[1] : [1,measure,measure,measure]}
                    if not attr[1] in uniqueValues:
                        uniqueValues.add(attr[1])
                x += 1
                progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
        # close layer
        tempLayer = None
        # return results
        return(results, uniqueValues)

    #
    # measure vector features
    #
    def vectorMeasureFromFile(self,progress,progMin,progMax,tfn,geomType):

        #
        # data structure for each record is
        # results[puid][calcField or pixel value] = [count,sum,max,min]
        #
        uniqueValues = set([])
        # open file
        if os.path.exists(tfn):
            f = open(tfn,'r')
            recs = f.readlines()
            f.close()
            featCnt = len(recs)
            # create blank dictionary
            results = {}
            # vars to track progress
            x = 0
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            for rec in recs:
                attr = rec.split('|')
                puid = int(attr[0])
                key = int(attr[1])
                measure = float(attr[2])
                if puid in results:
                    # record exists for this puid
                    if key in results[puid]:
                        # record exits for this puid and this unique value of calcfield value
                        results[puid][key][0] += 1
                        results[puid][key][1] += measure
                        if measure > results[puid][key][2]:
                            results[puid][key][2] = measure
                        if measure < results[puid][key][3]:
                            results[puid][key][3] = measure
                    else:
                        # create this unique value of calcfield value within existing puid record
                        results[puid][key] = [1,measure,measure,measure]
                        if not key in uniqueValues:
                            uniqueValues.add(key)
                else:
                    # create record for this puid
                    # store array of [count, sum, max, min] for each calcField or unique value
                    results[puid] = {key : [1,measure,measure,measure]}
                    if not key in uniqueValues:
                        uniqueValues.add(key)
                x += 1
                progPct = ((float(x) / float(featCnt) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
        # return results
        return(results, uniqueValues)
