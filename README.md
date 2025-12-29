# qmarxantoolbox
## Marxan Processing tools for QGIS

[Marxan](https://marxansolutions.org/) is one of the leading conservation tools in the world. Marxan is designed as a decision support tool which asks the question, "How can I meet these targets efficiently?". Marxan uses spatial data in a non-spatial environment to test many different solutions to find near-optimal solutions to the before stated question. The QMarxan Toolbox for QGIS 3 and above provides a series of tools to generate convert spatial data into a format that Marxan can understand and use. The QMarxan Toolbox also provides tools to assist in the calibration of your Marxan analysis.

## Overview

The QMarxan Toolbox is a QGIS plugin that provides a set of processing tools for QGIS 3.x for Marxan data preparation, export to Marxan, calibration and analysis of results. The underlying algorithms for the QMarxan Toolbox come from the now retired QMarxanZ project. The current version is 2.0.3. 

QMarxan can be used with Marxan 2.4.3 or with the new Marxan version 4.0.5. Marxan can be downloaded for Windows, Linux and MacOS computers here.

This document is not however a substitute for Marxan training. For information on training see the Marxan Solutions website.

## Use Overview

The QMarxan Toolbox has the following work-flow design:
1. With other tools create your planning unit file and make sure to add status and cost fields.
2. Calculate the planning unit contributions for each feature using standard QGIS methods and join your results into a single large table.
3. Create a folder for each scenario and within it use the Create Input File and Folders tool to make a input.dat file along with an input, output and pu folder.
4. Use the Export Boundary File tool to create a bound.dat file in the scenario's input folder.
5. Use the Export Feature Files tool to create the spec.dat, puvsp.dat and puvsp_sporder.dat files from your single joined table with all features.
6. After creation edit the content of the spec.dat file to set targets using one of the three options of prop, target and targetocc.
7. Use the Export Planning Units tool to create the pu.dat file from your planning unit layer using the cost and status fields. Make sure that all records have valid values.
8. Calibrate the SPF values first to ensure targets are met.
9. Calibrate the BLM values using the Graph BLM tool or the Graph BLM tool together with the Estimate BLM tool.
10. Calibrate the Iterations using the Iteration Calibration tool.
11. Use the Report Features tool to assess the conservation feature compositions of groups of planning units as needed.

## Tool Details

The QMarxan Toolbox consists of nine tools in four groups. The groups and tools are organized as follows:

1. Create Project
    * Create Input File and Folders
2. Export Input Files
    * Export Boundary File
    * Export Feature Files
    * Export Planning Unit File
3. Refine Results
    * Calibrate SPF
    * Estimate BLM
    * Graph BLM
    * Iteration Calibration
4. Report
    * Report Feature for Selected Planning Units

### Create Input File and Folders

This tool creates a folder structure with an input, output, pu and report folder and an input.dat file. The input.dat file is the basic control file for a Marxan project and the input and output folders are default names for the Marxan inputs and outputs respectively.

The input value for this tool is the name of the folder you want to use for your Marxan project.

### Export Boundary File

The boundary file in Marxan provides information on what planning units are next to other planning units and the weight of the boundary relationship between them.

Input values for this tool are:
 * Planning unit layer - For a Marxan analysis you must create a planning unit layer which will divide the study area into planning units. Planning units are usually of regularly shaped areas and they must be numbered with a unique id. This is the correct layer to choose for this input value.
 * Planning unit id field - The name of the field with the planning unit id is selected here.
 * Boundary method - The boundary length between planning units can be set in multiple ways. If you have no specific concerns about wanting to impact how areas are selected except by their adjacency to other areas then the first option, using a single value for all planning units, is appropriate. If you want to use the actual length of the boundaries then use the measured option. If you want to use some weighted value of the measured length times a field value choose weighted. If you want to use a field value only choose the field option.
 * Boundary treatment - Some Marxan practitioners suggests there is merit is excluding or assigning half values to planning unit boundaries at the perimeter of the planning area. This option enables this choice. Best empirical evidence suggests that using a consistent value on all boundaries gives the least biased result if all planning units are the same size.
 * Boundary value - If you are using the Single Value method which assigns a single value to al boundaries enter that value into this field.
 * Calculation field - If you are using the Weighted or Field methods, select your calculating field here.
 * Calculation method - If you are using a weighted or field method, it is possible that the values from one PU's field will not match the values of the adjacent PU. You can choose three options of how to process these differences which are to use the mean, maximum or minimum.
 * Marxan input folder - This folder is where the bound.dat file will be written. This file does not need to be edited after creation unless a new planning unit layer is created or the planning unit layer is altered.

### Export Feature Files

There are three files in Marxan that tell Marxan about your features of interest and their targets. These files are the spec.dat file, pusvsp.dat and puvsp_sporder.dat. This tool creates all three in a single step, with the understanding that you will need to manually edit the spec.dat file in a text editor or spreadsheet program to set target and species penalty factor values. For users unfamiliar with the puvsp_sporder.dat file, it has the same contents as the puvsp.dat file, but in species order and this saves processing time when running Marxan.

Input values for this tool are:

    Planning unit layer - The planning unit layer or table with all the calculated values for each feature is selected here. This might be a shape file or a table or a GeoPackage or spatial database layer. What is important is that all the calculated values are available in a single file and that it has a planning unit id field.
    Planning unit id field - The name of the field with the planning unit id is selected here.
    Feature fields - Select fields for inclusion as features in your project by marking the check box beside them
    Marxan input folder - This folder is where the spec.dat, puvsp.dat and pusvsp_sporder.dat files will be written. The puvsp.data and pusvsp_sporder.dat describe how much of each feature exists in each planning unit. Although only the puvsp.dat file is required, creating both files speeds the initialization process for Marxan. These two files do not need to be edited after creation unless features are added, removed or recalculated. The spec.dat file will need to be altered after creation to set targets using the prop, target or targetocc fields. The prop field is a proportional target field with values ranging from 0 to 1. The target field is used to set targets in the units of the measured feature. The targetocc field allows users to set targets based on the number of occurrences of a feature. Please note that only one file can be used for each feature. Please refer to the Marxan user documentation for more details.

### Export Planning Unit File

The planning units file describes what planning units exist, their status and the cost associated with selecting them.

Input values for this tool are:

    Planning unit layer - The planning unit layer with the id, cost and status values as fields.
    Planning unit id field - The name of the field with the planning unit id is selected here.
    Planning unit cost field - The name of the field with planning unit cost values for each planning unit is selected here.
    Planning unit status field - The name of the field with the planning unit status values for each planning unit is selected here.
    Marxan input folder - This folder is where the pu.dat file will be written.

### Calibrate SPF

This tool provides the means to adjust SPF values to ensure that all targets are met. Note that if you are using version 4.0.5 of Marxan, you need to set the VERBOSITY value to 4 or higher in the input.dat file so that the MarOptTotalAreas.csv file gets created. The input parameters are as follows:

    Marxan Executable File Name - The name and path to the executable Marxan file is selected here. On Windows, this is most commonly placed in the project folder itself.
    Feature SPF Adjustment Method - This tool offers three methods of adjusting the SPF values. The default option is called "As Group". In this first method, all features who are targets are not met have their SPF values increased together and other features whose targets are met, have their SPF values unaltered. The second method is called "Individually" and in this case each feature that fails to reach its targets has its SPF values increased on its own while all other features SPF values are left unaltered. The third method is called "All Together" and in this case, SPF values for all features are increased if any features fail to meet their targets. The group method is recommended because it requires far fewer iterations than the individual method and is more precise than the all together method.
    Target success percentage - This is the percentage of the time the feature is expected to meet its target. The default value is 90% because this provides Marxan with more flexibility than selecting 100%.
    Step size for SPF increases - This is the size of the stepwise increases of the SPF value between each time that Marxan is run.
    Marxan project folder (with input.dat) - This is the Marxan project folder that contains the input.dat file and the input, output, pu and report folders.

###Estimate BLM

The Estimate BLM tool provides a relatively quick method to estimate a BLM value. The method involved is detailed in the Marxan Good Practices Handbook in Section 8.3.5. Please see the handbook for details on the theory. In practice this method runs Marxan three times and provides a range of BLM values that will be close to the range of BLM values which will result in the largest changes in results. This tool provides a quick and dirty way to get a reasonable BLM value, but the Graph BLM tool and the methods for using it are still preferred to get an authoritative result. Input parameters are as follows:

    Marxan Executable File Name - The name and path to the executable Marxan file is selected here. On Windows, this is most commonly placed in the project folder itself.
    Marxan project folder (with input.dat) - This is the Marxan project folder that contains the input.dat file and the input, output, pu and report folders.

### Graph BLM

The Graph BLM tool provides a methodical means to evaluate BLM values for a Marxan problem. The details of this method are detailed in the Marxan User Manual. The method involve testing a series of values and then producing a graph of cost vs boundary length, to allow the user to select the balance point between these two competing concerns. This tool also produces a series of histograms and csv files for each BLM value to allow the user to see how the increase in BLM values effects target achievement for features. In general as the BLM values increase some features become over-represented in the final solutions as a result of extra planning units being added to the solution to create clumped solutions. This histograms and tables are extra information to assist the analyst in assessing an appropriate BLM value and the implications of that choice. In some cases after an BLM value is selected it may be worthwhile to reset SPF values and conduct a second SPF calibration. Input parameters are as follows:

    Marxan Executable File Name - The name and path to the executable Marxan file is selected here. On Windows, this is most commonly placed in the project folder itself.
    BLM Value List - This is a comma separated list of BLM values to be tested. The system provides a default value and users are encouraged to adjust or replace these values according to their needs.
    Marxan project folder (with input.dat) - This is the Marxan project folder that contains the input.dat file and the input, output, pu and report folders.

### Iteration Calibration

The Iteration Calibration tool implements the method found in the Marxan Good Practices Handbook in Section 8.3.2. This involves testing a series of values and examining the costs as Cumulative Distribution Function (CDF) graphs. As the graphs move to the left, it means that the variance in the solutions has been reduced and more of the solutions are near the minimum solution. This tool provides CDF graphs for costs, boundary and Marxan score as well as a csv file containing a summary of those data as well as the raw values. By using the graphs and tabular results together users are able to assess the real impact of different SPF values. Input parameters are as follows:

    Marxan Executable File Name - The name and path to the executable Marxan file is selected here. On Windows, this is most commonly placed in the project folder itself.
    Iteration List - This is a comma separated list of iteration values to be tested. The system provides a default value and users are encouraged to adjust or replace these values according to their needs.
    Marxan project folder (with input.dat) - This is the Marxan project folder that contains the input.dat file and the input, output, pu and report folders.

### Report Features for Selected Planning Units

This tool lets you look at the feature contents of arbitrary selections of planning units. To use this tool select the planning units of interest using QGIS and then open this tool and run it.

Input values for this tool are:

    Planning unit layer - The planning unit layer with the planning unit id field
    Planning unit id field - The name of the field with the planning unit id is selected here.
    Marxan input folder - The Marxan input folder is selected here. This tool reads the puvsp.dat and spec.dat files to generate the report.
    Report output file name - Assign a name and location for your report name here.

This tool will create a comma separated file you can open in an spreadsheet program to look at the results. The file will contain the following values:

    Marxan Feature Id - Each feature is assigned a numerical id in the spec.dat file.
    Marxan Feature Name - Each feature is assigned a name in the spec.dat file. When using the QMarxan Toolbox this name is the field name in the source planning unit layer.
    Feature Count - The number of times this feature was recorded in the selected planning units.
    Selected Planning Unit Count - The number of selected planning units.
    Occurrence Percent - The percent occurrence of the feature in the selected planning units.
    Feature Value Total (sum) - The total amount of the feature in the selected planning units in the units provided to Marxan.

How to Cite use of the QMarxan Toolbox

Trevor Wiens QMarxan Toolbox, Version 2.0.3.
