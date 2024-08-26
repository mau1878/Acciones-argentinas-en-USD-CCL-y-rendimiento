import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

# Function to load data
@st.cache
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, progress=False)
    df.reset_index(inplace=True)
    return df

# Streamlit app
st.title("Stock Price Analysis with Max/Min and SMA")
st.sidebar.header("User Input")

# User input fields
ticker = st.sidebar.text_input("Ticker", value="AAPL")
start_date = st.sidebar.date_input("Start date", value=datetime(2020, 1, 1))
end_date = st.sidebar.date_input("End date", value=datetime.today())

# SMA slider outside the button block to keep it visible
sma_period = st.sidebar.slider("SMA Period", min_value=1, max_value=100, value=20)

# Button to apply changes
if st.sidebar.button("Enter"):
    # Load data
    df = load_data(ticker, start_date, end_date)

    # Display data and plot
    st.subheader(f"Price data for {ticker} from {start_date} to {end_date}")
    st.write(df.head())

    # Price chart with adjustable SMA
    st.subheader("Price Chart with Max/Min and SMA")
    
    # Plotting with Plotly
    fig = go.Figure()

    # Add price line
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name="Price"))

    # Add max and min lines
    fig.add_trace(go.Scatter(x=df['Date'], y=df['High'], mode='lines', name="Max Value", line=dict(color='green')))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Low'], mode='lines', name="Min Value", line=dict(color='red')))

    # Add SMA
    df['SMA'] = df['Close'].rolling(window=sma_period).mean()
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['SMA'], 
        mode='lines', 
        name=f"SMA {sma_period}",
        line=dict(color='yellow')  # Set the line color to yellow
    ))

    fig.update_layout(title=f"{ticker} Price Chart",
                      xaxis_title="Date",
                      yaxis_title="Price (USD)",
                      xaxis_rangeslider_visible=False)

    st.plotly_chart(fig)

    # Ratio of Max/Min with SMA and Average
    st.subheader("Ratio of Max/Min with SMA and Average")
    df['Ratio'] = df['High'] / df['Low']
    df['SMA_Ratio'] = df['Ratio'].rolling(window=sma_period).mean()
    average_ratio = df['Ratio'].mean()

    fig_ratio = go.Figure()

    # Add Ratio line
    fig_ratio.add_trace(go.Scatter(x=df['Date'], y=df['Ratio'], mode='lines', name="Max/Min Ratio"))

    # Add SMA of Ratio
    fig_ratio.add_trace(go.Scatter(x=df['Date'], y=df['SMA_Ratio'], mode='lines', name=f"SMA {sma_period} of Ratio"))

    # Add average line
    fig_ratio.add_trace(go.Scatter(x=df['Date'], y=[average_ratio]*len(df), mode='lines', name="Average Ratio", line=dict(color='green', dash='dash')))

    fig_ratio.update_layout(title="Max/Min Ratio with SMA and Average",
                            xaxis_title="Date",
                            yaxis_title="Ratio",
                            xaxis_rangeslider_visible=False)

    st.plotly_chart(fig_ratio)
