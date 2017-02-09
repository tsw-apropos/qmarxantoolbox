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

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterSelection, \
    ParameterNumber, ParameterExtent, ParameterCrs, ParameterFile
from processing.core.outputs import OutputVector
from calculations import qmtGrid, qmtSpatial

class CreatePULayer(GeoAlgorithm):

    EXTENT = 'EXTENT'
    CRS = 'CRS'
    SHAPE = 'SHAPE'
    SIZETYPE = 'SIZETYPE'
    SIZE = 'SIZE'
    OUTPUT = 'OUTPUT'
    CLIP = 'CLIP'
    
    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Create Planning Unit Layer'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Data Preparation'
        
        # set defaults values needed
        self.gridTools = qmtGrid()
        self.spatialTools = qmtSpatial()
        self.tempPrefix = 'qmt%d_' % os.getpid()
        self.encoding = u'UTF-8'
        self.puArea = 1000.0
        self.puSideLength = 0.0
        self.outFName = ''
        # define parameters
        self.addParameter(ParameterExtent(self.EXTENT, self.tr('Grid extent')))
        self.addParameter(ParameterCrs(self.CRS, 'Grid CRS'))
        self.addParameter(ParameterSelection(self.SHAPE, self.tr('Output polygons shape'), \
            ["hexagon","square"]))
        self.addParameter(ParameterSelection(self.SIZETYPE, self.tr('Define polygon size by'), \
            ["area","side length"]))
        self.addParameter(ParameterNumber(self.SIZE, \
            self.tr('Enter polygon size value (projection units or projection units squared)'), \
            1.0, None, 1000000.0))
        self.addParameter(ParameterVector(self.CLIP, \
            self.tr('Clip new plannning unit layer to this layer'), \
            [ParameterVector.VECTOR_TYPE_ANY], True))
        self.addOutput(OutputVector(self.OUTPUT,self.tr('Plannning unit layer name')))

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        # process values
        extent = self.getParameterValue(self.EXTENT).split(',')
        self.bbox = [float(extent[0]), float(extent[2]),
                            float(extent[1]), float(extent[3])]
        self.crs = QgsCoordinateReferenceSystem(self.getParameterValue(self.CRS))
        self.puShapeIdx = self.getParameterValue(self.SHAPE)
        self.puSizeTypeIdx = self.getParameterValue(self.SIZETYPE)
        self.outFName = self.getOutputValue(self.OUTPUT)
        self.puidFieldName = 'puid'
        fn, fext = os.path.splitext(self.outFName)
        progress.setPercentage(0)
        if fext.lower() <> '.shp':
            self.outFName += '.shp'
        temp = self.getParameterValue(self.CLIP)
        if temp <> None:
            self.clipLayer = QgsVectorLayer(temp, 'clipLayer', 'ogr')
            progMin = 0
            progMax = 20
            progress.setText('Creating base grid...')
        else:
            self.clipLayer = None
            progMin = 0
            progMax = 100
            progress.setText('Creating PU layer...')
        
        # build grid
        if self.puShapeIdx == 1:
            if self.puSizeTypeIdx == 0:
                self.puArea = self.getParameterValue(self.SIZE)
                self.puSideLength = self.gridTools.calcSquareSideLength(self.puArea)
            else:
                self.puSideLength = self.getParameterValue(self.SIZE)
                self.puArea = self.gridTools.calcSquareArea(self.puSideLength)
            self.spatialTools.buildSquares(progress,progMin,progMax,False,self.bbox,self.outFName,self.encoding,self.crs,self.puSideLength,'',self.puidFieldName)
        else:
            if self.puSizeTypeIdx == 0:
                self.puArea = self.getParameterValue(self.SIZE)
                self.puSideLength = self.gridTools.calcHexagonSideLength(self.puArea)
            else:
                self.puSideLength = self.getParameterValue(self.SIZE)
                self.puArea = self.gridTools.calcHexagonArea(self.puSideLength)
            self.spatialTools.buildHexagons(progress,progMin,progMax,self.bbox,self.outFName,self.encoding,self.crs,self.puSideLength,self.puidFieldName)
        # clip grid if require
        if self.clipLayer <> None:
            progress.setText('Starting clipping process...')
            # create temporary file names
            path,fname = os.path.split(self.outFName)
            tsn = os.path.join(path, self.tempPrefix + 'single.shp')
            tgn = os.path.join(path, self.tempPrefix + 'grid.shp')
            tin = os.path.join(path, self.tempPrefix + 'int.shp')
            tsgn = os.path.join(path, self.tempPrefix + 'singlegrid.shp')
            progMin = 20
            progMax = 25
            progress.setText('Convert clip layer from multi to single...')
            self.spatialTools.multiToSingle(progress,progMin,progMax,self.clipLayer,self.outFName,self.tempPrefix,self.encoding,self.crs)
            # make temporary grid
            progress.setText('Making temporary grid...')
            progMin = 25
            progMax = 30
            self.spatialTools.buildSquares(progress,progMin,progMax,True,self.bbox,self.outFName,self.encoding,self.crs,self.puSideLength,self.tempPrefix,self.puidFieldName)
            # intersect with single clip layer with temporary grid
            progMin = 30
            progMax = 35
            progress.setText('Intersecting temporary grid with single clip layer...')
            grdLyr = QgsVectorLayer(tgn, 'tempgrid', 'ogr')
            sngLyr = QgsVectorLayer(tsn, 'tempsingle', 'ogr')
            self.spatialTools.intersectLayers(progress,progMin,progMax,sngLyr,grdLyr,tsgn,'POLYGON',self.encoding,self.crs,self.puidFieldName,None)
            grdLyr = None
            self.spatialTools.removeTempFile(tgn)
            sngLyr = None
            self.spatialTools.removeTempFile(tsn)
            # intersect result from above with grid layer
            progress.setText('Intersecting intersect results with pu layer...')
            progMin = 35
            progMax = 60
            puLyr = QgsVectorLayer(self.outFName, 'pu', 'ogr')
            tsgLyr = QgsVectorLayer(tsgn, 'tempsinglegrid', 'ogr')
            self.spatialTools.intersectLayers(progress,progMin,progMax,tsgLyr,puLyr,tin,'POLYGON',self.encoding,self.crs,self.puidFieldName,None)
            puLyr = None
            tsgLyr = None
            self.spatialTools.removeTempFile(tsgn)
            # find matching PUs
            progMin = 60
            progMax = 70
            progress.setText('Identifying interesecting PUs...')
            intLyr = QgsVectorLayer(tin, 'tempint', 'ogr')
            matchList = self.spatialTools.vectorFindMatchingPUs(progress,progMin,progMax,intLyr)
            intLyr = None
            self.spatialTools.removeTempFile(tin)
            # delete non-overlapping PUs
            progMin = 70
            progMax = 80
            progress.setText('Deleting non-intersecting PUs...')
            self.spatialTools.deleteCells(progress,progMin,progMax,matchList,self.outFName)
            # renumber PUs
            progress.setPercentage(85)
            progMin = 85
            progMax = 95
            progress.setText('Renumbering PUs...')
            self.spatialTools.reNumberPUs(progress,progMin,progMax,self.outFName,self.puidFieldName)

