set I;  # Set of farms

# Parameters
param R;                      # Revenue per cow per year
param C;                      # Cost per cow per year
param k;                      # Cost coefficient for emission reduction
param u;                      # Watercredit price decided by the goverment
param Cap {I};                # Emission cap per farm
param E {I};                  # Emissions per cow per year 
param Size {I};               # Farm size
param min_prod_factor;        # Minimum production factor
param max_prod_factor;        # Maximum production factor

# Decision variables
var q {I} >= 0; # Cow quantity
var delta {I} ; # Watercredit bought/sold
var theta {I} >= 0, <= 100;     # Emission reduction level

maximize total_profit:
    sum {i in I} (
        R * q[i]
      - C * q[i]
      - k * theta[i]^2 * q[i] 
      + u * delta[i]
    );
 

# Constraints
subject to 
    nitrogen_balance {i in I}:  q[i] * E[i] * (1 - theta[i]/100) + delta[i] = Cap[i];

    min_production {i in I}:    q[i] >= min_prod_factor * Size[i];

    production_upper_bound {i in I}:   q[i] <= max_prod_factor * Size[i];
