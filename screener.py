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
import webbrowser
from finvizfinance.quote import finvizfinance
from finvader import finvader
import webbrowser as wb

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

def filterednews(stocks, released, start_time, end_time):
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
            if date_time_list[0] != released:
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
                    data.append([row['Date'], ticker, change, row['Title'], scores, row['Link']])

    return data

# Function to format date and time for API queries
def get_formatted_datetime(input_date, input_time):
    temp = input_date.split('-')
    final_date = "".join(temp)  # Format date as YYYYMMDD
    temptime = convert24(input_time).split(':')
    final_time = "".join(temptime)[0:4]  # Format time as HHMM
    return final_date + "T" + final_time

# Function to reverse the formatted date and time to a readable format
def reverse_date_time(input):
    date = input.split("T")[0]
    time = input.split("T")[1]
    date = date[0:4] + '-' + date[4:6] + '-' + date[6:]  # Format date as YYYY-MM-DD
    time = time[0:2] + ':' + time[2:4]  # Format time as HH:MM
    return date + " " + time

# Function to collect URLs of news articles within a specified time range
def url_collector(filtered_data, date_time_from, date_time_to):
    ticker_list = filtered_data['Symbol'].tolist()  # Convert the symbol column to a list
    print(ticker_list)

    csvdata = []

    # Iterate through each ticker symbol
    for ticker in ticker_list:
        # Create the API URL for fetching news sentiment
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&time_from={date_time_from}&time_to={date_time_to}&apikey= B7HYV65ADQ4YCR7Q"
        r = requests.get(url)
        data = r.json()
        print(data)
        if len(data) == 1:
            continue
        datas = data['feed']

        # Iterate through the news data
        for news in datas:
            news_url = news['url']  # Get the news URL
            ts = news['time_published']
            news_time = reverse_date_time(ts)  # Convert the published time to a readable format

            summary_text = str(news['summary'])
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
            csvdata.append([news_time, change, ticker, summary_text, scores, news_url])
        else:
            continue

    return csvdata

# GUI functions

# Function to fetch news from Finviz and display it in the GUI
def fetch_finviz_news():
    url = finviz_entry.get()  # Get the URL from the Finviz entry field
    filtered_stocks = filter_stocks_pm(url)  # Filter stocks based on the URL

    date = finviz_date_from_entry.get()  # Get the date from the entry field
    start_time = finviz_time_from_entry.get()  # Get the start time from the entry field
    end_time = finviz_time_to_entry.get()  # Get the end time from the entry field
    finviz_news = filterednews(filtered_stocks, date, start_time, end_time)  # Fetch filtered news

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
    date_time_from = get_formatted_datetime(from_date, from_time)
    date_time_till = get_formatted_datetime(till_date, till_time)

    # Collect news URLs within the specified time range
    news_data = url_collector(filtered_data, date_time_from, date_time_till)
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
finviz_tree = ttk.Treeview(tab1, columns=("Date/Time", "Ticker", "Change", "Title", "SScore", "Link"), show='headings', height=500)
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
