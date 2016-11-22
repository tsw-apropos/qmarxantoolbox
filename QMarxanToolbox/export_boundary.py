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

import os, sys, datetime, math
from tempfile import gettempdir
from itertools import islice, cycle
from collections import namedtuple
import heapq
from qgis.core import *

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterFile,\
    ParameterSelection, ParameterTableField
from processing.tools import dataobjects, vector
from processing.core.ProcessingLog import ProcessingLog
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException

# The following merge and batch_sort code is from:
#
# Author: Gabriel Genellina 2009-05-14
# License: MIT
# Source: http://code.activestate.com/recipes/576755/

# based on Recipe 466302: Sorting big files the Python 2.4 way
# by Nicolas Lehuen

Keyed = namedtuple("Keyed", ["key", "obj"])

def merge(key=None, *iterables):
    # based on code posted by Scott David Daniels in c.l.p.
    # http://groups.google.com/group/comp.lang.python/msg/484f01f1ea3c832d

    if key is None:
        for element in heapq.merge(*iterables):
            yield element
    else:
        keyed_iterables = [(Keyed(key(obj), obj) for obj in iterable)
                        for iterable in iterables]
        for element in heapq.merge(*keyed_iterables):
            yield element.obj


def batch_sort(input, output, key=None, buffer_size=32000, tempdirs=None):
    if tempdirs is None:
        tempdirs = []
    if not tempdirs:
        tempdirs.append(gettempdir())

    chunks = []
    try:
        with open(input,'rb',64*1024) as input_file:
            input_iterator = iter(input_file)
            for tempdir in cycle(tempdirs):
                current_chunk = list(islice(input_iterator,buffer_size))
                if not current_chunk:
                    break
                current_chunk.sort(key=key)
                output_chunk = open(os.path.join(tempdir,'%06i'%len(chunks)),'w+b',64*1024)
                chunks.append(output_chunk)
                output_chunk.writelines(current_chunk)
                output_chunk.flush()
                output_chunk.seek(0)
        with open(output,'wb',64*1024) as output_file:
            output_file.writelines(merge(key, *chunks))
    finally:
        for chunk in chunks:
            try:
                chunk.close()
                os.remove(chunk.name)
            except Exception:
                pass

class ExportBoundary(GeoAlgorithm):

    PU_LAYER = 'PU_LAYER'
    PU_FIELD = 'PU_FIELD'
    CALC_METHOD = 'CALC_METHOD'
    BLEN_FIELD = 'BLEN_FIELD'
    DIFF_METHOD = 'DIFF_METHOD'
    EDGE_METHOD = 'EDGE_METHOD'
    TOL = 'TOL'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        
        # The name that the user will see in the toolbox
        self.name = 'Export Boundary File (bound.dat)'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to Marxan'

        self.addParameter(ParameterVector(self.PU_LAYER, self.tr('Planning Unit layer'), \
            [ParameterVector.VECTOR_TYPE_POLYGON], False))
        self.addParameter(ParameterTableField(self.PU_FIELD, self.tr('Planning Unit Id Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterSelection(self.CALC_METHOD, self.tr('Calculation Method'), \
            ["measure","weighted","field"], False))
        self.addParameter(ParameterTableField(self.BLEN_FIELD, self.tr('Boundary Length Field'), \
            self.PU_LAYER,0,True))
        self.addParameter(ParameterSelection(self.DIFF_METHOD, self.tr('When boundary field values differ use the'), \
            ["mean","maximum","minimum"], False))
        self.addParameter(ParameterSelection(self.EDGE_METHOD, self.tr('Value of boundary length for planning units on edge should be'), \
            ["full","half","zero"], False))
        self.addParameter(ParameterSelection(self.TOL, self.tr('Export precision rounding (in map units)'), \
            ["100","10","1","0.1","0.01","0.001","0.0001","0.00001"], 2, False, False))
        self.addParameter(ParameterFile(self.OUT_DIR,self.tr('Folder for bound.dat file'), \
            True, False))

    def checkParameterValuesBeforeExecuting(self):
        """If there is any check to do before launching the execution
        of the algorithm, it should be done here.

        If values are not correct, a message should be returned
        explaining the problem.

        This check is called from the parameters dialog, and also when
        calling from the console.
        """
        result = None
        
        # get parameters
        self.puLayer = self.getParameterValue(self.PU_LAYER)
        lList = QgsMapLayerRegistry.instance().mapLayers()
        for key, value in lList.iteritems():
            fileName = value.dataProvider().dataSourceUri().split('|')[0]
            if fileName == self.puLayer:
                self.puL = value
        self.puField = self.getParameterValue(self.PU_FIELD)
        self.calcIdx = self.getParameterValue(self.CALC_METHOD)
        if self.calcIdx == 0:
            self.calcMethod = 'Measure'
        elif self.calcIdx == 1:
            self.calcMethod = 'Weighted'
        else:
            self.calcMethod = 'Field'
        self.blField = self.getParameterValue(self.BLEN_FIELD)
        self.diffIdx = self.getParameterValue(self.DIFF_METHOD)
        if self.diffIdx == 0:
            self.diffMethod = 'Mean'
        elif self.diffIdx == 1:
            self.diffMethod = 'Maximum'
        else:
            self.diffMethod = 'Minimum'
        self.edgeIdx = self.getParameterValue(self.EDGE_METHOD)
        if self.edgeIdx == 0:
            self.edgeMethod = 'Full Value'
        elif self.edgeIdx == 1:
            self.edgeMethod = 'Half Value'
        else:
            self.edgeMethod = 'Zero'
        # note that tolerance here is set to the index -2 because
        # the third item, is round numbers so 2 - 2 is zero and
        # round(125.12,0) => 125 and round(125.12,-2) => 100
        self.tol = self.getParameterValue(self.TOL) - 2
        self.outDir = self.getParameterValue(self.OUT_DIR)
        self.outFName = os.path.join(self.outDir,'bound.dat')
        # validate options to ensure that choices are valid
        if self.calcMethod in ('Weighted','Field') and self.blField == None:
            result = 'The weighted and field methods require a boundary length field'

        return result

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        errorCount,messageText = self.createBoundFile(progress)
        if errorCount > 0:
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, messageText)
            raise GeoAlgorithmExecutionException(messageText)

    #
    # create bound.dat file
    #
    def createBoundFile(self,progress):

        # calculate line length
        def LineLength(p1,p2):
            ll = math.sqrt( (float(p1[0]) - float(p2[0]))**2 + \
                (float(p1[1]) - float(p2[1]))**2 )
            return(ll)

        # extract points from polygon
        # modified from ftools_utils.py by Carson Farmer
        def extractPoints( geom ):
            multi_geom = QgsGeometry()
            temp_geom = []
            if geom.isMultipart():
                multi_geom = geom.asMultiPolygon() #multi_geom is a multipolygon
                for i in multi_geom: #i is a polygon
                    for j in i: #j is a line
                        temp_geom.extend( j )
            else:
                multi_geom = geom.asPolygon() #multi_geom is a polygon
                for i in multi_geom: #i is a line
                    temp_geom.extend( i )
            return(temp_geom)

        # adjust boundary length
        def adjBound(inVal,id1,id2):
            if id1 == id2:
                if self.edgeMethod == 'Full Value':
                    retVal = inVal
                elif self.edgeMethod == 'Half Value':
                    retVal = inVal/2.0
                else:
                    retVal = 0.0
            else:
                retVal = inVal
            return(retVal)

        #
        # pre-run setup
        #
        # track # of possible topological errors
        topoErrorCount = 0
        # change to output directory
        path,fname = os.path.split(self.outFName)
        os.chdir(path)
        nl = os.linesep
        # create temporary file names 
        tempsegfile = 'tempsegfile_%s.txt' % os.getpid()
        tempsortedfile = 'tempsortedfile_%s.txt' % os.getpid()
        tempadjfile = 'tempadjfile_%s.txt' % os.getpid()
        tempsortedadjfile = 'tempsortedadjfile_%s.txt' % os.getpid()
        errorlog = 'topo_error_log_%s.txt' % datetime.date.today().isoformat()
        # get field indexes for puid and boundary fields
        puIdx = self.puL.dataProvider().fields().indexFromName(self.puField)
        if self.blField <> None:
            fldIdx = self.puL.dataProvider().fields().indexFromName(self.blField)
        else:
            fldIdx = -1
        #
        # step 1 - build temporary segment file and dictionary
        #
        # notify users
        progress.setPercentage(0)
        progress.setText('Extracting line segments')
        # set values
        tsf = open(tempsegfile,'w')
        inGeom = QgsGeometry()
        puFeatures = vector.features(self.puL)
        segLineCnt = 0
        # loop through features
        fCount = len(puFeatures)
        lineCount = 0
        x = 0
        progPct = 0
        progMin = 0
        progMax = 30
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for feat in puFeatures:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            attr = feat.attributes()
            pid = str(attr[puIdx])
            if fldIdx != -1:
                cost = str(attr[fldIdx])
            else:
                cost = '1.0'
            inGeom = feat.geometry()
            pointList = extractPoints(inGeom)
            prevPoint = 0
            for i in pointList:
                if prevPoint == 0:
                    prevPoint = i
                else:
                    # write line segment
                    segLen = LineLength([prevPoint[0],prevPoint[1]], [i[0],i[1]])
                    # make spatial key to segment file
                    if round(float(prevPoint[0]),self.tol) < round(float(i[0]),self.tol) or \
                        (round(float(prevPoint[0]),self.tol) == round(float(i[0]),self.tol) \
                        and round(float(prevPoint[1]),self.tol) < round(float(i[1]),self.tol) ):
                        skey = str(round(float(prevPoint[0]),self.tol)) + '|' + \
                            str(round(float(prevPoint[1]),self.tol)) + '|' + \
                            str(round(float(i[0]),self.tol)) + '|' +  \
                            str(round(float(i[1]),self.tol))
                    else:
                        skey = str(round(float(i[0]),self.tol)) + '|' +  \
                            str(round(float(i[1]),self.tol)) + '|' + \
                            str(round(float(prevPoint[0]),self.tol)) + '|' + \
                            str(round(float(prevPoint[1]),self.tol))
                    if segLen > 0:
                        outLine = '%s,%d,%f,%f %s' %  (skey, int(pid), float(cost), segLen, nl )
                        tsf.write(outLine)
                        lineCount += 1
                    prevPoint = i
        # clean up
        tsf.close()
        # sort the file
        batch_sort(tempsegfile, tempsortedfile)
        os.remove(tempsegfile)
        #
        # step 2 - loop through sorted file and create adjacency file
        #    
        # notify users
        progress.setText('Creating adjacency file')
        # 
        tsf = open(tempsortedfile,'r')
        taf = open(tempadjfile,'w')
        done = False
        pl = ''
        x = 0
        adjFileLen = 0
        progMin = 35
        progMax = 65
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        while not done:
            x += 1
            progPct = ((float(x) / float(lineCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            line = tsf.readline()
            if line == '':
                done = True
            else:
                cl = line.rstrip().split(',')
            if pl != '' and pl != ['']:
                if cl != '' and pl[0] == cl[0]:
                    fCost = 1
                    if self.calcMethod == 'Field':
                        bCost = 1
                        if float(pl[2])== float(cl[2]):
                            bCost = float(pl[2])
                        else:
                            if self.diffMethod == 'Maximum':
                                bCost = max([float(pl[2]),float(cl[2])])
                            elif self.diffMethod == 'Minimum':
                                bCost = min([float(pl[2]),float(cl[2])])
                            else:
                                bCost = (float(pl[2]) + float(cl[2]))/2.0
                        fCost = str(bCost)
                    elif self.calcMethod  == 'Weighted':
                        bCost = 1
                        if float(pl[2])== float(cl[2]):
                            bCost = float(pl[2])
                        else:
                            if self.diffMethod == 'Maximum':
                                bCost = max([float(pl[2]),float(cl[2])])
                            elif self.diffMethod == 'Minimum':
                                bCost = min([float(pl[2]),float(cl[2])])
                            else:
                                bCost = sum([float(pl[2]),float(cl[2])])/2.0
                        fCost = str(float(pl[3]) * bCost)
                    else:
                        fCost = str(pl[3])
                    # topology error test
                    # check for more matching lines
                    errorLines = True
                    topologyErrorFound = False
                    pids = ''
                    while errorLines:
                        line = tsf.readline()
                        chkLine = line.rstrip().split(',')
                        if chkLine != '' and chkLine[0] == pl[0]:
                            topologyErrorFound = True
                            # an error exists
                            if pids == '':
                                pids = str(pl[1]) + ',' + str(cl[1]) + ',' + str(chkLine[1])
                            else:
                                pids = pids + ',' + str(chkLine[1])
                        else:
                            errorLines = False
                    if topologyErrorFound:
                        if topoErrorCount == 0:
                            el = open(errorlog, 'w')
                            outline = 'There should never be more than 2 overlapping ' + \
                                'line segments. ' + nl + \
                                'Below are listed cases where more than 2 have ' + \
                                'been identified. ' +  nl + 'These should all be ' + \
                                'corrected before using the boundary file' + nl + \
                                '-------' + nl
                            el.write(outline)
                        outline = 'Line segments defined as %s may be topologically invalid.%s' % (str(pl[0]),nl)
                        outline = outline + 'Area ids %s appear to overlap.%s--%s' % (pids,nl,nl) 
                        el.write(outline)
                        topoErrorCount += 1
                    else:
                        # no error proceed
                        if int(pl[1]) < int(cl[1]):
                            taf.write('%020d,%020d,%s %s' % (int(pl[1]),int(cl[1]),fCost,nl))
                        else:
                            taf.write('%020d,%020d,%s %s' % (int(cl[1]),int(pl[1]),fCost,nl))
                        adjFileLen += 1
                elif type(pl) == list:
                    fCost = 1
                    if self.calcMethod  == 'Field':
                        fCost = str(pl[2])
                    elif self.calcMethod  == 'Weighted':
                        fCost = str(float(pl[3]) * float(pl[2]))
                    else:
                        fCost = str(pl[3])
                    taf.write('%020d,%020d,%s %s' % (int(pl[1]),int(pl[1]),fCost,nl))
            pl = line.rstrip().split(',')
        tsf.close()
        taf.close()
        os.remove(tempsortedfile)
        # sort adjacency file
        batch_sort(tempadjfile, tempsortedadjfile)
        os.remove(tempadjfile)
        #
        # step 3 - write boundary file
        #
        # notify users
        progress.setText('Writing boundary file')
        #
        saf = open(tempsortedadjfile,'r')
        faf = open(self.outFName,'w')
        faf.write("id1\tid2\tboundary%s" % nl)
        done = False
        pl = ''
        x = 0
        progMin = 70
        progMax = 99
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        while not done:
            x += 1
            progPct = ((float(x) / float(adjFileLen) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            line = saf.readline()
            if line == '':
                done = True
                cl = ''
            else:
                cl = line.rstrip().split(',')
            if pl != '':
                if cl != '' and pl[0] == cl[0] and pl[1] == cl[1]:
                    if self.calcMethod  != 'Field':
                        # note that if field value don't sum the line segments
                        pl = [pl[0],pl[1],sum([float(pl[2]),float(cl[2])])]
                else:
                    bound = adjBound(float(pl[2]),pl[0],pl[1])
                    if self.calcMethod  in ('Field','Weighted'):
                        boundStr = str(bound)
                    else:
                        boundStr = str(round(float(bound),self.tol))
                    if float(bound) > 0.0:
                        faf.write('%d\t%d\t%s%s' % (int(pl[0]),int(pl[1]),boundStr,nl))
                    pl = line.rstrip().split(',')
            else:
                pl = cl
        saf.close()
        faf.close()
        os.remove(tempsortedadjfile)
        if topoErrorCount > 0:
            el.close()
            messageText = '%d possible topological error(s) found. ' % topoErrorCount
            messageText += 'Please check error log in same directory as boundary file.'
        else:
            messageText = 'Export of bound.dat executed without problems'
        return(topoErrorCount,messageText)
        
    #
    #
    # The code below was an attempt to use intersections to increase processing speed and account
    # for cases where there may not be matching line work between adjacent polygons. This proved
    # to be problematic for some grids where the line intersections generated points rather than line
    # work so it is shelved for now until it can be analyzed and corrected.
    #
    #
    #def createBoundaryArray(self,progress,puFieldName,costFieldName,progMin,progMax):
        ## determine which field to use
        #puIdx = self.puL.dataProvider().fieldNameIndex(puFieldName)
        #if costFieldName <> None:
            #coIdx = self.puL.dataProvider().fieldNameIndex(costFieldName)
        #else:
            #coIdx = None
        ## build spatial index and feature list
        #spatialIdx = QgsSpatialIndex()
        #featDict = {}
        #puFeats = vector.features(self.puL)
        #for feat in puFeats:
            #temp = spatialIdx.insertFeature(feat)
            #featDict[feat.id()] = feat
        ## iterate over list and buid results
        #resDict = {}
        #featCount = len(featDict)
        #x = 0
        #progPct = 0
        #progMin = 0
        #progMax = 80
        #progPct = progMin
        #lastPct = progPct
        #progRange = progMax - progMin
        #for aId in featDict:
            #x += 1
            #progPct = ((float(x) / float(featCount) * 100) * (progRange/100.0)) + progMin
            #if int(progPct) > lastPct:
                #progress.setPercentage(progPct)
                #lastPct = progPct
            #intersectList = spatialIdx.intersects(featDict[aId].geometry().buffer(1,2).boundingBox())
            #aLineGeom = QgsGeometry.fromPolyline(featDict[aId].geometry().asPolygon()[0])
            #for bId in intersectList:
                #if aId <> bId:
                    #bLineGeom = QgsGeometry.fromPolyline(featDict[bId].geometry().asPolygon()[0])
                    #if aLineGeom.intersects(bLineGeom):
                        ##xLineGeom = aLineGeom.intersection(bLineGeom)
                        #aSet = set(aLineGeom.asPolyline())
                        #bSet = set(bLineGeom.asPolyline())
                        #coords = list(set.intersection(aSet,bSet))
                        #QgsMessageLog.logMessage(str(coords))
                        #if len(coords) == 2:
                            #xLineGeom = QgsGeometry.fromPolyline([QgsPoint(coords[0]),QgsPoint(coords[1])])
                        ##if xLineGeom.wkbType() == QGis.WKBLineString:
                            ##QgsMessageLog.logMessage('is line string')
                            #aPuId = featDict[aId].attributes()[puIdx]
                            #bPuId = featDict[bId].attributes()[puIdx]
                            #if coIdx <> None:
                                #aCost = featDict[aId].attributes()[coIdx]
                                #bCost = featDict[bId].attributes()[coIdx]
                            #else:
                                #aCost = None
                                #bCost = None
                            #if aPuId < bPuId:
                                #resDict[str(aPuId) + '|' + str(bPuId)] = [ [aPuId,bPuId], xLineGeom.length(), [aCost,bCost] ]
                            #else:
                                #resDict[str(bPuId) + '|' + str(aPuId)] = [ [bPuId,aPuId], xLineGeom.length(), [bCost,aCost] ]
                        ##elif xLineGeom.wkbType() == QGis.WKBPoint:
                        #else:
                            #QgsMessageLog.logMessage(str(aLineGeom.asPolyline()))
                            #QgsMessageLog.logMessage(str(bLineGeom.asPolyline()))
                            #QgsMessageLog.logMessage('%d intersects %d' % (aId,bId))
                            ##QgsMessageLog.logMessage('%f, %f' % (xLineGeom.asPoint()[0], xLineGeom.asPoint()[1]))
                            #return()
        ##QgsMessageLog.logMessage(str(resDict))                        
        #results = [value for key, value in resDict.iteritems()]
        ##QgsMessageLog.logMessage(str(results))                        
        #results.sort()
        #return(results)            
        
    #def writeBoundaryFile(self,progress,boundInfo,oFName,progMin,progMax):

        #featCount = len(boundInfo)
        #x = 0
        #progPct = 0
        #progMin = 0
        #progMax = 80
        #progPct = progMin
        #lastPct = progPct
        #progRange = progMax - progMin
        #nl = os.linesep
        #f = open(oFName,'w')
        #f.write("id1,id2,boundary%s" % nl)
        #for rec in boundInfo:
            #x += 1
            #progPct = ((float(x) / float(featCount) * 100) * (progRange/100.0)) + progMin
            #if int(progPct) > lastPct:
                #progress.setPercentage(progPct)
                #lastPct = progPct
            #f.write('%d,%d,%f%s' % (rec[0][0],rec[0][1],rec[1],nl) )
        #f.close()


