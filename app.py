import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu
import calendar
from datetime import datetime
import database as db  
import pandas as pd
import requests
from sklearn.linear_model import LinearRegression
import numpy as np
# Define income and expense categories
incomes = ["Salary", "Other income"]
expenses = ["Rent", "Utilities", "Groceries", "Car", "Other Expenses", "Saving"]

# Streamlit page configuration
page_title = "Income and Expense Tracker"
page_icon = ":money_with_wings:"
layout = "centered"

st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)

# Page title
st.title(page_title + " " + page_icon)

# Available years and months
years = [datetime.today().year, datetime.today().year + 1]
months = list(calendar.month_name[1:])

# Get all periods from Firestore
def get_all_periods():
    items = db.fetch_all_periods()  
    return items

# Sidebar menu for navigation
selected = st.sidebar.selectbox("Choose an option", ["data entry", "data visualisation", "AI Insights"])

# Data entry section
if selected == "data entry":
    st.header(f"Data Entry")

    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        col1.selectbox("Select month:", months, key="month")
        col2.selectbox("Select year:", years, key="year")

        # Income input fields
        with st.expander("Income"):
            for income in incomes:
                st.number_input(
                    f"{income}:", min_value=0, format="%i", step=10, key=f"income_{income}"
                )

        # Expense input fields
        with st.expander("Expenses:"):
            for expense in expenses:
                st.number_input(
                    f"{expense}:", min_value=0, format="%i", step=10, key=f"expense_{expense}"
                )

        # Budget Goal Input
        with st.expander("Budget Goal"):
            budget_goal = st.number_input(
                "Set your budget goal for this period:",
                min_value=0,
                format="%i",
                step=100,
                key="budget_goal"
            )

        # Comment input
        with st.expander("Comment:"):
            comment = st.text_area("", placeholder="Enter a comment here", key="comment")

        # Submit button
        submitted = st.form_submit_button("Save Data")

        if submitted:
            period = str(st.session_state["year"]) + "_" + str(st.session_state["month"])
            incomes_data = {income: st.session_state[f"income_{income}"] for income in incomes}
            expenses_data = {expense: st.session_state[f"expense_{expense}"] for expense in expenses}
            budget_goal_value = st.session_state["budget_goal"]
            db.insert_period(period, incomes_data, expenses_data, comment, budget_goal=budget_goal_value)
            st.success("Data saved successfully!")

# Helper Function to Fetch Exchange Rates
def get_exchange_rate(base_currency, target_currency):
    """
    Fetch the exchange rate from base_currency to target_currency.
    Returns 1 if target_currency is the same as base_currency or in case of failure.
    """
    if base_currency == target_currency:
        return 1
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"  # Use your preferred API here
        response = requests.get(url)
        if response.status_code == 200:
            rates = response.json().get("rates", {})
            return rates.get(target_currency, 1)
        else:
            st.error("Failed to fetch exchange rates.")
            return 1
    except Exception as e:
        st.error(f"An error occurred while fetching exchange rates: {e}")
        return 1

# Data Visualization Section
if selected == "data visualisation":
    st.header("Data Visualisation")

    with st.form("saved_period"):
        periods = get_all_periods()  # Fetch periods from the database
        period = st.selectbox("Select Period:", periods)
        currency = st.selectbox("Select Currency:", ["TND", "USD", "EUR"])  # Currency options

        submitted = st.form_submit_button("Plot Period")

        if submitted:
            # Fetch period data from the database
            period_data = db.get_period(period)
            comment = period_data.get("comment")
            expenses_data = period_data.get("expenses")
            incomes_data = period_data.get("incomes")
            budget_goal = period_data.get("budget_goal", 0)

            # Get exchange rate based on selected currency
            exchange_rate = get_exchange_rate("TND", currency)
            currency_symbol = {"TND": "TND", "USD": "$", "EUR": "€"}[currency]

            # Convert amounts to the selected currency
            total_income = sum(incomes_data.values()) * exchange_rate
            total_expense = sum(expenses_data.values()) * exchange_rate
            remaining_budget = total_income - total_expense
            converted_budget_goal = budget_goal * exchange_rate

            # Display Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Income", f"{total_income:.2f} {currency_symbol}")
            col2.metric("Total Expense", f"{total_expense:.2f} {currency_symbol}")
            col3.metric("Remaining Budget", f"{remaining_budget:.2f} {currency_symbol}")

            # Budget Goal Analysis
            st.subheader("Budget Goal Analysis")
            if budget_goal > 0:
                if total_expense <= budget_goal:
                    st.success(f"Great! You're within your budget of {converted_budget_goal:.2f} {currency_symbol}.")
                else:
                    st.error(f"You've exceeded your budget of {converted_budget_goal:.2f} {currency_symbol} by {(total_expense - converted_budget_goal):.2f} {currency_symbol}.")
                progress = min(total_expense / converted_budget_goal, 1.0)
                st.progress(progress)
            else:
                st.warning("No budget goal set for this period.")

            # Visualizations
            # Line Chart for Trends
            st.subheader("Income and Expense Trend Over Time")
            all_periods_data = []
            for p in periods:
                period_data = db.get_period(p)
                total_income = sum(period_data["incomes"].values()) * exchange_rate
                total_expense = sum(period_data["expenses"].values()) * exchange_rate
                all_periods_data.append({"period": p, "income": total_income, "expense": total_expense})

            df = pd.DataFrame(all_periods_data)
            line_fig = px.line(
                df,
                x="period",
                y=["income", "expense"],
                title="Income and Expense Trends",
                labels={"value": f"Amount ({currency_symbol})", "variable": "Category"}
            )
            st.plotly_chart(line_fig, use_container_width=True)

            # Sankey Diagram
            st.subheader("Income and Expense Breakdown")
            label = list(incomes_data.keys()) + ["Total Income"] + list(expenses_data.keys())
            source = list(range(len(incomes_data))) + [len(incomes_data)] * len(expenses_data)
            target = [len(incomes_data)] * len(incomes_data) + [
                label.index(exp) for exp in expenses_data.keys()
            ]
            value = (
                [v * exchange_rate for v in incomes_data.values()]
                + [v * exchange_rate for v in expenses_data.values()]
            )

            link = dict(source=source, target=target, value=value)
            node = dict(label=label, pad=20, thickness=30, color="#E694FF")
            sankey_fig = go.Figure(data=go.Sankey(link=link, node=node))
            sankey_fig.update_layout(margin=dict(l=0, r=0, t=5, b=5))
            st.plotly_chart(sankey_fig, use_container_width=True)

            # Bar Chart: Income vs Expense
            st.subheader("Income and Expenses per Category")
            income_values = [v * exchange_rate for v in incomes_data.values()]
            expense_values = [v * exchange_rate for v in expenses_data.values()]

            bar_fig = go.Figure()
            bar_fig.add_trace(go.Bar(x=list(incomes_data.keys()), y=income_values, name="Income", marker_color="green"))
            bar_fig.add_trace(go.Bar(x=list(expenses_data.keys()), y=expense_values, name="Expense", marker_color="red"))
            bar_fig.update_layout(
                barmode="stack",
                title="Income and Expenses by Category",
                xaxis_title="Category",
                yaxis_title=f"Amount ({currency_symbol})",
                showlegend=True
            )
            st.plotly_chart(bar_fig, use_container_width=True)

            # Display Comment
            st.text(f"Comment: {comment}")



# AI Insights Section
if selected == "AI Insights":
    st.header("AI-Powered Insights")

    # Fetch data from database
    periods = get_all_periods()
    all_periods_data = []
    for p in periods:
        period_data = db.get_period(p)
        total_income = sum(period_data["incomes"].values())
        total_expense = sum(period_data["expenses"].values())
        all_periods_data.append({"period": p, "income": total_income, "expense": total_expense})

    # Prepare data for predictions
    df = pd.DataFrame(all_periods_data)
    if len(df) >= 2:  # Ensure enough data points for training
        df["month"] = range(1, len(df) + 1)  # Encode periods as sequential numbers

        # Train a model for predicting expenses
        X = df[["month"]]  # Feature: month index
        y = df["expense"]  # Target: total expense
        model = LinearRegression()
        model.fit(X, y)

        # Predict next month's expense
        next_month = len(df) + 1
        predicted_expense = model.predict([[next_month]])[0]

        # Display predictions
        st.subheader("Expense Prediction")
        st.write(f"Based on your historical data, your predicted expense for the next period is approximately **{predicted_expense:.2f} TND**.")

        # Suggest savings goal
        avg_income = df["income"].mean()
        suggested_savings = max(0, avg_income - predicted_expense)
        st.subheader("Suggested Savings Goal")
        st.write(f"Consider setting a savings goal of **{suggested_savings:.2f} TND** for the next period based on your average income.")

        # Financial Health Score
        health_score = max(0, 100 - (predicted_expense / avg_income) * 100) if avg_income > 0 else 0
        st.subheader("Financial Health Score")
        st.write(f"Your financial health score is **{health_score:.2f}/100**.")

        # 1. Expense Prediction Chart (Line Chart)
        st.subheader("Expense Prediction Trend")
        df["predicted_expense"] = model.predict(X)
        expense_fig = go.Figure()
        expense_fig.add_trace(go.Scatter(x=df["month"], y=df["expense"], mode='lines', name='Actual Expense', line=dict(color='red')))
        expense_fig.add_trace(go.Scatter(x=[next_month], y=[predicted_expense], mode='markers+text', name='Predicted Expense', 
                                        marker=dict(color='blue', size=12), text=[f"Predicted: {predicted_expense:.2f}"], textposition='top center'))
        expense_fig.update_layout(title="Income and Expense Trend with Prediction", 
                                  xaxis_title="Month", yaxis_title="Expense (TND)", showlegend=True)
        st.plotly_chart(expense_fig)

        # 2. Income vs Expense Comparison (Bar Chart)
        st.subheader("Income vs Expense Comparison")
        income_expense_fig = go.Figure()
        income_expense_fig.add_trace(go.Bar(x=df["period"], y=df["income"], name="Income", marker_color='green'))
        income_expense_fig.add_trace(go.Bar(x=df["period"], y=df["expense"], name="Expense", marker_color='red'))
        income_expense_fig.update_layout(title="Income vs Expense per Period", barmode='group', 
                                        xaxis_title="Period", yaxis_title="Amount (TND)")
        st.plotly_chart(income_expense_fig)

        # 3. Savings Goal vs Predicted Expense (Bar Chart)
        st.subheader("Suggested Savings vs Predicted Expense")
        savings_expense_fig = go.Figure()
        savings_expense_fig.add_trace(go.Bar(x=["Suggested Savings", "Predicted Expense"], 
                                            y=[suggested_savings, predicted_expense], 
                                            marker_color=['blue', 'red']))
        savings_expense_fig.update_layout(title="Suggested Savings Goal vs Predicted Expense", 
                                          xaxis_title="Category", yaxis_title="Amount (TND)")
        st.plotly_chart(savings_expense_fig)

        # 4. Financial Health Score (Gauge Chart)
        st.subheader("Financial Health Score")
        health_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            title={'text': "Financial Health Score"},
            gauge={'axis': {'range': [0, 100]},
                   'bar': {'color': "darkblue"},
                   'steps': [
                       {'range': [0, 50], 'color': "red"},
                       {'range': [50, 80], 'color': "yellow"},
                       {'range': [80, 100], 'color': "green"}]
                   }))
        st.plotly_chart(health_fig)

    else:
        st.warning("Not enough data to generate AI insights. Please add more historical data.")