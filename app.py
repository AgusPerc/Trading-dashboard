import streamlit as st
import pandas as pd
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

# Set page configuration
st.set_page_config(page_title="Trading Dashboard", layout="wide")

class DashboardPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # Modern header with background color
        self.set_fill_color(47, 73, 95)  # Dark blue background
        self.rect(0, 0, 210, 20, 'F')
        self.set_font('Arial', 'B', 15)
        self.set_text_color(255, 255, 255)  # White text
        self.cell(0, 20, 'Trading Performance Dashboard', 0, 1, 'C', True)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)  # Gray text
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")} | Page {self.page_no()}', 0, 0, 'C')

    def add_metric_box(self, title, value, delta=None):
        self.set_fill_color(245, 245, 245)  # Light gray background
        self.rect(self.get_x(), self.get_y(), 60, 25, 'F')
        self.set_font('Arial', 'B', 10)
        self.set_text_color(70, 70, 70)
        self.cell(60, 10, title, 0, 2, 'L')
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        value_text = f"${value:,.2f}"
        self.cell(60, 8, value_text, 0, 1, 'L')
        if delta:
            self.set_font('Arial', '', 10)
            color = (0, 150, 0) if delta >= 0 else (150, 0, 0)
            self.set_text_color(*color)
            self.cell(60, 8, f"({delta:+.2f}%)", 0, 1, 'L')
        self.ln(5)

    def add_table(self, headers, data, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(47, 73, 95)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)
        
        # Calculate column widths
        col_widths = [40] * len(headers)
        
        # Table header
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(47, 73, 95)
        self.set_text_color(255, 255, 255)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, 1, 0, 'C', True)
        self.ln()
        
        # Table data
        self.set_font('Arial', '', 9)
        self.set_text_color(0, 0, 0)
        for row in data:
            for i, item in enumerate(row):
                if isinstance(item, (int, float)):
                    text = f"${item:,.2f}" if i == len(row)-1 else f"{item:,.2f}"
                else:
                    text = str(item)
                self.cell(col_widths[i], 7, text, 1, 0, 'C')
            self.ln()
        self.ln(5)

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
    
    # [Previous code remains the same until the metrics section]
    
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
    
    # [Also update the PDF generation to include the daily percentage]
    def create_dashboard_pdf(data):
        pdf = DashboardPDF()
        pdf.add_page()
        
        # Calculate summary statistics
        starting_balance = data.get('starting_balance', 50000)
        total_realized = sum(trade['realized'] for trade in data['trades'])
        total_locate_cost = sum(locate['totalCost'] for locate in data['locates'])
        net_pnl = total_realized - total_locate_cost
        ending_balance = starting_balance + net_pnl
        return_percent = (net_pnl / starting_balance) * 100 if starting_balance else 0
        latest_daily_pnl, daily_return_percent, latest_date = calculate_latest_daily_pnl(data['trades'], starting_balance)
        
        # Add metrics section
        pdf.add_metric_box("Starting Balance", starting_balance)
        pdf.set_x(75)
        pdf.set_y(pdf.get_y() - 30)
        pdf.add_metric_box("Net P&L", net_pnl, return_percent)
        pdf.set_x(140)
        pdf.set_y(pdf.get_y() - 30)
        pdf.add_metric_box("Ending Balance", ending_balance)
        pdf.set_x(205)
        pdf.set_y(pdf.get_y() - 30)
        if latest_date != "No trades":
            pdf.add_metric_box(f"Daily P&L ({latest_date})", latest_daily_pnl, daily_return_percent)
    
    # Add P&L chart if there are trades
    if data['trades']:
        trades_df = pd.DataFrame(data['trades'])
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # Create and add the P&L chart
        chart_path = create_pnl_chart(trades_df)
        try:
            pdf.image(chart_path, x=10, y=None, w=190)
            pdf.ln(10)
        finally:
            # Clean up temporary file
            if os.path.exists(chart_path):
                os.unlink(chart_path)
        
        # Add trades summary
        trades_data = [
            [trade['date'], trade['symbol'], trade['type'], trade['realized']]
            for trade in sorted(data['trades'], key=lambda x: x['date'], reverse=True)
        ]
        pdf.add_table(
            ['Date', 'Symbol', 'Type', 'P&L'],
            trades_data,
            'Trades Summary'
        )
    
    # Add new page for locates if needed
    if len(data['trades']) > 5:
        pdf.add_page()
    
    # Add locates summary
    if data['locates']:
        locates_data = [
            [locate['date'], locate['symbol'], locate['totalCost']]
            for locate in sorted(data['locates'], key=lambda x: x['date'], reverse=True)
        ]
        pdf.add_table(
            ['Date', 'Symbol', 'Cost'],
            locates_data,
            'Locates Summary'
        )
    
    # Add daily summary
    if data['trades']:
        trades_df = pd.DataFrame(data['trades'])
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        daily_summary = trades_df.groupby('date')['realized'].sum()
        daily_data = [
            [date.strftime('%Y-%m-%d'), pnl]
            for date, pnl in daily_summary.items()
        ]
        pdf.add_table(
            ['Date', 'Daily P&L'],
            daily_data,
            'Daily Summary'
        )
    
    return pdf.output(dest='S').encode('latin-1')

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

# Main dashboard
st.title("Trading Dashboard")

# Calculate summary statistics
starting_balance = data.get('starting_balance', 50000)
total_realized = sum(trade['realized'] for trade in data['trades'])
total_locate_cost = sum(locate['totalCost'] for locate in data['locates'])
net_pnl = total_realized - total_locate_cost
ending_balance = starting_balance + net_pnl
return_percent = (net_pnl / starting_balance) * 100 if starting_balance else 0

# Calculate latest daily P&L
latest_daily_pnl, latest_date = calculate_latest_daily_pnl(data['trades'])

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
        st.metric(f"Daily P&L ({latest_date})", f"${latest_daily_pnl:,.2f}")
    else:
        st.metric("Daily P&L", "No trades")

# Trades table
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

# Add daily summary
st.subheader("Daily Summary")
if data['trades']:
    trades_df = pd.DataFrame(data['trades'])
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    daily_summary = trades_df.groupby('date')['realized'].sum()
    
    st.dataframe(daily_summary.sort_index(ascending=False), use_container_width=True)

# Add PDF export button
if data['trades'] or data['locates']:
    st.subheader("Export Report")
    
    if st.button("Generate PDF Report"):
        try:
            pdf_bytes = create_dashboard_pdf(data)
            
            # Create download button
            pdf_filename = f"trading_dashboard_{datetime.now().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf"
            )
            st.success("PDF report generated successfully!")
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")

if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.write("Trading Dashboard v1.0")
    st.sidebar.write("© 2024 All rights reserved")
