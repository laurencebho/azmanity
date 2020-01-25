import csv
import math
import pprint
import datetime


#these top 2 functions are shamelessly stolen from stackoverflow
def datetime_to_float(d):
    epoch = datetime.datetime.utcfromtimestamp(0)
    total_seconds =  (d - epoch).total_seconds()
    return total_seconds


def float_to_datetime(fl):
    return datetime.datetime.fromtimestamp(fl)


def str_to_datetime(s):
    '''
    mm/yyyy to datetime
    '''
    day = 1
    month = int(s[:2])
    year = int(s[3:])
    dt = datetime.datetime(year, month, day)
    return dt


def filter(filename):
    with open(filename) as fr:
        reader = csv.reader(fr)
        with open('filtered.csv', 'w') as fw:
            writer = csv.writer(fw)
            for row in reader:
                if row[2] in ['1.0', '3.0']:
                    writer.writerow(row)


def create_prices_dict(filename):
    prices_dict = {}
    with open(filename) as fr:
        reader = csv.reader(fr)
        for row in reader:
            cusip = row[3]
            if cusip not in prices_dict:
                prices_dict[cusip] = {}
            month = row[1][3:]
            if row[4] == '':
                prices_dict[cusip][month] = None
            else:
                prices_dict[cusip][month] = abs(float(row[4]))
    return prices_dict


def key_from_value(target_val, d):
    for k, v in d.items():
        if v == target_val:
            return k
    return None


def create_returns_dict(prices_dict):
    returns_dict = {}
    for key in prices_dict:
        returns_dict[key] = {}
    for cusip, months in prices_dict.items():
        timestamps = {}
        for month in months:
            timestamps[month] = str_to_datetime(month)
        timestamps_list = list(timestamps.values())
        sorted_timestamps = sorted(timestamps_list)
        for i, month in reversed(list(enumerate(sorted_timestamps))):
            key = key_from_value(sorted_timestamps[i], timestamps)
            if i == 0:
                returns_dict[cusip][key] = None
                break
            prev_key = key_from_value(sorted_timestamps[i-1], timestamps)
            if prices_dict[cusip][key] is None or prices_dict[cusip][prev_key] is None:
                continue
            else:
                ret = math.log(prices_dict[cusip][key]) - math.log(prices_dict[cusip][prev_key])
                returns_dict[cusip][key] = ret
    return returns_dict


def pick_portfolios(prices_dict, date):
    ranges = [100.0, 60.0, 30.0, 15.0, 5.0, 0.0]
    portfolios = [[] for i in range(6)]
    for cusip, months in prices_dict.items():
        if date in months:
            price = months[date]
            for i, r in enumerate(ranges):
                if price is None:
                    break
                else:
                    #print(f'price: {price}, r: {r}')
                    if price > r:
                        portfolios[i].append(cusip)
                        break
    return portfolios


def get_mean_returns(portfolios, returns_dict):
    means = [0.0 for i in range(len(portfolios))]
    for i, portfolio in enumerate(portfolios):
        total = 0.0
        for cusip in portfolio:
            returns_sum = 0.0
            for ret in returns_dict[cusip].values():
                if ret is not None:
                    returns_sum += ret
            total += returns_sum
            #print(f'cusip: {cusip}, log returns sum: {returns_sum}')
        mean = total/len(portfolio)
        means[i] = mean
    return means


def get_returns_variance(portfolios, returns_dict, means):
    variances = [0.0 for i in range(len(portfolios))]
    for i, portfolio in enumerate(portfolios):
        total = 0.0
        for cusip in portfolio:
            returns_sum = 0.0
            for ret in returns_dict[cusip].values():
                if ret is not None:
                    returns_sum += ret
            total += (returns_sum - means[i]) ** 2
            #print(f'cusip: {cusip}, log returns sum: {returns_sum}')
        variance = total/len(portfolio)
        variances[i] = variance
    return variances


def add_quarter(date):
    month = int(date[:2])
    year = int(date[3:])

    month += 3
    if month > 12:
        year += 1
        month -= 12
    month_str = '{:2d}'.format(month)
    month_str = month_str.replace(' ', '0')
    return f'{month_str}/{str(year)}'


def calc_weights(portfolio, prices_dict, date, weighted):
    weights = {}
    if weighted:
        price_sum = 0.0
        for cusip in portfolio:
            if date in prices_dict[cusip]:
                price = prices_dict[cusip][date]
                if price is not None:
                    price_sum += price

        for cusip in portfolio:
            if date in prices_dict[cusip]:
                price = prices_dict[cusip][date]
                if price is not None:
                    weight = price * len(portfolio) / price_sum
                    weights[cusip] = weight
        #print(f'sum for date {date}: {sum(list(weights.values()))}')
        #print(price_sum)
    else:
        for cusip in portfolio:
            weights[cusip] = 1.0
    return weights


def roll_window(portfolios, start_date, prices_dict, weighted=False):
    performances = {}
    end_date = add_quarter(start_date)
    for i, portfolio in enumerate(portfolios):
        start_sum = 0.0
        end_sum = 0.0
        weights = calc_weights(portfolio, prices_dict, start_date, weighted)
        for cusip in portfolio:
            if start_date not in prices_dict[cusip]:
                continue
            start_price = prices_dict[cusip][start_date]
            if start_price is None:
                continue
            else:
                start_sum += start_price * weights[cusip]
                if end_date in prices_dict[cusip]:
                    end_price = prices_dict[cusip][end_date]
                    if end_price is None:
                        end_sum += ((-1) * start_price * weights[cusip])
                    else:
                        end_sum += end_price * weights[cusip]
        performances[i] = {
            'start': start_sum,
            'end': end_sum,
            'log return': math.log(end_sum) - math.log(start_sum)
        }
    portfolios = pick_portfolios(prices_dict, end_date)
    return performances, portfolios


def backtest(prices_dict, start_date, weighted=False):
    portfolios = pick_portfolios(prices_dict, start_date)
    with open('out.csv', 'a') as fw:
        ranges = ['100+', '60-100', '30-60', '15-30', '5-15', '0-5']
        fieldnames = ['quarter', 'start date', 'end date', 'portfolio type',
        'start value', 'end value', 'log return', 'portfolio range']
        writer = csv.DictWriter(fw, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(1, 41):
            performances, portfolios = roll_window(portfolios, start_date, prices_dict, weighted)
            #pprint.pprint(performances)
            prev_start = start_date
            start_date = add_quarter(start_date)

            for j, p in enumerate(portfolios):
                row = {
                    'portfolio range': ranges[j],
                    'quarter': i,
                    'start date': prev_start,
                    'end date': start_date,
                    'start value': performances[j]['start'],
                    'end value': performances[j]['end'],
                    'log return': performances[j]['log return'],
                }

                if weighted:
                    row['portfolio type'] = 'weighted'
                else:
                    row['portfolio type'] = 'unweighted'
                writer.writerow(row)


if __name__=='__main__':
    filter('raw.csv')
    prices = create_prices_dict('filtered.csv')
    returns = create_returns_dict(prices)
    backtest(prices, '12/2008')
    backtest(prices, '12/2008', True)
    '''
    portfolios = pick_portfolios(prices, '09/2010')
    mean_returns = get_mean_returns(portfolios, returns)
    variances = get_returns_variance(portfolios, returns, mean_returns)
    pprint.pprint(mean_returns)
    pprint.pprint(variances)
    '''