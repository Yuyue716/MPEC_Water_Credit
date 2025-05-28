set I;

# Parameters
param R;                      # Revenue per unit of production
param C;                      # Cost per unit of production
param D;                      # Total market demand (if needed)
param k;                      # Abatement cost coefficient
param f;                      # Fine per unit of excess nitrogen
param s;                      # Subsidy per unit of unused nitrogen allowance
param Cap {I};                # Nitrogen cap per farm
param E {I};                  # Emission rate per unit of production
param Size {I};               # Farm size
param min_prod_factor;        # Minimum production factor

# Decision variables
var q {I} >= 0;               # Production quantity
var theta {I} >= 0, <= 1;     # Emission reduction level (0-100%)
var excess {I} >= 0;          # Emissions above the cap
var unused {I} >= 0;          # Emissions below the cap (eligible for subsidy)

# Constraints
subject to nitrogen_balance {i in I}:
    q[i] * E[i] * (1 - theta[i]) + unused[i] - excess[i] = Cap[i];

subject to min_production {i in I}:
    q[i] >= min_prod_factor * Size[i];

# Objective: maximize total profit
maximize total_profit:
    sum {i in I} (
        R * q[i]
      - C * q[i]
      - k * theta[i]^2
      - f * excess[i]
      + s * unused[i]
    );
