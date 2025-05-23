import re

def parse_results(filename):
    with open(filename) as f:
        text = f.read()
    
    pn_match = re.search(r"PN = ([\d\.eE+-]+)", text)

    theta_block = re.search(r"theta \[\*\] :=(.*?);", text, re.DOTALL)
    theta_vals = []

    if theta_block:
        nums = [float(m) for m in re.findall(r"[\d\.eE+-]+", theta_block.group(1))]
        theta_vals = nums[1::2]  
        print("DEBUG: Extracted theta values (cleaned):", theta_vals)

    x_block = re.search(r"x \[\*,\*\]\s*:.*?\n(.*?);", text, re.DOTALL)
    trade_vals = []


    if x_block:
        lines = x_block.group(1).strip().splitlines()
        if lines:
            for line in lines[1:]:
                tokens = line.strip().split()
                values = [float(tok) for tok in tokens[1:] if re.match(r"[\d\.eE+-]+", tok)]
                trade_vals.extend(values)
        print("DEBUG: Extracted trade values:", trade_vals)

    if not x_block:
        print("DEBUG: x_block not found in AMPL output.")

    q_block = re.search(r"q \[\*\] :=(.*?);", text, re.DOTALL)
    q_vals = []
    if q_block:
        nums = [float(m) for m in re.findall(r"[\d\.eE+-]+", q_block.group(1))]
        q_vals = nums[1::2]  
        print("DEBUG: Extracted q values:", q_vals)


    PN = float(pn_match.group(1)) if pn_match else 0.0
    avg_theta = sum(theta_vals) / len(theta_vals) if theta_vals else 0.0
    total_trade = sum(trade_vals) if trade_vals else 0.0
    avg_q = sum(q_vals) / len(q_vals) if q_vals else 0.0
    return PN, avg_theta, total_trade, avg_q
