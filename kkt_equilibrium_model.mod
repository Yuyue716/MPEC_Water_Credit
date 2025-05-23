# Sets
set I;                        # Set of farms
set J within I;               # Potential trading partners

# Parameters
param R;                      # Revenue per unit of production
param C;                      # Cost per unit of production
param D;                      # Total market demand  
param k;                      # Cost coefficient for emission reduction
param E {I};                  # Emissions per unit of production 
param Cap {I};                # Nitrogen cap per farm
param Size {I};               # Farm size  
param min_prod_factor;        # Minimum production factor



# Decision Variables
var q {I} >= 0;               # Production quantity
var theta {I} >= 0, <= 1;     # Emission reduction level
var x {I, J} >= 0;            # Credits sent from i to j (x[i,j])
var PN >= 0;                  # Market price for nitrogen credits

# Dual Variables (for KKT conditions)
var lambda {I} >= 0;          # Dual for nitrogen constraint
var mu {I} >= 0;              # Dual for theta[i] ≥ 0
var gamma {I} >= 0;           # Dual for theta[i] ≤ 1
var v {J, I} >= 0;            # Dual for x[i,j] ≥ 0 (buyer side)
var v_s {I, J} >= 0;          # Dual for x[i,j] ≥ 0 (seller side)


# Net credit brought
var net_credit {i in I} = sum {j in J: j != i} x[j,i] - sum {j in J: j != i} x[i,j];

<!-- # Profit Objective per farm
maximize total_profit:
  sum {i in I} (
    R * q[i] - C * q[i] - k * theta[i]^2 + PN * sum {j in J: j != i} (x[i,j] - x[j,i])
  );


# Nitrogen Constraint 
subject to nitrogen_balance {i in I}:
    Cap[i] + net_credit[i] - q[i] * E[i] * (1 - theta[i]) >= 0; -->

# Complementarity condition (dual feasibility and stationarity)
subject to KKT_theta {i in I}:
    -lambda[i] * q[i] * E[i] + 2 * k * theta[i] + mu[i] - gamma[i] = 0;

subject to comp_theta_lb {i in I}:
    mu[i] * theta[i] = 0;

subject to comp_theta_ub {i in I}:
    gamma[i] * (1 - theta[i]) = 0;

subject to KKT_q {i in I}:
    R - C - lambda[i] * E[i] * (1 - theta[i]) = 0;

subject to KKT_x {j in I, i in J: i != j}:  # Buyer-side KKT for trading
    lambda[j] - PN - v[j,i] = 0;

subject to comp_x {j in I, i in J: i != j}:
    x[i,j] * (lambda[j] - PN) = 0;

subject to KKT_x_seller {i in I, j in J: i != j}: # Seller-side KKT for trading
    PN - lambda[i] - v_s[i,j] = 0;

subject to comp_x_seller {i in I, j in J: i != j}:
    x[i,j] * (PN - lambda[i]) = 0;

subject to comp_nitrogen {i in I}:
    lambda[i] * (Cap[i] + net_credit[i] - q[i] * E[i] * (1 - theta[i])) = 0;

subject to no_credit_sales_without_production {i in I}:
    sum {j in J: j != i} x[i,j] <= q[i] * E[i];

subject to min_production {i in I}:
    q[i] >= min_prod_factor * Size[i];

subject to total_demand:
    sum {i in I} q[i] >= D;

# Objective
maximize total_output: sum {i in I} q[i] - 1e-5 * sum {i in I, j in J: i != j} x[i,j];
