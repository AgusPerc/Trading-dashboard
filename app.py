import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pytz import timezone
import requests
import datetime

# Set page config
st.set_page_config(page_title="Trading Dashboard", layout="wide")

# Function to calculate VWAP (unchanged)
def calculate_vwap(df):
    df = df.copy()
    df['typical_price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['cum_vol'] = df['Volume'].cumsum()
    df['cum_vp'] = (df['typical_price'] * df['Volume']).cumsum()
    df['VWAP'] = df['cum_vp'] / df['cum_vol']
    return df

# Modified fetch_minute_data function with API key as parameter
def fetch_minute_data(ticker, date, api_key):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date}/{date}"
    params = {'apiKey': api_key}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            ohlc_df = pd.DataFrame(data['results'])
            ohlc_df['timestamp'] = pd.to_datetime(ohlc_df['t'], unit='ms')
            ohlc_df.set_index('timestamp', inplace=True)
            ohlc_df.index = ohlc_df.index.tz_localize('UTC')
            eastern = timezone('America/New_York')
            ohlc_df.index = ohlc_df.index.tz_convert(eastern)
            
            ohlc_df.rename(columns={
                'o': 'Open', 'h': 'High', 'l': 'Low',
                'c': 'Close', 'v': 'Volume'
            }, inplace=True)
            
            return calculate_vwap(ohlc_df[['Open', 'High', 'Low', 'Close', 'Volume']])
    return pd.DataFrame()

# Modified backtest function
def short_backtest(ticker, date, portfolio_value, api_key):
    df = fetch_minute_data(ticker, date, api_key)
    
    if df.empty:
        return None, None, None, None
    
    short_time = df.between_time('9:35', '9:45')
    if short_time.empty:
        return None, None, None, None
    
    open_price = short_time.iloc[0]['Open']
    stop_loss_price = open_price * 1.15
    risk_per_share = stop_loss_price - open_price
    num_shares = 6000 / risk_per_share
    shares_short_30 = num_shares * 0.3
    
    df_after_open = df.between_time('9:35', '16:00')
    remaining_shares_shorted = False
    shares_short_70 = 0
    
    for index, row in df_after_open.iterrows():
        if not remaining_shares_shorted and row['Close'] < row['VWAP']:
            shares_short_70 = num_shares * 0.7
            remaining_shares_shorted = True
        
        if row['High'] >= stop_loss_price:
            close_price = stop_loss_price
            return_pct = (open_price - close_price) / open_price * 100
            profit_loss = -6000
            return open_price, close_price, return_pct, profit_loss
    
    cover_time_end = df.between_time('15:59', '16:00')
    if cover_time_end.empty:
        return None, None, None, None
    
    close_price = cover_time_end.iloc[0]['Close']
    return_pct = (open_price - close_price) / open_price * 100
    profit_loss = (shares_short_30 + shares_short_70) * (open_price - close_price)
    
    return open_price, close_price, return_pct, profit_loss

def calculate_max_drawdown(portfolio_values):
    cummax = pd.Series(portfolio_values).cummax()
    drawdown = (pd.Series(portfolio_values) - cummax) / cummax
    return drawdown.min()

# Streamlit app
def main():
    st.title("Trading Strategy Dashboard")
    
    # Sidebar for inputs
    st.sidebar.header("Configuration")
    api_key = st.sidebar.text_input("Enter Polygon.io API Key", type="password")
    uploaded_file = st.sidebar.file_uploader("Upload CSV file", type="csv")
    initial_portfolio = st.sidebar.number_input("Initial Portfolio Value ($)", value=20000)
    
    if uploaded_file and api_key:
        df_filtered_stocks = pd.read_csv(uploaded_file)
        
        # Initialize tracking variables
        portfolio_value = initial_portfolio
        trades = []
        wins = losses = total_profit = total_loss = 0
        portfolio_values = [portfolio_value]
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process each trade
        for idx, row in df_filtered_stocks.iterrows():
            progress = (idx + 1) / len(df_filtered_stocks)
            progress_bar.progress(progress)
            status_text.text(f"Processing trade {idx + 1} of {len(df_filtered_stocks)}")
            
            ticker = row['ticker']
            date = row['date']
            results = short_backtest(ticker, date, portfolio_value, api_key)
            
            if all(v is not None for v in results):
                open_price, close_price, return_pct, profit_loss = results
                portfolio_value += profit_loss
                portfolio_values.append(portfolio_value)
                
                if profit_loss > 0:
                    wins += 1
                    total_profit += profit_loss
                else:
                    losses += 1
                    total_loss += profit_loss
                
                trades.append({
                    'ticker': ticker,
                    'date': date,
                    'open_price': open_price,
                    'close_price': close_price,
                    'return_pct': return_pct,
                    'profit_loss': profit_loss,
                    'portfolio_value': portfolio_value
                })
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        if trades:
            df_trades = pd.DataFrame(trades)
            
            # Calculate metrics
            max_drawdown = calculate_max_drawdown(portfolio_values)
            total_trades = wins + losses
            expected_value = (total_profit + total_loss) / total_trades if total_trades > 0 else 0
            win_loss_ratio = wins / losses if losses > 0 else wins
            avg_profit = total_profit / wins if wins > 0 else 0
            avg_loss = total_loss / losses if losses > 0 else 0
            risk_reward_ratio = avg_profit / abs(avg_loss) if avg_loss != 0 else 0
            
            # Display metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Max Drawdown", f"{max_drawdown * 100:.2f}%")
            with col2:
                st.metric("Expected Value", f"${expected_value:.2f}")
            with col3:
                st.metric("Win-Loss Ratio", f"{win_loss_ratio:.2f}")
            with col4:
                st.metric("Risk-Reward Ratio", f"{risk_reward_ratio:.2f}")
            
            # Portfolio value chart
            st.subheader("Portfolio Value Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_trades['date'],
                y=df_trades['portfolio_value'],
                mode='lines+markers',
                name='Portfolio Value'
            ))
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Portfolio Value ($)",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Trade results table
            st.subheader("Trade Results")
            st.dataframe(df_trades)
            
            # Download results button
            csv = df_trades.to_csv(index=False)
            st.download_button(
                label="Download Results CSV",
                data=csv,
                file_name="backtest_results.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()