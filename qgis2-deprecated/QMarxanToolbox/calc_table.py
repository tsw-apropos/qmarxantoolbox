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

class CalculateTable(GeoAlgorithm):

    PU_LAYER = 'PU_LAYER'
    ID_FIELD = 'ID_FIELD'
    CALC_FIELD = 'CALC_FIELD'
    FLD_PREFIX = 'FLD_PREFIX'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Table Values in Planning Units'

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
        self.addParameter(ParameterTableField(self.CALC_FIELD, self.tr('Calculation Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterFile(self.OUT_DIR,self.tr('Output Directory'), \
            True, False))
        self.addParameter(ParameterString(self.FLD_PREFIX, self.tr('File Name'), \
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
        self.calcField = self.getParameterValue(self.CALC_FIELD)
        self.destination = 'single'
        self.method = 'measure'
        self.outDir = self.getParameterValue(self.OUT_DIR)
        self.fieldName = self.getParameterValue(self.FLD_PREFIX).strip()
        # validate options to ensure that choices are valid
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
        progress.setPercentage(10)
        # write output file
        progress.setText('Writing Results')
        progMin = 10
        progMax = 90
        ofn = os.path.join(self.outDir,self.fieldName)
        self.calcTools.fileTableOutput(progress,progMin,progMax,self.puL,self.puidField,self.calcField,ofn)

        return 'Done'


