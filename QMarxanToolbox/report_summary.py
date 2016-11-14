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
import os, sys, csv

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterFile, ParameterTableField
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector
from processing.core.ProcessingLog import ProcessingLog
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException

class ReportSummary(GeoAlgorithm):

    PU_LAYER = 'PU_LAYER'
    PU_FIELD = 'PU_FIELD'
    IN_DIR = 'IN_DIR'
    REPORT_FILE = 'REPORT_FILE'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Report Features for Selected Planning Units'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Results Analysis'
        
        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterVector(self.PU_LAYER, self.tr('Planning Unit Layer'), \
            [ParameterVector.VECTOR_TYPE_POLYGON], False))
        self.addParameter(ParameterTableField(self.PU_FIELD, self.tr('Planning Unit Id Field'), \
            self.PU_LAYER,0,False))
        self.addParameter(ParameterFile(self.IN_DIR,self.tr('Marxan Input Folder'), \
            True, False))
        self.addParameter(ParameterFile(self.REPORT_FILE,self.tr('Report Output File'), \
            isFolder=False, optional=False, ext='csv'))
        
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
        self.puField = self.getParameterValue(self.PU_FIELD)
        self.inDir = self.getParameterValue(self.IN_DIR)
        self.reportFile = self.getParameterValue(self.REPORT_FILE)
        
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
        # get selected feature list
        features = self.puL.selectedFeatures()
        puCount = self.puL.selectedFeatureCount()
        if puCount == 0:
            messageText = 'No planning units selected.'
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, messageText)
            raise GeoAlgorithmExecutionException(messageText)
            return()
        puIdx = self.puL.dataProvider().fields().indexFromName(self.puField)
        puIdList = []
        x = 0
        progress.setPercentage(0)
        progMin = 0
        progMax = 20
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for feat in features:
            x += 1
            progPct = ((float(x) / float(puCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            attr = feat.attributes()
            puIdList.append(int(attr[puIdx]))
        puIdList.sort()
        # get feature ids from spec.dat
        progPct = 0
        progress.setText('Checking spec.dat file')
        progress.setPercentage(progPct)
        specFile = os.path.join(self.inDir,'spec.dat')
        if os.path.exists(specFile):
            f = open(specFile,'r')
            contents = f.readlines()
            f.close()
            x = 0
            fCount = len(contents)
            progMin = 25
            progMax = 35
            progPct = progMin
            lastPct = progPct
            progRange = progMax - progMin
            specRecs = {}
            for specLine in contents:
                x += 1
                progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
                if int(progPct) > lastPct:
                    progress.setPercentage(progPct)
                    lastPct = progPct
                vals = specLine.strip().split('\t')
                if vals[0] <> 'id':
                    specRecs[int(vals[0])] = vals[5]
        else:
            messageText = 'File spec.data not found. Create spec.dat file first.'
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, messageText)
            raise GeoAlgorithmExecutionException(messageText)
            return()
        # aggregate data
        progress.setText('Reading puvsp.dat file')
        puvspFile = os.path.join(self.inDir,'puvsp.dat')
        if os.path.exists(puvspFile):
            # count lines using raw count for speed
            f = open(puvspFile, 'rb')
            lCount = 0
            buf_size = 1024 * 1024
            read_f = f.read
            buf = read_f(buf_size)
            while buf:
                lCount += buf.count(b'\n')
                buf = read_f(buf_size)
            f.close()
            #QgsMessageLog.logMessage(str(lCount))
            # now read through the contents
            featSummary = {}
            with open(puvspFile,'r') as csvfile:
                qmdReader = csv.DictReader(csvfile,delimiter='\t')
                progMin = 40
                progMax = 85
                progPct = progMin
                lastPct = progPct
                progRange = progMax - progMin
                for line in qmdReader:
                    x += 1
                    progPct = ((float(x) / float(lCount) * 100) * (progRange/100.0)) + progMin
                    if int(progPct) > lastPct:
                        progress.setPercentage(progPct)
                        lastPct = progPct
                    if int(line['pu']) in puIdList:
                        if line['species'] in featSummary:
                            featSummary[line['species']][0] += 1
                            featSummary[line['species']][1] += float(line['amount'])
                        else:
                            featSummary[line['species']] = [1,float(line['amount'])]
        else:
            messageText = 'File puvsp.data not found. Create puvsp.dat file first.'
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, messageText)
            raise GeoAlgorithmExecutionException(messageText)
            return()
        # convert to list to sort
        summaryList = [[int(key),value[0],value[1]] for key, value in featSummary.iteritems()]
        summaryList.sort()
        # write report
        nl = os.linesep
        progress.setText('Creating Report')
        f = open(self.reportFile,'w')
        f.write('featureId,featureName,featureCount,selectedPuCount,occurrencePercent,featureSum %s' % nl)
        x = 0
        fCount = len(summaryList)
        progMin = 90
        progMax = 99
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for rec in summaryList:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            f.write('%d,%s,%d,%d,%f,%f %s' % (rec[0],specRecs[rec[0]],rec[1],puCount,float(rec[1])/float(puCount)*100,rec[2],nl) )
        f.close()
