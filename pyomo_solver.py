from pyomo.environ import *
from pyomo.mpec import Complementarity, complements

def solve_model_pyomo(k, min_prod, D, R, C, Cap, E, Size):
    model = ConcreteModel()

    model.I = Set(initialize=Cap.keys())
    model.J = model.I

    model.R = Param(initialize=R)
    model.C = Param(initialize=C)
    model.D = Param(initialize=D)
    model.k = Param(initialize=k)
    model.min_prod = Param(initialize=min_prod)

    model.Cap = Param(model.I, initialize=Cap)
    model.E = Param(model.I, initialize=E)
    model.Size = Param(model.I, initialize=Size)

    model.q = Var(model.I, domain=NonNegativeReals)
    model.theta = Var(model.I, bounds=(0, 1))
    model.x = Var(model.I, model.J, domain=NonNegativeReals)
    model.PN = Var(domain=NonNegativeReals)

    model.lambda_ = Var(model.I, domain=NonNegativeReals)
    model.mu = Var(model.I, domain=NonNegativeReals)
    model.gamma = Var(model.I, domain=NonNegativeReals)
    model.v = Var(model.J, model.I, domain=NonNegativeReals)
    model.v_s = Var(model.I, model.J, domain=NonNegativeReals)

    def net_credit_rule(m, i):
        return sum(m.x[j, i] for j in m.J if j != i) - sum(m.x[i, j] for j in m.J if j != i)
    model.net_credit = Expression(model.I, rule=net_credit_rule)

    def nitrogen_balance(m, i):
        return m.Cap[i] + m.net_credit[i] - m.q[i] * m.E[i] * (1 - m.theta[i]) >= 0
    model.nitrogen_balance = Constraint(model.I, rule=nitrogen_balance)

    def kkt_theta(m, i):
        return complements(0 <= m.theta[i], -m.lambda_[i] * m.q[i] * m.E[i] + 2 * m.k * m.theta[i] + m.mu[i] - m.gamma[i])
    model.kkt_theta = Complementarity(model.I, rule=kkt_theta)

    def kkt_q(m, i):
        return m.R - m.C - m.lambda_[i] * m.E[i] * (1 - m.theta[i]) == 0
    model.kkt_q = Constraint(model.I, rule=kkt_q)

    def kkt_x(m, j, i):
        if i == j: return Constraint.Skip
        return m.lambda_[j] - m.PN - m.v[j, i] == 0
    model.kkt_x = Constraint(model.I, model.J, rule=kkt_x)

    def comp_x(m, j, i):
        if i == j: return Constraint.Skip
        return complements(0 <= m.x[i, j], m.lambda_[j] - m.PN)
    model.comp_x = Complementarity(model.I, model.J, rule=comp_x)

    def kkt_x_seller(m, i, j):
        if i == j: return Constraint.Skip
        return m.PN - m.lambda_[i] - m.v_s[i, j] == 0
    model.kkt_x_seller = Constraint(model.I, model.J, rule=kkt_x_seller)

    def comp_x_seller(m, i, j):
        if i == j: return Constraint.Skip
        return complements(0 <= m.x[i, j], m.PN - m.lambda_[i])
    model.comp_x_seller = Complementarity(model.I, model.J, rule=comp_x_seller)

    def comp_nitrogen(m, i):
        return complements(0 <= m.lambda_[i], m.Cap[i] + m.net_credit[i] - m.q[i] * m.E[i] * (1 - m.theta[i]))
    model.comp_nitrogen = Complementarity(model.I, rule=comp_nitrogen)

    def no_trade_without_prod(m, i):
        return sum(m.x[i, j] for j in m.J if j != i) <= m.q[i] * m.E[i]
    model.no_trade = Constraint(model.I, rule=no_trade_without_prod)

    def min_production(m, i):
        return m.q[i] >= m.min_prod * m.Size[i]
    model.min_prod = Constraint(model.I, rule=min_production)

    def total_demand(m):
        return sum(m.q[i] for i in m.I) >= m.D
    model.total_demand = Constraint(rule=total_demand)

    model.obj = Objective(expr=sum(model.q[i] for i in model.I) - 1e-5 * sum(model.x[i, j] for i in model.I for j in model.J if i != j), sense=maximize)

    solver = SolverFactory('ipopt')  # or 'bonmin' or any available NLP solver
    results = solver.solve(model, tee=False)

    avg_theta = sum(value(model.theta[i]) for i in model.I) / len(model.I)
    avg_q = sum(value(model.q[i]) for i in model.I) / len(model.I)
    total_trade = sum(value(model.x[i, j]) for i in model.I for j in model.J if i != j)

    return value(model.PN), avg_theta, total_trade, avg_q
