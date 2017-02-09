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
from qgis.core import QgsVectorFileWriter
import os, datetime

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterFile
from processing.tools import dataobjects, vector

class ExportFeatures(GeoAlgorithm):

    IN_DIR = 'IN_DIR'
    OUT_DIR = 'OUT_DIR'

    def defineCharacteristics(self):
        """Define tool placement and parameters"""
        
        # The name that the user will see in the toolbox
        self.name = 'Export Feature File (spec.dat)'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to Marxan'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterFile(self.IN_DIR,self.tr('Select folder with calculated results (*.qmd files)'), \
            True, False))
        self.addParameter(ParameterFile(self.OUT_DIR,self.tr('Folder for spec.dat file'), \
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
        self.outFName = os.path.join(self.outDir,'spec.dat')
        result = None

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        # read directory file list
        progress.setText('Processing file list')
        fileList = os.listdir(self.srcDir)
        fCount = len(fileList)
        qmdFiles = []
        x = 0
        progPct = 0
        progMin = 0
        progMax = 45
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for fName in fileList:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            prefix,ext = os.path.splitext(fName)
            if ext == '.qmd':
                qmdFiles.append(os.path.split(fName)[1])
        qmdFiles.sort()
        progress.setText('Writing file')
        # write spec.dat file
        # rename existing spec.dat files
        if os.path.exists(self.outFName):
            nName = self.outFName + '.backup_%s' % datetime.datetime.now().isoformat()[:19].replace(':','').replace('-','')
            os.rename(self.outFName,nName)
        header = 'id\tprop\ttarget\ttargetocc\tspf\tname\n'
        f = open(self.outFName,'w')
        f.write(header)
        x = 0
        progMin = 50
        progMax = 99
        progPct = progMin
        lastPct = progPct
        progRange = progMax - progMin
        for rec in qmdFiles:
            x += 1
            progPct = ((float(x) / float(fCount) * 100) * (progRange/100.0)) + progMin
            if int(progPct) > lastPct:
                progress.setPercentage(progPct)
                lastPct = progPct
            f.write('%d\t0.0\t0.0\t0\t1.0\t%s\n' % (x,os.path.splitext(rec)[0]))
        f.close()
