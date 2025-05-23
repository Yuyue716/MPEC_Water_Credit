import streamlit as st
import numpy as np
import pandas as pd
import subprocess
import re
from generate_dat import write_dat_file
from results_parser import parse_results

st.title("Water Credit Market Simulator")

# Sliders for user input
k = st.slider("Abatement cost (k)", 0.01, 1.0, 0.1)
min_prod = st.slider("Minimum production factor", 1, 20, 10)
tighten = st.slider("Cap tightening rate per year (%)", 0, 20, 5) / 100
demand_growth = st.slider("Demand growth rate per year (%)", 0, 20, 5) / 100
years = st.slider("Years to simulate", 1, 10, 5)
E_mean = st.slider("Average emission rate per unit (E)", 2.0, 25.0, 12.0)
E_sd = st.slider("Emission variation (std dev)", 0.0, 10.0, 2.0)
num_farms = 5 
cap_per_hectare = st.slider("Cap per hectare (kg N/ha)", 50, 400, 200)
size_mean = st.slider("Average farm size (hectares)", 5, 50, 15)
size_sd = st.slider("Size variability (std dev)", 0, 20, 5)
base_demand = st.slider("Base total market demand (D)", min_value=1000, max_value=10000, value=5000, step=10)


# Load historical R and C data
cost_df = pd.read_csv("total_cow_revenue_model_2025_2029.csv")
farm_ids = [f"F{i+1}" for i in range(num_farms)]
Size = {f: max(1, int(np.random.normal(size_mean, size_sd))) for f in farm_ids}
Cap_base = {f: Size[f] * cap_per_hectare for f in farm_ids}
E_base = {f: round(np.random.normal(E_mean, E_sd), 2) for f in farm_ids}
PN_series = []
theta_series = []
trade_series = []
q_series = []
available_years = sorted(cost_df["Year"].unique())

for t, year in enumerate(available_years):
    R_scalar = cost_df[cost_df["Year"] == year]["Total_Revenue_per_day (€)"].iloc[0] * 365
    C_scalar = cost_df[cost_df["Year"] == year]["Operational_Cost_per_day (€)"].iloc[0] * 365
    Cap = {f: Cap_base[f] * ((1 - tighten) ** t) for f in farm_ids}
    E = {f: E_base[f] for f in farm_ids}
    D = int(base_demand * ((1 + demand_growth) ** t))
    dat_path = f"data_{year}.dat"
    write_dat_file(k, min_prod, D, R_scalar, C_scalar, Cap, E, Size, dat_path)

    with open("ampl_script.run", "w") as f:
        f.write(f"""model kkt_equilibrium_model.mod;
    data {dat_path};
    option solver conopt;
    solve;
    option display_1col 1;
    display PN, theta, x, q;
    """)

    subprocess.run(["ampl", "ampl_script.run"], stdout=open("ampl_output.txt", "w"))

    PN, avg_theta, total_trade, avg_q = parse_results("ampl_output.txt")
    PN_series.append(PN)
    theta_series.append(avg_theta)
    trade_series.append(total_trade / len(farm_ids))
    q_series.append(avg_q)

# Display results
st.subheader("Water Credit Price (PN)")
st.line_chart(pd.DataFrame({"PN": PN_series}, index=available_years))

st.subheader("Average Emission Reduction (θ)")
st.line_chart(pd.DataFrame({"θ": theta_series}, index=available_years))

st.subheader("Average Water Credit Trade per Farm")
st.line_chart(pd.DataFrame({"Avg Trade per Farm": trade_series}, index=available_years))

st.subheader("Average Production per Farm")
st.line_chart(pd.DataFrame({"Avg Production per Farm": q_series}, index=available_years))
