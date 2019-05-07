#!/usr/bin/python
# -*- coding: utf-8 -*-
# Chart the amortization table for an icelandic loan
#
# optionally, include actual mortage index for stated period
#
#    ice_graph principal interest year
#    argv    1                                          2           3           4
# inputs: <principal (loan is 80% of principal)> <interestRate> <startYear> <durationMonths>
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime as dt
import time
import locale
import numpy as np
import matplotlib
# matplotlib.use('Agg')					# PNG file output
from pylab import rcParams, subplot, legend, MaxNLocator, FuncFormatter
from matplotlib.dates import date2num
import matplotlib.pyplot as plot
import matplotlib.axis as axis
import matplotlib.mlab as mlab
import matplotlib.cbook as cbook
import matplotlib.ticker as ticker
import gchart as gc

#       VARIABLES

DISPLAY = True
CPI = 0.05		        # Default, fixed cpi
cpi_index = []			 # list of cpi indices as data
dates = []
x_dates = []

projectedDate = -1       # Year from which values are extrapolated
projectedTitle = ""

# Base parameters for calculation (default values for sanity testing)

Principal = 10000000			# command line specified
Interest = 0.04			        # command line specified
duration = 480					# Use 480 for 40 year loans, 300 for 25, etc.

defaultInflation = 0.05

# When the loan is made.
loanMadeYear = 1980
loanMadeMonth = 1

# Chart information
# Set font characteristics
rcParams['font.family'] = 'serif'
rcParams['axes.labelsize'] = '10'
rcParams['font.size'] = '12'

#       FUNCTIONS

# getInflation(i)
#    i = index of inflation rate to get
#   Returns the inflation rate for indexation. Can be specified
#    as constant or read in from file on a per month basis


def getInflation(i):
    global projectedDate
    global projectedTitle

    if(len(cpi_index) == 0):
        inflation = 0
    else:
        if i < len(cpi_index):
            inflation = cpi_index[i]/cpi_index[i-1] - 1
        else:
            # # Calculate average inflation/year
            # inflation = sum(cpi_index[-12:])/12
            # # for 0% projections
            # # inflation = 0
            x_dates.append(x_dates[-1] + 30)  # Tack on month to dates array
            inflation = defaultInflation / 12	              # for fixed rate charts

            if projectedDate == -1:             # store extrapolation year
                projectedDate = len(x_dates)-1

                projectedTitle = "\nProjected from July 2019 with %d%% annual inflation rate" % (
                    inflation * 12 * 100)
    return inflation

# comma_format()
#   , formatting function for matplotlib y axis - changes , to .


def comma_format(num, places=0):
    locale.setlocale(locale.LC_ALL, '')
    return locale.format_string("%.0f",  num, True)


def to_float(string):
    parts = string.split(',', 1)
    stringNum = parts[0] + '.' + parts[1]
    return float(stringNum)


# Open Google spreadsheet
def getCPIfromGoogleSheets(startYear, startMonth, durationMonths, filler):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'verdtrygging-931be3470c29.json', scope)
    gc = gspread.authorize(credentials)
    spreadsheetUrlKey = "1Ns2wWMUpsq5LAssKc4-AyRrey4-UPk6GAvx5s9YV6jo"

    CpiWorksheet = gc.open_by_key(
        spreadsheetUrlKey).worksheet("Lanakjaravisitala")

    if int(startYear) > 1995:
        CpiWorksheet = gc.open_by_key(
            spreadsheetUrlKey).worksheet("VisitalaNeysluverds")

    # Print the name of spreadsheet used
    print(CpiWorksheet.acell('A1').value)
    years = CpiWorksheet.col_values(1)

   # dates = spreadsheet.worksheet("IcelandIndex").col_values(1)
   # index = gc.getSeries(3, "IcelandIndex", spreadsheet)

    yearIndex = 0
    for i in range(1, len(years)):
        if(years[i] == startYear):
            yearIndex = i
            break

    months = 0
    monthIndex = startMonth
    thisYearsValues = CpiWorksheet.row_values(yearIndex)
    while months < int(durationMonths):
        if monthIndex >= len(thisYearsValues) or yearIndex >= len(years):
            break
        else:
            cpi_index.append(to_float(thisYearsValues[monthIndex]))

        x_dates.append(date2num(dt.datetime(
            int(years[yearIndex]), monthIndex, 1)))
        if monthIndex == 12:
            yearIndex += 1
            monthIndex = 1
            thisYearsValues = CpiWorksheet.row_values(yearIndex)
        else:
            monthIndex += 1
        months += 1


#       THE ACTION STARTS!

# I         = Interest
D = float(30.0/360.0)

AF = []			# Annuity factor
P = []
payment = []
interest = []
II = []			        # Inflation index
total = 0		        # Total capital paid
P0 = []
increase = 0
capital_out = []		# Capital outstanding
paid = []


# Determine whether fixed or supplied CPI rate should be used
# To use actual data, specify starting year. If period of loan is
# longer than data (which it will be for forty year loans) then the fixed
# rate will be used for missing time periods

#    argv    1                                          2           3           4
# inputs: <principal (loan is 80% of principal)> <interestRate> <startYear> <durationMonths>

if(len(sys.argv) >= 2):
    Principal = int(float(sys.argv[1]) * 0.8)		# Use 80% of value
    Interest = float(sys.argv[2])

dates = []
cpi_index = []
if len(sys.argv) >= 4:
    getCPIfromGoogleSheets(sys.argv[3], 1, sys.argv[4], 0.02)

if len(sys.argv) == 5:
    duration = int(sys.argv[4])
    years = duration/12

# Compute Payments
print("II     AF     P  ")
for i in range(0, duration):
    AF.append((1/(D*Interest) - 1/((D*Interest)*pow(1+D*Interest, duration-i))))

    if(i == 0):
        II.append(100 + 100 * getInflation(i))
        P.append(Principal * II[0]/100)
        increase = P[0] - Principal
    else:
        II.append(II[i-1] + II[i-1]*getInflation(i))
        P.append((P[i-1] - capital) * II[i]/II[i-1])
        increase = ((P[i-1] - capital) * II[i]/II[i-1]) - (P[i-1] - capital)

    payment = P[i]/AF[i]
    interest = P[i] * Interest * D
    capital = payment - interest
    total += capital

    paid.append(payment)
    capital_out.append(capital)

# #  print "%0.1f %.2f %0.1f %0.1f %0.2f %0.1f  Inc:%0.1f" % (II[i],AF[i], P[i], payment, capital, interest, increase)


#          GRAPHING
fig, ax1 = plot.subplots()
plot.title('Verðtryggð lán Principal = %s ISK in %s @ %.1f%% base rate %s'
           % (comma_format(Principal), sys.argv[3], Interest*100, projectedTitle), fontsize=13)

# Plot Capital Outstanding - blue
color = 'tab:blue'
ax1.set_ylabel("Capital Outstanding", color=color)
ax1.tick_params(axis='y', labelcolor=color)

plot.plot_date(x_dates[0:projectedDate], P[0:projectedDate],
               label="Capital Outstanding", marker='', lw=3.0,
               color=color, ls='-')
if projectedDate != -1:      # if the loan has not ended, add dotted lines
    plot.plot_date(x_dates[projectedDate:-1], P[projectedDate:-1],
                   marker='', color='tab:blue', ls='--', lw=3.0)

# Plot Monthly payments - red
color = 'tab:red'
ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
ax2.set_ylabel("Monthly Repayment", color=color)
ax2.tick_params(axis='y', labelcolor=color)

plot.plot_date(x_dates[0:projectedDate], paid[0:projectedDate],
               label="Monthly payment", marker='', ls='-', lw=3.0,
               color=color)

if projectedDate != -1:      # if the loan has not ended, add dotted lines
    plot.plot_date(x_dates[projectedDate:-1], paid[projectedDate:-1],
                   marker='', ls='--', color=color, lw=3.0)


lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
legnd = legend(lines + lines2, labels + labels2,
               loc='upper left', fancybox=True)
legnd.get_frame().set_alpha(0.5)


ax1.set_ylim(ymin=0)
ax2.set_ylim(ymin=0)
# ax1.xaxis.set_major_locator(MaxNLocator(12))
ax1.yaxis.set_major_formatter(FuncFormatter(comma_format))
ax2.yaxis.set_major_formatter(FuncFormatter(comma_format))

print("%s Total paid = %.2f" % (sys.argv[3], sum(paid)))
print("Additional money = %d (max was %d)\n" % (max(P) - Principal, max(P)))

if DISPLAY:
    plot.show()

figure.savefig(("fig_vl_%s_%s_%d.eps" %
                (sys.argv[1], sys.argv[3], years)), format="eps")
