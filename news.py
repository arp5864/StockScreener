import tkinter as tk
from tkinter import ttk
from urllib.request import urlopen, Request
import requests
from bs4 import BeautifulSoup
from finvizfinance.quote import finvizfinance
import webbrowser  # To open links in the default browser

# Function to fetch and display news and stock data
def get_news():
    # Clear the Treeview
    for item in tree.get_children():
        tree.delete(item)

    # URL and headers for the news data
    finviz_url = 'https://elite.finviz.com/news.ashx?v=3'
    headers = {'user-agent': 'my-app'}

    # Send request to get the news page content
    response = requests.get(finviz_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find news tables and rows
    news_tables = soup.find_all('div', {'class': 'content'})
    data = []

    for news_table in news_tables:
        table = news_table.find('table', {'class': 'styled-table-new is-rounded table-fixed'})
        if table:
            rows = table.findAll('tr', {'class': 'styled-row is-hoverable is-bordered is-rounded is-border-top is-hover-borders has-color-text news_table-row'})
            for row in rows:
                time_cell = row.find('td', {'class': 'news_date-cell color-text is-muted text-right'})
                link_cell = row.find('td', {'class': 'news_link-cell'})
                a_tags = link_cell.find_all('a')[1:]

                # Initialize default values
                news_time = 'No time available'
                ticker = 'No ticker available'
                tickers = []

                # Extract time
                if time_cell:
                    news_time = time_cell.text.strip()

                # Extract ticker symbol
                for a in a_tags:
                    href = a['href']
                    if 'quote.ashx?t=' in href:
                        ticker = href.split('=')[1].upper()  # Extract and capitalize the ticker symbol
                        tickers.append(ticker)

                # Extract news title and link
                if link_cell:
                    link = link_cell.find('a', {'class': 'nn-tab-link'})
                    if link:
                        news_title = link.text.strip()
                        news_link = link['href']

                        # Fetch financial data for each ticker
                        if ticker != 'No ticker available':
                            try:
                                stock = finvizfinance(ticker)
                                stock_fundament = stock.ticker_fundament(ticker)

                                # Extract 'Rel Volume', 'Price', and 'Change'
                                rel_volume = stock_fundament.get('Rel Volume', 'N/A')
                                price = stock_fundament.get('Price', 'N/A')
                                change = stock_fundament.get('Change', 'N/A')
                            except Exception as e:
                                # If fetching data fails, set defaults
                                rel_volume = 'N/A'
                                price = 'N/A'
                                change = 'N/A'

                            # Append combined data
                            data.append([news_time, tickers, news_title, rel_volume, price, change, news_link])

    # Display the data in the Treeview
    for entry in data:
        tree.insert('', tk.END, values=(entry[0], entry[1], entry[2], entry[3], entry[4], entry[5], entry[6]))

    # Automatically re-run get_news() every 20 seconds (20,000 milliseconds)
    window.after(60000, get_news)  # Schedule the function to run again in 20 seconds

# Function to open the selected link in the default web browser
def open_link(event):
    region = tree.identify("region", event.x, event.y)  # Identify the region clicked
    if region == "cell":  # Only proceed if a cell (not header or margin) is clicked
        column = tree.identify_column(event.x)  # Get which column was clicked
        if column == '#7':  # If it's the 7th column ("Link")
            selected_item = tree.focus()  # Get the selected item (row)
            if selected_item:
                item_values = tree.item(selected_item, 'values')  # Get the values of the selected item
                link = item_values[6]  # The link is stored in the 7th column (index 6)
                if link:
                    webbrowser.open_new_tab(link)  # Open the link in the default web browser

# Set up the main GUI window
window = tk.Tk()
window.title("Stock News Fetcher")
window.geometry("1000x600")

# Create the "Get News" button
get_news_button = tk.Button(window, text="Get News", command=get_news, font=("Arial", 14))
get_news_button.pack(pady=10)

# Set up columns for the table (Treeview)
columns = ("Time", "Ticker", "Title", "Rel Volume", "Price", "Change", "Link")

# Create the Treeview widget
tree = ttk.Treeview(window, columns=columns, show='headings', height=20)
tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

# Define headings for each column
tree.heading("Time", text="Time")
tree.heading("Ticker", text="Ticker")
tree.heading("Title", text="Title")
tree.heading("Rel Volume", text="Rel Volume")
tree.heading("Price", text="Price")
tree.heading("Change", text="Change")
tree.heading("Link", text="Link")

# Set column widths (adjust as necessary)
tree.column("Time", width=100, anchor=tk.CENTER)
tree.column("Ticker", width=80, anchor=tk.CENTER)
tree.column("Title", width=300, anchor=tk.W)
tree.column("Rel Volume", width=100, anchor=tk.CENTER)
tree.column("Price", width=80, anchor=tk.CENTER)
tree.column("Change", width=80, anchor=tk.CENTER)
tree.column("Link", width=300, anchor=tk.W)

# Bind the Treeview select event to open links only in the "Link" column
tree.bind("<Button-1>", open_link)  # Single-click to trigger the link opening in the "Link" column

# Start the Tkinter main loop
window.mainloop()