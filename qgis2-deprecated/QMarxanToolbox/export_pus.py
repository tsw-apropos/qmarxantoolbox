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

import os
from PyQt4.QtCore import QSettings
from qgis.core import *

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterFile,\
    ParameterTableField
from processing.tools import dataobjects, vector
from processing.core.ProcessingLog import ProcessingLog
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException

class ExportPlanningUnits(GeoAlgorithm):

    PU_LAYER = 'PU_LAYER'
    PU_FIELD = 'PU_FIELD'
    STAT_FIELD = 'STAT_FIELD'
    COST_FIELD = 'COST_FIELD'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Export Planning Unit File (pu.dat)'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to Marxan'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterVector(self.PU_LAYER, self.tr('Planning Unit layer'), \
            [ParameterVector.VECTOR_TYPE_POLYGON], False))
        self.addParameter(ParameterTableField(self.PU_FIELD, self.tr('Planning Unit Id Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterTableField(self.STAT_FIELD, self.tr('Planning Unit Status Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterTableField(self.COST_FIELD, self.tr('Planning Unit Cost Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterFile(self.OUT_DIR,self.tr('Folder for pu.dat file'), \
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
        self.costField = self.getParameterValue(self.COST_FIELD)
        self.statusField = self.getParameterValue(self.STAT_FIELD)
        self.outDir = self.getParameterValue(self.OUT_DIR)
        self.outFName = os.path.join(self.outDir,'pu.dat')

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        errorStatus,messageText = self.createPUFile(progress)
        if errorStatus <> 0:
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, messageText)
            raise GeoAlgorithmExecutionException(messageText)
                
    def createPUFile(self, progress):
        
        #
        # Step 1 - pull data from shape file
        #
        # get value indexes
        puIdx = self.puL.dataProvider().fields().indexFromName(self.puField)
        costIdx = self.puL.dataProvider().fields().indexFromName(self.costField)
        statusIdx = self.puL.dataProvider().fields().indexFromName(self.statusField)
        progress.setText('Processing Features')
        puFeatures = vector.features(self.puL)
        fCount = len(puFeatures)
        x = 0
        progPct = 0
        progMin = 0
        progMax = 45
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        puData = []
        for feat in puFeatures:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            # get values
            puId = int(feat.attributes()[puIdx])
            statusValue = int(feat.attributes()[statusIdx])
            costValue = float(feat.attributes()[costIdx])
            # add them to the array unless invalid
            if statusValue > 3:
                return(-1,'Invalid status values. Planning Unit Id: %d, Status Value: %d' % (puId,statusValue))
            else:
                puData.append([puId,costValue,statusValue])
        # sort data
        #QgsMessageLog.logMessage(str(puData))
        puData.sort()
        #
        # Step 2 - write file
        #
        progress.setText('Writing File')
        #QgsMessageLog.logMessage('writing file')
        tmpf = file(self.outFName, 'w')
        tmpf.write("id,cost,status\n")
        x = 0
        progMin = 50
        progMax = 99
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for row in puData:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            outText = '%d,%f,%d\n' % (row[0],row[1],row[2])
            tmpf.write(outText)
        tmpf.close()
        return(0,'Export of PU file successful')
