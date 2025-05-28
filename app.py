import streamlit as st
import numpy as np
import pandas as pd
from generate_dat import write_dat_file
import os
from amplpy import AMPL, modules
os.environ["AMPL_LICENSE"] = st.secrets["AMPL_LICENSE"]
modules.activate(os.environ["AMPL_LICENSE"])
def run_model(mod_file, model_type, years, k, min_prod, tighten, demand_growth, cost_df, Cap_base, E_base, Size, base_demand, penalty, s, farm_ids):
    ampl = AMPL()
    PN_series, theta_series, trade_series, q_series = [], [], [], []
    excess_series, unused_series = [], []
    available_years = sorted(cost_df["Year"].unique())
    
    for t, year in enumerate(available_years[:years]):
        R_scalar = cost_df[cost_df["Year"] == year]["Total_Revenue_per_day (€)"].iloc[0] * 365
        C_scalar = cost_df[cost_df["Year"] == year]["Operational_Cost_per_day (€)"].iloc[0] * 365
        Cap = {f: Cap_base[f] * ((1 - tighten) ** t) for f in farm_ids}
        E = {f: E_base[f] for f in farm_ids}
        D = int(base_demand * ((1 + demand_growth) ** t))
        dat_path = f"data_{mod_file}_{model_type}_{year}.dat"
        write_dat_file(k, min_prod, D, R_scalar, C_scalar, Cap, E, Size, penalty, s, dat_path, model_type)

        ampl.reset()
        ampl.read(mod_file)
        ampl.read_data(dat_path)
        ampl.set_option("solver", "knitro")
        ampl.solve()

        if model_type == "trading":
            PN = ampl.get_variable("PN").value()
            theta = ampl.get_variable("theta").get_values().to_list()
            q = ampl.get_variable("q").get_values().to_dict()
            x = ampl.get_variable("x").get_values().to_dict() 
            avg_theta = np.mean([v for _, v in theta]) if theta else 0
            total_trade = sum(x.values()) if x else 0
            avg_q = np.mean(list(q.values())) if q else 0

            PN_series.append(PN)
            theta_series.append(avg_theta)
            trade_series.append(total_trade / len(farm_ids))
            q_series.append(avg_q)


        elif model_type == "subsidy":
                    excess = ampl.get_variable("excess").get_values().to_dict()
                    unused = ampl.get_variable("unused").get_values().to_dict()

                    # Net reward/penalty (for display as "PN")
                    net_value = sum(s * unused[farm] - penalty * excess[farm] for farm in unused)
                    avg_balance = (sum(unused.values()) - sum(excess.values())) / len(unused)

                    PN_series.append(net_value)
                    trade_series.append(avg_balance)  # Interpreted like "net credit position"
                    excess_series.append(excess)
                    unused_series.append(unused)

            # Add additional values for subsidy output
        if model_type == "subsidy":
                return PN_series, theta_series, trade_series, q_series, excess_series, unused_series
        else:
                return PN_series, theta_series, trade_series, q_series
        # avg_theta = np.mean([v for _, v in theta]) if theta else 0
        # total_trade = sum(x.values()) if x else 0
        # avg_q = np.mean(list(q.values())) if q else 0

        # PN_series.append(PN)
        # theta_series.append(avg_theta)
        # trade_series.append(total_trade / len(farm_ids))
        # q_series.append(avg_q)

    return PN_series, theta_series, trade_series, q_series


st.title("Water Credit Market Simulator")

# Sliders for user input
k = st.slider("Abatement cost (k)", 0.01, 1.0, 0.1)
min_prod = st.slider("Minimum production factor", 1, 20, 10)
tighten = st.slider("Cap tightening rate per year (%)", 0, 20, 5) / 100
demand_growth = st.slider("Demand growth rate per year (%)", 0, 20, 5) / 100
E_mean = st.slider("Average emission rate per unit (E)", 10.0, 40.0, 30.0)
E_sd = st.slider("Emission variation (std dev)", 0.0, 20.0, 10.0)
num_farms = 5 
cap_per_hectare = st.slider("Cap per hectare (kg N/ha)", 50, 400, 200)
size_mean = st.slider("Average farm size (hectares)", 5, 100, 15)
size_sd = st.slider("Size variability (std dev)", 0, 20, 5)
base_demand = st.slider("Base total market demand (D)", min_value=500, max_value=1000, value=750, step=10)
penalty = st.slider("Penalty for water pollution", min_value=1, max_value=50, value=1, step=10)
s = st.slider("Subsidy for water pollution", min_value=1, max_value=50, value=1, step=10)
# Load historical R and C data
cost_df = pd.read_csv("total_cost_revenue_data.csv")
farm_ids = [f"F{i+1}" for i in range(num_farms)]
Size = {f: max(1, int(np.random.normal(size_mean, size_sd))) for f in farm_ids}
Cap_base = {f: Size[f] * cap_per_hectare for f in farm_ids}
E_base = {f: round(np.random.normal(E_mean, E_sd), 2) for f in farm_ids}
PN_series = []
theta_series = []
trade_series = []
q_series = []
available_years = sorted(cost_df["Year"].unique())

# Model files
mod_trading = "kkt_equilibrium_model.mod"
mod_subsidy = "no_trading_kkt_equilibrium_model.mod"

col1, col2 = st.columns(2)

with col1:
    st.subheader("Trading Model")
    PN_t, theta_t, trade_t, q_t = run_model(
        mod_file=mod_trading,
        years=len(available_years),
        E_base=E_base,
        tighten = tighten,
        demand_growth = demand_growth,
        cost_df = cost_df,
        Cap_base = Cap_base, 
        Size=Size,
        k=k,
        base_demand = base_demand,
        penalty = penalty,
        s = s,
        min_prod=min_prod,
        model_type = "trading", 
        farm_ids=farm_ids
    )
    st.subheader("Water Credit Price (PN)")
    st.line_chart(pd.DataFrame({"PN": PN_t}, index=available_years))

    st.subheader("Average Emission Reduction (θ)")
    st.line_chart(pd.DataFrame({"θ": theta_t}, index=available_years))

    st.subheader("Average Water Credit Trade per Farm")
    st.line_chart(pd.DataFrame({"Avg Trade per Farm": trade_t}, index=available_years))

    st.subheader("Average Production per Farm")
    st.line_chart(pd.DataFrame({"Avg Production per Farm": q_t}, index=available_years))

with col2:
    st.subheader(" Subsidy/Penalty Model")
    PN_s, theta_s, trade_s, q_s  = run_model(
        mod_file=mod_subsidy,
        years = len(available_years),
        E_base=E_base,
        tighten = tighten,
        demand_growth = demand_growth,
        cost_df = cost_df,
        Cap_base = Cap_base, 
        Size=Size,
        k=k,
        base_demand = base_demand,
        penalty = penalty,
        s = s,
        min_prod=min_prod,
        model_type = "subsidy", 
        farm_ids=farm_ids
    )
    st.subheader("Water Credit Price (PN)")
    st.line_chart(pd.DataFrame({"PN": PN_s}, index=available_years))

    st.subheader("Average Emission Reduction (θ)")
    st.line_chart(pd.DataFrame({"θ": theta_s}, index=available_years))

    st.subheader("Average Water Credit Trade per Farm")
    st.line_chart(pd.DataFrame({"Avg Trade per Farm": trade_s}, index=available_years))

    st.subheader("Average Production per Farm")
    st.line_chart(pd.DataFrame({"Avg Production per Farm": q_s}, index=available_years))
