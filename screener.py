import pandas as pd
import time
from selenium import webdriver
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from datetime import datetime

def filter_stocks_pm(file_path):
    # Load the data from the specified file
    data = pd.read_csv(file_path)

    # Convert the necessary columns to numeric, handling errors for non-numeric entries
    data['Shares Float'] = pd.to_numeric(data['Shares Float'], errors='coerce')
    data['Relative Volume'] = pd.to_numeric(data['Relative Volume'], errors='coerce')

    # Calculate per minute values
    minutes_in_day = 24 * 60
    data['Shares Float per Minute'] = data['Shares Float'] / minutes_in_day
    data['Relative Volume per Minute'] = data['Relative Volume'] / minutes_in_day

    # Filter the data where 'Relative Volume' is greater than 'Shares Float'
    filtered_data = data[data['Relative Volume per Minute'] > data['Shares Float per Minute']]

    # Return the filtered data with only relevant columns
    return filtered_data[['Ticker', 'Company', 'Shares Float per Minute', 'Relative Volume per Minute']]

def gathernews(ticker_list):
    news_tables = {}
    finviz_url = 'https://elite.finviz.com/quote.ashx?t='
    for ticker in ticker_list:

        url = finviz_url + ticker

        req = Request(url=url, headers={'user-agent': 'my-app'})
        response = urlopen(req)

        html = BeautifulSoup(response, features='html.parser')
        news_table = html.find(id='news-table')
        news_tables[ticker] = news_table
    return news_tables

def filterednews(table, released, start_time, end_time):
    start_time = convert24(start_time)
    end_time = convert24(end_time)
    parsed_data = []
    ticker_list = []


    for ticker, news_table in table.items():
        finviz_url = 'https://elite.finviz.com/quote.ashx?t=' + ticker

        if news_table != None:
            for row in news_table.findAll('tr'):

                date_data = row.td.text.split(' ')

                if len(date_data) == 22:
                    date = date_data[12]
                    time = date_data[13]
                elif len(date_data) == 1:
                    time = date_data[0]
                elif len(date_data) == 21:

                    time = date_data[12]
                else:
                    continue
                time = time.strip()

                temp_time = convert24(time)


                if (row.a != None) and (released == date) and (temp_time >= start_time) and (temp_time <= end_time):

                    title = row.a.text
                    ticker_list.append(ticker)
                    parsed_data.append([ticker, date, time, title, finviz_url])

    return parsed_data, ticker_list

def convert24(time):
    # Parse the time string into a datetime object
    t = datetime.strptime(time, '%I:%M%p')
    # Format the datetime object into a 24-hour time string
    return t.strftime('%H:%M')


if __name__ == "__main__":

    # Usage:
    filtered_stocks = filter_stocks_pm('finviz1.csv.')

    # Print the filtered DataFrame in a readable format
    print(filtered_stocks.to_string(index=False))

    tickers_list = filtered_stocks['Ticker'].tolist()
    print("Filtered Tickers:", tickers_list)

    news_tables = gathernews(tickers_list)

    date = str(input("Please provide date for the news in format of 'mmm-dd-yy' ex. 'Jun-29-23'\n"))
    start_time = str(input("Please provide start time for the news in format of 'hh:mmAM' ex. '04:30AM'\n"))
    end_time = str(input("Please provide end time for the news in format of 'hh:mmAM' ex. '08:30AM'\n"))
    finviz_news, filtered_ticker_list = filterednews(news_tables, date, start_time, end_time)

    print('Latest news of finviz:')
    for x in finviz_news:
        print(x)
