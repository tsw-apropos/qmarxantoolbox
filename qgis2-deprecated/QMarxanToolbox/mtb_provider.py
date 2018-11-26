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

from processing.core.AlgorithmProvider import AlgorithmProvider
from processing.core.ProcessingConfig import Setting, ProcessingConfig

from create_pulayer import CreatePULayer
from calc_points import CalculatePoints
from calc_lines import CalculateLines
from calc_polygons import CalculatePolygons
from calc_raster import CalculateRaster
from calc_table import CalculateTable

from export_input import ExportInput
from export_boundary import ExportBoundary
from export_pus import ExportPlanningUnits
from export_features import ExportFeatures
from export_features_vs_planningunits import ExportFeaturesVsPlanningUnits

from report_summary import ReportSummary

class QMarxanToolboxProvider(AlgorithmProvider):

    def __init__(self):
        AlgorithmProvider.__init__(self)
        self.alglist = [
            CreatePULayer(),
            CalculatePoints(),
            CalculateLines(),
            CalculatePolygons(),
            CalculateRaster(),
            CalculateTable(),
            ExportInput(),
            ExportBoundary(),
            ExportPlanningUnits(),
            ExportFeatures(),
            ExportFeaturesVsPlanningUnits(),
            ReportSummary()
        ]

    def initializeSettings(self):
        AlgorithmProvider.initializeSettings(self)

    def unload(self):
        AlgorithmProvider.unload(self)

    def getName(self):
        return "qmarxantoolbox"

    def getDescription(self):
        return "QMarxan Toolbox Algorithms"

    def getIcon(self):
        return AlgorithmProvider.getIcon(self)

    def _loadAlgorithms(self):
        self.algs = self.alglist

    def supportsNonFileBasedOutput(self):
        return True
