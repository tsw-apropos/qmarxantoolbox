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

from PyQt4.QtCore import QSettings
from qgis.core import *
import os, sys

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterSelection, ParameterTableField, ParameterString, ParameterFile, ParameterRaster
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector
from calculations import qmtCalc, qmtSpatial

class CalculateRaster(GeoAlgorithm):

    PU_LAYER = 'PU_LAYER'
    RASTER_LAYER = 'RASTER_LAYER'
    METHOD = 'METHOD'
    DESTINATION = 'DESTINATION'
    INTERSECT_OPERATION = 'INTERSECT_OPERATION'
    FLD_PREFIX = 'FLD_PREFIX'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Rasters in Planning Units'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Data Preparation'
        
        # set defaults values needed
        self.calcTools = qmtCalc()
        self.spatialTools = qmtSpatial()
        self.tempPrefix = 'qmt%d_' % os.getpid()
        self.encoding = u'UTF-8'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterVector(self.PU_LAYER, self.tr('Planning Unit Layer'), \
            [ParameterVector.VECTOR_TYPE_POLYGON], False))
        self.addParameter(ParameterRaster(self.RASTER_LAYER, self.tr('Raster Source Layer'), \
            False))
        self.addParameter(ParameterSelection(self.METHOD, self.tr('Calculation Method'), \
            ["measure","weighted","pixel value"], False))
        self.addParameter(ParameterSelection(self.DESTINATION, self.tr('Output Format'), \
            ["single field","multiple fields"], False))
        self.addParameter(ParameterSelection(self.INTERSECT_OPERATION, self.tr('Intersection Operation'), \
            ["sum","mean","max","min","count","presence"], False))
        self.addParameter(ParameterFile(self.OUT_DIR,self.tr('Output Directory'), \
            True, False))
        self.addParameter(ParameterString(self.FLD_PREFIX, self.tr('File Name or Prefix'), \
            default=''))
        
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
        self.rstLayer = self.getParameterValue(self.RASTER_LAYER)
        #self.calcField = self.getParameterValue(self.CALC_FIELD)
        self.methodIdx = self.getParameterValue(self.METHOD)
        if self.methodIdx == 0:
            self.method = 'measure'
        elif self.methodIdx == 1:
            self.method = 'weighted'
        else:
            self.method = 'field'
        self.intersectOpIdx = self.getParameterValue(self.INTERSECT_OPERATION)
        if self.intersectOpIdx == 0:
            self.intersectOp = 'sum'
        elif self.intersectOpIdx == 1:
            self.intersectOp = 'mean'
        elif self.intersectOpIdx == 2:
            self.intersectOp = 'max'
        elif self.intersectOpIdx == 3:
            self.intersectOp = 'min'
        elif self.intersectOpIdx == 4:
            self.intersectOp = 'count'
        elif self.intersectOpIdx == 5:
            self.intersectOp = 'presence'
        self.destIdx = self.getParameterValue(self.DESTINATION)
        if self.destIdx == 0:
            self.destination = 'single'
        else:
            self.destination = 'multiple'
        self.outDir = self.getParameterValue(self.OUT_DIR)
        self.fieldName = self.getParameterValue(self.FLD_PREFIX).strip()
        # validate options to ensure that choices are valid
        if self.destination == 'single':
            # single column output
            if self.method == 'measure':
                # all measure permitted
                pass
            elif self.method == 'weighted':
                if self.intersectOp == 'presence':
                    result = 'The weighted method can not be used with presence operator; use the measure method.'
                elif self.intersectOp == 'count':
                    result = 'The weighted method can not be used with count operator; use the measure or pixel value methods.'
            elif self.method == 'field':
                if self.intersectOp == 'presence':
                    result = 'The pixel value method can not be used with presence operator; use the measure method.'
        else:
            # multiple column output
            if self.method == 'measure':
                # all methods permitted
                pass
            elif self.method == 'weighted':
                result = 'Multiple field output can not be weighted; use measure method.'
            elif self.method == 'field':    
                result = 'Multiple field output can not use field method; use measure method.'
        # check lengths
        if len(self.fieldName) > 20 or len(self.fieldName) == 0 or ' ' in self.fieldName:
            if result == None:
                result = ''
            else:
                result += '\n'
            result += 'File names or prefixes must be between 1 and 20 characters long and can not contain spaces.'
            
        return result

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        
        
        # get path
        path,fileName = os.path.split(self.puLayer)
        # find open layer instance
        lList = QgsMapLayerRegistry.instance().mapLayers()
        for key, value in lList.iteritems():
            fileName = value.dataProvider().dataSourceUri().split('|')[0]
            if fileName == self.puLayer:
                self.puL = value
            if fileName == self.rstLayer:
                self.rstL = value
        # create temp file name
        self.tempPrefix = 'qmt%d_' % os.getpid()
        trg = os.path.join(path, self.tempPrefix + 'grid.tif')
        # extract raster information
        pixelSize = self.rstL.rasterUnitsPerPixelX()
        if self.rstL.dataProvider().srcHasNoDataValue(1):
            srcNDValue = self.rstL.dataProvider().srcNoDataValue(1)
        else:
            srcNDValue = 0
        # create raster
        progress.setText('Creating Matching Raster')
        progress.setPercentage(15)
        self.spatialTools.rasterCreateMatching(trg,self.puL,self.rstL,'puid')
        # measure
        progress.setText('Measuring Raster')
        progMin = 15
        progMax = 90
        results, uniqueValues = self.spatialTools.rasterMeasure(progress,progMin,progMax,trg,self.rstL.source(),False,srcNDValue,pixelSize)
        # output file
        progress.setText('Writing Results')
        progMin = 90
        progMax = 99
        ofn = os.path.join(self.outDir,self.fieldName)
        if self.destIdx == 0:
            self.calcTools.fileSingleOutput(progress,progMin,progMax,results,self.puL,'puid',ofn,self.method,self.intersectOp)
        else:
            self.calcTools.fileMultiOutput(progress,progMin,progMax,results,self.puL,'puid',ofn,self.method,self.intersectOp, uniqueValues)


