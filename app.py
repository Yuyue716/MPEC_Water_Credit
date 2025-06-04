import streamlit as st
import numpy as np
import pandas as pd
from generate_dat import write_dat_file
import zipfile
from io import BytesIO
import os
import altair as alt
import pandas as pd
from amplpy import AMPL, modules

os.environ["AMPL_LICENSE"] = st.secrets["AMPL_LICENSE"]
modules.activate(os.environ["AMPL_LICENSE"])

# function to run the optimization model
def run_model(mod_file, model_type, years, k, min_prod, max_prod,tighten, cost_df, Cap_base, E_base, Size, credit_price_base, price_increase, farm_ids):
    ampl = AMPL()
    PN_series, theta_series, trade_series, q_series = [], [], [], []
    available_years = sorted(cost_df["Year"].unique())
    dat_files = [] 
    for t, year in enumerate(available_years[:years]):
        R_scalar = cost_df[cost_df["Year"] == year]["Total_Revenue_per_day (€)"].iloc[0] * 365
        C_scalar = cost_df[cost_df["Year"] == year]["Operational_Cost_per_day (€)"].iloc[0] * 365
        Cap = {f: Cap_base[f] * ((1 - tighten) ** t) for f in farm_ids}
        credit_price = credit_price_base * ((1 + price_increase) ** t)
        E = {f: E_base[f] for f in farm_ids}
        dat_path = f"data_{mod_file}_{model_type}_{year}.dat"
        write_dat_file(k, min_prod, max_prod, R_scalar, C_scalar, Cap, E, Size, credit_price, dat_path, model_type)
        dat_files.append(dat_path) 
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
                    trade_series.append(avg_balance) 
                    q_series.append(avg_q)

    result_df = pd.DataFrame({
        "Year": available_years[:years],
        "PN": PN_series,
        "theta": theta_series,
        "trade": trade_series,
        "q": q_series,
                    })
   
    return PN_series, theta_series, trade_series, q_series, dat_files, result_df


st.title("Watercredit System Simulator")

# Intro paragraph
st.markdown("""
This is a simulator that evaluate the financial and enviromental benefit of water credit systems for cattle farms. 

This tool simulates two types of Watercredit systems for cattle farms: a market-based system and a government-regulated system. In **the market-based system**, farms can trade Watercredits freely. The Watercredit price is determined by market equilibrium. In **the government-regulated system**, the credit price is fixed by policymakers.

The model supports simulations with **10 to 50 farms**, each with different emission levels and farm sizes. It calculates the **optimal production levels** and **emission reductions** for each farm over a 5-year period. For the market-based system, it also shows the **equilibrium Watercredit price** and the **amount of credit traded**. For the government-controlled system, it reports **how much credit each farm buys or sells** to meet nitrogen cap requirements.

Use the slider bar below to define farm characteristics and policy parameters to start the simulation!
""")


# Sliders for user input
st.subheader("Production Constraints")
min_prod = st.slider("Minimum production (cows/ha)", 1, 10, 1,help="This represents the minimum requirement amount of cows per hectare. It prevents people from only selling Watercredit without producing.")
max_prod = st.slider("Maximum production factor(cows/ha)", 10, 40, 20,help="This represents the maximum allowed amoutn of cows per hectare. It prevents the model from assigning unreasonably high production values.")

st.subheader("Nitrogen emissions for each farm")
E_mean = st.slider("Average nitrogen emission (kg N/cow/year)", 10.0, 40.0, 30.0,help="This represents the average nitrogen emission per cow per year across all simulated farms.")
E_sd = st.slider("Nitrogen emission variation (kg N/cow/year)", 0.0, 20.0, 10.0, help="This represents the standerd deviation of nitrogen emission per cow per year across all simulated farms.")

st.subheader("Nitrogen emissions cap")
cap_per_hectare = st.slider("Emission cap per hectare (kg N/ha)", 50, 400, 250, help="This represents the maximum amount of nitrogen emission allowed per hectare. If a farm's emissions exceed this cap, it must purchase water credits. If emissions are below the cap, the farm can sell excess credits.")
tighten = st.slider("Emission cap tightening rate per year (%)", 0, 20, 5,help="This defines how much the nitrogen emission cap decreases each year. Set a higher value to simulate stricter environmental policies over time. Set to 0 for a constant cap.") / 100
st.subheader("Abatement cost")
k = st.slider("Abatement cost (€/squared percent of emission reduction/cow/year)", 0.1, 1.0, 0.1,help="This represents the cost of reducing emissions through adapting sustainable farming practices. The abatement cost grows quadratically, which means that the more you reduce your emission with sustainable farming practice, the more expensive it gets.")


st.subheader("Farm size and quantity")
size_mean = st.slider("Average farm size (ha)", 5, 100, 15, help="This represents the average farm size across all simulated farms in hectares")
size_sd = st.slider("Size variation (ha)", 0, 20, 5, help="This represents the standard deviation of farm size across all simulated farms in hectares")
num_farms = st.slider("Number of farms", 10, 50, 10, help="Choose how many farms will be included in the simulation" )

st.subheader("Watercredit price(only for goverment-regulated system)")
credit_price_base = st.slider("Watercredit price (€)", min_value=1.0, max_value=10.0, value=7.0, step=1.0, help="This represent the fixed Watercredit price in the goverment-regulated system")
price_increase = st.slider("Watercredit price increase rate per year(€)", min_value=0.0, max_value=20.0, value=5.0, step=1.0, help="This defines how much the Watercredit price increase each year in the goverment-regulated system")/ 100

# Generate model data base on user input and cost revenue prediction result 
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

mod_trading = "kkt_equilibrium_model.mod"
mod_subsidy = "no_trading_kkt_equilibrium_model.mod"

# Function to make line charts
def alt_line_chart(data, y_col, y_title):
    df = pd.DataFrame({y_col: data}, index=available_years).reset_index()
    df.columns = ["Year", y_col]
    df["Year"] = df["Year"].astype(int)
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Year:Q", title="Year", axis=alt.Axis(format="d")),
        y=alt.Y(f"{y_col}:Q", title=y_title),
        tooltip=["Year", y_col]
    )
    return chart
col1, col2, col3 = st.columns([3, 1, 3])

with col1:
    st.subheader("Market-based System")
    st.markdown(" *In the market-based system, farms can trade water credits freely. The water credit price is determined by market equilibrium.*")
    PN_t, theta_t, trade_t, q_t, dat_files_t,  result_df_t = run_model(
        mod_file=mod_trading,
        years=len(available_years),
        E_base=E_base,
        tighten = tighten,
        cost_df = cost_df,
        Cap_base = Cap_base, 
        Size=Size,
        k=k,
        credit_price_base= credit_price_base,
        min_prod=min_prod,
        max_prod=max_prod,
        price_increase = price_increase,
        model_type = "trading", 
        farm_ids=farm_ids
    )
    st.markdown("### Watercredit Price")
    st.markdown(" *This chart shows the Watercredit price determined by the model based on the supply and demand balance.*")
    chart1 = alt_line_chart(PN_t, "PN", "euros(€)")
    st.altair_chart(chart1, use_container_width=True)

    st.markdown("### Average Percentage of Emission Reduced")
    st.markdown(" *This chart shows the average percentage of emission reduced across all simulated farms.*")
    chart2 = alt_line_chart(theta_t, "θ", "%")
    st.altair_chart(chart2, use_container_width=True)

    st.markdown("### Average Water Credit Trade per Farm")
    st.markdown(" *This chart shows the average number of credits traded per simulated farm, per year.*")
    chart3 = alt_line_chart(trade_t, "x", "number  of  Watercredit")
    st.altair_chart(chart3, use_container_width=True)

    st.markdown("### Average number of cows per Farm")
    st.markdown(" *This chart shows the average number of the optimal amount of cows per farm*")
    chart4 = alt_line_chart(q_t, "q", "number  of  cows")
    st.altair_chart(chart4, use_container_width=True)
with col2:
    st.write(    )


with col3:
    st.subheader("Government-regulated system")
    st.markdown(" *In the government-regulated system, the credit price is fixed by policymakers.*")
    PN_s, theta_s, trade_s, q_s,dat_files_s, result_df_s = run_model(
        mod_file=mod_subsidy,
        years = len(available_years),
        E_base=E_base,
        tighten = tighten,
        cost_df = cost_df,
        Cap_base = Cap_base, 
        Size=Size,
        k=k,
        credit_price_base= credit_price_base,
        price_increase = price_increase,
        min_prod=min_prod,
        max_prod=max_prod,
        model_type = "subsidy", 
        farm_ids=farm_ids
    )
    st.markdown("### Watercredit Price ")
    st.markdown(" *This chart shows the fixing Watercredit price determined for the goverment-controled system.*")
    chart5 = alt_line_chart(PN_s, "PN", "euros(€)")
    st.altair_chart(chart5, use_container_width=True)

    st.markdown("### Average Percentage of Emission Reduced")
    st.markdown(" *This chart shows the average percentage of emission reduced across all simulated farms.*")
    chart6 = alt_line_chart(theta_s, "θ", "%")
    st.altair_chart(chart6, use_container_width=True)

    st.markdown("### Average Watercredit bought/sold")
    st.markdown(" *This chart shows the average Watercredit bought or sold across all simulated farms.*")
    chart7 = alt_line_chart(trade_s, "x", "number  of  Watercredits")
    st.altair_chart(chart7, use_container_width=True)

    st.markdown("### Average number of cows per Farm")
    st.markdown(" *This chart shows the average number of the optimal amount of cows per farm*")
    chart8 = alt_line_chart(q_s, "q", "number  of  cows")
    st.altair_chart(chart8, use_container_width=True)


# add download button
all_dat_files = []

all_dat_files.extend(dat_files_t)
all_dat_files.extend(dat_files_s)

zip_buffer = BytesIO()
with zipfile.ZipFile(zip_buffer, "w") as zipf:
    for file in all_dat_files:
        zipf.write(file, arcname=os.path.basename(file))
zip_buffer.seek(0)
for file in all_dat_files:
    if os.path.exists(file):
        os.remove(file)

result_df_t["System"] = "Market"
result_df_s["System"] = "Subsidy"
combined_df = pd.concat([result_df_t, result_df_s], ignore_index=True)

csv_buffer = BytesIO()
combined_df.to_csv(csv_buffer, index=False)
csv_buffer.seek(0)

st.subheader("Download Simulation Results")
st.download_button(
    label="Download Raw Data Files",
    data=zip_buffer,
    file_name="simulation_dat_files.zip",
    mime="application/zip"
)

st.download_button(
    label="Download Simulation Result Summary ",
    data=csv_buffer,
    file_name="simulation_summary.csv",
    mime="text/csv"
)
