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
from processing.core.parameters import ParameterVector, ParameterSelection, ParameterTableField, ParameterString, ParameterFile
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector
from calculations import qmtCalc, qmtSpatial

class CalculatePoints(GeoAlgorithm):

    PU_LAYER = 'PU_LAYER'
    ID_FIELD = 'ID_FIELD'
    POINT_LAYER = 'POINT_LAYER'
    METHOD = 'METHOD'
    DESTINATION = 'DESTINATION'
    CALC_FIELD = 'CALC_FIELD'
    INTERSECT_OPERATION = 'INTERSECT_OPERATION'
    FLD_PREFIX = 'FLD_PREFIX'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Points in Planning Units'

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
        self.addParameter(ParameterTableField(self.ID_FIELD, self.tr('Planning Unit Id Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterVector(self.POINT_LAYER, self.tr('Point Source Layer'), \
            [ParameterVector.VECTOR_TYPE_POINT], False))
        self.addParameter(ParameterSelection(self.METHOD, self.tr('Calculation Method'), \
            ["measure","weighted","field"], False))
        self.addParameter(ParameterSelection(self.DESTINATION, self.tr('Output Format'), \
            ["single field","multiple fields"], False))
        self.addParameter(ParameterTableField(self.CALC_FIELD, self.tr('Calculation Field'), \
            self.POINT_LAYER,0,True))
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
        self.puidField = self.getParameterValue(self.ID_FIELD)
        self.pntLayer = self.getParameterValue(self.POINT_LAYER)
        self.calcField = self.getParameterValue(self.CALC_FIELD)
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
                if self.calcField == None:
                    result = 'The weighted method requires a calculation field.'
                else:
                    if self.intersectOp == 'presence':
                        result = 'The weighted method can not be used with presence operator; use the measure method.'
                    elif self.intersectOp == 'count':
                        result = 'The weighted method can not be used with count operator; use the measure or field methods.'
            elif self.method == 'field':
                if self.calcField == None:
                    result = 'The field method requires a calculation field.'
                else:
                    if self.intersectOp == 'presence':
                        result = 'With single field output the field method can not be used with presence operator; use the measure method.'
        else:
            # multiple column output
            if self.method == 'measure':
                # all methods permitted
                if self.calcField == None:
                    result = 'With multiple field output the measure method requires a calculation field.'
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
            if fileName == self.pntLayer:
                self.pntL = value
        # create temp file name
        self.tempPrefix = 'qmt%d_' % os.getpid()
        tfn = os.path.join(path, self.tempPrefix + 'int.shp')
        self.crs = self.puL.crs()
        progress.setPercentage(10)
        # intersection
        progress.setText('Intersecting Layers')
        progMin = 10
        progMax = 70
        self.spatialTools.intersectLayers(progress, progMin, progMax, self.pntL, self.puL, tfn, 'POINT', self.encoding, self.crs, self.puidField, self.calcField)
        # measure
        progress.setText('Measuring Points')
        progMin = 70
        progMax = 90
        results, uniqueValues = self.spatialTools.vectorMeasure(progress, progMin, progMax, tfn, 'POINT')
        self.spatialTools.removeTempFile(tfn)
        # output file
        progress.setText('Writing Results')
        progMin = 90
        progMax = 99
        ofn = os.path.join(self.outDir,self.fieldName)
        if self.destIdx == 0:
            #self.calcTools.puLayerSingleUpdate(results,self.puL,'puid',self.fieldName,self.method,self.intersectOp)
            self.calcTools.fileSingleOutput(progress,progMin,progMax,results,self.puL,self.puidField,ofn,self.method,self.intersectOp)
        else:
            #self.calcTools.puLayerMultiUpdate(results,self.puL,'puid',self.fieldName,self.method,self.intersectOp, uniqueValues)
            self.calcTools.fileMultiOutput(progress,progMin,progMax,results,self.puL,self.puidField,ofn,self.method,self.intersectOp, uniqueValues)
        return 'Done'


