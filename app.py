import streamlit as st
import numpy as np
import pandas as pd
from generate_dat import write_dat_file
import os
import pandas as pd
from amplpy import AMPL, modules
os.environ["AMPL_LICENSE"] = st.secrets["AMPL_LICENSE"]
modules.activate(os.environ["AMPL_LICENSE"])
def run_model(mod_file, model_type, years, k, min_prod, max_prod,tighten, cost_df, Cap_base, E_base, Size, credit_price, farm_ids):
    ampl = AMPL()
    PN_series, theta_series, trade_series, q_series = [], [], [], []
    available_years = sorted(cost_df["Year"].unique())
    
    for t, year in enumerate(available_years[:years]):
        R_scalar = cost_df[cost_df["Year"] == year]["Total_Revenue_per_day (€)"].iloc[0] * 365
        C_scalar = cost_df[cost_df["Year"] == year]["Operational_Cost_per_day (€)"].iloc[0] * 365
        Cap = {f: Cap_base[f] * ((1 - tighten) ** t) for f in farm_ids}
        E = {f: E_base[f] for f in farm_ids}
        dat_path = f"data_{mod_file}_{model_type}_{year}.dat"
        write_dat_file(k, min_prod, max_prod, R_scalar, C_scalar, Cap, E, Size, credit_price, dat_path, model_type)
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
            
            # Extract all farm IDs from the tuple keys of x
            farms = sorted(set(f for pair in x.keys() for f in pair))

            # Initialize a DataFrame with zeros
            trade_matrix = pd.DataFrame(0.0, index=farms, columns=farms)

            # Fill in the trades
            for (seller, buyer), value in x.items():
                trade_matrix.loc[seller, buyer] = value

            # # Display in Streamlit
            # st.subheader("Trade Matrix (Farm-to-Farm)")
            # st.dataframe(trade_matrix.style.format("{:.2f}"))

            # st.write(f"Year: {year}")
            # st.write(f"Cap: {Cap}")   
            # st.write(f"Revenue: {R}")   
            # st.write(f"Cost: {C}") 
            # st.write(f"K: {k}") 
            # st.write("θ (theta):", theta)
            # st.write("q (production):", q)
            # st.write("PN:", PN)

        elif model_type == "subsidy":
                    delta = ampl.get_variable("delta").get_values().to_dict()
                    
                    # Net reward/penalty (for display as "PN")
                    u = ampl.get_parameter("u").value()
                    avg_balance = sum(delta.values()) / len(delta) if delta else 0
                    theta = ampl.get_variable("theta").get_values().to_list()
                    avg_theta = np.mean([v for _, v in theta]) if theta else 0
                    q = ampl.get_variable("q").get_values().to_dict()
                    avg_q = np.mean(list(q.values())) if q else 0
                    PN_series.append(u)
                    theta_series.append(avg_theta)
                    trade_series.append(avg_balance)  # Interpreted like "net credit position"
                    q_series.append(avg_q)
                    # st.write(f"Year: {year}")
                    # st.write("θ (theta):", theta)
                    # st.write("q (production):", q)
                    # st.write("excess N:", excess)
                    # st.write("unused N:", unused)

            # Add additional values for subsidy output
    if model_type == "subsidy":
                return PN_series, theta_series, trade_series, q_series
    else:
                return PN_series, theta_series, trade_series, q_series
        # avg_theta = np.mean([v for _, v in theta]) if theta else 0
        # total_trade = sum(x.values()) if x else 0
        # avg_q = np.mean(list(q.values())) if q else 0

        # PN_series.append(PN)
        # theta_series.append(avg_theta)
        # trade_series.append(total_trade / len(farm_ids))
        # q_series.append(avg_q)

    # return PN_series, theta_series, trade_series, q_series


st.title("Water Credit Market Simulator")

# Intro paragraph
st.markdown("""
This tool simulates two types of water credit systems for cattle farms:

- A market-based system, where farms can trade water credits freely. The water credit price is determined by market equilibrium.
- A government-regulated system, where the credit price is fixed by policymakers.

The model supports simulations with 5 to 20 farms, each with different emission levels and farm sizes. It calculates:

- Optimal production levels and emission reductions for each farm over a 5-year period.
- For the market-based system:
  - The equilibrium water credit price
  - The amount of water credit traded by farms
- For the government-regulated system:
  - How much credit each farm buys or sells to meet nitrogen cap requirements

Use the inputs below to define farm characteristics and policy parameters to start the simulation.
""")


# Sliders for user input
st.subheader("Production Constraints")
min_prod = st.slider("Minimum production (cows/ha)", 1, 10, 1,help="This represents the minimum requirement amount of cows per hectare. It prevents people from only selling water credit without producing.")
max_prod = st.slider("Maximum production factor(cows/ha)", 10, 40, 20,help="This represents the maximum allowed amoutn of cows per hectare. It prevents the model from assigning unreasonably high production values.")

st.subheader("Emissions for each farm")
E_mean = st.slider("Average nitrogen emission (kg N/cow/year)", 10.0, 40.0, 30.0,help="This represents the average nitrogen emission per cow per year across all simulated farms.")
E_sd = st.slider("Nitrogen emission variation (kg N/cow/year)", 0.0, 20.0, 10.0, help="This represents the standerd deviation of nitrogen emission per cow per year across all simulated farms.")

st.subheader("Emissions cap")
cap_per_hectare = st.slider("Cap per hectare (kg N/ha)", 50, 400, 250, help="This represents the maximum amount of nitrogen emission allowed per hectare. If a farm's emissions exceed this cap, it must purchase water credits. If emissions are below the cap, the farm can sell excess credits.")
tighten = st.slider("Cap tightening rate per year (%)", 0, 20, 5,help="This defines how much the nitrogen emission cap decreases each year. Set a higher value to simulate stricter environmental policies over time. Set to 0 for a constant cap.") / 100
st.subheader("Abatement cost")
k = st.slider("Abatement cost (€/percent of emission reduction/year)", 1.0, 20.0, 10.0,help="This represents the cost of reducing emissions through adapting sustainable farming practices. The abatement cost grows quadratically, which means that the more you reduce your emission with sustainable farming practice, the more expensive it gets.")


st.subheader("Farm size and quantity")
size_mean = st.slider("Average farm size (ha)", 5, 100, 15)
size_sd = st.slider("Size variation (ha)", 0, 20, 5)
num_farms = st.slider("Number of farms", 5, 20, 10)
credit_price = st.slider("Credit price (only for goverment controled system)", min_value=1.0, max_value=10.0, value=7.0, step=1.0)
# num_farms = 10 
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
        cost_df = cost_df,
        Cap_base = Cap_base, 
        Size=Size,
        k=k,
        credit_price= credit_price,
        min_prod=min_prod,
        max_prod=max_prod,
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
        cost_df = cost_df,
        Cap_base = Cap_base, 
        Size=Size,
        k=k,
        credit_price= credit_price,
        min_prod=min_prod,
        max_prod=max_prod,
        model_type = "subsidy", 
        farm_ids=farm_ids
    )
    st.subheader("Total earned subsidy/ paid fine")
    st.line_chart(pd.DataFrame({"PN": PN_s}, index=available_years))

    st.subheader("Average Emission Reduction (θ)")
    st.line_chart(pd.DataFrame({"θ": theta_s}, index=available_years))

    st.subheader("Average Water Credit Trade per Farm")
    st.line_chart(pd.DataFrame({"Avg Trade per Farm": trade_s}, index=available_years))

    st.subheader("Average Production per Farm")
    st.line_chart(pd.DataFrame({"Avg Production per Farm": q_s}, index=available_years))
