def write_dat_file(k, min_prod, D, R, C, Cap, E, Size,penalty,s, filename, model_type):
    with open(filename, "w") as f:
        farm_ids = list(Size.keys())  
        f.write("set I := " + " ".join(farm_ids) + ";\n\n")
        if model_type == "trading":
            f.write("set J := " + " ".join(farm_ids) + ";\n\n")
        # Scalars
        f.write(f"param k := {k};\n")
        f.write(f"param min_prod_factor := {min_prod};\n")
        f.write(f"param D := {D};\n")
        f.write(f"param R := {R};\n")
        f.write(f"param C := {C};\n")
        if model_type == "subsidy":
            f.write(f"param f := {penalty};\n\n")
            f.write(f"param s := {s};\n\n")
        for param, data in [("Cap", Cap), ("E", E), ("Size", Size)]:
            f.write(f"param {param} :=\n")
            for i in data:
                f.write(f"  {i} {data[i]}\n")
            f.write(";\n\n")
