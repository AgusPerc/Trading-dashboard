import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
from fpdf import FPDF
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from matplotlib.gridspec import GridSpec
import tempfile
import os
import pytz
import scipy.stats as stats

# Set page configuration
st.set_page_config(page_title="Trading Dashboard", layout="wide")

# Function to load data from JSON file
def load_data():
    try:
        with open('trading_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'trades': [],
            'locates': [],
            'starting_balance': 50000
        }

# Function to save data to JSON file
def save_data(data):
    with open('trading_data.json', 'w') as f:
        json.dump(data, f, indent=4)

# [Previous functions remain the same until calculate_weekly_stats]

def calculate_weekly_detailed_stats(trades_df, week_start_date, starting_balance):
    # Filter trades for the specific week
    week_end_date = week_start_date + pd.Timedelta(days=6)
    weekly_trades = trades_df[
        (trades_df['date'] >= week_start_date) & 
        (trades_df['date'] <= week_end_date)
    ]
    
    if weekly_trades.empty:
        return None
    
    # Basic statistics
    total_trades = len(weekly_trades)
    total_pnl = weekly_trades['realized'].sum()
    
    # Calculate portfolio percentage change
    portfolio_percent_change = (total_pnl / starting_balance) * 100
    
    # Win rate calculation
    profitable_trades = weekly_trades[weekly_trades['realized'] > 0]
    win_rate = len(profitable_trades) / total_trades * 100 if total_trades > 0 else 0
    
    # Average win/loss
    avg_win = profitable_trades['realized'].mean() if len(profitable_trades) > 0 else 0
    losing_trades = weekly_trades[weekly_trades['realized'] <= 0]
    avg_loss = losing_trades['realized'].mean() if len(losing_trades) > 0 else 0
    
    # Largest win/loss
    largest_win = profitable_trades['realized'].max() if len(profitable_trades) > 0 else 0
    largest_loss = losing_trades['realized'].min() if len(losing_trades) > 0 else 0
    
    # Day of week performance
    weekly_trades['day_of_week'] = weekly_trades['date'].dt.day_name()
    day_performance = weekly_trades.groupby('day_of_week')['realized'].agg(['sum', 'count'])
    day_performance['avg_pnl'] = day_performance['sum'] / day_performance['count']
    best_day = day_performance['avg_pnl'].idxmax() if not day_performance.empty else "N/A"
    
    # Symbol performance
    symbol_performance = weekly_trades.groupby('symbol')['realized'].agg(['sum', 'count'])
    symbol_performance['avg_pnl'] = symbol_performance['sum'] / symbol_performance['count']
    best_symbol = symbol_performance['sum'].idxmax() if not symbol_performance.empty else "N/A"
    
    results = {
        'Total Trades': total_trades,
        'Total P&L': total_pnl,
        'Portfolio Change': portfolio_percent_change,
        'Win Rate': win_rate,
        'Average Win': avg_win,
        'Average Loss': avg_loss,
        'Largest Win': largest_win,
        'Largest Loss': largest_loss,
        'Best Day': best_day,
        'Best Symbol': best_symbol,
        'Day Performance': day_performance,
        'Symbol Performance': symbol_performance
    }
    
    return results

def create_modern_calendar_view(trades_df, year, month):
    # Filter trades for the specified year and month
    monthly_trades = trades_df[
        (trades_df['date'].dt.year == year) & 
        (trades_df['date'].dt.month == month)
    ]
    
    # Create daily P&L dictionary
    daily_pnl = monthly_trades.groupby('date')['realized'].agg(['sum', 'count']).to_dict('index')
    
    # Create calendar data
    start_date = pd.Timestamp(f'{year}-{month}-01')
    end_date = start_date + pd.offsets.MonthEnd(1)
    dates = pd.date_range(start_date, end_date)
    
    calendar_data = []
    week = []
    
    # Add empty cells for days before the 1st of the month
    first_day_weekday = dates[0].weekday()
    for _ in range(first_day_weekday):
        week.append(None)
    
    # Fill in the calendar
    for date in dates:
        stats = daily_pnl.get(date, {'sum': 0, 'count': 0})
        week.append({
            'date': date,
            'day': date.day,
            'pnl': stats['sum'],
            'trades': stats['count']
        })
        
        if len(week) == 7:
            calendar_data.append(week)
            week = []
    
    # Add empty cells for remaining days
    if week:
        while len(week) < 7:
            week.append(None)
        calendar_data.append(week)
    
    return calendar_data

def render_modern_calendar(calendar_data):
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # CSS for modern calendar with dark theme
    st.markdown("""
        <style>
        .calendar-header {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            background-color: #1e1e1e;
        }
        .calendar-cell {
            aspect-ratio: 1;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            transition: transform 0.2s;
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        .calendar-cell:hover {
            transform: scale(1.05);
            background-color: #383838;
        }
        .trades-badge {
            background-color: #383838;
            border-radius: 12px;
            padding: 2px 6px;
            font-size: 0.8em;
            color: #b0b0b0;
        }
        .empty-cell {
            background-color: #262626;
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Display day headers with dark theme styling
    cols = st.columns(7)
    for i, day in enumerate(days):
        cols[i].markdown(
            f"<div style='text-align: center; font-weight: 500; color: #b0b0b0;'>{day}</div>",
            unsafe_allow_html=True
        )
    
    # Display calendar grid
    for week in calendar_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day is None:
                cols[i].markdown(
                    "<div class='empty-cell' style='aspect-ratio: 1;'></div>",
                    unsafe_allow_html=True
                )
            else:
                pnl = day['pnl']
                trades = day['trades']
                
                # Using fixed colors instead of intensity-based colors
                bg_color = "rgba(0,255,157,0.15)" if pnl > 0 else "rgba(255,77,77,0.15)" if pnl < 0 else "#2d2d2d"
                text_color = '#e0e0e0'
                
                cols[i].markdown(
                    f"""
                    <div class='calendar-cell' style='background-color: {bg_color};'>
                        <div style='font-size: 1.1em; font-weight: 500; color: {text_color};'>{day['day']}</div>
                        <div style='color: {'#00ff9d' if pnl > 0 else '#ff4d4d' if pnl < 0 else '#b0b0b0'};
                                   font-weight: 500;'>${pnl:,.2f}</div>
                        <div class='trades-badge'>{trades} trades</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

def render_weekly_details(trades_df, week_start_date, starting_balance):
    stats = calculate_weekly_detailed_stats(trades_df, week_start_date, starting_balance)
    
    if stats:
        # Main metrics in modern cards with dark theme
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pnl_color = '#00ff9d' if stats['Total P&L'] > 0 else '#ff4d4d'
            pnl_formatted = "${:,.2f}".format(stats['Total P&L'])
            
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h3 style='color: #e0e0e0;'>Performance</h3>
                    <div style='font-size: 1.8em; font-weight: bold; color: {pnl_color};'>{pnl_formatted}</div>
                    <div style='color: #b0b0b0;'>Total P&L</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            win_rate_formatted = "{:.1f}%".format(stats['Win Rate'])
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h3 style='color: #e0e0e0;'>Win Rate</h3>
                    <div style='font-size: 1.8em; font-weight: bold; color: #e0e0e0;'>{win_rate_formatted}</div>
                    <div style='color: #b0b0b0;'>{stats['Total Trades']} Total Trades</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col3:
            portfolio_change_formatted = "{:+.2f}%".format(stats['Portfolio Change'])
            change_color = '#00ff9d' if stats['Portfolio Change'] > 0 else '#ff4d4d'
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h3 style='color: #e0e0e0;'>Portfolio Change</h3>
                    <div style='font-size: 1.8em; font-weight: bold; color: {change_color};'>{portfolio_change_formatted}</div>
                    <div style='color: #b0b0b0;'>Weekly Return</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Additional statistics
        st.markdown("<h3 style='color: #e0e0e0;'>Trade Statistics</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <div style='color: #00ff9d; font-weight: bold;'>Average Win: ${stats['Average Win']:,.2f}</div>
                    <div style='color: #ff4d4d; font-weight: bold;'>Average Loss: ${stats['Average Loss']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <div style='color: #00ff9d; font-weight: bold;'>Largest Win: ${stats['Largest Win']:,.2f}</div>
                    <div style='color: #ff4d4d; font-weight: bold;'>Largest Loss: ${stats['Largest Loss']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Day performance analysis
        st.markdown("<h3 style='color: #e0e0e0;'>Daily Performance</h3>", unsafe_allow_html=True)
        day_perf = stats['Day Performance']
        
        # Create bar chart for daily performance with dark theme
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=day_perf.index,
            y=day_perf['sum'],
            marker_color=['#00ff9d' if x > 0 else '#ff4d4d' for x in day_perf['sum']],
            name='Daily P&L'
        ))
        
        fig.update_layout(
            title='P&L by Day of Week',
            xaxis_title='Day of Week',
            yaxis_title='P&L ($)',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#1e1e1e',
            font=dict(color='#e0e0e0'),
            xaxis=dict(
                gridcolor='#333333',
                zerolinecolor='#333333'
            ),
            yaxis=dict(
                gridcolor='#333333',
                zerolinecolor='#333333'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Best performing metrics
        st.markdown(f"""
            <div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                <div style='color: #e0e0e0; font-weight: bold;'>🏆 Best Trading Day: {stats['Best Day']}</div>
                <div style='color: #e0e0e0; font-weight: bold;'>💫 Best Symbol: {stats['Best Symbol']}</div>
            </div>
        """, unsafe_allow_html=True)

# Function to calculate monthly statistics
def calculate_monthly_detailed_stats(trades_df, month_start_date, starting_balance):
    # Filter trades for the specific month
    month_end_date = month_start_date + pd.offsets.MonthEnd(1)
    monthly_trades = trades_df[
        (trades_df['date'] >= month_start_date) & 
        (trades_df['date'] <= month_end_date)
    ]
    
    if monthly_trades.empty:
        return None
    
    # Basic statistics
    total_trades = len(monthly_trades)
    total_pnl = monthly_trades['realized'].sum()
    
    # Calculate portfolio percentage change
    portfolio_percent_change = (total_pnl / starting_balance) * 100
    
    # Win rate calculation
    profitable_trades = monthly_trades[monthly_trades['realized'] > 0]
    win_rate = len(profitable_trades) / total_trades * 100 if total_trades > 0 else 0
    
    # Average win/loss
    avg_win = profitable_trades['realized'].mean() if len(profitable_trades) > 0 else 0
    losing_trades = monthly_trades[monthly_trades['realized'] <= 0]
    avg_loss = losing_trades['realized'].mean() if len(losing_trades) > 0 else 0
    
    # Largest win/loss
    largest_win = profitable_trades['realized'].max() if len(profitable_trades) > 0 else 0
    largest_loss = losing_trades['realized'].min() if len(losing_trades) > 0 else 0
    
    # Day of week performance
    monthly_trades['day_of_week'] = monthly_trades['date'].dt.day_name()
    day_performance = monthly_trades.groupby('day_of_week')['realized'].agg(['sum', 'count'])
    day_performance['avg_pnl'] = day_performance['sum'] / day_performance['count']
    best_day = day_performance['avg_pnl'].idxmax() if not day_performance.empty else "N/A"
    
    # Symbol performance
    symbol_performance = monthly_trades.groupby('symbol')['realized'].agg(['sum', 'count'])
    symbol_performance['avg_pnl'] = symbol_performance['sum'] / symbol_performance['count']
    best_symbol = symbol_performance['sum'].idxmax() if not symbol_performance.empty else "N/A"
    
    results = {
        'Total Trades': total_trades,
        'Total P&L': total_pnl,
        'Portfolio Change': portfolio_percent_change,
        'Win Rate': win_rate,
        'Average Win': avg_win,
        'Average Loss': avg_loss,
        'Largest Win': largest_win,
        'Largest Loss': largest_loss,
        'Best Day': best_day,
        'Best Symbol': best_symbol,
        'Day Performance': day_performance,
        'Symbol Performance': symbol_performance
    }
    
    return results

def render_monthly_details(trades_df, month_start_date, starting_balance):
    stats = calculate_monthly_detailed_stats(trades_df, month_start_date, starting_balance)
    
    if stats:
        # Main metrics in modern cards with dark theme
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pnl_color = '#00ff9d' if stats['Total P&L'] > 0 else '#ff4d4d'
            pnl_formatted = "${:,.2f}".format(stats['Total P&L'])
            
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h3 style='color: #e0e0e0;'>Performance</h3>
                    <div style='font-size: 1.8em; font-weight: bold; color: {pnl_color};'>{pnl_formatted}</div>
                    <div style='color: #b0b0b0;'>Total P&L</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            win_rate_formatted = "{:.1f}%".format(stats['Win Rate'])
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h3 style='color: #e0e0e0;'>Win Rate</h3>
                    <div style='font-size: 1.8em; font-weight: bold; color: #e0e0e0;'>{win_rate_formatted}</div>
                    <div style='color: #b0b0b0;'>{stats['Total Trades']} Total Trades</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col3:
            portfolio_change_formatted = "{:+.2f}%".format(stats['Portfolio Change'])
            change_color = '#00ff9d' if stats['Portfolio Change'] > 0 else '#ff4d4d'
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h3 style='color: #e0e0e0;'>Portfolio Change</h3>
                    <div style='font-size: 1.8em; font-weight: bold; color: {change_color};'>{portfolio_change_formatted}</div>
                    <div style='color: #b0b0b0;'>Monthly Return</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Additional statistics
        st.markdown("<h3 style='color: #e0e0e0;'>Trade Statistics</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <div style='color: #00ff9d; font-weight: bold;'>Average Win: ${stats['Average Win']:,.2f}</div>
                    <div style='color: #ff4d4d; font-weight: bold;'>Average Loss: ${stats['Average Loss']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <div style='color: #00ff9d; font-weight: bold;'>Largest Win: ${stats['Largest Win']:,.2f}</div>
                    <div style='color: #ff4d4d; font-weight: bold;'>Largest Loss: ${stats['Largest Loss']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Day performance analysis
        st.markdown("<h3 style='color: #e0e0e0;'>Daily Performance</h3>", unsafe_allow_html=True)
        day_perf = stats['Day Performance']
        
        # Create bar chart for daily performance with dark theme
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=day_perf.index,
            y=day_perf['sum'],
            marker_color=['#00ff9d' if x > 0 else '#ff4d4d' for x in day_perf['sum']],
            name='Daily P&L'
        ))
        
        fig.update_layout(
            title='P&L by Day of Week',
            xaxis_title='Day of Week',
            yaxis_title='P&L ($)',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#1e1e1e',
            font=dict(color='#e0e0e0'),
            xaxis=dict(
                gridcolor='#333333',
                zerolinecolor='#333333'
            ),
            yaxis=dict(
                gridcolor='#333333',
                zerolinecolor='#333333'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Best performing metrics
        st.markdown(f"""
            <div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                <div style='color: #e0e0e0; font-weight: bold;'>🏆 Best Trading Day: {stats['Best Day']}</div>
                <div style='color: #e0e0e0; font-weight: bold;'>💫 Best Symbol: {stats['Best Symbol']}</div>
            </div>
        """, unsafe_allow_html=True)

def calculate_advanced_monthly_stats(trades_df, month_year, starting_balance):
    # Filter trades for the specific month
    monthly_trades = trades_df[
        (trades_df['date'].dt.year == month_year.year) & 
        (trades_df['date'].dt.month == month_year.month)
    ]
    
    if monthly_trades.empty:
        return None
    
    # Basic statistics
    total_trades = len(monthly_trades)
    total_pnl = monthly_trades['realized'].sum()
    
    # Calculate portfolio percentage change
    portfolio_percent_change = (total_pnl / starting_balance) * 100
    
    # Win rate calculation
    profitable_trades = monthly_trades[monthly_trades['realized'] > 0]
    win_rate = len(profitable_trades) / total_trades * 100
    
    # Average win/loss
    avg_win = profitable_trades['realized'].mean() if len(profitable_trades) > 0 else 0
    losing_trades = monthly_trades[monthly_trades['realized'] <= 0]
    avg_loss = losing_trades['realized'].mean() if len(losing_trades) > 0 else 0
    
    # Day of week performance
    monthly_trades['day_of_week'] = monthly_trades['date'].dt.day_name()
    day_performance = monthly_trades.groupby('day_of_week')['realized'].agg(['sum', 'count'])
    day_performance['avg_pnl'] = day_performance['sum'] / day_performance['count']
    best_day = day_performance['avg_pnl'].idxmax()
    
    # Detailed results
    results = {
        'Total Trades': total_trades,
        'Total P&L': total_pnl,
        'Portfolio Change': portfolio_percent_change,
        'Win Rate': win_rate,
        'Average Win': avg_win,
        'Average Loss': avg_loss,
        'Best Day': best_day,
        'Day Performance': day_performance
    }
    
    return results

# Function to calculate latest daily P&L
def calculate_latest_daily_pnl(trades, starting_balance):
    if not trades:
        return 0, 0, "No trades"
    
    trades_df = pd.DataFrame(trades)
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    latest_date = trades_df['date'].max()
    latest_pnl = trades_df[trades_df['date'] == latest_date]['realized'].sum()
    
    # Calculate daily percentage return based on starting balance
    daily_return_percent = (latest_pnl / starting_balance) * 100
    
    return latest_pnl, daily_return_percent, latest_date.strftime("%Y-%m-%d")

def calculate_weekly_stats(trades_df):
    # Ensure date column is datetime
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    
    # Group by week and calculate weekly statistics
    weekly_stats = trades_df.groupby(pd.Grouper(key='date', freq='W-MON')).agg({
        'realized': 'sum',
        'symbol': 'count'  # Number of trades
    }).reset_index()
    
    # Rename columns for clarity
    weekly_stats.columns = ['Week', 'Weekly P&L', 'Number of Trades']
    
    # Calculate cumulative P&L
    weekly_stats['Cumulative P&L'] = weekly_stats['Weekly P&L'].cumsum()
    
    # Calculate weekly win/loss ratio
    weekly_stats['Win/Loss Ratio'] = weekly_stats.apply(
        lambda row: 'Positive' if row['Weekly P&L'] > 0 else 'Negative', 
        axis=1
    )
    
    return weekly_stats

def create_calendar_view(trades_df, year, month):
    # Filter trades for the specified year and month
    monthly_trades = trades_df[
        (trades_df['date'].dt.year == year) & 
        (trades_df['date'].dt.month == month)
    ]
    
    # Create a calendar DataFrame
    start_date = pd.Timestamp(f'{year}-{month}-01')
    end_date = start_date + pd.offsets.MonthEnd(1)
    dates = pd.date_range(start_date, end_date)
    
    # Create daily P&L dictionary
    daily_pnl = monthly_trades.groupby('date')['realized'].sum().to_dict()
    
    # Create calendar data
    calendar_data = []
    week = []
    
    # Add empty cells for days before the 1st of the month
    first_day_weekday = dates[0].weekday()
    for _ in range(first_day_weekday):
        week.append(None)
    
    # Fill in the calendar
    for date in dates:
        pnl = daily_pnl.get(date, 0)
        week.append({'date': date.day, 'pnl': pnl})
        
        if len(week) == 7:
            calendar_data.append(week)
            week = []
    
    # Add empty cells for remaining days
    if week:
        while len(week) < 7:
            week.append(None)
        calendar_data.append(week)
    
    return calendar_data

def main():
    # Load existing data
    data = load_data()

    # Sidebar for adding new entries
    st.sidebar.title("Add New Trade")

    # Combined trade and locate input
    mexico_tz = pytz.timezone('America/Mexico_City')
    mexico_now = datetime.now(pytz.UTC).astimezone(mexico_tz)
    trade_date = st.sidebar.date_input("Date", mexico_now)
    trade_symbol = st.sidebar.text_input("Symbol")
    trade_type = st.sidebar.selectbox("Type", ["Long", "Short"])
    trade_realized = st.sidebar.number_input("Realized P&L")
    locate_cost = st.sidebar.number_input("Locate Cost", min_value=0.0)

    if st.sidebar.button("Add Trade"):
        # Format date as string
        date_str = trade_date.strftime("%Y-%m-%d")
        
        # Add trade
        new_trade = {
            "date": date_str,
            "symbol": trade_symbol,
            "type": trade_type,
            "realized": trade_realized
        }
        data['trades'].append(new_trade)
        
        # Add locate if cost > 0
        if locate_cost > 0:
            new_locate = {
                "date": date_str,
                "symbol": trade_symbol,
                "totalCost": locate_cost
            }
            data['locates'].append(new_locate)
        
        save_data(data)
        st.sidebar.success("Trade data added successfully!")

    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Dashboard", "Trades", "Monthly Performance", 
        "Monthly Drill Down", "Weekly Performance", "Calendar View"
    ])

    with tab1:
        # Main dashboard
        st.title("Trading Dashboard")

        # Calculate summary statistics
        starting_balance = data.get('starting_balance', 50000)
        total_realized = sum(trade['realized'] for trade in data['trades'])
        total_locate_cost = sum(locate['totalCost'] for locate in data['locates'])
        net_pnl = total_realized - total_locate_cost
        ending_balance = starting_balance + net_pnl
        return_percent = (net_pnl / starting_balance) * 100 if starting_balance else 0

        # Calculate latest daily P&L with percentage
        latest_daily_pnl, daily_return_percent, latest_date = calculate_latest_daily_pnl(data['trades'], starting_balance)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Starting Balance", f"${starting_balance:,.2f}")
        with col2:
            st.metric("Net P&L", f"${net_pnl:,.2f}", f"{return_percent:.2f}%")
        with col3:
            st.metric("Ending Balance", f"${ending_balance:,.2f}")
        with col4:
            if latest_date != "No trades":
                st.metric(f"Daily P&L ({latest_date})", f"${latest_daily_pnl:,.2f}", f"{daily_return_percent:.2f}%")
            else:
                st.metric("Daily P&L", "No trades")

        # P&L Chart
        if data['trades']:
            trades_df = pd.DataFrame(data['trades'])
            trades_df['date'] = pd.to_datetime(trades_df['date'])
            daily_pnl = trades_df.groupby('date')['realized'].sum().cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_pnl.index,
                y=daily_pnl.values,
                mode='lines+markers',
                name='Cumulative P&L'
            ))
            
            fig.update_layout(
                title='Cumulative P&L Over Time',
                xaxis_title='Date',
                yaxis_title='Cumulative P&L ($)',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Trades table and details
        st.subheader("Trades Summary")
        if data['trades']:
            trades_df = pd.DataFrame(data['trades'])
            trades_df = trades_df.sort_values('date', ascending=False)
            st.dataframe(trades_df[['date', 'symbol', 'type', 'realized']], use_container_width=True)
        else:
            st.info("No trades recorded yet")

        # Locates table
        st.subheader("Locates Summary")
        if data['locates']:
            locates_df = pd.DataFrame(data['locates'])
            locates_df = locates_df.sort_values('date', ascending=False)
            st.dataframe(locates_df[['date', 'symbol', 'totalCost']], use_container_width=True)
        else:
            st.info("No locates recorded yet")

    with tab3:
        # Monthly Performance Tab
        if data['trades']:
            trades_df = pd.DataFrame(data['trades'])
            trades_df['date'] = pd.to_datetime(trades_df['date'])
            
            # Get available months
            unique_months = trades_df['date'].dt.to_period('M').unique()
            selected_month = st.selectbox(
                "Select Month", 
                sorted(unique_months, reverse=True), 
                format_func=lambda x: x.strftime("%B %Y")
            )
            
            # Pass starting_balance to the function
            selected_month_date = selected_month.to_timestamp()
            render_monthly_details(trades_df, selected_month_date, data.get('starting_balance', 50000))
        else:
            st.info("No trades recorded yet to generate monthly performance")

    with tab4:
        if data['trades']:
            trades_df = pd.DataFrame(data['trades'])
            trades_df['date'] = pd.to_datetime(trades_df['date'])
            
            unique_months = trades_df['date'].dt.to_period('M').unique()
            
            selected_month = st.selectbox(
                "Select Month", 
                sorted(unique_months, reverse=True), 
                format_func=lambda x: x.strftime("%B %Y")
            )
            
            # Pass starting_balance to the function
            monthly_stats = calculate_advanced_monthly_stats(trades_df, selected_month.to_timestamp(), data.get('starting_balance', 50000))
            
            if monthly_stats:
                st.subheader(f"Monthly Statistics for {selected_month.strftime('%B %Y')}")
                
                # Main metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Trades", monthly_stats['Total Trades'])
                    st.metric("Total P&L", f"${monthly_stats['Total P&L']:,.2f}")
                
                with col2:
                    st.metric("Win Rate", f"{monthly_stats['Win Rate']:.2f}%")
                    st.metric("Average Win", f"${monthly_stats['Average Win']:,.2f}")
                
                with col3:
                    st.metric("Portfolio Change", f"{monthly_stats['Portfolio Change']:.2f}%")
                    st.metric("Average Loss", f"${monthly_stats['Average Loss']:,.2f}")
                
                # Day of Week Performance
                st.subheader("Day of Week Performance")
                day_perf_df = monthly_stats['Day Performance'].reset_index()
                day_perf_df.columns = ['Day', 'Total P&L', 'Trade Count', 'Avg P&L']
                st.dataframe(day_perf_df, use_container_width=True)
                
                # Bar chart of day performance
                fig_day_perf = go.Figure(data=[
                    go.Bar(
                        x=day_perf_df['Day'],
                        y=day_perf_df['Avg P&L'],
                        marker_color=day_perf_df['Avg P&L'].apply(lambda x: 'green' if x > 0 else 'red')
                    )
                ])
                fig_day_perf.update_layout(
                    title='Average P&L by Day of Week',
                    xaxis_title='Day of Week',
                    yaxis_title='Average P&L ($)',
                    height=400
                )
                st.plotly_chart(fig_day_perf, use_container_width=True)
                
                # Highlight best day
                st.info(f"Best Performing Day: {monthly_stats['Best Day']}")
            
            else:
                st.warning("No trades for the selected month")
        
        else:
            st.info("No trades recorded yet to generate monthly drill-down")

    with tab5:
        if data['trades']:
            trades_df = pd.DataFrame(data['trades'])
            trades_df['date'] = pd.to_datetime(trades_df['date'])
            
            # Get available weeks
            weekly_stats = calculate_weekly_stats(trades_df)
            selected_week = st.selectbox(
                "Select Week",
                weekly_stats['Week'].dt.strftime('%Y-%m-%d'),
                format_func=lambda x: f"Week of {x}"
            )
            
            selected_week_date = pd.to_datetime(selected_week)
            render_weekly_details(trades_df, selected_week_date, data.get('starting_balance', 50000))
        else:
            st.info("No trades recorded yet to generate weekly performance")
    
    with tab6:
        if data['trades']:
            trades_df = pd.DataFrame(data['trades'])
            trades_df['date'] = pd.to_datetime(trades_df['date'])
            
            # Date selection with modern styling
            col1, col2 = st.columns(2)
            with col1:
                selected_year = st.selectbox(
                    "Select Year",
                    sorted(trades_df['date'].dt.year.unique(), reverse=True)
                )
            with col2:
                selected_month = st.selectbox(
                    "Select Month",
                    range(1, 13),
                    format_func=lambda x: datetime(2000, x, 1).strftime('%B')
                )
            
            calendar_data = create_modern_calendar_view(trades_df, selected_year, selected_month)
            render_modern_calendar(calendar_data)
        else:
            st.info("No trades recorded yet to generate calendar view")

    # Sidebar footer
    st.sidebar.markdown("---")
    st.sidebar.write("Trading Dashboard v1.0")
    st.sidebar.write("© 2025 All rights reserved")

# Run the main function
if __name__ == "__main__":
    main()
