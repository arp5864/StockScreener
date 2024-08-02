import tkinter as tk
from yahoo_fin import news
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
import webbrowser
from finvizfinance.quote import finvizfinance
from finvader import finvader
import webbrowser as wb
import pytz



# Initialize the Sentiment Intensity Analyzer from NLTK
vader = SentimentIntensityAnalyzer()

# Function to open a link in a new browser tab when a cell in a specific column is clicked
def open_link(event):
    tree = event.widget  # get the treeview widget
    region = tree.identify_region(event.x, event.y)  # identify the region clicked
    col = tree.identify_column(event.x)  # identify the column clicked
    iid = tree.identify('item', event.x, event.y)  # identify the item clicked
    if region == 'cell' and col == '#6':  # check if the clicked cell is in column 6
        link = tree.item(iid)['values'][5]  # get the link from the selected row
        wb.open_new_tab(link)  # open the link in a browser tab

# Function to sort a treeview column in ascending or descending order
def sort_column(tree, col, reverse):
    # Retrieve and sort the data in the specified column
    data = [(tree.set(child, col), child) for child in tree.get_children('')]
    data.sort(reverse=reverse)

    # Rearrange the items in sorted order
    for index, (val, child) in enumerate(data):
        tree.move(child, '', index)

    # Update the heading to call this function again when clicked, with the reverse order
    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

# Function to filter stocks based on volume per minute compared to shares float per minute
def filter_stocks_pm(finviz_url):
    export_url = finviz_url[0:25] + 'export' + finviz_url[33:]  # Modify the URL to get the export link

    OS = os_var.get()  # Get the operating system (OS) type from a variable

    # Open the export URL in the browser based on the OS
    if OS == "macOS":
        applescript = f'''
        tell application "Safari"
            open location "{export_url}"
            activate
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript])
        time.sleep(5)  # Wait for 5 seconds to ensure the file is downloaded
    elif OS == "Windows":
        webbrowser.open(export_url)
        time.sleep(5)  # Wait for 5 seconds to ensure the file is downloaded

    # Define paths for downloads and current directory
    downloads_path = str(Path.home() / "Downloads")
    current_directory = os.path.dirname(os.path.abspath(__file__))
    new_file_name = 'data.csv'

    # Get the most recent file from the Downloads folder
    files = [f for f in os.listdir(downloads_path) if os.path.isfile(os.path.join(downloads_path, f))]
    if not files:
        raise FileNotFoundError("No files found in the Downloads folder.")
    most_recent_file = max(files, key=lambda x: os.path.getctime(os.path.join(downloads_path, x)))
    recent_file_path = os.path.join(downloads_path, most_recent_file)

    # Move the most recent file to the current directory with a new name
    destination_file_path = os.path.join(current_directory, new_file_name)
    if os.path.exists(destination_file_path):
        os.remove(destination_file_path)
    shutil.move(recent_file_path, destination_file_path)

    # Read the CSV file into a DataFrame
    data = pd.read_csv(destination_file_path)

    # Calculate the time difference from a fixed time (04:00:00) to the current time
    time1 = datetime.strptime("04:00:00", "%H:%M:%S")
    now = datetime.now()
    current_time = str(now.strftime("%H:%M:%S"))
    current_time = datetime.strptime(current_time, "%H:%M:%S")
    delta = current_time - time1
    time_difference = delta.total_seconds() / 60  # Convert time difference to minutes

    # Convert 'Shares Float' and 'Volume' columns to numeric values
    data['Shares Float'] = pd.to_numeric(data['Shares Float'], errors='coerce')
    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    # Calculate 'Shares Float per Minute' and 'Volume per Minute'
    minutes_in_day = 12 * 60
    data['Shares Float per Minute'] = ((data['Shares Float'] * 1000000) / minutes_in_day) * time_difference


    # Filter data where 'Volume per Minute' is greater than 'Shares Float per Minute'
    filtered_data = data[data['Volume'] > data['Shares Float per Minute']]

    # Return selected columns from the filtered data
    return filtered_data[['Ticker', 'Company', 'Shares Float per Minute', 'Volume', 'Change']]

# Function to convert 12-hour time format to 24-hour time format
def convert24(time_str):
    t = datetime.strptime(time_str, '%I:%M%p')
    return t.strftime('%H:%M:%S')

def filterednews(stocks, date_from, date_to, start_time, end_time):
    print(stocks)
    # Convert the start and end times to 24-hour format
    start_time = convert24(start_time)
    end_time = convert24(end_time)

    ticker_list = stocks['Ticker'].tolist()  # Convert the ticker column to a list
    data = []

    # Iterate through each ticker symbol
    for ticker in ticker_list:
        stock = finvizfinance(ticker)  # Get the stock information
        news_df = stock.ticker_news()  # Get the news for the stock

        # Iterate through the news data
        for index, row in news_df.iterrows():
            date_time_list = str(row['Date']).split(' ')  # Split the date and time

            # Check if the news release date matches the given date
            if (date_time_list[0] >= date_from and date_time_list[0] <= date_to) == False:
                break
            else:
                # Check if the news release time is within the start and end time range
                if date_time_list[1] >= start_time and date_time_list[1] <= end_time:
                    news_url = row['Link']  # Get the news link
                    article_text = ''

                    # Fetch the news article
                    try:
                        response = requests.get(news_url)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Extract text from paragraphs
                        for paragraph in soup.find_all('p'):
                            article_text += paragraph.get_text()
                    except requests.RequestException as e:
                        print(f"Failed to fetch {news_url}: {e}")

                    # Perform sentiment analysis on the article text
                    scores = finvader(article_text,
                                      use_sentibignomics=True,
                                      use_henry=True,
                                      indicator='compound')
                    change = stocks.loc[stocks["Ticker"] == ticker, "Change"].values[0]

                    # Ensure change has a consistent length
                    if len(change) == 5:
                        change = "0" + change

                    # Append the news data to the result list
                    data.append([row['Date'], change, ticker, row['Title'], scores, row['Link']])

    return data


def is_within_range(input_date_time, date_from, date_to, time_from, time_to):

    # Define time zones
    utc = pytz.utc
    est = pytz.timezone('US/Eastern')

    # Parse the input date and time in UTC
    input_dt = datetime.strptime(input_date_time, '%a, %d %b %Y %H:%M:%S %z')

    # Convert input date and time to EST
    input_dt_est = input_dt.astimezone(est)

    # Parse the from and to date and time strings
    datetime_from = datetime.strptime(f"{date_from} {time_from}", '%Y-%m-%d %I:%M%p')
    datetime_to = datetime.strptime(f"{date_to} {time_to}", '%Y-%m-%d %I:%M%p')

    # Localize the from and to datetime to EST
    datetime_from_est = est.localize(datetime_from)
    datetime_to_est = est.localize(datetime_to)

    # Check if input date and time is within the range
    return datetime_from_est <= input_dt_est <= datetime_to_est


# Function to collect URLs of news articles within a specified time range
def url_collector(filtered_data, date_from, date_to, time_from, time_to):
    ticker_list = filtered_data['Symbol'].tolist()  # Convert the symbol column to a list
    print(ticker_list)

    csvdata = []

    for ticker in ticker_list:
        try:
            news_data = news.get_yf_rss(ticker)
            for article in news_data:
                if is_within_range(article["published"], date_from, date_to, time_from, time_to) == True:
                    utc = pytz.utc
                    est = pytz.timezone('US/Eastern')

                    # Parse the input date and time in UTC
                    input_dt = datetime.strptime(article["published"], '%a, %d %b %Y %H:%M:%S %z')

                    # Convert input date and time to EST
                    input_dt_est = str(input_dt.astimezone(est))
                    input_dt_est = input_dt_est[:19]
                    news_url = article["link"]
                    summary_text = str(article["summary"])
                    article_text = ''

                    # Fetch the news article
                    try:
                        response = requests.get(news_url)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Extract text from paragraphs
                        for paragraph in soup.find_all('p'):
                            article_text += paragraph.get_text()
                    except requests.RequestException as e:
                        print(f"Failed to fetch {news_url}: {e}")

                    # Perform sentiment analysis on the article text or summary
                    if article_text == '':
                        scores = finvader(summary_text,
                                          use_sentibignomics=True,
                                          use_henry=True,
                                          indicator='compound')
                    else:
                        scores = finvader(article_text,
                                          use_sentibignomics=True,
                                          use_henry=True,
                                          indicator='compound')

                    change = filtered_data.loc[filtered_data["Symbol"] == ticker, "Price Change % 1 day"].values[0]
                    change = round(change,2)
                    csvdata.append([input_dt_est,change,ticker,article["title"],scores,article["link"]])


        except Exception as e:
            print(f"An error occurred: {e}")


    start_time = convert24(time_from)
    end_time = convert24(time_to)



    # Iterate through each ticker symbol
    for ticker in ticker_list:
        stock = finvizfinance(ticker)  # Get the stock information
        news_df = stock.ticker_news()  # Get the news for the stock

        # Iterate through the news data
        for index, row in news_df.iterrows():
            date_time_list = str(row['Date']).split(' ')  # Split the date and time

            # Check if the news release date matches the given date
            if (date_time_list[0] >= date_from and date_time_list[0] <= date_to) == False:
                break
            else:
                # Check if the news release time is within the start and end time range
                if date_time_list[1] >= start_time and date_time_list[1] <= end_time:
                    news_url = row['Link']  # Get the news link
                    article_text = ''

                    # Fetch the news article
                    try:
                        response = requests.get(news_url)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Extract text from paragraphs
                        for paragraph in soup.find_all('p'):
                            article_text += paragraph.get_text()
                    except requests.RequestException as e:
                        print(f"Failed to fetch {news_url}: {e}")

                    # Perform sentiment analysis on the article text
                    scores = finvader(article_text,
                                      use_sentibignomics=True,
                                      use_henry=True,
                                      indicator='compound')
                    change = filtered_data.loc[filtered_data["Symbol"] == ticker, "Price Change % 1 day"].values[0]
                    change = round(change,2)

                    # Ensure change has a consistent length


                    # Append the news data to the result list
                    csvdata.append([row['Date'], change, ticker, row['Title'], scores, row['Link']])
    # Iterate through each ticker symbol

    return csvdata

# GUI functions

# Function to fetch news from Finviz and display it in the GUI
def fetch_finviz_news():
    url = finviz_entry.get()  # Get the URL from the Finviz entry field
    filtered_stocks = filter_stocks_pm(url)  # Filter stocks based on the URL

    date_from = finviz_date_from_entry.get() # Get the date from the entry field
    date_to = finviz_date_till_entry.get()
    start_time = finviz_time_from_entry.get()  # Get the start time from the entry field
    end_time = finviz_time_to_entry.get()  # Get the end time from the entry field
    finviz_news = filterednews(filtered_stocks, date_from, date_to, start_time, end_time)  # Fetch filtered news

    # Clear the existing rows in the Finviz treeview
    for row in finviz_tree.get_children():
        finviz_tree.delete(row)

    # Insert the fetched news into the Finviz treeview
    for news in finviz_news:
        print(news)
        finviz_tree.insert("", tk.END, values=news)

# Function to select a CSV file and set its path
def select_csv_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])  # Open a file dialog to select a CSV file
    if file_path:
        csv_file_path.set(file_path)  # Set the selected file path

# Function to fetch news from TradingView and display it in the GUI
def fetch_tradingview_news():
    #url = tradingview_entry.get()
    #filtered_stocks = filter_stocks_pm(url)
    #data = pd.read_csv("tradingviewdata.csv")
    data = pd.read_csv(csv_file_path.get())  # Read the selected CSV file

    # Calculate the time difference from a fixed time (04:00:00) to the current time
    time1 = datetime.strptime("04:00:00", "%H:%M:%S")
    now = datetime.now()
    current_time = str(now.strftime("%H:%M:%S"))
    current_time = datetime.strptime(current_time, "%H:%M:%S")
    delta = current_time - time1
    time_difference = delta.total_seconds() / 60  # Convert time difference to minutes

    # Convert 'Float shares outstanding' and 'Volume 1 minute' columns to numeric values
    data['Float shares outstanding'] = pd.to_numeric(data['Float shares outstanding'], errors='coerce')
    data['Volume 1 minute'] = pd.to_numeric(data['Volume 1 minute'], errors='coerce')

    # Calculate per minute values
    minutes_in_day = 12 * 60
    data['Float shares outstanding'] = (data['Float shares outstanding'] / minutes_in_day) * time_difference
    data['Volume 1 minute'] = data['Volume 1 minute']

    # Filter the data where 'Volume 1 day' is greater than 'Float shares outstanding'
    filtered_data = data[data['Volume 1 day'] > data['Float shares outstanding']]

    # Get the date and time range from the entry fields
    from_date = tradingview_date_from_entry.get()
    till_date = tradingview_date_till_entry.get()
    from_time = tradingview_time_from_entry.get()
    till_time = tradingview_time_till_entry.get()

    # Format the date and time for the API query

    # Collect news URLs within the specified time range
    news_data = url_collector(filtered_data, from_date, till_date, from_time, till_time)
    print(news_data)

    # Clear the existing rows in the TradingView treeview
    for row in tradingview_tree.get_children():
        tradingview_tree.delete(row)

    # Insert the fetched news into the TradingView treeview
    for news in news_data:
        print(news)
        tradingview_tree.insert("", tk.END, values=news)

# Create the main application window
root = tk.Tk()
root.geometry('1500x2000+250+200')  # Set the window size and position
root.title("Stock News Dashboard")  # Set the window title

# Create a tab control
tabControl = ttk.Notebook(root)

# Create tabs
tab1 = ttk.Frame(tabControl)
tab2 = ttk.Frame(tabControl)

# Add tabs to the tab control
tabControl.add(tab1, text='Finviz')
tabControl.add(tab2, text='TradingView')

tabControl.pack(expand=1, fill="both")  # Pack the tab control to fill the window

# Finviz tab

# Label for entering the Finviz URL
finviz_label = ttk.Label(tab1, text="Enter Finviz URL:")
finviz_label.place(x=5, y=0)  # Position the label on the tab
# Entry field for the Finviz URL
finviz_entry = ttk.Entry(tab1, width=115)
finviz_entry.place(x=115, y=0)  # Position the entry field on the tab

# Label for selecting the OS
os_var = tk.StringVar(value="macOS")  # Default OS is macOS
os_label = ttk.Label(tab1, text="Select OS:")
os_label.place(x=850, y=30)  # Position the label on the tab
# Radio button for macOS
os_mac_radio = ttk.Radiobutton(tab1, text="macOS", variable=os_var, value="macOS")
os_mac_radio.place(x=950, y=30)  # Position the radio button on the tab
# Radio button for Windows
os_windows_radio = ttk.Radiobutton(tab1, text="Windows", variable=os_var, value="Windows")
os_windows_radio.place(x=1050, y=30)  # Position the radio button on the tab

# Label for entering the start date
finviz_label = ttk.Label(tab1, text="Enter Date From(YYYY-MM-DD):")
finviz_label.place(x=5, y=30)  # Position the label on the tab
# Entry field for the start date
finviz_date_from_entry = ttk.Entry(tab1, width=20)
finviz_date_from_entry.insert(0, "2024-07-30")  # Set default date
finviz_date_from_entry.place(x=210, y=30)  # Position the entry field on the tab

# Label for entering the start time
finviz_label = ttk.Label(tab1, text="Enter Time From(hh:mmAM):")
finviz_label.place(x=430, y=30)  # Position the label on the tab
# Entry field for the start time
finviz_time_from_entry = ttk.Entry(tab1, width=20)
finviz_time_from_entry.place(x=610, y=30)  # Position the entry field on the tab

# Label for entering the end date
finviz_label = ttk.Label(tab1, text="Enter Date Till(YYYY-MM-DD):")
finviz_label.place(x=5, y=60)  # Position the label on the tab
# Entry field for the end date
finviz_date_till_entry = ttk.Entry(tab1, width=20)
finviz_date_till_entry.insert(0, "2024-07-30")  # Set default date
finviz_date_till_entry.place(x=210, y=60)  # Position the entry field on the tab

# Label for entering the end time
finviz_label = ttk.Label(tab1, text="Enter Time To(hh:mmAM):")
finviz_label.place(x=430, y=60)  # Position the label on the tab
# Entry field for the end time
finviz_time_to_entry = ttk.Entry(tab1, width=20)
finviz_time_to_entry.place(x=610, y=60)  # Position the entry field on the tab


# Button to fetch Finviz news
finviz_button = ttk.Button(tab1, text="Get News", command=fetch_finviz_news)
finviz_button.place(x=650, y=100)  # Position the button on the tab

# Treeview for displaying Finviz news
finviz_tree = ttk.Treeview(tab1, columns=("Date/Time", "Change", "Ticker", "Title", "SScore", "Link"), show='headings', height=500)
# Define column headings and sorting commands
finviz_tree.heading("Date/Time", text="Date/Time", command=lambda: sort_column(finviz_tree, "Date/Time", False))
finviz_tree.heading("Ticker", text="Ticker", command=lambda: sort_column(finviz_tree, "Ticker", False))
finviz_tree.heading("Change", text="Change", command=lambda: sort_column(finviz_tree, "Change", False))
finviz_tree.heading("Title", text="Title", command=lambda: sort_column(finviz_tree, "Title", False))
finviz_tree.heading("SScore", text="SScore", command=lambda: sort_column(finviz_tree, "SScore", False))
finviz_tree.heading("Link", text="Link", command=lambda: sort_column(finviz_tree, "Link", False))
finviz_tree.place(x=5, y=150)  # Position the treeview on the tab
# Set column widths
finviz_tree.column("Ticker", width=50)
finviz_tree.column("Date/Time", width=150)
finviz_tree.column("Change", width=55)
finviz_tree.column("Title", width=500)
finviz_tree.column("SScore", width=55)
finviz_tree.column("Link", width=500)
# Bind left mouse button click to open links
finviz_tree.bind('<Button-1>', open_link)

# TradingView tab

# Label for selecting the CSV file
tradingview_label = ttk.Label(tab2, text="Select CSV File:")
tradingview_label.place(x=5, y=0)  # Position the label on the tab
# Entry field to display the selected CSV file path
csv_file_path = tk.StringVar()
csv_file_entry = ttk.Entry(tab2, textvariable=csv_file_path, width=50)
csv_file_entry.place(x=110, y=0)  # Position the entry field on the tab
# Button to browse and select a CSV file
select_csv_button = tk.Button(tab2, text="Browse", command=select_csv_file)
select_csv_button.place(x=600, y=0)  # Position the button on the tab


# Label for entering the start date for TradingView news
tradingview_label = ttk.Label(tab2, text="Enter Date From(YYYY-MM-DD):")
tradingview_label.place(x=5, y=30)  # Position the label on the tab
# Entry field for the start date
tradingview_date_from_entry = ttk.Entry(tab2, width=20)
tradingview_date_from_entry.insert(0, "2024-07-30")  # Set default date
tradingview_date_from_entry.place(x=210, y=30)  # Position the entry field on the tab

# Label for entering the start time for TradingView news
tradingview_label = ttk.Label(tab2, text="Enter Time From(hh:mmAM):")
tradingview_label.place(x=430, y=30)  # Position the label on the tab
# Entry field for the start time
tradingview_time_from_entry = ttk.Entry(tab2, width=20)
tradingview_time_from_entry.place(x=610, y=30)  # Position the entry field on the tab

# Label for entering the end date for TradingView news
tradingview_label = ttk.Label(tab2, text="Enter Date Till(YYYY-MM-DD):")
tradingview_label.place(x=5, y=60)  # Position the label on the tab
# Entry field for the end date
tradingview_date_till_entry = ttk.Entry(tab2, width=20)
tradingview_date_till_entry.insert(0, "2024-07-30")  # Set default date
tradingview_date_till_entry.place(x=210, y=60)  # Position the entry field on the tab

# Label for entering the end time for TradingView news
tradingview_label = ttk.Label(tab2, text="Enter Time To(hh:mmAM):")
tradingview_label.place(x=430, y=60)  # Position the label on the tab
# Entry field for the end time
tradingview_time_till_entry = ttk.Entry(tab2, width=20)
tradingview_time_till_entry.place(x=610, y=60)  # Position the entry field on the tab

# Button to fetch TradingView news
tradingview_button = ttk.Button(tab2, text="Get News", command=fetch_tradingview_news)
tradingview_button.place(x=650, y=100)  # Position the button on the tab

# Treeview for displaying TradingView news
tradingview_tree = ttk.Treeview(tab2, columns=("Date/Time", "Change", "Ticker", "Title", "SScore", "Link"), show='headings', height=500)
# Define column headings and sorting commands
tradingview_tree.heading("Date/Time", text="Date/Time", command=lambda: sort_column(tradingview_tree, "Date/Time", False))
tradingview_tree.heading("Ticker", text="Ticker", command=lambda: sort_column(tradingview_tree, "Ticker", False))
tradingview_tree.heading("Change", text="Change", command=lambda: sort_column(tradingview_tree, "Change", False))
tradingview_tree.heading("Title", text="Title", command=lambda: sort_column(tradingview_tree, "Title", False))
tradingview_tree.heading("Link", text="Link", command=lambda: sort_column(tradingview_tree, "Link", False))
tradingview_tree.heading("SScore", text="SScore", command=lambda: sort_column(tradingview_tree, "SScore", False))
tradingview_tree.place(x=5, y=150)  # Position the treeview on the tab
# Set column widths
tradingview_tree.column("Ticker", width=50)
tradingview_tree.column("Change", width=50)
tradingview_tree.column("Date/Time", width=150)
tradingview_tree.column("Title", width=500)
tradingview_tree.column("SScore", width=55)
tradingview_tree.column("Link", width=500)
# Bind left mouse button click to open links
tradingview_tree.bind('<Button-1>', open_link)

# Run the application
root.mainloop()  # Start the Tkinter event loop
