import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import ttk, filedialog
import pandas as pd
import time
from bs4 import BeautifulSoup
import requests
import os
import shutil
from pathlib import Path
import subprocess
from datetime import datetime
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import finnhub
from finvizfinance.quote import finvizfinance
from finvader import finvader
import webbrowser as wb


# Initialize Finnhub client and VADER sentiment analyzer
from pandas.core.interchange import column

finnhub_client = finnhub.Client(api_key="cpk7f99r01qs6dmbu0a0cpk7f99r01qs6dmbu0ag")
vader = SentimentIntensityAnalyzer()

def open_link(event):
    tree = event.widget  # get the treeview widget
    region = tree.identify_region(event.x, event.y)
    col = tree.identify_column(event.x)
    iid = tree.identify('item', event.x, event.y)
    if region == 'cell' and col == '#6':
        link = tree.item(iid)['values'][5]  # get the link from the selected row
        wb.open_new_tab(link)  # open the link in a browser tab

def sort_column(tree, col, reverse):
    data = [(tree.set(child, col), child) for child in tree.get_children('')]
    data.sort(reverse=reverse)

    for index, (val, child) in enumerate(data):
        tree.move(child, '', index)

    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))


# Your existing functions
def filter_stocks_pm(finviz_url):
    export_url = finviz_url[0:25] + 'export' + finviz_url[33:]

    OS = os_var.get()  # You can change this to 2 for Windows if needed

    if OS == "macOS":
        applescript = f'''
        tell application "Safari"
            open location "{export_url}"
            activate
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript])
        time.sleep(5)
    elif OS == "Windows":
        subprocess.Popen(['chrome', export_url])
        time.sleep(5)

    downloads_path = str(Path.home() / "Downloads")
    current_directory = os.path.dirname(os.path.abspath(__file__))
    new_file_name = 'data.csv'

    files = [f for f in os.listdir(downloads_path) if os.path.isfile(os.path.join(downloads_path, f))]
    if not files:
        raise FileNotFoundError("No files found in the Downloads folder.")
    most_recent_file = max(files, key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))
    recent_file_path = os.path.join(downloads_path, most_recent_file)

    destination_file_path = os.path.join(current_directory, new_file_name)

    if os.path.exists(destination_file_path):
        os.remove(destination_file_path)
    shutil.move(recent_file_path, destination_file_path)

    data = pd.read_csv(destination_file_path)

    time1 = datetime.strptime("04:00:00", "%H:%M:%S")
    now = datetime.now()
    current_time = str(now.strftime("%H:%M:%S"))
    current_time = datetime.strptime(current_time, "%H:%M:%S")

    delta = current_time - time1
    time_difference = delta.total_seconds()/60

    data['Shares Float'] = pd.to_numeric(data['Shares Float'], errors='coerce')
    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    minutes_in_day = 24 * 60
    data['Shares Float per Minute'] = ((data['Shares Float'] * 1000000) / minutes_in_day) * time_difference
    data['Volume per Minute'] = data['Volume'] / minutes_in_day

    filtered_data = data[data['Volume per Minute'] > data['Shares Float per Minute']]

    return filtered_data[['Ticker', 'Company', 'Shares Float per Minute', 'Volume per Minute', 'Change']]


def convert24(time_str):
    t = datetime.strptime(time_str, '%I:%M%p')
    return t.strftime('%H:%M:%S')



def filterednews(stocks, released, start_time, end_time):
    ticker_list = stocks['Ticker'].tolist()
    data = []

    start_time = convert24(start_time)

    end_time = convert24(end_time)
    for ticker in ticker_list:
        stock = finvizfinance(ticker)
        news_df = stock.ticker_news()

        for index, row in news_df.iterrows():
            date_time_list = str(row['Date']).split(' ')

            if date_time_list[0] != released:
                break
            else:
                if date_time_list[1] >= start_time and date_time_list[1] <= end_time:
                    news_url = row['Link']
                    article_text = ''
                    try:
                        response = requests.get(news_url)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')


                        for paragraph in soup.find_all('p'):
                            article_text += paragraph.get_text()
                    except requests.RequestException as e:

                        print(f"Failed to fetch {news_url}: {e}")
                    scores = finvader(article_text,
                                      use_sentibignomics = True,
                                      use_henry = True,
                                      indicator = 'compound')
                    change = stocks.loc[stocks["Ticker"] == ticker, "Change"].values[0]
                    if len(change) == 5:
                        change = "0" + change
                    data.append([row['Date'],ticker, change, row['Title'], scores, row['Link']])
    return data

def url_collector(ticker_list, date_from, date_to):
    print(ticker_list)
    csvdata = []
    for ticker in ticker_list:
        datas = finnhub_client.company_news(ticker, _from=date_from, to=date_to)
        for news in datas:
            news_url = news['url']
            ts = int(news['datetime'])
            news_time = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')[11:19]
            if news_time >= convert24(tradingview_time_from_entry.get()) and news_time <= convert24(tradingview_time_to_entry.get()):
                summary_text = str(news['summary'])
                article_text = ''
                try:
                    response = requests.get(news_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')


                    for paragraph in soup.find_all('p'):
                        article_text += paragraph.get_text()
                except requests.RequestException as e:

                    print(f"Failed to fetch {news_url}: {e}")
                if article_text == '':
                    scores = finvader(summary_text,
                                      use_sentibignomics = True,
                                      use_henry = True,
                                      indicator = 'compound')
                else:
                    scores = finvader(article_text,
                                      use_sentibignomics = True,
                                      use_henry = True,
                                      indicator = 'compound')
                csvdata.append([datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'), ticker, summary_text, scores, news_url])
            else:
                continue

    return csvdata

# GUI functions
def fetch_finviz_news():
    url = finviz_entry.get()
    filtered_stocks = filter_stocks_pm(url)


    date = finviz_date_from_entry.get()
    start_time = finviz_time_from_entry.get()  # You can make this dynamic
    end_time = finviz_time_to_entry.get()  # You can make this dynamic
    finviz_news = filterednews(filtered_stocks, date, start_time, end_time)

    for row in finviz_tree.get_children():
        finviz_tree.delete(row)

    for news in finviz_news:
        print(news)
        finviz_tree.insert("", tk.END, values=news)

def select_csv_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        csv_file_path.set(file_path)


def fetch_tradingview_news():
    #url = tradingview_entry.get()
    #filtered_stocks = filter_stocks_pm(url)
    #data = pd.read_csv("tradingviewdata.csv")
    data = pd.read_csv(csv_file_path.get())
    time1 = datetime.strptime("04:00:00", "%H:%M:%S")
    now = datetime.now()
    current_time = str(now.strftime("%H:%M:%S"))
    current_time = datetime.strptime(current_time, "%H:%M:%S")

    delta = current_time - time1
    time_difference = delta.total_seconds()/60

    data['Float shares outstanding'] = pd.to_numeric(data['Float shares outstanding'], errors='coerce')
    data['Volume 1 minute'] = pd.to_numeric(data['Volume 1 minute'], errors='coerce')

    # Calculate per minute values
    minutes_in_day = 24 * 60
    data['Float shares outstanding'] = (data['Float shares outstanding'] / minutes_in_day) * time_difference
    data['Volume 1 minute'] = data['Volume 1 minute']

    # Filter the data where 'Relative Volume' is greater than 'Shares Float'

    filtered_data = data[data['Volume 1 day'] > data['Float shares outstanding']]

    tickers_list = filtered_data['Symbol'].tolist()
    from_date = tradingview_date_from_entry.get()  # You can make this dynamic
    to_date = tradingview_date_till_entry.get()  # You can make this dynamic
    news_data = url_collector(tickers_list, from_date, to_date)
    print(news_data)
    for row in tradingview_tree.get_children():
        tradingview_tree.delete(row)

    for news in news_data:
        print(news)
        tradingview_tree.insert("", tk.END, values=news)

# Create the main application window
root = tk.Tk()
root.geometry('1500x2000+250+200')
root.title("Stock News Dashboard")

# Create a tab control
tabControl = ttk.Notebook(root)

# Create tabs
tab1 = ttk.Frame(tabControl)
tab2 = ttk.Frame(tabControl)

tabControl.add(tab1, text='Finviz')
tabControl.add(tab2, text='TradingView')

tabControl.pack(expand=1, fill="both")

# Finviz tab
finviz_label = ttk.Label(tab1, text="Enter Finviz URL:")
finviz_label.place(x=5, y=0)
finviz_entry = ttk.Entry(tab1, width=115)
finviz_entry.place(x=115, y=0)

os_var = tk.StringVar(value="macOS")
os_label = ttk.Label(tab1, text="Select OS:")
os_label.place(x=850, y=30)
os_mac_radio = ttk.Radiobutton(tab1, text="macOS", variable=os_var, value="macOS")
os_mac_radio.place(x=950, y=30)
os_windows_radio = ttk.Radiobutton(tab1, text="Windows", variable=os_var, value="Windows")
os_windows_radio.place(x=1050, y=30)

finviz_label = ttk.Label(tab1, text="Enter Date From(YYYY-MM-DD):")
finviz_label.place(x=5, y=30)
finviz_date_from_entry = ttk.Entry(tab1, width=20)
finviz_date_from_entry.insert(0, "2024-07-19")
finviz_date_from_entry.place(x=210, y=30)


finviz_label = ttk.Label(tab1, text="Enter Time From(hh:mmAM):")
finviz_label.place(x=430, y=30)
finviz_time_from_entry = ttk.Entry(tab1, width=20)
finviz_time_from_entry.place(x=610, y=30)


finviz_label = ttk.Label(tab1, text="Enter Date Till(YYYY-MM-DD):")
finviz_label.place(x=5, y=60)
finviz_date_till_entry = ttk.Entry(tab1, width=20)
finviz_date_till_entry.insert(0, "2024-07-19")
finviz_date_till_entry.place(x=210, y=60)


finviz_label = ttk.Label(tab1, text="Enter Time To(hh:mmAM):")
finviz_label.place(x=430, y=60)
finviz_time_to_entry = ttk.Entry(tab1, width=20)
finviz_time_to_entry.place(x=610, y=60)


finviz_button = ttk.Button(tab1, text="Get News", command=fetch_finviz_news)
finviz_button.place(x=650, y=100)


finviz_tree = ttk.Treeview(tab1, columns=("Date/Time","Ticker","Change", "Title", "SScore", "Link"), show='headings', height = 500)
finviz_tree.heading("Date/Time", text="Date/Time", command=lambda: sort_column(finviz_tree, "Date/Time", False))
finviz_tree.heading("Ticker", text="Ticker", command=lambda: sort_column(finviz_tree, "Ticker", False))
finviz_tree.heading("Change", text="Change", command=lambda: sort_column(finviz_tree, "Change", False))
finviz_tree.heading("Title", text="Title", command=lambda: sort_column(finviz_tree, "Title", False))
finviz_tree.heading("SScore", text="SScore", command=lambda: sort_column(finviz_tree, "SScore", False))
finviz_tree.heading("Link", text="Link", command=lambda: sort_column(finviz_tree, "Link", False))
finviz_tree.place(x=5, y=150)
finviz_tree.column("Ticker", width = 50)
finviz_tree.column("Date/Time", width = 150)
finviz_tree.column("Change", width = 55)
finviz_tree.column("Title", width = 500)
finviz_tree.column("SScore", width = 55)
finviz_tree.column("Link", width = 500)
finviz_tree.bind('<Button-1>', open_link)

# TradingView tab
"""tradingview_label = ttk.Label(tab2, text="Enter TradingView URL:")
tradingview_label.place(x=5, y=0)
tradingview_entry = ttk.Entry(tab2, width=110)
tradingview_entry.place(x=155, y=0)"""

tradingview_label = ttk.Label(tab2, text="Select CSV File:")
tradingview_label.place(x=5, y=0)
csv_file_path = tk.StringVar()
csv_file_entry = ttk.Entry(tab2, textvariable=csv_file_path, width=50)
csv_file_entry.place(x=110, y=0)
select_csv_button = tk.Button(tab2, text="Browse", command=select_csv_file)
select_csv_button.place(x=600, y=0)



tradingview_label = ttk.Label(tab2, text="Enter Date From(YYYY-MM-DD):")
tradingview_label.place(x=5, y=30)
tradingview_date_from_entry = ttk.Entry(tab2, width=20)
tradingview_date_from_entry.insert(0, "2024-07-19")
tradingview_date_from_entry.place(x=210, y=30)

tradingview_label = ttk.Label(tab2, text="Enter Time From(hh:mmAM):")
tradingview_label.place(x=430, y=30)
tradingview_time_from_entry = ttk.Entry(tab2, width=20)
tradingview_time_from_entry.place(x=610, y=30)

tradingview_label = ttk.Label(tab2, text="Enter Date Till(YYYY-MM-DD):")
tradingview_label.place(x=5, y=60)
tradingview_date_till_entry = ttk.Entry(tab2, width=20)
tradingview_date_till_entry.insert(0, "2024-07-19")
tradingview_date_till_entry.place(x=210, y=60)


tradingview_label = ttk.Label(tab2, text="Enter Time To(hh:mmAM):")
tradingview_label.place(x=430, y=60)
tradingview_time_to_entry = ttk.Entry(tab2, width=20)
tradingview_time_to_entry.place(x=610, y=60)


tradingview_button = ttk.Button(tab2, text="Get News", command=fetch_tradingview_news)
tradingview_button.place(x=650, y=100)

tradingview_tree = ttk.Treeview(tab2, columns=("Date/Time","Ticker", "Title", "SScore", "Link"), show='headings', height = 500)
tradingview_tree.heading("Date/Time", text="Date/Time", command=lambda: sort_column(tradingview_tree, "Date/Time", False))
tradingview_tree.heading("Ticker", text="Ticker", command=lambda: sort_column(tradingview_tree, "Ticker", False))
tradingview_tree.heading("Title", text="Title", command=lambda: sort_column(tradingview_tree, "Title", False))
tradingview_tree.heading("Link", text="Link", command=lambda: sort_column(tradingview_tree, "Link", False))
tradingview_tree.heading("SScore", text="SScore", command=lambda: sort_column(tradingview_tree, "SScore", False))
tradingview_tree.place(x=5, y=150)
tradingview_tree.column("Ticker", width = 50)
tradingview_tree.column("Date/Time", width = 150)
tradingview_tree.column("Title", width = 500)
tradingview_tree.column("SScore", width = 55)
tradingview_tree.column("Link", width = 500)
tradingview_tree.bind('<Button-1>', open_link)


# Run the application
root.mainloop()
