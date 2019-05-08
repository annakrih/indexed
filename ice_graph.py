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

# Chart information
# Set font characteristics
rcParams['font.family'] = 'sans-serif'
rcParams['axes.labelsize'] = '10'
rcParams['font.size'] = '12'


def getInflation(i):
    # i = index of inflation rate to get
    # Returns the inflation rate for indexation. Can be specified
    # as constant or read in from file on a per month basis
    global projectedDate, chartTitle, x_dates

    if(len(cpi_index) == 0):
        inflation = ((1+defaultInflation)**(1.0/12.0)-1)
        if i == 0: 
            x_dates.append(date2num(dt.datetime(
                int(loanMadeYear), loanMadeMonth, 1)))
        else: 
            x_dates.append(x_dates[-1] + 30)  # Tack on month to dates array
    else:
        if i == 0:
            inflation = 0
        if i < len(cpi_index):      # calculate inflation from CPI from spreadsheet
            inflation = cpi_index[i]/cpi_index[i-1] - 1
        else:                       # return default inflation
            x_dates.append(x_dates[-1] + 30)  # Tack on month to dates array
            inflation =((1+defaultInflation)**(1.0/12.0)-1)	              # for fixed rate charts

            if projectedDate == -1:             # store extrapolation year
                projectedDate = len(x_dates)-1

                chartTitle = chartTitle + "\nProjected from July 2019 with %d%% annual inflation rate" % (defaultInflation * 100)
    return inflation


def comma_format(num, places=0):
    # formatting function for matplotlib y axis - changes , to .
    locale.setlocale(locale.LC_ALL, '')
    return locale.format_string("%.0f",  num, True)


def to_float(string):
    # takes a string with the number format 1000,2
    # and changes it to a float
    parts = string.split(',', 1)
    stringNum = parts[0] + '.' + parts[1]
    return float(stringNum)


def getCPIfromGoogleSheets():
    # Gets the Consumer Price Index from the google spreadsheet
    # from startMonth-startYear and for duration months.
    # Open Google spreadsheet
    global cpi_index, x_dates
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'verdtrygging-931be3470c29.json', scope)
    gc = gspread.authorize(credentials)
    spreadsheetUrlKey = "1Ns2wWMUpsq5LAssKc4-AyRrey4-UPk6GAvx5s9YV6jo"

    CpiWorksheet = gc.open_by_key(
        spreadsheetUrlKey).worksheet("Lanakjaravisitala")

    if int(loanMadeYear) > 1995:
        CpiWorksheet = gc.open_by_key(
            spreadsheetUrlKey).worksheet("VisitalaNeysluverds")

    # Print the name of spreadsheet used
    print(CpiWorksheet.acell('A1').value)
    years = CpiWorksheet.col_values(1)

    # Find starting year row
    yearIndex = 0
    for i in range(1, len(years)):
        if(years[i] == loanMadeYear):
            yearIndex = i
            break

    # Get data:
    months = 0
    monthIndex = loanMadeMonth
    thisYearsValues = CpiWorksheet.row_values(yearIndex+1)
    while months < int(duration):
        if monthIndex >= len(thisYearsValues) or yearIndex >= len(years):
            break
        else:
            cpi_index.append(to_float(thisYearsValues[monthIndex]))

        x_dates.append(date2num(dt.datetime(
            int(years[yearIndex]), monthIndex, 1)))

        # go to next month:
        if monthIndex == 12:
            yearIndex += 1
            monthIndex = 1
            thisYearsValues = CpiWorksheet.row_values(yearIndex+1)
        else:
            monthIndex += 1
        months += 1


def computePayments():
    global paid, capital_out, increase, P, II, AF, payment, capital, total, interest, chartTitle

    if chartTitle == '':
        chartTitle = 'Verðtryggð lán Principal = %s ISK in %s @ %.1f%% base rate' % (comma_format(Principal),loanMadeYear, Interest*100) 

    # Compute Payments
    # print("II     AF     P  ")
    for i in range(0, duration):
        AF.append((1/(D*Interest) - 1/((D*Interest)*pow(1+D*Interest, duration-i))))

        thisMonthInflation = getInflation(i)
        if(i == 0):
            II.append(100 + 100 * thisMonthInflation)
            P.append(Principal)
            increase = P[0] - Principal
        else:
            II.append(II[i-1] + II[i-1]*thisMonthInflation)
            P.append((P[i-1] - capital) * II[i]/II[i-1])
            increase = ((P[i-1] - capital) * II[i] /
                        II[i-1]) - (P[i-1] - capital)

        payment = P[i]/AF[i]
        interest = P[i] * Interest * D
        capital = payment - interest
        total += capital

        paid.append(payment)
        capital_out.append(capital)

        if i == 0:
            indexedInitialPayment.append(payment)
        else:
            indexedInitialPayment.append(indexedInitialPayment[i-1] * (thisMonthInflation+1))


    # #  print "%0.1f %.2f %0.1f %0.1f %0.2f %0.1f  Inc:%0.1f" % (II[i],AF[i], P[i], payment, capital, interest, increase)


def graphResults(saveName):
    fig, ax1 = plot.subplots(figsize=(11, 6))
    plot.title(chartTitle, fontsize=13)

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
    ax2.set_ylabel("Monthly payment", color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    plot.plot_date(x_dates[0:projectedDate], paid[0:projectedDate],
                   label="Monthly payment", marker='', ls='-', lw=3.0,
                   color=color)

    if projectedDate != -1:      # if the loan has not ended, add dotted lines
        plot.plot_date(x_dates[projectedDate:-1], paid[projectedDate:-1],
                       marker='', ls='--', color=color, lw=3.0)
    
    # Plot inital payment amount adjusted for inflation - yellow
    # color = 'orange'
    # plot.plot_date(x_dates[0:-1], indexedInitialPayment[0:-1],
    #                label="Inital payment - adjusted for infation", marker='', ls=':', lw=1.0,
    #                color=color)

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    legnd = legend(lines + lines2, labels + labels2,
                   loc='upper left', fancybox=True)
    legnd.get_frame().set_alpha(0.5)

    ax1.set_ylim(bottom=0)
    ax2.set_ylim(bottom=0)
    # ax1.xaxis.set_major_locator(MaxNLocator(12))
    ax1.yaxis.set_major_formatter(FuncFormatter(comma_format))
    ax2.yaxis.set_major_formatter(FuncFormatter(comma_format))

    if DISPLAY:
        plot.show()

    figFormat = "png"
    fig.savefig(("%s.%s" %
                 (saveName,  figFormat)), format=figFormat)


def printResults():
    print("------------Results-------------")
    print("  Loan: %s" % chartTitle)
    print("  Total paid =               %s" % comma_format(sum(paid)))
    print("  Maximum capital outstanding : %s" % comma_format(max(P)))
    print("               max - original : %s" %
          comma_format(max(P) - Principal))
    print("  First payment: %s" % comma_format(paid[0]))


def runSingleExperimentFromArgs():
    # Determine whether fixed or supplied CPI rate should be used
    # To use actual data, specify starting year. If period of loan is
    # longer than data (which it will be for forty year loans) then the fixed
    # rate will be used for missing time periods
    # inputs: <principal (loan is 80% of principal)> <interestRate> <startYear> <durationMonths>
    global Principal, Interest, dates, cpi_index, durationInYears, duration, loanMadeYear

    if(len(sys.argv) >= 2):
        Principal = int(float(sys.argv[1]) * 0.8)		# Use 80% of value
        Interest = float(sys.argv[2])

    if len(sys.argv) == 5:
        loanMadeYear = sys.argv[3]
        duration = int(sys.argv[4])
        durationInYears = duration/12
        getCPIfromGoogleSheets()
    computePayments()
    printResults()
    graphResults("saveName")


def initializeGlobalVariables():
    # should be run before running another consecutive experiment.
    global projectedDate, chartTitle, D, AF, P, payment, interest, II, total, increase, capital_out, cpi_index, dates, x_dates, paid,indexedInitialPayment
    projectedDate = -1
    D = float(30.0/360.0)
    AF = []
    P = []
    payment = []
    interest = []
    II = []
    total = 0
    increase = 0
    capital_out = []
    cpi_index = []
    dates = []
    x_dates = []
    paid = []
    indexedInitialPayment = []



# GLOBAL VARIABLES - should be initialized this way before running.
# Can be initialized with initializeGlobalVariables function
projectedDate = -1       # Year from which values are extrapolated
D = float(30.0/360.0)
AF = []			        # Annuity factor
P = []
payment = []
interest = []
II = []			        # Inflation index - Not used, using the CPI index directly, 
                        # but calculate the inflation index change from previous month here
total = 0		        # Total capital paid
increase = 0
capital_out = []		# Capital outstanding
cpi_index = []			# list of cpi indexes as data
dates = []
x_dates = []
paid = []
indexedInitialPayment = [] # How the payments should increase per month if they would only
                           # increase with inflation, not negative amortization


# VARIABLES - these are the default values
# set these values for experiments
DISPLAY = False
defaultInflation = 0.05		        # Default inflation per year, if cpi isn't used. 
loanMadeYear = 0
loanMadeMonth = 1
duration = 0
durationInYears = 0
Principal = 0
Interest = 0.2
chartTitle = ''

# main:

if len(sys.argv) >= 2:
    runSingleExperimentFromArgs()
    exit()


# Run multiple expiriments below this, and don't put arguments 
def run(title, saveName):
    global chartTitle
    initializeGlobalVariables()
    computePayments()
    chartTitle = title
    printResults()
    graphResults(saveName)

def runWithData(title, saveName):
    global chartTitle
    initializeGlobalVariables()
    getCPIfromGoogleSheets()
    computePayments()
    chartTitle = title
    printResults()
    graphResults(saveName)


def loanN40(): 
    global defaultInflation, loanMadeYear, loanMadeMonth, durationInYears, duration, Principal, Interest
    defaultInflation = 0.00		        # Default inflation per year, if cpi isn't used. 
    durationInYears = 40
    duration = durationInYears*12
    Interest = 0.07

def loanI40(): 
    global defaultInflation, loanMadeYear, loanMadeMonth, durationInYears, duration, Principal, Interest
    durationInYears = 40
    duration = durationInYears*12
    Interest = 0.02

def loanI25(): 
    global defaultInflation, loanMadeYear, loanMadeMonth, durationInYears, duration, Principal, Interest
    durationInYears = 25
    duration = durationInYears*12
    Interest = 0.02

def loanI20(): 
    global defaultInflation, loanMadeYear, loanMadeMonth, durationInYears, duration, Principal, Interest
    durationInYears = 20
    duration = durationInYears*12
    Interest = 0.02

Principal = 25000000
loanMadeYear = "2019"
loanMadeMonth = 1

# GOAL
loanN40()
run("40 year loan (N40) - Goal inflation 2.5%", "n40_goal")

defaultInflation = 0.025 # goalInflation

loanI40()
run("Indexed 40 year loan (I40) - Goal inflation 2.5%", "i40_goal")

loanI25()
run("Indexed 25 year loan (I25) - Goal inflation 2.5%", "i25_goal")

loanI20()
run("Indexed 20 year loan (I20) - Goal inflation 2.5%", "i20_goal")


# Average
loanN40()
run("40 year loan (N40) - Average inflation 5.0%", "n40_avg")

defaultInflation = 0.05 # goalInflation

loanI40()
run("Indexed 40 year loan (I40) - Average inflation 5.0%", "i40_avg")

loanI25()
run("Indexed 25 year loan (I25) - Average inflation 5.0%", "i25_avg")

loanI20()
run("Indexed 20 year loan (I20) - Average inflation 5.0%", "i20_avg")

# 1980
Principal = 327000
loanMadeYear = "1980"
loanMadeMonth = 1

loanN40()
run("40 year loan (N40)  - Loan made in 1980", "n40_1980")

defaultInflation = 0.05 # goalInflation

loanI40()
runWithData("Indexed 40 year loan (I40) - Loan made in 1980", "i40_1980")

loanI25()
runWithData("Indexed 25 year loan (I25) - Loan made in 1980", "i25_1980")

loanI20()
runWithData("Indexed 20 year loan (I20) - Loan made in 1980", "i20_1980")

# 1992
Principal = 8670000
loanMadeYear = "1992"
loanMadeMonth = 1

loanN40()
run("Loan N40 - Loan made in 1992", "n40_1980")

defaultInflation = 0.05 # goalInflation

loanI40()
runWithData("Indexed 40 year loan (I40) - Loan made in 1992", "i40_1980")

loanI25()
runWithData("Indexed 25 year loan (I25) - Loan made in 1992", "i25_1980")

loanI20()
runWithData("Indexed 20 year loan (I20) - Loan made in 1992", "i20_1980")