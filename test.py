import pandas as pd
import time
from selenium import webdriver
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import os
import shutil
from pathlib import Path
import subprocess
import pyautogui as pg
import finnhub


def tradingview():
    pg.keyDown('ctrl')
    pg.hotkey('left')
    pg.keyUp('ctr')
    pg.click(x=40, y=173, clicks=1, interval=0, button='left')
    pg.click(x=33, y=343, clicks=2, interval=1, button='left')
    downloads_path = str(Path.home() / "Downloads")

    # Get the path to the current directory where the script is located
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Define the new name for the file
    new_file_name = 'tradingviewdata.csv'  # Change this to the desired new file name

    # Find the most recently downloaded file in the Downloads folder
    recent_file = max([f for f in os.listdir(downloads_path) if os.path.isfile(os.path.join(downloads_path, f))], key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))

    # Construct full paths
    recent_file_path = os.path.join(downloads_path, recent_file)
    destination_file_path = os.path.join(current_directory, new_file_name)

    # Move and rename the file, replacing any existing file with the same name
    shutil.move(recent_file_path, destination_file_path)

    data = pd.read_csv(new_file_name)

    # Convert the necessary columns to numeric, handling errors for non-numeric entries
    data['Float shares %'] = pd.to_numeric(data['Float shares %'], errors='coerce')
    data['Volume 1 day'] = pd.to_numeric(data['Volume 1 day'], errors='coerce')

    # Calculate per minute values
    minutes_in_day = 24 * 60
    data['Float shares %'] = data['Shares Float'] / minutes_in_day
    data['Volume 1 day'] = data['Volume 1 day'] / minutes_in_day

    # Filter the data where 'Relative Volume' is greater than 'Shares Float'

    filtered_data = data[data['Volume 1 day'] > data['Float shares %']]

    # Return the filtered data with only relevant columns
    return filtered_data[['Ticker', 'Company', 'Float shares %', 'Volume 1 day']]



def filter_stocks_pm(finviz_url):
    export_url = finviz_url[0:25] + 'export' + finviz_url[33:]

    OS = input("Which OS are you using? Answer 1 for MacOS, 2 for Windows\n")

    if OS == "1":
        applescript = f'''
        tell application "Safari"
            open location "{export_url}"
            activate
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript])
        time.sleep(5)
    elif OS == "2":
        subprocess.Popen(['chrome', export_url])
        time.sleep(5)

    downloads_path = str(Path.home() / "Downloads")
    current_directory = os.path.dirname(os.path.abspath(__file__))
    new_file_name = 'data.csv'  # Change this to the desired new file name

    # Find the most recently downloaded file in the Downloads folder
    files = [f for f in os.listdir(downloads_path) if os.path.isfile(os.path.join(downloads_path, f))]
    if not files:
        raise FileNotFoundError("No files found in the Downloads folder.")
    most_recent_file = max(files, key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))
    recent_file_path = os.path.join(downloads_path, most_recent_file)

    # Create the full path for the destination file
    destination_file_path = os.path.join(current_directory, new_file_name)

    # Move and rename the file, replacing any existing file with the same name
    if os.path.exists(destination_file_path):
        os.remove(destination_file_path)
    shutil.move(recent_file_path, destination_file_path)

    # Read the downloaded CSV file
    data = pd.read_csv(destination_file_path)

    # Convert the necessary columns to numeric, handling errors for non-numeric entries
    data['Shares Float'] = pd.to_numeric(data['Shares Float'], errors='coerce')
    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    # Calculate per minute values
    minutes_in_day = 24 * 60
    data['Shares Float per Minute'] = data['Shares Float'] / minutes_in_day
    data['Volume per Minute'] = data['Volume'] / minutes_in_day

    # Filter the data where 'Volume per Minute' is greater than 'Shares Float per Minute'
    filtered_data = data[data['Volume per Minute'] > data['Shares Float per Minute']]

    # Return the filtered data with only relevant columns
    return filtered_data[['Ticker', 'Company', 'Shares Float per Minute', 'Volume per Minute']]

def gathernews(ticker_list):
    news_tables = {}
    finviz_url_2 = "https://elite.finviz.com/quote.ashx?t="
    for ticker in ticker_list:

        url = finviz_url_2 + ticker

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

def finhub_news(ticker_list, from_date, to_date):
    finnhub_client = finnhub.Client(api_key="cpk7f99r01qs6dmbu0a0cpk7f99r01qs6dmbu0ag")
    news= []
    for ticker in ticker_list:
        news.append(finnhub_client.company_news(str(ticker), _from=str(from_date), to=str(to_date)))


if __name__ == "__main__":


    # Usage:
    """url = 'https://elite.finviz.com/screener.ashx?v=152&p=i1&f=cap_0.01to,geo_usa|china|france|europe|australia|belgium|canada|chinahongkong|germany|hongkong|iceland|japan|newzealand|ireland|netherlands|norway|singapore|southkorea|sweden|taiwan|unitedarabemirates|unitedkingdom|switzerland|spain,sh_curvol_o100,sh_price_u50,sh_relvol_o2,ta_change_u&ft=4&o=sharesfloat&ar=10&c=0,1,2,5,6,25,26,27,28,29,30,84,45,50,51,68,60,61,63,64,67,65,66'
    filtered_stocks = filter_stocks_pm(url)

    # Print the filtered DataFrame in a readable format
    print(filtered_stocks.to_string(index=False))

    tickers_list = filtered_stocks['Ticker'].tolist()
    print("Filtered Tickers:", tickers_list)

    news_tables = gathernews(tickers_list)

    date = str(input("Please provide date for the news in format of 'mmm-dd-yy' ex. 'Jun-29-23'\n"))
    start_time = str(input("Please provide start time for the news in format of 'hh:mmAM' ex. '04:30AM'\n"))
    end_time = str(input("Please provide end time for the news in format of 'hh:mmAM' ex. '08:30AM'\n"))
    finviz_news, filtered_ticker_list = filterednews(news_tables, date, start_time, end_time)


    print('Latest news of finviz:\n')
    for x in finviz_news:
        print(x)
"""

    from_date = str(input("Please provide from_date for the news in format of 'yyyy-mm-dd' ex. '2022-01-15'\n"))
    to_date = str(input("Please provide to_date for the news in format of 'yyyy-mm-dd' ex. '2022-01-15'\n"))
    trading_view_filtered_tickers = tradingview()
    trading_view_filtered_tickers = trading_view_filtered_tickers['Ticker'].tolist()
    print(trading_view_filtered_tickers)
    finnhub = finhub_news(trading_view_filtered_tickers, from_date, to_date)

    print("News from finnhub: \n")
    if finnhub is not None:
        for x in finnhub:
            print(x)