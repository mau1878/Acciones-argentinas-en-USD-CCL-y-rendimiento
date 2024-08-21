import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Streamlit web interface for inputting tickers and time period
st.title('Precio de activos argentinos en CCL y rendimiento actual en CCL según la fecha de compra. MTaurus. https://x.com/MTaurus_ok')

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
        ypfd_price = data["YPFD.BA"]['Close']

        # Calculate the daily ratio of YPFD.BA to YPF
        daily_ratio = ypfd_price / ypf_price

        # Normalize other stocks' prices by this daily ratio
        normalized_data = {}
        for ticker in tickers:
            if ticker not in ["YPF", "YPFD.BA"]:
                if ticker in data:
                    stock_data = data[ticker].copy()
                    stock_data = stock_data.reindex(argentina_dates, method='ffill')
                    stock_data['Normalized_Price'] = stock_data['Close'] / daily_ratio

                    # Calculate profit percentage based on today's price
                    today_price = stock_data['Normalized_Price'].iloc[-1]
                    stock_data['Profit_Percentage'] = ((today_price / stock_data['Normalized_Price']) - 1) * 100

                    # Calculate traditional profit percentage
                    valid_start_index = stock_data['Normalized_Price'].loc[start_date:end_date].first_valid_index()
                    if valid_start_index is not None:
                        start_price = stock_data.loc[valid_start_index, 'Normalized_Price']
                        stock_data['Traditional_Profit'] = ((stock_data['Normalized_Price'] / start_price) - 1) * 100
                    else:
                        st.warning(f"No valid data available for {ticker} from {start_date} to {end_date}.")
                        stock_data['Traditional_Profit'] = None

                    normalized_data[ticker] = stock_data

        # Plotting with Plotly
        fig = go.Figure()

        # Track if zero is present in any y_data
        zero_present = False

        # Depending on the selected display option, plot the data
        for ticker, stock_data in normalized_data.items():
            if display_option == "Rendimiento en USD CCL desde la fecha de inicio seleccionada":
                y_data = stock_data['Traditional_Profit'].dropna()  # Drop NaN values to avoid plotting issues
            elif display_option == "Rendimiento actual en USD CCL según la fecha de compra":
                y_data = stock_data['Profit_Percentage'].dropna()
            else:  # Precios en USD CCL
                y_data = stock_data['Normalized_Price'].dropna()

            if not y_data.empty:  # Ensure there's data to plot
                if (y_data == 0).any():
                    zero_present = True

                hovertext = stock_data.apply(
                    lambda row: f"Fecha: {row.name.date()}<br>{'Rendimiento actual' if display_option == 'Rendimiento actual en USD CCL según la fecha de compra' else 'Rendimiento tradicional' if display_option == 'Rendimiento en USD CCL desde la fecha de inicio seleccionada' else 'Precio'}: {row[y_data.name] if row[y_data.name] is not None else 'N/A']:.2f}",
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
            xaxis_rangeslider_visible=False,
            title_font_size=title_font_size,
            xaxis=dict(title_font_size=label_font_size, tickfont=dict(size=axis_font_size), showgrid=True, gridcolor='LightGray'),
            yaxis=dict(title_font_size=label_font_size, tickfont=dict(size=axis_font_size), type='linear', showgrid=True, gridcolor='LightGray'),
            hovermode='closest'
        )

        # Display the Plotly figure in Streamlit
        st.plotly_chart(fig, use_container_width=True)
