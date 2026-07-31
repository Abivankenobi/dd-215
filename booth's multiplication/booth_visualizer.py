import os
import sys
import subprocess
import json
import shutil

def get_int_input(prompt):
    """Safely get an integer input from the user."""
    while True:
        try:
            val_str = input(prompt).strip()
            if not val_str:
                continue
            return int(val_str)
        except ValueError:
            print("Error: Please enter a valid integer (e.g., 7, -3).")

def get_min_bits(m, q):
    """
    Calculate the minimum number of bits required to represent both m and q 
    in 2's complement without negation overflow.
    We require that m is in (-2^(n-1), 2^(n-1)-1] so that -m is also representable.
    """
    for n in range(4, 32):
        # Prevent the edge case where -m is not representable in n bits (i.e. m = -2^(n-1))
        min_range = -(1 << (n - 1)) + 1
        max_range = (1 << (n - 1)) - 1
        if min_range <= m <= max_range and min_range <= q <= max_range:
            return n
    return 8  # fallback default

def to_bin(val, bits):
    """Convert an integer to its 2's complement binary representation of length 'bits'."""
    if val < 0:
        val = (1 << bits) + val
    return bin(val)[2:].zfill(bits)

def run_booth_algorithm(M_dec, Q_dec):
    """
    Trace Booth's multiplication algorithm step-by-step.
    Returns: (n_bits, M_bin, neg_M_bin, Q_bin, steps_data, final_bin, product_dec)
    """
    n = get_min_bits(M_dec, Q_dec)
    
    M_bin = to_bin(M_dec, n)
    neg_M_dec = -M_dec
    neg_M_bin = to_bin(neg_M_dec, n)
    Q_bin = to_bin(Q_dec, n)
    
    steps = []
    
    A = 0
    Q_val = Q_dec
    if Q_val < 0:
        Q_val = (1 << n) + Q_val
    Q_minus_1 = 0
    
    for step_num in range(1, n + 1):
        q0 = Q_val & 1
        q_m1 = Q_minus_1
        
        old_A_str = to_bin(A, n)
        old_Q_str = to_bin(Q_val, n)
        
        # Determine arithmetic operation
        if q0 == 1 and q_m1 == 0:
            action = "A <- A - M"
            A_after = (A - M_dec) & ((1 << n) - 1)
            Q_after = Q_val
        elif q0 == 0 and q_m1 == 1:
            action = "A <- A + M"
            A_after = (A + M_dec) & ((1 << n) - 1)
            Q_after = Q_val
        else:
            action = "No arithmetic"
            A_after = A
            Q_after = Q_val
            
        A_after_str = to_bin(A_after, n)
        Q_after_str = to_bin(Q_after, n)
        
        # Combine registers for Arithmetic Shift Right (A, Q, Q-1)
        # combined length: A (n bits) + Q (n bits) + Q-1 (1 bit) = 2n + 1 bits
        combined = (A_after << (n + 1)) | (Q_after << 1) | q_m1
        msb = (combined >> (2 * n)) & 1
        combined_shifted = combined >> 1
        # Sign extension
        if msb:
            combined_shifted |= (1 << (2 * n))
            
        new_q_m1 = combined_shifted & 1
        new_Q_val = (combined_shifted >> 1) & ((1 << n) - 1)
        new_A = (combined_shifted >> (n + 1)) & ((1 << n) - 1)
        
        new_A_str = to_bin(new_A, n)
        new_Q_str = to_bin(new_Q_val, n)
        
        steps.append({
            "step": step_num,
            "q0": str(q0),
            "q_m1": str(q_m1),
            "action": action,
            "old_A": old_A_str,
            "old_Q": old_Q_str,
            "old_qm1": str(q_m1),
            "A_after": A_after_str,
            "Q_after": Q_after_str,
            "new_A": new_A_str,
            "new_Q": new_Q_str,
            "new_qm1": str(new_q_m1)
        })
        
        # Update state for next step
        A = new_A
        Q_val = new_Q_val
        Q_minus_1 = new_q_m1
        
    final_A = to_bin(A, n)
    final_Q = to_bin(Q_val, n)
    final_bin = final_A + final_Q
    
    # Evaluate product in 2's complement of 2n bits
    prod_val = int(final_bin, 2)
    if prod_val & (1 << (2 * n - 1)):
        prod_val -= (1 << (2 * n))
        
    return n, M_bin, neg_M_bin, Q_bin, steps, final_bin, prod_val

def generate_manim_file(M_dec, Q_dec, n, M_bin, neg_M_bin, Q_bin, steps, final_bin, prod_val, temp_dir):
    """Write the temp_booth_scene.py file containing the Manim code in the temp_dir."""
    
    # JSON-serialize steps to embed in the script
    steps_json = json.dumps(steps, indent=4)
    
    code = f"""# Generated Manim code for Booth's Multiplication Algorithm
from manim import *
import numpy as np

# Config data
M_dec = {M_dec}
Q_dec = {Q_dec}
n = {n}
M_bin = "{M_bin}"
neg_M_bin = "{neg_M_bin}"
Q_bin = "{Q_bin}"
final_bin = "{final_bin}"
prod_val = {prod_val}

steps_data = {steps_json}

class BoothMultiplication(Scene):
    def construct(self):
        # Configure background
        self.camera.background_color = "#121214"
        
        # Helper function to create register graphics
        def create_register(name, num_bits, color, box_size=0.6):
            boxes = VGroup(*[
                Square(side_length=box_size, stroke_color=color, fill_color=BLACK, fill_opacity=0.5) 
                for _ in range(num_bits)
            ])
            boxes.arrange(RIGHT, buff=0)
            label = Text(name, font_size=14, color=color, font="Arial")
            label.next_to(boxes, UP, buff=0.15)
            reg = VGroup(boxes, label)
            reg.boxes = boxes
            return reg

        # 1. Title Section
        title = Text("Booth's Multiplication Algorithm", font_size=28, color=BLUE, font="Arial")
        title.to_edge(UP, buff=0.3)
        
        subtitle = Text(
            f"Multiplicand (M) = {{M_dec}} ({{M_bin}})   |   Multiplier (Q) = {{Q_dec}} ({{Q_bin}})", 
            font_size=15, color=WHITE, font="Arial"
        )
        subtitle.next_to(title, DOWN, buff=0.15)
        
        self.play(Write(title), FadeIn(subtitle))
        self.wait(0.5)
        
        # 2. Constants Panel (Top Right)
        constants_box = VGroup(
            Text(f" M = {{M_bin}} ({{M_dec}})", font_size=14, font="Courier New", color=BLUE_B),
            Text(f"-M = {{neg_M_bin}} ({{-M_dec}})", font_size=14, font="Courier New", color=RED_B)
        )
        constants_box.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        constants_box_container = VGroup(
            RoundedRectangle(corner_radius=0.1, stroke_color=GRAY_E, fill_color="#18181C", fill_opacity=0.8).stretch_to_fit_width(2.6).stretch_to_fit_height(0.9),
            constants_box
        )
        constants_box.move_to(constants_box_container)
        constants_box_container.to_edge(UR, buff=0.4).shift(DOWN * 0.2)
        
        self.play(FadeIn(constants_box_container))
        
        # 3. Create Registers
        reg_A = create_register("Register A", n, TEAL)
        reg_Q = create_register("Register Q", n, ORANGE)
        reg_Qm1 = create_register("Register Q_-1", 1, PURPLE)
        
        registers = VGroup(reg_A, reg_Q, reg_Qm1)
        registers.arrange(RIGHT, buff=0.6)
        registers.move_to(np.array([-2.2, 0.8, 0.0]))
        
        # Initialize text labels in registers
        # Initially, A = 0, Q = multiplier, Q_-1 = 0
        reg_A.labels = VGroup(*[
            Text("0", font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
            for box in reg_A.boxes
        ])
        reg_Q.labels = VGroup(*[
            Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
            for char, box in zip(Q_bin, reg_Q.boxes)
        ])
        reg_Qm1.labels = VGroup(
            Text("0", font_size=20, font="Courier New", color=WHITE).move_to(reg_Qm1.boxes[0].get_center())
        )
        
        self.play(
            FadeIn(reg_A),
            FadeIn(reg_Q),
            FadeIn(reg_Qm1),
            FadeIn(reg_A.labels),
            FadeIn(reg_Q.labels),
            FadeIn(reg_Qm1.labels),
            run_time=0.8
        )
        
        # 4. Bottom Info Panel (Logic Description)
        info_box = Rectangle(
            width=4.0, height=1.6, stroke_color=GRAY_D, stroke_width=1, 
            fill_color="#18181C", fill_opacity=0.85
        )
        info_box.to_edge(DL, buff=0.5).shift(UP * 0.1)
        info_title = Text("CURRENT OPERATION", font_size=11, color=GRAY_B, font="Arial")
        info_title.next_to(info_box, UP, aligned_edge=LEFT, buff=0.08)
        
        step_text = Text("Step: --", font_size=13, font="Arial", color=WHITE)
        cond_text = Text("Scan bits Q_0, Q_-1: --", font_size=13, font="Arial", color=WHITE)
        act_text = Text("Action: --", font_size=13, font="Arial", color=YELLOW)
        
        # Arrange positions but do not add composite texts_group to the scene
        texts_group = VGroup(step_text, cond_text, act_text).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        texts_group.move_to(info_box.get_center())
        
        self.play(FadeIn(info_box), FadeIn(info_title), FadeIn(step_text), FadeIn(cond_text), FadeIn(act_text))
        
        # 5. Right Trace Panel
        trace_box = Rectangle(
            width=4.0, height=4.8, stroke_color=GRAY_D, stroke_width=1, 
            fill_color="#18181C", fill_opacity=0.85
        )
        trace_box.to_edge(DR, buff=0.5).shift(UP * 0.4)
        trace_title_label = Text("EXECUTION TRACE", font_size=11, color=GRAY_B, font="Arial")
        trace_title_label.next_to(trace_box, UP, aligned_edge=LEFT, buff=0.08)
        
        # Setup trace items
        trace_items = []
        trace_items.append(Text("Initial State", font_size=13, font="Arial", color=GRAY))
        for step in steps_data:
            step_num = step["step"]
            action = step["action"]
            if "A - M" in action:
                op_short = "A <- A - M, Shift"
            elif "A + M" in action:
                op_short = "A <- A + M, Shift"
            else:
                op_short = "Shift only"
            trace_items.append(Text(f"Step {{step_num}}: {{op_short}}", font_size=13, font="Arial", color=GRAY))
        trace_items.append(Text("Final Product", font_size=13, font="Arial", color=GRAY))
        
        trace_panel = VGroup(*trace_items).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        trace_panel.move_to(trace_box.get_center())
        
        self.play(FadeIn(trace_box), FadeIn(trace_title_label), FadeIn(trace_panel))
        
        # Highlight "Initial State" trace
        self.play(trace_items[0].animate.set_color(YELLOW), run_time=0.3)
        self.wait(1.0)
        
        # Loop through Booth steps
        for i, step in enumerate(steps_data):
            step_num = step["step"]
            q0 = step["q0"]
            qm1 = step["q_m1"]
            action = step["action"]
            old_A = step["old_A"]
            old_Q = step["old_Q"]
            A_after = step["A_after"]
            new_A = step["new_A"]
            new_Q = step["new_Q"]
            new_qm1 = step["new_qm1"]
            
            new_step_text = Text(f"Step: {{step_num}} / {{n}}", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
            new_cond_text = Text(f"Scan bits Q_0, Q_-1: {{q0}}{{qm1}}", font_size=13, font="Arial", color=WHITE).move_to(cond_text.get_center())
            
            if q0 == "1" and qm1 == "0":
                act_str = "Action: A <- A - M (add -M)"
            elif q0 == "0" and qm1 == "1":
                act_str = "Action: A <- A + M"
            else:
                act_str = "Action: No arithmetic operation"
                
            new_act_text = Text(act_str, font_size=13, font="Arial", color=YELLOW)
            new_act_text.move_to(act_text.get_center())
            
            self.play(
                Transform(step_text, new_step_text),
                Transform(cond_text, new_cond_text),
                Transform(act_text, new_act_text),
                trace_items[i].animate.set_color(GRAY_C),
                trace_items[i+1].animate.set_color(YELLOW),
                run_time=0.4
            )
            
            # 2. Highlight scanning bits: Q_0 (last bit of Q) and Q_-1
            scan_highlight = VGroup(
                reg_Q.boxes[-1].copy().set_stroke(YELLOW, width=4).set_fill(YELLOW, opacity=0.2),
                reg_Qm1.boxes[0].copy().set_stroke(YELLOW, width=4).set_fill(YELLOW, opacity=0.2)
            )
            self.play(FadeIn(scan_highlight), run_time=0.4)
            self.wait(0.8)
            
            # --- PHASE B: ARITHMETIC OPERATION ---
            if action != "No arithmetic":
                # Create visual math scratchpad
                math_box = RoundedRectangle(
                    corner_radius=0.1, width=4.2, height=2.2, stroke_color=YELLOW, stroke_width=2, 
                    fill_color="#18181C", fill_opacity=0.95
                )
                math_box.move_to(np.array([-0.5, -1.8, 0.0]))
                math_title = Text("Arithmetic Sub-step", font_size=11, color=YELLOW, font="Arial").next_to(math_box, UP, aligned_edge=LEFT, buff=0.08)
                
                # Align labels to right and values to left to prevent layout shifting
                label_A = Text("A:", font_size=16, color=WHITE)
                value_A = Text(f"{{old_A}}", font_size=16, font="Courier New", color=WHITE)
                
                if "A - M" in action:
                    label_M = Text("+ -M:", font_size=16, color=WHITE)
                    value_M = Text(f"{{neg_M_bin}}", font_size=16, font="Courier New", color=WHITE)
                else:
                    label_M = Text("+  M:", font_size=16, color=WHITE)
                    value_M = Text(f"{{M_bin}}", font_size=16, font="Courier New", color=WHITE)
                    
                label_Sum = Text("Sum:", font_size=16, color=YELLOW)
                value_Sum = Text(f"{{A_after}}", font_size=16, font="Courier New", color=YELLOW)
                
                labels_col = VGroup(label_A, label_M, label_Sum).arrange(DOWN, aligned_edge=RIGHT, buff=0.2)
                values_col = VGroup(value_A, value_M, value_Sum).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
                values_col.next_to(labels_col, RIGHT, buff=0.3)
                
                # Combine columns and center them in the box
                math_elements = VGroup(labels_col, values_col)
                math_elements.move_to(math_box.get_center())
                
                # Create divider line placed vertically between row 2 and row 3
                divider = Line(
                    start=labels_col.get_left() + LEFT*0.1,
                    end=values_col.get_right() + RIGHT*0.1,
                    stroke_width=1.5,
                    color=WHITE
                )
                divider.move_to(np.array([
                    (labels_col.get_x() + values_col.get_x()) / 2,
                    (labels_col[1].get_y() + labels_col[2].get_y()) / 2,
                    0
                ]))
                
                math_group = VGroup(math_box, math_title, labels_col, values_col, divider)
                
                self.play(FadeIn(math_group), run_time=0.5)
                self.wait(1.0)
                
                # Flash A boxes to show update
                flash_animations = [Flash(box, color=YELLOW, run_time=0.6, flash_radius=0.3) for box in reg_A.boxes]
                new_labels = VGroup(*[
                    Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                    for char, box in zip(A_after, reg_A.boxes)
                ])
                
                self.play(
                    *flash_animations,
                    Transform(reg_A.labels, new_labels),
                    run_time=0.6
                )
                self.wait(0.8)
                self.play(FadeOut(math_group), run_time=0.5)
                
            # Remove scanning highlights
            self.play(FadeOut(scan_highlight), run_time=0.3)
            self.wait(0.3)
            
            # --- PHASE C: ARITHMETIC SHIFT RIGHT ---
            new_act_text = Text("Action: Arithmetic Shift Right (ASR)", font_size=14, font="Courier New", color=GOLD_B).move_to(act_text.get_center())
            self.play(Transform(act_text, new_act_text), run_time=0.3)
            self.wait(0.5)
            
            shift_anims = []
            
            # Create a duplicate of A[0] (sign extension)
            a0_clone = reg_A.labels[0].copy()
            self.add(a0_clone)
            shift_anims.append(a0_clone.animate.move_to(reg_A.boxes[1].get_center()))
            
            # Shift A[1] to A[n-1] to the right
            for idx in range(1, n - 1):
                shift_anims.append(reg_A.labels[idx].animate.move_to(reg_A.boxes[idx + 1].get_center()))
                
            # Shift A[n-1] to Q[0]
            shift_anims.append(reg_A.labels[-1].animate.move_to(reg_Q.boxes[0].get_center()))
            
            # Shift Q[0] to Q[n-1] to the right
            for idx in range(0, n - 1):
                shift_anims.append(reg_Q.labels[idx].animate.move_to(reg_Q.boxes[idx + 1].get_center()))
                
            # Shift Q[n-1] to Q_m1[0]
            shift_anims.append(reg_Q.labels[-1].animate.move_to(reg_Qm1.boxes[0].get_center()))
            
            # Fade out old Q_-1
            shift_anims.append(FadeOut(reg_Qm1.labels[0]))
            
            self.play(*shift_anims, run_time=1.0)
            self.wait(0.5)
            
            # Clean swap with fresh static text elements
            self.remove(reg_A.labels, reg_Q.labels, reg_Qm1.labels, a0_clone)
            
            reg_A.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(new_A, reg_A.boxes)
            ])
            reg_Q.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(new_Q, reg_Q.boxes)
            ])
            reg_Qm1.labels = VGroup(
                Text(new_qm1, font_size=20, font="Courier New", color=WHITE).move_to(reg_Qm1.boxes[0].get_center())
            )
            
            self.add(reg_A.labels, reg_Q.labels, reg_Qm1.labels)
            self.wait(0.8)
            
        # --- END OF LOOP: FINAL PRODUCT ---
        # Highlight last line of trace
        self.play(
            trace_items[-2].animate.set_color(GRAY_C),
            trace_items[-1].animate.set_color(YELLOW),
            run_time=0.4
        )
        
        # Update Info Panel
        new_step_text = Text(f"Done: {{n}} Steps Completed", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
        new_cond_text = Text("Result: A and Q combined", font_size=13, font="Arial", color=WHITE).move_to(cond_text.get_center())
        new_act_text = Text(f"Product = {{prod_val}}", font_size=13, font="Arial", color=GREEN).move_to(act_text.get_center())
        
        self.play(
            Transform(step_text, new_step_text),
            Transform(cond_text, new_cond_text),
            Transform(act_text, new_act_text),
            run_time=0.4
        )
        
        # Draw a beautiful box around A and Q to show the final product
        product_box = SurroundingRectangle(
            VGroup(reg_A.boxes, reg_Q.boxes), 
            color=GREEN, stroke_width=3, buff=0.1
        )
        product_label = Text("Final Product (AQ)", font_size=14, color=GREEN, font="Arial").next_to(product_box, DOWN, buff=0.15)
        
        self.play(Create(product_box), FadeIn(product_label), run_time=0.8)
        self.wait(1.0)
        
        # Draw final summary card in center-bottom
        summary_box = RoundedRectangle(
            corner_radius=0.1, width=7.0, height=2.0, stroke_color=GREEN, stroke_width=2, 
            fill_color="#18181C", fill_opacity=0.9
        )
        summary_box.move_to(np.array([-1.2, -1.8, 0.0]))
        summary_title = Text("Verification Summary", font_size=12, color=GREEN, font="Arial").next_to(summary_box, UP, aligned_edge=LEFT, buff=0.08)
        
        verify_line1 = Text(f"Multiplicand (M):  {{M_dec}} (binary: {{M_bin}})", font_size=14, font="Courier New", color=WHITE)
        verify_line2 = Text(f"Multiplier (Q):    {{Q_dec}} (binary: {{Q_bin}})", font_size=14, font="Courier New", color=WHITE)
        verify_line3 = Text(f"Final AQ (2n-bit): {{final_bin}} = {{prod_val}}", font_size=14, font="Courier New", color=GREEN_A)
        
        summary_content = VGroup(verify_line1, verify_line2, verify_line3).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        summary_content.move_to(summary_box.get_center())
        
        self.play(
            FadeOut(info_box), FadeOut(info_title), FadeOut(step_text), FadeOut(cond_text), FadeOut(act_text),
            FadeIn(summary_box), FadeIn(summary_title), FadeIn(summary_content),
            run_time=0.8
        )
        self.wait(3.0)
"""
    
    scene_path = os.path.join(temp_dir, "temp_booth_scene.py")
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Manim scene file '{scene_path}' generated successfully.")

def main():
    print("=" * 60)
    print("   BOOTH'S MULTIPLICATION ALGORITHM MANIM VISUALIZER")
    print("=" * 60)
    print("This program runs Booth's algorithm and creates a step-by-step")
    print("animated demonstration video using Manim.")
    
    # 1. Get inputs
    M_dec = get_int_input("\nEnter Multiplicand M (e.g. 7 or -7): ")
    Q_dec = get_int_input("Enter Multiplier Q (e.g. -3 or 3): ")
    
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
        
    # 3. Trace Booth's Algorithm
    print("\nTracing Booth's algorithm...")
    n, M_bin, neg_M_bin, Q_bin, steps, final_bin, prod_val = run_booth_algorithm(M_dec, Q_dec)
    
    print(f"  Calculated optimal bit-width: n = {n} bits")
    print(f"  Multiplicand M : {M_dec} (binary: {M_bin})")
    print(f"  Negation -M    : {-M_dec} (binary: {neg_M_bin})")
    print(f"  Multiplier Q   : {Q_dec} (binary: {Q_bin})")
    print(f"  Expected Product: {M_dec * Q_dec}")
    
    # 4. Define temporary render directory (avoiding apostrophes/quotes to prevent FFmpeg demuxer bugs)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.abspath(os.path.join(script_dir, "..", "booth_temp"))
    os.makedirs(temp_dir, exist_ok=True)
    
    # 5. Generate Manim code inside temp_dir
    generate_manim_file(M_dec, Q_dec, n, M_bin, neg_M_bin, Q_bin, steps, final_bin, prod_val, temp_dir)
    
    # 6. Add FFmpeg to PATH inside python and run Manim
    print("\nSetting up rendering environment...")
    ffmpeg_dir = r"C:\Users\Abhinav\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin"
    
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"  FFmpeg located and added to environment path: {ffmpeg_dir}")
    else:
        print("  WARNING: FFmpeg directory from winget was not found.")
        print("  We will attempt to run manim using the system PATH.")
        
    scene_path = os.path.join(temp_dir, "temp_booth_scene.py")
    
    print("\nRendering Manim animation. Please wait...")
    cmd = [sys.executable, "-m", "manim", scene_path, "BoothMultiplication", quality_flag]
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run Manim inside temp_dir
        result = subprocess.run(cmd, check=True, cwd=temp_dir)
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("         ANIMATION RENDERED SUCCESSFULLY!")
            print("=" * 60)
            
            # Find the output file
            # Manim standard path is temp_dir/media/videos/temp_booth_scene/<quality>/BoothMultiplication.mp4
            quality_folder = "480p15"
            if quality_flag == "-qm":
                quality_folder = "720p30"
            elif quality_flag == "-qh":
                quality_folder = "1080p60"
                
            temp_out_video = os.path.abspath(os.path.join(temp_dir, "media", "videos", "temp_booth_scene", quality_folder, "BoothMultiplication.mp4"))
            
            # Define final target path inside "booth's multiplication"
            target_video_dir = os.path.join(script_dir, "media", "videos", "temp_booth_scene", quality_folder)
            os.makedirs(target_video_dir, exist_ok=True)
            target_out_video = os.path.abspath(os.path.join(target_video_dir, "BoothMultiplication.mp4"))
            
            # Copy final compiled video to target directory and remove temp dir
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
