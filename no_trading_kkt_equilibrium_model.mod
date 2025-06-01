set I;  # Set of farms

# Parameters
param R;                      # Revenue per unit of production
param C;                      # Cost per unit of production
param D;                      # Total market demand (optional)
param k;                      # Abatement cost coefficient
param u;                      # Unit price for both fine and subsidy
param Cap {I};                # Nitrogen cap per farm
param E {I};                  # Emission rate per unit of production
param Size {I};               # Farm size
param min_prod_factor;        # Minimum production factor
param max_prod_factor;        # Maximum production factor

# Decision variables
var q {I} >= 0;
var delta {I} ; # Net difference from cap (positive = unused, negative = excess)

var theta {I} >= 0, <= 100;     # Emission reduction level (0-100%)

maximize total_profit:
    sum {i in I} (
        R * q[i]
      - C * q[i]
      - k * theta[i]^2
      + u * delta[i]
    );
 

# Constraints
subject to 
    nitrogen_balance {i in I}:  q[i] * E[i] * (1 - theta[i]/100) + delta[i] = Cap[i];

    min_production {i in I}:    q[i] >= min_prod_factor * Size[i];

    production_upper_bound {i in I}:   q[i] <= max_prod_factor * Size[i];
