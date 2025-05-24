import streamlit as st
import numpy as np
import pandas as pd
from generate_dat import write_dat_file
from results_parser import parse_results
import os
from amplpy import AMPL, modules
os.environ["AMPL_LICENSE"] = st.secrets["AMPL_LICENSE"]
modules.activate(os.environ["AMPL_LICENSE"])
ampl = AMPL()

st.write("AMPL is ready!")

st.title("Water Credit Market Simulator")

# Sliders for user input
k = st.slider("Abatement cost (k)", 0.01, 1.0, 0.1)
min_prod = st.slider("Minimum production factor", 1, 20, 10)
tighten = st.slider("Cap tightening rate per year (%)", 0, 20, 5) / 100
demand_growth = st.slider("Demand growth rate per year (%)", 0, 20, 5) / 100
years = st.slider("Years to simulate", 1, 10, 5)
E_mean = st.slider("Average emission rate per unit (E)", 10.0, 40.0, 30.0)
E_sd = st.slider("Emission variation (std dev)", 0.0, 10.0, 2.0)
num_farms = 5 
cap_per_hectare = st.slider("Cap per hectare (kg N/ha)", 50, 400, 200)
size_mean = st.slider("Average farm size (hectares)", 5, 100, 15)
size_sd = st.slider("Size variability (std dev)", 0, 20, 5)
base_demand = st.slider("Base total market demand (D)", min_value=500, max_value=1000, value=750, step=10)


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
    ampl.reset()  
    ampl.read("kkt_equilibrium_model.mod")
    ampl.read_data(dat_path)
    ampl.set_option("solver", "knitro")
    ampl.solve()
    # Extract variables directly
    PN = ampl.get_variable("PN").value()
    theta = ampl.get_variable("theta").get_values().to_list()
    q = ampl.get_variable("q").get_values().to_dict()
    x = ampl.get_variable("x").get_values().to_dict()
    print(f"\n=== Year {year} ===")
    print("Production quantities (q):")
    for farm, val in q.items():
        print(f"Farm {farm}: {val}")

    print("\nCredit trades (x[i,j]):")
    for (i, j), val in x.items():
        if abs(val) > 1e-6:
            print(f"Farm {i} sent {val:.4f} credits to Farm {j}")

    print("\nCredit price (PN):")
    print(PN)
    avg_theta = np.mean([v for _, v in theta])
    total_trade = sum([v for _, v in x.items()])
    avg_q = np.mean([v for _, v in q.items()])
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
