# Sets
set I;                        # Set of farms
set J within I;               # Potential trading partners

# Parameters
param R;                      # Revenue per cow per year
param C;                      # Cost per cow per year
param k;                      # Cost coefficient for emission reduction
param E {I};                  # Emissions per cow per year 
param Cap {I};                # Emission cap per farm
param Size {I};               # Farm size  
param min_prod_factor;        # Minimum production factor
param max_prod_factor;        # Maximum production factor

# Decision Variables
var q {I} >= 0;               # Cow quantity
var theta {I} >= 0, <= 100;   # Emission reduction level
var x {I, J} >= 0;            # Credits sent from i to j 
var PN >= 0;                  # Market price for watercredits

# Dual Variables (for KKT conditions)
var lambda {I} >= 0;          # Dual for nitrogen constraint
var mu {I} >= 0;              # Dual for theta[i] ≥ 0
var gamma {I} >= 0;           # Dual for theta[i] ≤ 100


# Net credit brought
var net_credit {i in I} = sum {j in J: j != i} x[j,i] - sum {j in J: j != i} x[i,j];

# Profit Objective per farm
maximize profit:
    sum {i in I} (
        R * q[i] - C * q[i] - k * theta[i]^2 * q[i] + PN * sum {j in J: j != i} (x[i,j] - x[j,i])
    );


# Nitrogen Constraint 
subject to 
    nitrogen_balance {i in I}: Cap[i] + net_credit[i] - q[i] * E[i] * (1 - theta[i]/100) >= 0;

    KKT_theta_lb {i in I}: 0 <= 2 * k * theta[i]* q[i] + gamma[i] - lambda[i] * q[i] * E[i]/100 complements mu[i] >= 0;
    KKT_theta_ub {i in I}: 0 <= lambda[i] * q[i] * E[i]/100 - 2 * k * theta[i]* q[i] + mu[i] complements gamma[i] >= 0;

    KKT_q {i in I}:
    0 <= C - R + lambda[i] * E[i] * (1 - theta[i]/100) complements q[i] >= 0;

    KKT_x {i in I, j in J: i != j}:  0 <= lambda[j] - PN complements  x[i,j] >= 0;

    no_credit_sales_without_production {i in I}: sum {j in J: j != i} x[i,j] <= q[i] * E[i];

    min_production {i in I}: q[i] >= min_prod_factor * Size[i];

    credit_market_balance: sum {i in I} net_credit[i] = 0;
    production_upper_bound {i in I}:   q[i] <= max_prod_factor * Size[i];