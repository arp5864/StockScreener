# Stock News Dashboard

This project provides a dashboard to fetch and display stock news from Finviz and TradingView using a graphical user interface (GUI) built with Tkinter. It includes features for filtering stocks, sentiment analysis, and displaying news articles in a user-friendly manner.

## Features

- Fetch and filter stock data from Finviz.
- Fetch news articles based on selected stocks and display them.
- Fetch and filter stock data from TradingView using a CSV file.
- Perform sentiment analysis on fetched news articles.
- Display news articles with clickable links in a GUI.

## Requirements

- Python 3.x
- Required libraries: 
  - `tkinter`
  - `pandas`
  - `bs4`
  - `requests`
  - `nltk`
  - `finvizfinance`
  - `finvader`
  - `alphavantage` (API key required) - https://www.alphavantage.co/support/#api-key 

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/arp5864/stock-news-dashboard.git
    ```
2. Navigate to the project directory:
    ```sh
    cd stock-news-dashboard
    ```
3. Install the required libraries:
    ```sh
    pip install -r requirements.txt
    ```
4. Download NLTK VADER lexicon:
    ```python
    import nltk
    nltk.download('vader_lexicon')
    ```

## Usage

1. Run the main script:
    ```sh
    python main.py
    ```
2. The application window will appear with two tabs: `Finviz` and `TradingView`.

### Finviz Tab

1. Enter the Finviz URL in the provided entry field.
2. Select your operating system (macOS or Windows).
3. Enter the date and time range for fetching news.
4. Click the `Get News` button to fetch and display news articles.

### TradingView Tab

1. Click the `Browse` button to select a CSV file with TradingView data.
2. Enter the date and time range for fetching news.
3. Click the `Get News` button to fetch and display news articles.

## Code Structure

- `main.py`: The main script that initializes the Tkinter GUI and contains all functions for fetching and displaying news.
- `requirements.txt`: List of required Python libraries.

### Key Functions

- `open_link(event)`: Opens a link in a new browser tab when a cell in a specific column is clicked.
- `sort_column(tree, col, reverse)`: Sorts a treeview column in ascending or descending order.
- `filter_stocks_pm(finviz_url)`: Filters stocks based on volume per minute compared to shares float per minute.
- `convert24(time_str)`: Converts 12-hour time format to 24-hour time format.
- `filterednews(stocks, released, start_time, end_time)`: Fetches and filters news for given stocks and performs sentiment analysis.
- `get_formatted_datetime(input_date, input_time)`: Formats date and time for API queries.
- `reverse_date_time(input)`: Reverses the formatted date and time to a readable format.
- `url_collector(filtered_data, date_time_from, date_time_to)`: Collects URLs of news articles within a specified time range.

### GUI Functions

- `fetch_finviz_news()`: Fetches news from Finviz and displays it in the GUI.
- `select_csv_file()`: Opens a file dialog to select a CSV file and sets its path.
- `fetch_tradingview_news()`: Fetches news from TradingView and displays it in the GUI.

## Troubleshooting

- Ensure that all required Python packages are installed.
- Ensure that the selected CSV file for TradingView contains the necessary columns.
- If no news articles are fetched, check the date and time range.
- It is highly likely that no stock tickers go through our first filter which is based on volume per minute compared to shares float per minute.
