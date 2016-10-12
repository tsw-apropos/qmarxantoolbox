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
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'Apropos Information Systems Inc'
__date__ = '2016-09-02'
__copyright__ = '(C) 2016 by Apropos Information Systems Inc'


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QMarxanToolbox class from file QMarxanToolbox.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .marxantoolbox import QMarxanToolboxPlugin
    return QMarxanToolboxPlugin()
