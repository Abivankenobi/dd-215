import os
import sys
import subprocess
import json
import shutil
import itertools

def get_positive_int_range(prompt, start, end):
    """Safely get an integer input from the user within a range."""
    while True:
        try:
            val_str = input(prompt).strip()
            if not val_str:
                return start  # default
            val = int(val_str)
            if start <= val <= end:
                return val
            print(f"Error: Please enter a value between {start} and {end}.")
        except ValueError:
            print("Error: Please enter a valid integer.")

def get_comma_list(prompt):
    """Get a set of integers from a comma-separated string input."""
    while True:
        try:
            val_str = input(prompt).strip()
            if not val_str:
                return set()
            # Split and strip, ignoring empty inputs
            parts = [p.strip() for p in val_str.split(",") if p.strip()]
            vals = {int(p) for p in parts}
            return vals
        except ValueError:
            print("Error: Please enter comma-separated integers only.")

# Quine-McCluskey Logic Solver
def count_ones(binary_str):
    return binary_str.count('1')

def can_combine(term1, term2):
    """Two terms combine if they differ by exactly one position and have dashes in the same places."""
    diff_count = 0
    diff_idx = -1
    for i in range(len(term1)):
        if term1[i] != term2[i]:
            if term1[i] == '-' or term2[i] == '-':
                return False, -1
            diff_count += 1
            diff_idx = i
            if diff_count > 1:
                return False, -1
    return diff_count == 1, diff_idx

def run_qm_algorithm(num_vars, minterms, dont_cares):
    """
    Run Quine-McCluskey to find Prime Implicants.
    Returns: (pi_list, steps_trace)
    """
    # Initialize terms: dict of binary -> dict(binary, minterms, combined)
    all_inputs = minterms | dont_cares
    terms = {}
    for val in all_inputs:
        bin_str = bin(val)[2:].zfill(num_vars)
        terms[bin_str] = {
            "binary": bin_str,
            "minterms": {val},
            "combined": False
        }
    
    steps_trace = []
    current_pass = 1
    
    while True:
        # Group current terms by number of 1s
        groups = {}
        for bin_str, term_data in terms.items():
            ones = count_ones(bin_str)
            groups.setdefault(ones, []).append(term_data)
        
        steps_trace.append({
            "pass": current_pass,
            "groups": {k: [dict(t) for t in v] for k, v in groups.items()},
            "merges": []
        })
        
        # Combine terms between adjacent groups
        next_terms = {}
        combined_any = False
        
        keys = sorted(groups.keys())
        for idx in range(len(keys) - 1):
            g1_key = keys[idx]
            g2_key = keys[idx + 1]
            if g2_key - g1_key != 1:
                continue
            
            for t1 in groups[g1_key]:
                for t2 in groups[g2_key]:
                    ok, diff_idx = can_combine(t1["binary"], t2["binary"])
                    if ok:
                        # Combine
                        combined_any = True
                        t1["combined"] = True
                        t2["combined"] = True
                        
                        merged_bin = t1["binary"][:diff_idx] + "-" + t1["binary"][diff_idx+1:]
                        merged_mins = t1["minterms"] | t2["minterms"]
                        
                        next_terms.setdefault(merged_bin, {
                            "binary": merged_bin,
                            "minterms": merged_mins,
                            "combined": False
                        })
                        
                        steps_trace[-1]["merges"].append((t1["binary"], t2["binary"], merged_bin))
        
        # Collect Prime Implicants
        if not combined_any:
            break
            
        # Update terms for next pass
        terms = next_terms
        current_pass += 1
    
    # Trace back all terms across all passes to find all uncombined terms
    all_generated = []
    for step in steps_trace:
        for ones, terms_list in step["groups"].items():
            all_generated.extend(terms_list)
            
    # Mark combined flags globally
    combined_binaries = set()
    for step in steps_trace:
        for t1_bin, t2_bin, m_bin in step["merges"]:
            combined_binaries.add(t1_bin)
            combined_binaries.add(t2_bin)
            
    pis = []
    seen_pi_bin = set()
    for term in all_generated:
        if term["binary"] not in combined_binaries and term["binary"] not in seen_pi_bin:
            # Check if it covers at least one actual minterm
            if term["minterms"] & minterms:
                pis.append(term)
                seen_pi_bin.add(term["binary"])
                
    return pis, steps_trace

def solve_prime_implicant_chart(minterms, pis):
    """
    Use Petrick's/exhaustive search to find the minimum sum-of-products cover.
    Returns: (epis, chosen_pis_remaining)
    """
    if not minterms:
        return [], []
        
    # Build chart
    chart = {}
    for m in minterms:
        chart[m] = []
        for idx, pi in enumerate(pis):
            if m in pi["minterms"]:
                chart[m].append(idx)
                
    # 1. Find Essential Prime Implicants (EPIs)
    epi_indices = set()
    for m, pi_idxs in chart.items():
        if len(pi_idxs) == 1:
            epi_indices.add(pi_idxs[0])
            
    epis = [pis[idx] for idx in epi_indices]
    
    # 2. Find remaining minterms to cover
    covered_by_epis = set()
    for epi in epis:
        covered_by_epis |= epi["minterms"]
        
    uncovered_minterms = minterms - covered_by_epis
    
    if not uncovered_minterms:
        return epis, []
        
    # Remove EPIs and covered minterms from consideration
    remaining_pi_indices = [idx for idx in range(len(pis)) if idx not in epi_indices]
    if not remaining_pi_indices:
        return epis, []
        
    # Solve remaining cover using exhaustive search
    best_comb = []
    best_score = (999, 999)
    
    for r in range(1, len(remaining_pi_indices) + 1):
        for comb in itertools.combinations(remaining_pi_indices, r):
            # Check cover
            covered = set()
            for idx in comb:
                covered |= (pis[idx]["minterms"] & minterms)
                
            if uncovered_minterms.issubset(covered):
                # Calculate literal count score
                num_pis = len(comb)
                num_literals = 0
                for idx in comb:
                    binary = pis[idx]["binary"]
                    num_literals += len(binary) - binary.count('-')
                    
                score = (num_pis, num_literals)
                if score < best_score:
                    best_score = score
                    best_comb = comb
                    
        if best_comb:
            break
            
    chosen_pis_remaining = [pis[idx] for idx in best_comb]
    return epis, chosen_pis_remaining

def get_sop_text(binary, var_names):
    """Convert binary string like '1-01' into text representation like 'A C' D'."""
    term_parts = []
    for i, char in enumerate(binary):
        if char == '1':
            term_parts.append(var_names[i])
        elif char == '0':
            term_parts.append(f"{var_names[i]}'")
    if not term_parts:
        return "1"
    return "".join(term_parts)

# Input UI loop
def get_user_inputs():
    while True:
        print("\n" + "-"*40)
        print("  K-MAP SOLVER INPUT INTERFACE (2-6 VARS)")
        print("-"*40)
        
        # 1. Variables Count
        num_vars = get_positive_int_range("Enter number of variables (2 to 6) [Default: 4]: ", 2, 6)
        
        # 2. Variable Names
        default_names = ['A', 'B', 'C', 'D', 'E', 'F'][:num_vars]
        default_names_str = ", ".join(default_names)
        
        var_names = []
        while True:
            prompt = f"Enter variable names separated by commas (e.g. {default_names_str}) [Press Enter for default]: "
            names_input = input(prompt).strip()
            if not names_input:
                var_names = default_names
                break
            parts = [p.strip() for p in names_input.split(",") if p.strip()]
            if len(parts) != num_vars:
                print(f"Error: You must enter exactly {num_vars} names.")
                continue
            if len(set(parts)) != num_vars:
                print("Error: Variable names must be unique.")
                continue
            if any(len(p) > 3 for p in parts):
                print("Error: Keep names short (<= 3 characters) to avoid layout overlaps.")
                continue
            var_names = parts
            break
            
        # 3. Minterms
        minterms = set()
        max_val = (1 << num_vars) - 1
        while True:
            prompt = f"Enter minterms (comma-separated integers in range 0-{max_val}): "
            minterms = get_comma_list(prompt)
            if not minterms:
                print("Error: You must enter at least one minterm.")
                continue
            if any(m < 0 or m > max_val for m in minterms):
                invalid_mins = [m for m in minterms if m < 0 or m > max_val]
                print(f"Error: Minterm(s) {invalid_mins} out of valid range (0-{max_val}).")
                continue
            break
            
        # 4. Don't Cares
        dont_cares = set()
        while True:
            prompt = f"Enter don't cares (comma-separated integers in range 0-{max_val}, or Enter for none): "
            dont_cares = get_comma_list(prompt)
            if dont_cares:
                if any(d < 0 or d > max_val for d in dont_cares):
                    invalid_dcs = [d for d in dont_cares if d < 0 or d > max_val]
                    print(f"Error: Don't care(s) {invalid_dcs} out of valid range (0-{max_val}).")
                    continue
                # Intersection check
                intersection = minterms & dont_cares
                if intersection:
                    print(f"Warning: Value(s) {list(intersection)} specified as both minterm and don't care.")
                    print("  Removing them from the don't cares list.")
                    dont_cares -= intersection
            break
            
        # 5. Review Summary
        print("\n" + "="*30)
        print("     INPUT SUMMARY")
        print("="*30)
        print(f"Number of Variables : {num_vars}")
        print(f"Variable Labels     : {', '.join(var_names)}")
        print(f"Minterms (value 1)  : {sorted(list(minterms))}")
        print(f"Don't Cares (val X) : {sorted(list(dont_cares)) if dont_cares else 'None'}")
        print(f"Valid Minterm Range : 0 to {max_val}")
        print("="*30)
        
        confirm = input("Is this correct? (y/n) [Default: y]: ").strip().lower()
        if confirm == 'n' or confirm == 'no':
            continue
        return num_vars, var_names, minterms, dont_cares

def generate_manim_file(num_vars, var_names, minterms, dont_cares, temp_dir):
    """Run logic solver, calculate layout properties, and generate temp_kmap_scene.py in temp_dir."""
    
    # 1. Run QM solver and cover chart
    pis, qm_steps = run_qm_algorithm(num_vars, minterms, dont_cares)
    epis, remaining_pis = solve_prime_implicant_chart(minterms, pis)
    
    # Pre-calculate text representations for each PI term to keep Manim side clean and LaTeX-free
    for pi in pis:
        pi["text_val"] = get_sop_text(pi["binary"], var_names)
        pi["minterms"] = sorted(list(pi["minterms"]))
        
    for epi in epis:
        epi["text_val"] = get_sop_text(epi["binary"], var_names)
        epi["minterms"] = sorted(list(epi["minterms"]))
        
    for r_pi in remaining_pis:
        r_pi["text_val"] = get_sop_text(r_pi["binary"], var_names)
        r_pi["minterms"] = sorted(list(r_pi["minterms"]))
        
    # Compile final expression lists
    final_pis_chosen = epis + remaining_pis
    final_sop_text = " + ".join([get_sop_text(pi["binary"], var_names) for pi in final_pis_chosen])
    if not final_sop_text:
        final_sop_text = "0"
        
    # Serialize everything for code injection
    minterms_list = sorted(list(minterms))
    dont_cares_list = sorted(list(dont_cares))
    var_names_repr = repr(var_names)
    pis_repr = repr(pis)
    epis_repr = repr(epis)
    remaining_pis_repr = repr(remaining_pis)
    
    # Write Manim template
    code = f"""# Generated Manim code for K-Map Solver
from manim import *
import numpy as np

# Config and Solver data
num_vars = {num_vars}
var_names = {var_names_repr}
minterms = set({minterms_list})
dont_cares = set({dont_cares_list})
pis = {pis_repr}
epis = {epis_repr}
remaining_pis = {remaining_pis_repr}
final_sop_text = "{final_sop_text}"

class KMapSolver(Scene):
    def construct(self):
        self.camera.background_color = "#121214"
        
        # 1. Display title
        title = Text("K-Map Solver Animation ({num_vars} Variables)", font_size=28, color=BLUE, font="Arial")
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(0.5)

        # 2. Build layout properties based on variable counts
        # Max rows/cols per grid
        if num_vars == 2:
            max_rows, max_cols = 2, 2
            row_vars, col_vars = var_names[0], var_names[1]
            row_headers_list = ["0", "1"]
            col_headers_list = ["0", "1"]
        elif num_vars == 3:
            max_rows, max_cols = 2, 4
            row_vars, col_vars = var_names[0], var_names[1] + var_names[2]
            row_headers_list = ["0", "1"]
            col_headers_list = ["00", "01", "11", "10"]
        elif num_vars == 4:
            max_rows, max_cols = 4, 4
            row_vars, col_vars = var_names[0] + var_names[1], var_names[2] + var_names[3]
            row_headers_list = ["00", "01", "11", "10"]
            col_headers_list = ["00", "01", "11", "10"]
        elif num_vars == 5:
            max_rows, max_cols = 4, 4
            row_vars, col_vars = var_names[1] + var_names[2], var_names[3] + var_names[4]
            row_headers_list = ["00", "01", "11", "10"]
            col_headers_list = ["00", "01", "11", "10"]
        elif num_vars == 6:
            max_rows, max_cols = 4, 4
            row_vars, col_vars = var_names[2] + var_names[3], var_names[4] + var_names[5]
            row_headers_list = ["00", "01", "11", "10"]
            col_headers_list = ["00", "01", "11", "10"]

        # Decodes decimal minterm index from (grid_idx, r, c)
        gray_rows = [0, 1, 3, 2]
        gray_cols = [0, 1, 3, 2]
        
        def get_minterm_val(g_idx, r, c):
            if num_vars == 2:
                return r * 2 + c
            elif num_vars == 3:
                return r * 4 + gray_cols[c]
            elif num_vars == 4:
                return gray_rows[r] * 4 + gray_cols[c]
            elif num_vars == 5:
                return g_idx * 16 + gray_rows[r] * 4 + gray_cols[c]
            elif num_vars == 6:
                grid_dec_val = [0, 1, 2, 3][g_idx]
                return grid_dec_val * 16 + gray_rows[r] * 4 + gray_cols[c]

        # Grids construction list
        grids = []
        grids_titles = []
        
        # We scale K-Map size based on variable count to fit nicely
        cell_size = 0.5 if num_vars >= 5 else 0.7
        text_size = 14 if num_vars >= 5 else 20
        idx_size = 8 if num_vars >= 5 else 10
        header_size = 10 if num_vars >= 5 else 14
        
        num_grids = 1
        if num_vars == 5:
            num_grids = 2
        elif num_vars == 6:
            num_grids = 4

        # Center coordinates for each grid
        grid_centers = []
        if num_grids == 1:
            grid_centers.append(np.array([-2.2, 0.0, 0.0]) if num_vars >= 4 else np.array([0.0, 0.0, 0.0]))
        elif num_grids == 2:
            grid_centers.append(np.array([-2.6, 0.2, 0.0]))
            grid_centers.append(np.array([2.0, 0.2, 0.0]))
        elif num_grids == 4:
            grid_centers.append(np.array([-2.6, 1.8, 0.0]))  # TL
            grid_centers.append(np.array([2.0, 1.8, 0.0]))   # TR
            grid_centers.append(np.array([-2.6, -1.8, 0.0])) # BL
            grid_centers.append(np.array([2.0, -1.8, 0.0]))  # BR

        # Helper to partition covered cells into rectangular boxes (handling wrap-arounds)
        def get_intervals(indices, max_val):
            if not indices:
                return []
            if len(indices) == max_val:
                return [(0, max_val - 1)]
            if len(indices) == 1:
                val = list(indices)[0]
                return [(val, val)]
            if len(indices) == 2:
                vals = sorted(list(indices))
                if vals == [0, max_val - 1]:
                    return [(0, 0), (max_val - 1, max_val - 1)]
                elif vals[1] - vals[0] == 1:
                    return [(vals[0], vals[1])]
            return [(v, v) for v in sorted(list(indices))]

        # Build each grid
        for g_idx in range(num_grids):
            grid_center = grid_centers[g_idx]
            
            # Grid container
            grid_group = VGroup()
            grid_group.boxes = []
            grid_group.labels = []
            
            # Create boxes and cell content
            for r in range(max_rows):
                row_boxes = []
                row_labels = []
                for c in range(max_cols):
                    box = Square(side_length=cell_size, stroke_color=GRAY, fill_color=BLACK, fill_opacity=0.3)
                    x_shift = (c - (max_cols - 1)/2) * cell_size
                    y_shift = (((max_rows - 1)/2) - r) * cell_size
                    box.move_to(grid_center + np.array([x_shift, y_shift, 0.0]))
                    grid_group.add(box)
                    row_boxes.append(box)
                    
                    # Compute minterm value
                    m_val = get_minterm_val(g_idx, r, c)
                    
                    # Cell content
                    if m_val in minterms:
                        char = "1"
                        color = WHITE
                    elif m_val in dont_cares:
                        char = "X"
                        color = GRAY_B
                    else:
                        char = "0"
                        color = GRAY_E
                        
                    label = Text(char, font_size=text_size, color=color, font="Courier New")
                    label.move_to(box.get_center())
                    grid_group.add(label)
                    row_labels.append(label)
                    
                    # Decimal index in bottom-right corner of cell
                    m_idx_text = Text(str(m_val), font_size=idx_size, color=GRAY_D, font="Arial")
                    m_idx_text.move_to(box.get_bottom() + RIGHT * (cell_size*0.35) + UP * (cell_size*0.2))
                    grid_group.add(m_idx_text)
                    
                grid_group.boxes.append(row_boxes)
                grid_group.labels.append(row_labels)
                
            # Add Row/Col Headers
            for r in range(max_rows):
                header_text = Text(row_headers_list[r], font_size=header_size, color=BLUE_A, font="Courier New")
                header_text.next_to(grid_group.boxes[r][0], LEFT, buff=0.15)
                grid_group.add(header_text)
                
            for c in range(max_cols):
                header_text = Text(col_headers_list[c], font_size=header_size, color=BLUE_A, font="Courier New")
                header_text.next_to(grid_group.boxes[0][c], UP, buff=0.15)
                grid_group.add(header_text)
                
            # Diagonal Divider and Row/Col variables label
            top_left_box = grid_group.boxes[0][0]
            divider_start = top_left_box.get_left() + UP * (cell_size * 0.5)
            row_vars_label = Text(row_vars, font_size=header_size, color=BLUE, font="Arial")
            col_vars_label = Text(col_vars, font_size=header_size, color=BLUE, font="Arial")
            
            row_vars_label.move_to(divider_start + LEFT * (cell_size * 0.8) + UP * (cell_size * 0.4))
            col_vars_label.move_to(divider_start + LEFT * (cell_size * 0.3) + UP * (cell_size * 0.9))
            
            div_line = Line(
                start=row_vars_label.get_bottom() + RIGHT*(cell_size*0.1), 
                end=col_vars_label.get_right() + DOWN*(cell_size*0.6), 
                stroke_color=BLUE, stroke_width=1.5
            )
            grid_group.add(row_vars_label, col_vars_label, div_line)
            
            if num_vars == 5:
                title_str = f"{var_names[0]} = {{g_idx}}"
                grid_title = Text(title_str, font_size=14, color=WHITE, font="Arial")
                grid_title.next_to(grid_group, UP, buff=1.0)
                grids_titles.append(grid_title)
            elif num_vars == 6:
                g_codes = ["00", "01", "10", "11"]
                title_str = f"{var_names[0]}{var_names[1]} = {{g_codes[g_idx]}}"
                grid_title = Text(title_str, font_size=12, color=WHITE, font="Arial")
                grid_title.next_to(grid_group, UP, buff=0.8)
                grids_titles.append(grid_title)
                
            grids.append(grid_group)
            
        play_anims = [FadeIn(g) for g in grids]
        if grids_titles:
            play_anims.extend([FadeIn(t) for t in grids_titles])
            
        self.play(*play_anims, run_time=1.0)
        self.wait(0.5)

        # 3. Dynamic Side Info / Trace Panel
        info_box = Rectangle(
            width=4.2, height=5.2, stroke_color=GRAY_D, stroke_width=1, 
            fill_color="#18181C", fill_opacity=0.9
        )
        info_box.to_edge(RIGHT, buff=0.4).shift(DOWN * 0.2)
        info_title = Text("QM SIMPLIFICATION STEPS", font_size=11, color=GRAY_B, font="Arial")
        info_title.next_to(info_box, UP, aligned_edge=LEFT, buff=0.08)
        
        info_content = VGroup(
            Text("1. Identify Implicants (1s & X)", font_size=12, color=GRAY),
            Text("2. Extract Prime Implicants (PI)", font_size=12, color=GRAY),
            Text("3. Find Essential PIs (EPI)", font_size=12, color=GRAY),
            Text("4. Cover remaining minterms", font_size=12, color=GRAY)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        info_content.move_to(info_box.get_center())
        
        self.play(FadeIn(info_box), FadeIn(info_title), FadeIn(info_content))
        self.wait(1.0)

        # Highlight Step 1: Implicants
        self.play(info_content[0].animate.set_color(YELLOW), run_time=0.4)
        
        # Flash all 1 cells on the grid
        one_highlights = []
        for g_idx, grid in enumerate(grids):
            for r in range(max_rows):
                for c in range(max_cols):
                    m_val = get_minterm_val(g_idx, r, c)
                    if m_val in minterms:
                        one_highlights.append(
                            grid.boxes[r][c].copy().set_stroke(YELLOW, width=3).set_fill(YELLOW, opacity=0.15)
                        )
                        
        if one_highlights:
            one_group = VGroup(*one_highlights)
            self.play(FadeIn(one_group), run_time=0.5)
            self.wait(0.8)
            self.play(FadeOut(one_group), run_time=0.4)

        # Highlight Step 2: Extract Prime Implicants
        self.play(
            info_content[0].animate.set_color(GRAY_C),
            info_content[1].animate.set_color(YELLOW),
            run_time=0.4
        )
        self.wait(0.5)
        
        pi_loops = VGroup()
        pi_drawings = []
        pi_colors = [RED, ORANGE, PURPLE, PINK, GOLD, TEAL, MAROON, BLUE_C]
        
        def get_pi_blocks(pi_minterms):
            coords_by_grid = {{}}
            for m in pi_minterms:
                found = False
                for g_idx in range(num_grids):
                    for r in range(max_rows):
                        for c in range(max_cols):
                            if get_minterm_val(g_idx, r, c) == m:
                                coords_by_grid.setdefault(g_idx, []).append((r, c))
                                found = True
                                break
                        if found:
                            break
            
            grid_blocks = {{}}
            for g_idx, cells in coords_by_grid.items():
                rows = {{r for r, c in cells}}
                cols = {{c for r, c in cells}}
                
                row_intervals = get_intervals(rows, max_rows)
                col_intervals = get_intervals(cols, max_cols)
                
                blocks = []
                for r_start, r_end in row_intervals:
                    for c_start, c_end in col_intervals:
                        blocks.append((r_start, r_end, c_start, c_end))
                grid_blocks[g_idx] = blocks
                
            return grid_blocks

        # Dynamic loop container to show the currently highlighted PI expression
        pi_expr_box = RoundedRectangle(
            corner_radius=0.1, width=3.8, height=1.5, stroke_color=BLUE_A, 
            fill_color="#1F1F24", fill_opacity=0.9
        )
        pi_expr_box.move_to(info_box.get_center() + DOWN*1.3)
        pi_expr_title = Text("Active Prime Implicant:", font_size=10, color=GRAY_B, font="Arial").move_to(pi_expr_box.get_top() + DOWN*0.22)
        pi_expr_text = Text("", font_size=14, color=YELLOW, font="Courier New").move_to(pi_expr_box.get_center() + DOWN*0.15)
        
        active_pi_display = VGroup(pi_expr_box, pi_expr_title, pi_expr_text)
        self.play(FadeIn(active_pi_display))

        # Show each PI
        for pi_idx, pi in enumerate(pis):
            pi_color = pi_colors[pi_idx % len(pi_colors)]
            
            # Using clean pre-calculated Text representations instead of MathTex
            text_str = f"Term: {{pi['binary']}} => {{pi['text_val']}}"
            new_text = Text(text_str, font_size=12, color=pi_color, font="Courier New")
            new_text.move_to(pi_expr_box.get_center() + DOWN*0.1)
            
            grid_blocks = get_pi_blocks(pi["minterms"])
            pi_loop_group = VGroup()
            block_centers = {{}}
            
            for g_idx, blocks in grid_blocks.items():
                grid = grids[g_idx]
                block_centers[g_idx] = []
                for r_start, r_end, c_start, c_end in blocks:
                    cell_0 = grid.boxes[r_start][c_start]
                    cell_1 = grid.boxes[r_end][c_end]
                    
                    top_left = np.array([cell_0.get_left()[0] + 0.05, cell_0.get_top()[1] - 0.05, 0.0])
                    bottom_right = np.array([cell_1.get_right()[0] - 0.05, cell_1.get_bottom()[1] + 0.05, 0.0])
                    
                    width = bottom_right[0] - top_left[0]
                    height = top_left[1] - bottom_right[1]
                    center = (top_left + bottom_right) / 2
                    block_centers[g_idx].append(center)
                    
                    loop = RoundedRectangle(
                        width=width, height=height, corner_radius=cell_size*0.2,
                        stroke_color=pi_color, stroke_width=2.5, fill_color=pi_color, fill_opacity=0.08
                    )
                    loop.move_to(center)
                    pi_loop_group.add(loop)
                    
            if num_grids > 1:
                if num_grids == 2 and 0 in block_centers and 1 in block_centers:
                    for c0, c1 in zip(block_centers[0], block_centers[1]):
                        link = DashedLine(start=c0, end=c1, stroke_color=pi_color, stroke_width=1.5, dash_length=0.1)
                        pi_loop_group.add(link)
                elif num_grids == 4:
                    for g_src, g_dst in [(0, 1), (2, 3), (0, 2), (1, 3)]:
                        if g_src in block_centers and g_dst in block_centers:
                            for c_src, c_dst in zip(block_centers[g_src], block_centers[g_dst]):
                                link = DashedLine(start=c_src, end=c_dst, stroke_color=pi_color, stroke_width=1.5, dash_length=0.1)
                                pi_loop_group.add(link)
            
            self.play(
                FadeIn(pi_loop_group),
                pi_expr_text.animate.become(new_text),
                run_time=0.8
            )
            self.wait(1.0)
            
            pi_loops.add(pi_loop_group)
            pi_drawings.append((pi_loop_group, pi, pi_color))

        self.play(FadeOut(active_pi_display))

        # Highlight Step 3: Identify Essential Prime Implicants
        self.play(
            info_content[1].animate.set_color(GRAY_C),
            info_content[2].animate.set_color(YELLOW),
            run_time=0.4
        )
        self.wait(0.5)
        
        # Build mapping of minterm -> list of indices in pi_drawings covering it
        minterm_covers = {{}}
        for m in minterms:
            minterm_covers[m] = []
            for idx, (loop, pi, color) in enumerate(pi_drawings):
                if m in pi["minterms"]:
                    minterm_covers[m].append(idx)
                    
        epi_indices = set()
        unique_mins_by_pi = {{}}
        
        for m, covers in minterm_covers.items():
            if len(covers) == 1:
                idx = covers[0]
                epi_indices.add(idx)
                unique_mins_by_pi.setdefault(idx, []).append(m)

        # First, fade all loops slightly
        self.play(*[loop.animate.set_opacity(0.2) for loop, pi, color in pi_drawings], run_time=0.5)
        self.wait(0.5)
        
        epi_loops = VGroup()
        
        # Highlight essential ones in GREEN
        for idx in sorted(list(epi_indices)):
            loop, pi, color = pi_drawings[idx]
            unique_mins = unique_mins_by_pi[idx]
            
            flash_highlights = []
            for m in unique_mins:
                for g_idx in range(num_grids):
                    found = False
                    for r in range(max_rows):
                        for c in range(max_cols):
                            if get_minterm_val(g_idx, r, c) == m:
                                cell = grids[g_idx].boxes[r][c]
                                flash_highlights.append(
                                    cell.copy().set_stroke(YELLOW, width=4).set_fill(YELLOW, opacity=0.2)
                                )
                                found = True
                                break
                        if found:
                            break
            
            if flash_highlights:
                flash_group = VGroup(*flash_highlights)
                self.play(FadeIn(flash_group), run_time=0.4)
                self.wait(0.4)
                self.play(FadeOut(flash_group), run_time=0.3)
            
            self.play(
                loop.animate.set_color(GREEN).set_opacity(0.85),
                run_time=0.8
            )
            epi_loops.add(loop)
            self.wait(0.4)
            
        self.wait(1.0)

        # Highlight Step 4: Cover remaining minterms
        self.play(
            info_content[2].animate.set_color(GRAY_C),
            info_content[3].animate.set_color(YELLOW),
            run_time=0.4
        )
        self.wait(0.5)
        
        # Highlight remaining chosen PIs in BLUE
        remaining_pi_covers = []
        for idx, (loop, pi, color) in enumerate(pi_drawings):
            if idx not in epi_indices:
                is_chosen = False
                for r_pi in remaining_pis:
                    if r_pi["binary"] == pi["binary"]:
                        is_chosen = True
                        break
                
                if is_chosen:
                    self.play(
                        loop.animate.set_color(BLUE).set_opacity(0.85),
                        run_time=0.8
                    )
                    remaining_pi_covers.append(loop)
                    self.wait(0.3)
                else:
                    self.play(loop.animate.set_opacity(0.05), run_time=0.5)

        self.wait(1.5)

        # 4. Final SOP Expression Card
        expr_box = RoundedRectangle(
            corner_radius=0.1, width=8.5, height=1.6, stroke_color=GREEN, stroke_width=2, 
            fill_color="#18181C", fill_opacity=0.9
        )
        expr_box.to_edge(DOWN, buff=0.4).shift(LEFT * 1.5 if num_vars >= 5 else LEFT * 0.5)
        expr_title = Text("SIMPLIFIED SOP EXPRESSION:", font_size=11, color=GREEN, font="Arial").next_to(expr_box.get_top(), DOWN, buff=0.18)
        
        expr_text = Text(f"F = {{final_sop_text}}", font_size=18, color=WHITE, font="Courier New")
        expr_text.move_to(expr_box.get_center() + DOWN*0.18)
        
        # Flash all chosen loops at the end
        selected_loops = [loop for loop, pi, color in pi_drawings if any(p["binary"] == pi["binary"] for p in epis + remaining_pis)]
        
        self.play(
            FadeOut(info_box), FadeOut(info_title), FadeOut(info_content),
            FadeIn(expr_box), FadeIn(expr_title), FadeIn(expr_text),
            *[loop.animate.set_opacity(0.9) for loop in selected_loops],
            run_time=1.0
        )
        self.wait(4.0)
"""
    
    scene_path = os.path.join(temp_dir, "temp_kmap_scene.py")
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Manim scene file '{scene_path}' generated successfully.")

def main():
    print("=" * 60)
    print("     K-MAP QUINE-MCCLUSKEY ALGORITHM MANIM VISUALIZER")
    print("=" * 60)
    print("This program solves a K-Map up to 6 variables and creates a step-by-step")
    print("animated demonstration video showing implicants, PIs, and EPIs.")
    
    # 1. Get inputs
    num_vars, var_names, minterms, dont_cares = get_user_inputs()
    
    # 2. Select rendering quality
    print("\nSelect video rendering quality:")
    print("  1. Low Quality (480p, 15fps) - Fast render [Recommended for quick testing]")
    print("  2. Medium Quality (720p, 30fps) - Balanced")
    print("  3. High Quality (1080p, 60fps) - Slow, High Res")
    
    choice = input("Enter choice (1/2/3) [Default: 1]: ").strip()
    if choice == "2":
        quality_flag = "-qm"
    elif choice == "3":
        quality_flag = "-qh"
    else:
        quality_flag = "-ql"
        
    # 3. Define temporary render directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.abspath(os.path.join(script_dir, "..", "kmap_temp"))
    os.makedirs(temp_dir, exist_ok=True)
    
    # 4. Generate Manim code inside temp_dir
    generate_manim_file(num_vars, var_names, minterms, dont_cares, temp_dir)
    
    # 5. Add FFmpeg to PATH inside python and run Manim
    print("\nSetting up rendering environment...")
    ffmpeg_dir = r"C:\Users\Abhinav\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin"
    
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"  FFmpeg located and added to environment path: {ffmpeg_dir}")
    else:
        print("  WARNING: FFmpeg directory from winget was not found.")
        print("  We will attempt to run manim using the system PATH.")
        
    scene_path = os.path.join(temp_dir, "temp_kmap_scene.py")
    
    print("\nRendering Manim animation. Please wait...")
    cmd = [sys.executable, "-m", "manim", scene_path, "KMapSolver", quality_flag]
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run Manim inside temp_dir
        result = subprocess.run(cmd, check=True, cwd=temp_dir)
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("         ANIMATION RENDERED SUCCESSFULLY!")
            print("=" * 60)
            
            # Find output file
            quality_folder = "480p15"
            if quality_flag == "-qm":
                quality_folder = "720p30"
            elif quality_flag == "-qh":
                quality_folder = "1080p60"
                
            temp_out_video = os.path.abspath(os.path.join(temp_dir, "media", "videos", "temp_kmap_scene", quality_folder, "KMapSolver.mp4"))
            
            # Define final target path inside "kmap solver"
            target_video_dir = os.path.join(script_dir, "media", "videos", "temp_kmap_scene", quality_folder)
            os.makedirs(target_video_dir, exist_ok=True)
            target_out_video = os.path.abspath(os.path.join(target_video_dir, "KMapSolver.mp4"))
            
            # Copy final video and clean up
            shutil.copy2(temp_out_video, target_out_video)
            print(f"Output video copied and saved to target:\n  {target_out_video}")
            
            # Clean up temp_dir
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            print("\nYou can open this file using your default video player.")
            
            # Ask if user wants to play it
            play_choice = input("\nDo you want to open and play the video now? (y/n) [Default: y]: ").strip().lower()
            if play_choice != "n":
                print("Launching video player...")
                try:
                    os.startfile(target_out_video)
                except Exception as e:
                    print(f"Could not open the video automatically: {e}")
        else:
            print("\nError: Manim render completed with non-zero exit code.")
            shutil.rmtree(temp_dir, ignore_errors=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError: Rendering failed. Command crashed with: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f"\nUnexpected error during execution: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
