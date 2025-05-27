set I;

param R;                     # Revenue per unit
param C;                     # Cost per unit
param k;                     # Abatement cost coefficient
param f;                     # Fine per unit of excess N
param Cap {I};               # Nitrogen cap
param E {I};                 # Emissions per unit production
param Size {I};
param min_prod_factor;

var q {I} >= 0;
var theta {I} >= 0, <= 1;
var excess {I} >= 0;   # nitrogen in excess of cap

# Constraint for excess
subject to nitrogen_excess {i in I}:
    excess[i] >= q[i] * E[i] * (1 - theta[i]) - Cap[i];

subject to min_production {i in I}:
    q[i] >= min_prod_factor * Size[i];

maximize total_profit:
    sum {i in I} (R * q[i] - C * q[i] - k * theta[i]^2 - f * excess[i]);
