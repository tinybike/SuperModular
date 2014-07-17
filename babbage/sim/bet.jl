# "Babbage" engine betting simulation
# Goals:
#   - Make sure the market isn't abusable
#   - Make sure the market doesn't "leak" funds
# @author jack@tinybike.net (Jack Peterson)

using Decimals
# using Winston
using Plotly

# there are N "agents" which can place bets
global const N = 10

# agents start with a fixed amount of money
global const STARTING_BALANCE = (100)

# discrete time simulation, where time goes from 1 to DURATION
global const DURATION = 100

global const DIGITS = 8

function place_bets(balance)
    # bet (1) or no bet (0)
    decisions = rand(0:1, N)
    @assert all((decisions .== 0) | (decisions .== 1))

    # fraction of agent's money used for the bet
    fraction_to_bet = decimal(round(rand(N) .* decisions, 4))

    # return amount of bet
    convert(Array{Decimal}, balance .* fraction_to_bet)
end

function close_market(bets)
    # targets of bets (red -1 or blue 1)
    target = rand(-1:2:1, N)

    # if both sides are represented, then disburse pools to the winners
    target_bets = float(target .* bets)
    if any(target_bets .> 0) && any(target_bets .< 0)

        # outcome of the event being bet on (-1 or 1)
        outcome = rand(-1:2:1)

        # figure out which users won and which lost
        winners = (target .== outcome)::BitArray{1}
        losers = ~winners

        # calculate the winning and losing pools
        win_bets = decimal(round(winners .* bets, DIGITS))
        lose_bets = decimal(round(losers .* bets, DIGITS))
        win_pool = sum(win_bets)
        lose_pool = sum(lose_bets)

        if (win_pool == 0) || (lose_pool == 0)
            return bets
        end
        # @assert win_pool + lose_pool == sum(bets)

        # calculate fractional contributions of winners/losers to their pools
        win_contrib = float(win_bets) ./ float(win_pool)
        lose_contrib = float(lose_bets) ./ float(lose_pool)

        # calculate payouts
        win_contrib .* round(float(lose_pool), DIGITS) + win_bets
    else
        bets
    end
end

# set up initial balances
balance = decimal(ones(N)) .* STARTING_BALANCE
total_balance = N * STARTING_BALANCE

# run simulation
# bins, counts = [], []
traces = []
for t in 1:DURATION

    # get bets from agents
    bets = place_bets(balance)
    # @assert all(0 .<= number(bets) .<= balance)

    # subtract bets from agents' balance
    balance -= bets
    # @assert sum(balance) == total_balance - sum(bets)

    # close the market and calculate payouts
    payouts = close_market(bets)
    # @assert sum(payouts) == sum(bets)

    # add payouts to winners' balances
    balance += payouts
    # @assert sum(balance) == total_balance

    # histogram balances
    if t % 10 == 0
        traces = [traces, [
            "x" => balance,
            "opacity" => 0.75,
            "type" => "histogram"
        ]]
        # b, c = hist(map(float, balance))
        # bins = [bins, midpoints(b)]
        # counts = [counts, c]
    end
end

# plot histograms (Plotly)
Plotly.signin("tinybike", "fnpdfepygv")
layout = ["barmode" => "overlay"]
response = Plotly.plot([traces], ["layout" => layout,
                                "filename" => "overlaid-histogram",
                                "fileopt" => "overwrite"])
plot_url = response["url"]
println(plot_url)

# plot histograms (Winston)
# plot(bins[1], counts[1])
# for b in bins, c in counts
#     oplot(b, c)
# end
# savefig("balances.png")
