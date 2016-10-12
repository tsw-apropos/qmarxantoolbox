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
import os, numpy, csv

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterFile
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector
from processing.core.ProcessingLog import ProcessingLog
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException

class ExportFeaturesVsPlanningUnits(GeoAlgorithm):

    IN_DIR = 'IN_DIR'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Export Features vs Planning Units (puvsp.dat)'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to Marxan'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterFile(self.IN_DIR,self.tr('Select folder with calculated results (*.qmd files)'), \
            True, False))
        self.addParameter(ParameterFile(self.OUT_DIR,self.tr('Folder for puvsp.dat and purvsp_sporder.dat files'), \
            True, False))

    def checkParameterValuesBeforeExecuting(self):
        """If there is any check to do before launching the execution
        of the algorithm, it should be done here.

        If values are not correct, a message should be returned
        explaining the problem.

        This check is called from the parameters dialog, and also when
        calling from the console.
        """
        self.srcDir = self.getParameterValue(self.IN_DIR)
        self.outDir = self.getParameterValue(self.OUT_DIR)
        self.outFName1 = os.path.join(self.outDir,'puvsp.dat')
        self.outFName2 = os.path.join(self.outDir,'puvsp_sporder.dat')
        result = None

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        # read directory file list
        nl = os.linesep
        progPct = 0
        progress.setText('Checking for spec.dat file')
        progress.setPercentage(progPct)
        specFile = os.path.join(self.outDir,'spec.dat')
        if os.path.exists(specFile):
            f = open(specFile,'r')
            contents = f.readlines()
            f.close()
            x = 0
            fCount = len(contents)
            progMin = 0
            progMax = 10
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
                    specRecs[vals[5]] = int(vals[0])
        else:
            messageText = 'File spec.data not found. Create spec.dat file first.'
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, messageText)
            raise GeoAlgorithmExecutionException(messageText)
            return()
        #QgsMessageLog.logMessage(str(specRecs))
        progress.setText('Matching species identifiers')
        fileList = os.listdir(self.srcDir)
        qmdFiles = []
        x = 0
        fCount = len(fileList)
        progMin = 10
        progMax = 20
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for fName in fileList:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            prefix,ext = os.path.splitext(os.path.basename(fName))
            if ext == '.qmd' and prefix in specRecs:
                qmdFiles.append([int(specRecs[prefix]),fName])
        qmdFiles.sort()
        #QgsMessageLog.logMessage(str(qmdFiles))
        progress.setText('Processing inputs')
        unOrdered = []
        # walk through qmd files and append to unordered list
        x = 0
        fCount = len(qmdFiles)
        progMin = 25
        progMax = 50
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for rec in qmdFiles:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            with open(os.path.join(self.srcDir,rec[1]),'r') as csvfile:
                qmdReader = csv.reader(csvfile,delimiter=',',quotechar="'")
                header = qmdReader.next()
                for row in qmdReader:
                    unOrdered.append((rec[0],row[0],row[1]))
        #
        # Step 2 - process costs
        #
        # use numpy to sort it quickly
        cnt = len(unOrdered)
        dtype = [('species', int),('pu', int),('amount', float)]
        npArray = numpy.array(unOrdered,dtype=dtype)
        # create puvsp order
        sList = list(numpy.sort(npArray, order=['pu','species']))
        # write results
        progress.setText('Writing puvsp.dat')
        puf = file(self.outFName1, 'w')
        puf.write("species\tpu\tamount%s" % nl)
        x = 0
        fCount = len(sList)
        progMin = 55
        progMax = 80
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for rec in sList:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            puf.write('%d\t%d\t%f%s' % (rec[0],rec[1],rec[2],nl))
        puf.close()
        # create puvsp_sporder order
        sList = list(numpy.sort(npArray,order=['species','pu']))
        # write results
        progress.setText('Writing puvsp_sporder.dat')
        spf = file(self.outFName2, 'w')
        spf.write("species\tpu\tamount%s" % nl)
        x = 0
        fCount = len(sList)
        progMin = 85
        progMax = 99
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for rec in sList:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            spf.write('%d\t%d\t%f%s' % (rec[0],rec[1],rec[2],nl))
        spf.close()
