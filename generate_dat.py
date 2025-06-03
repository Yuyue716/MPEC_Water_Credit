def write_dat_file(k, min_prod, max_prod, R, C, Cap, E, Size,credit_price, filename, model_type):
    with open(filename, "w") as f:
        farm_ids = list(Size.keys())  
        f.write("set I := " + " ".join(farm_ids) + ";\n\n")
        if model_type == "trading":
            f.write("set J := " + " ".join(farm_ids) + ";\n\n")
        f.write(f"param k := {k};\n")
        f.write(f"param min_prod_factor := {min_prod};\n")
        f.write(f"param max_prod_factor := {max_prod};\n")
        f.write(f"param R := {R};\n")
        f.write(f"param C := {C};\n")
        if model_type == "subsidy":
            f.write(f"param u := {credit_price};\n\n")
        for param, data in [("Cap", Cap), ("E", E), ("Size", Size)]:
            f.write(f"param {param} :=\n")
            for i in data:
                f.write(f"  {i} {data[i]}\n")
            f.write(";\n\n")
