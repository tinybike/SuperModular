#!/usr/bin/env python
import sys 
import cdecimal
sys.modules["decimal"] = cdecimal
# requires: pip install --allow-external cdecimal cdecimal
from decimal import *

import numpy as np
import scipy.stats
import pandas as pd

import matplotlib
import pylab as P

np.set_printoptions(linewidth=500)
pd.options.display.mpl_style = "default"

if matplotlib.is_interactive():
    P.ioff()

DIGITS = Decimal(".00000001")

# there are N "agents" which can place bets
N = 1000

# agents start with a fixed amount of money
STARTING_BALANCE = Decimal("100")

# discrete time simulation, where time goes from 1 to DURATION
DURATION = 100

# rounding errors are put into a fund and disbursed as needed
error_fund = Decimal("0")

def quant(arr):
    return np.array(
        [a.quantize(DIGITS) if a != 0 else Decimal("0") for a in arr]
    )

def shift(arr):
    return np.array(
        [-1 if a else 1 for i, a in enumerate(arr == 0)]
    )

def place_bets(balance):
    # bet (1) or no bet (0)
    decisions = np.round(np.random.rand(N))

    # fraction of agent's money used for the bet
    fraction_to_bet = map(Decimal, np.round(np.random.rand(N) * decisions, 4))

    # return amount of bet
    bets = []
    for i, b in enumerate(balance):
        bets.append(Decimal(round(b * fraction_to_bet[i])))
    return quant(bets)

def adjust_for_rounding_error(contrib):
    total = sum(contrib)
    if total != 1:
        if total > 1:
            err = total - 1
            error_fund += err
        else:
            err = 1 - total
            error_fund -= err

def close_market(bets):
    # targets of bets (red -1 or blue 1)
    target = shift(np.random.randint(0, 2, N))
    
    # if both sides are represented, then disburse pools to the winners
    target_bets = target * bets
    if any(target_bets > 0) and any(target_bets < 0):

        # outcome of the event being bet on (-1 or 1)
        outcome = shift(np.random.randint(0, 2, 1))

        # figure out which users won and which lost
        winners = (target == outcome)
        losers = ~winners

        # calculate the winning and losing pools
        win_bets = quant(winners * bets)
        lose_bets = quant(losers * bets)
        win_pool = sum(win_bets).quantize(DIGITS)
        lose_pool = sum(lose_bets).quantize(DIGITS)
        # assert win_pool + lose_pool == sum(bets)

        # calculate fractional contributions of winners/losers to their pools
        win_contrib = win_bets / win_pool
        lose_contrib = lose_bets / lose_pool
        assert sum(win_bets + win_contrib*lose_pool).quantize(DIGITS) == sum(bets)
        # assert sum(quant(win_bets + win_contrib*lose_pool)) == sum(bets)

        # calculate payouts
        return quant(win_contrib * lose_pool + win_bets)
    else:
        return bets

def median_quartile(data):
    med = np.median(data)
    left = scipy.stats.scoreatpercentile(data, 25)
    right = scipy.stats.scoreatpercentile(data, 75)
    return med, (med - left) / 0.68, (right - med) / 0.68

def midpoints(edges):
    left = edges[1:]
    right = edges[:-1]
    return (left + right) / 2.0

# set up initial balances
balance = np.array([i*STARTING_BALANCE for i in map(Decimal, np.ones(N))])
total_balance = N * STARTING_BALANCE

# run simulation
P.figure()
for t in xrange(DURATION):

    # get bets from agents
    bets = np.array(map(Decimal, place_bets(balance)))

    # subtract bets from agents' balance
    balance -= bets

    # close the market and calculate payouts
    payouts = close_market(bets)

    # add payouts to winners' balances
    balance += payouts

    # make histograms
    if t in (0, 5, 10, 50, 100):
        n, bins, patches = P.hist(map(float, balance),
                                  bins=25,
                                  normed=1,
                                  histtype="step",
                                  log=False,
                                  align="mid")

# view the plots
P.xlabel("account balance")
P.ylabel("probability")
P.title("wealth distribution")
P.grid(False)
P.show(block=True)
