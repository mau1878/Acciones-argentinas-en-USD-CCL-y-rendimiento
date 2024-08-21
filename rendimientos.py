import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Streamlit web interface for inputting tickers and time period
st.title('Análisis de acciones argentinas en USD CCL y rendimiento actual en CCL. MTaurus.')

# Input for list of stocks and time period
tickers_input = st.text_area("Ingresar los tickers de las acciones separadas por comas y con '.BA' luego de cada ticker:", "GGAL.BA, METR.BA, YPFD.BA")
start_date = st.date_input("Fecha de inicio", pd.to_datetime("2023-01-01"))
end_date = st.date_input("Fecha de finalización", pd.to_datetime("today"))  # Default to the present date

# Options to select between price and profit percentage
display_option = st.selectbox("Seleccionar datos a mostrar:", ["Precios en USD CCL", "Rendimiento actual en USD CCL según la fecha de compra", "Rendimiento en USD CCL desde la fecha de inicio seleccionada"])

# Inputs for font size configuration
title_font_size = st.slider("Tamaño de fuente de los títulos", min_value=10, max_value=40, value=20)
label_font_size = st.slider("Tamaño de fuente de los títulos de los ejes", min_value=10, max_value=30, value=14)
axis_font_size = st.slider("Tamaño de fuente de los valores en los ejes", min_value=8, max_value=20, value=12)

# Button to fetch data
if st.button('Fetch Data'):
    # Convert tickers input to list
    tickers = [ticker.strip() for ticker in tickers_input.split(',')]
    tickers.extend(["YPF", "YPFD.BA"])  # Add YPF and YPFD.BA to the list

    # Fetch historical data
    data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            hist['Ticker'] = ticker
            data[ticker] = hist
        except Exception as e:
            st.warning(f"Failed to fetch data for {ticker}: {e}")

    # Convert datetime index to timezone-naive
    for ticker in data:
        if data[ticker].index.tz is not None:
            data[ticker].index = data[ticker].index.tz_localize(None)

    # Convert start_date and end_date to timezone-naive
    start_date = pd.to_datetime(start_date).tz_localize(None)
    end_date = pd.to_datetime(end_date).tz_localize(None)

    # Ensure YPFD.BA and YPF are present
    if "YPF" not in data or "YPFD.BA" not in data:
        st.error("Data for YPF or YPFD.BA is missing. Please check ticker symbols.")
    else:
        # Align dates to Argentina working dates
        argentina_dates = data["YPFD.BA"].index

        # Get the price data for YPF and YPFD.BA, reindex to Argentina dates
        ypf_price = data["YPF"]['Close'].reindex(argentina_dates, method='ffill')
        ypfd_price = data["YPFD.BA"]['Close'].reindex(argentina_dates, method='ffill')

        # Debugging: Check if ypf_price and ypfd_price are correctly aligned
        st.write("YPF Price Data:")
        st.write(ypf_price.head())
        st.write("YPFD.BA Price Data:")
        st.write(ypfd_price.head())

        # Calculate the daily ratio of YPFD.BA to YPF
        daily_ratio = ypfd_price / ypf_price
        st.write("Daily Ratio:")
        st.write(daily_ratio.head())

        # Normalize other stocks' prices by this daily ratio
        normalized_data = {}
        for ticker in tickers:
            if ticker not in ["YPF", "YPFD.BA"]:
                if ticker in data:
                    stock_data = data[ticker].copy()
                    stock_data = stock_data.reindex(argentina_dates, method='ffill')

                    # Debugging: Ensure no data is missing
                    st.write(f"Data for {ticker} before normalization:")
                    st.write(stock_data[['Close']].head())

                    stock_data['Normalized_Price'] = stock_data['Close'] / daily_ratio

                    # Debugging: Check normalized prices
                    st.write(f"Data for {ticker} after normalization:")
                    st.write(stock_data[['Normalized_Price']].head())

                    # Calculate profit percentage based on today's price
                    today_price = stock_data['Normalized_Price'].iloc[-1] if not stock_data['Normalized_Price'].empty else None
                    if today_price is not None:
                        stock_data['Profit_Percentage'] = ((today_price / stock_data['Normalized_Price']) - 1) * 100

                    # Calculate traditional profit percentage
                    start_price = stock_data.loc[start_date:end_date, 'Normalized_Price'].iloc[0] if not stock_data.loc[start_date:end_date, 'Normalized_Price'].empty else None
                    if pd.isna(start_price) or start_price == 0:
                        st.warning(f"Start price is NaN or zero for {ticker}. Check data availability.")
                        stock_data['Traditional_Profit'] = None
                    else:
                        stock_data['Traditional_Profit'] = ((stock_data['Normalized_Price'] / start_price) - 1) * 100

                    # Debugging: Check traditional profit calculation
                    st.write(f"Traditional profit for {ticker}:")
                    st.write(stock_data[['Traditional_Profit']].head())

                    normalized_data[ticker] = stock_data

        # Debugging: Check the contents of normalized_data
        for ticker, stock_data in normalized_data.items():
            st.write(f"Data for {ticker}:")
            st.write(stock_data.head())

        # Plotting with Plotly
        fig = go.Figure()

        # Track if zero is present in any y_data
        zero_present = False

        # Depending on the selected display option, plot the data
        for ticker, stock_data in normalized_data.items():
            if display_option == "Rendimiento en USD CCL desde la fecha de inicio seleccionada":
                y_data = stock_data['Traditional_Profit']
            elif display_option == "Rendimiento actual en USD CCL según la fecha de compra":
                y_data = stock_data['Profit_Percentage']
            else:  # Precios en USD CCL
                y_data = stock_data['Normalized_Price']

            # Debugging: Check y_data values
            st.write(f"y_data for {ticker}:")
            st.write(y_data.dropna().head())

            if (y_data == 0).any():
                zero_present = True

            # Corrected hovertext lambda function
            hovertext = stock_data.apply(
                lambda row: (
                    f"Fecha: {row.name.date()}<br>"
                    f"{'Rendimiento actual' if display_option == 'Rendimiento actual en USD CCL según la fecha de compra' else 'Rendimiento tradicional' if display_option == 'Rendimiento en USD CCL desde la fecha de inicio seleccionada' else 'Precio'}: "
                    f"{row[y_data.name]:.2f}" if pd.notna(row[y_data.name]) else "N/A"
                ),
                axis=1
            )

            fig.add_trace(go.Scatter(
                x=stock_data.index,
                y=y_data,
                mode='lines',
                name=ticker,
                text=hovertext,
                hoverinfo='text'
            ))

        # Add horizontal red line if zero is present
        if zero_present:
            fig.add_shape(
                type='line',
                x0=stock_data.index.min(),
                x1=stock_data.index.max(),
                y0=0,
                y1=0,
                line=dict(color='Red', width=2)
            )

        # Update layout with title, labels, and font sizes
        if display_option == "Rendimiento en USD CCL desde la fecha de inicio seleccionada":
            y_axis_title = "Rendimiento porcentual en USD"
        else:
            y_axis_title = "Rendimiento actual en USD CCL según la fecha de compra" if display_option == "Rendimiento actual en USD CCL según la fecha de compra" else "Precios en USD CCL"
        
        fig.update_layout(
            title='Stock Analysis: ' + display_option,
            xaxis_title='Fecha',
            yaxis_title=y_axis_title,
            xaxis_rangeslider
