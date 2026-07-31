import os
import sys
import subprocess
import json
import shutil

def get_positive_int_input(prompt, allow_zero=True):
    """Safely get a positive integer input from the user."""
    while True:
        try:
            val_str = input(prompt).strip()
            if not val_str:
                continue
            val = int(val_str)
            if val < 0:
                print("Error: Please enter a positive integer (>= 0).")
                continue
            if not allow_zero and val == 0:
                print("Error: Divisor cannot be zero.")
                continue
            return val
        except ValueError:
            print("Error: Please enter a valid integer.")

def get_min_bits_unsigned(dividend, divisor):
    """
    Calculate the minimum number of bits required to represent both the 
    dividend and divisor as unsigned binary numbers (minimum 4 bits).
    """
    max_val = max(dividend, divisor)
    for n in range(4, 32):
        if max_val < (1 << n):
            return n
    return 8  # fallback default

def to_bin(val, bits):
    """Convert an integer to its unsigned binary representation of length 'bits'."""
    return bin(val)[2:].zfill(bits)

def run_non_restoring_division(dividend, divisor):
    """
    Trace the Non-Restoring Division algorithm step-by-step.
    Returns: (n_bits, M_bin, neg_M_bin, Q_bin, steps_data, post_correction, final_Q, final_A)
    """
    n = get_min_bits_unsigned(dividend, divisor)
    
    M_bin = to_bin(divisor, n)
    # For subtraction, we need the 2's complement of M of length n bits
    neg_M_val = (-divisor) & ((1 << n) - 1)
    neg_M_bin = to_bin(neg_M_val, n)
    Q_bin = to_bin(dividend, n)
    
    steps = []
    
    A = 0
    Q = dividend
    M = divisor
    
    for step_num in range(1, n + 1):
        old_A_str = to_bin(A, n)
        old_Q_str = to_bin(Q, n)
        
        # 0. Get the sign bit of A BEFORE shift (determines addition vs subtraction)
        prev_sign_A = (A >> (n - 1)) & 1
        
        # 1. Combined Shift Left (A, Q) by 1 bit
        msb_Q = (Q >> (n - 1)) & 1
        A_shifted = ((A << 1) | msb_Q) & ((1 << n) - 1)
        Q_shifted = (Q << 1) & ((1 << n) - 1)  # LSB is 0
        
        A_shifted_str = to_bin(A_shifted, n)
        Q_shifted_str = to_bin(Q_shifted, n)
        
        # 2. Perform conditional arithmetic based on prev_sign_A
        if prev_sign_A == 0:
            # Positive: Subtract M from A
            A_op = (A_shifted - M) & ((1 << n) - 1)
            op_type = "Subtract"
        else:
            # Negative: Add M to A
            A_op = (A_shifted + M) & ((1 << n) - 1)
            op_type = "Add"
            
        A_op_str = to_bin(A_op, n)
        
        # 3. Determine quotient bit Q0 based on the sign of the result
        new_sign_A = (A_op >> (n - 1)) & 1
        if new_sign_A == 0:
            Q_final = Q_shifted | 1
            action = f"{op_type} (Set Q0 = 1)"
        else:
            Q_final = Q_shifted  # LSB remains 0
            action = f"{op_type} (Set Q0 = 0)"
            
        A_final_str = to_bin(A_op, n)
        Q_final_str = to_bin(Q_final, n)
        
        steps.append({
            "step": step_num,
            "old_A": old_A_str,
            "old_Q": old_Q_str,
            "prev_sign_A": str(prev_sign_A),
            "A_shifted": A_shifted_str,
            "Q_shifted": Q_shifted_str,
            "op_type": op_type,
            "A_op": A_op_str,
            "new_sign_A": str(new_sign_A),
            "action": action,
            "new_A": A_final_str,
            "new_Q": Q_final_str
        })
        
        # Update state registers
        A = A_op
        Q = Q_final
        
    # 4. Post-correction step
    # If final remainder in A is negative, add M to correct it
    final_sign_A = (A >> (n - 1)) & 1
    post_correction = {
        "needed": False,
        "old_A": to_bin(A, n),
        "new_A": to_bin(A, n)
    }
    
    if final_sign_A == 1:
        corrected_A = (A + M) & ((1 << n) - 1)
        post_correction["needed"] = True
        post_correction["new_A"] = to_bin(corrected_A, n)
        A = corrected_A
        
    final_A_str = to_bin(A, n)
    final_Q_str = to_bin(Q, n)
    
    return n, M_bin, neg_M_bin, Q_bin, steps, post_correction, final_Q_str, final_A_str

def generate_manim_file(dividend, divisor, n, M_bin, neg_M_bin, Q_bin, steps, post_correction, final_Q, final_A, temp_dir):
    """Write the temp_non_restoring_scene.py file containing the Manim code in the temp_dir."""
    
    # Python-serialize using repr to preserve booleans (True/False instead of true/false)
    steps_repr = repr(steps)
    post_correction_repr = repr(post_correction)
    
    code = f"""# Generated Manim code for Non-Restoring Division Algorithm
from manim import *
import numpy as np

# Config data
dividend = {dividend}
divisor = {divisor}
n = {n}
M_bin = "{M_bin}"
neg_M_bin = "{neg_M_bin}"
Q_bin = "{Q_bin}"
final_Q = "{final_Q}"
final_A = "{final_A}"

steps_data = {steps_repr}
post_correction = {post_correction_repr}

class NonRestoringDivision(Scene):
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
        title = Text("Non-Restoring Division Algorithm", font_size=28, color=BLUE, font="Arial")
        title.to_edge(UP, buff=0.3)
        
        subtitle = Text(
            f"Dividend (Q) = {{dividend}} ({{Q_bin}})   |   Divisor (M) = {{divisor}} ({{M_bin}})", 
            font_size=15, color=WHITE, font="Arial"
        )
        subtitle.next_to(title, DOWN, buff=0.15)
        
        self.play(Write(title), FadeIn(subtitle))
        self.wait(0.5)
        
        # 2. Constants Panel (Top Right)
        constants_box = VGroup(
            Text(f" M = {{M_bin}} ({{divisor}})", font_size=14, font="Courier New", color=BLUE_B),
            Text(f"-M = {{neg_M_bin}}", font_size=14, font="Courier New", color=RED_B)
        )
        constants_box.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        constants_box_container = VGroup(
            RoundedRectangle(corner_radius=0.1, stroke_color=GRAY_E, fill_color="#18181C", fill_opacity=0.8).stretch_to_fit_width(2.6).stretch_to_fit_height(0.9),
            constants_box
        )
        constants_box.move_to(constants_box_container)
        constants_box_container.to_edge(UR, buff=0.4).shift(DOWN * 0.2)
        
        self.play(FadeIn(constants_box_container))
        
        # 3. Create Registers (A and Q)
        reg_A = create_register("Register A (Remainder)", n, TEAL)
        reg_Q = create_register("Register Q (Quotient)", n, ORANGE)
        
        registers = VGroup(reg_A, reg_Q)
        registers.arrange(RIGHT, buff=0.8)
        registers.move_to(np.array([-2.2, 0.8, 0.0]))
        
        # Initialize text labels in registers A=0, Q=dividend
        reg_A.labels = VGroup(*[
            Text("0", font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
            for box in reg_A.boxes
        ])
        reg_Q.labels = VGroup(*[
            Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
            for char, box in zip(Q_bin, reg_Q.boxes)
        ])
        
        self.play(
            FadeIn(reg_A),
            FadeIn(reg_Q),
            FadeIn(reg_A.labels),
            FadeIn(reg_Q.labels),
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
        cond_text = Text("Sign of A: --", font_size=13, font="Arial", color=WHITE)
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
            if "Set Q0 = 1" in action:
                op_short = "SHL, " + ("Sub" if "Subtract" in action else "Add") + ", Q0=1"
            else:
                op_short = "SHL, " + ("Sub" if "Subtract" in action else "Add") + ", Q0=0"
            trace_items.append(Text(f"Step {{step_num}}: {{op_short}}", font_size=13, font="Arial", color=GRAY))
            
        if post_correction["needed"]:
            trace_items.append(Text("Correction: Add M", font_size=13, font="Arial", color=GRAY))
            
        trace_items.append(Text("Final Product", font_size=13, font="Arial", color=GRAY))
        
        trace_panel = VGroup(*trace_items).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        trace_panel.move_to(trace_box.get_center())
        
        self.play(FadeIn(trace_box), FadeIn(trace_title_label), FadeIn(trace_panel))
        
        # Highlight "Initial State" trace
        self.play(trace_items[0].animate.set_color(YELLOW), run_time=0.3)
        self.wait(1.0)
        
        # Loop through Division steps
        for i, step in enumerate(steps_data):
            step_num = step["step"]
            old_A = step["old_A"]
            old_Q = step["old_Q"]
            prev_sign_A = step["prev_sign_A"]
            A_shifted = step["A_shifted"]
            Q_shifted = step["Q_shifted"]
            op_type = step["op_type"]
            A_op = step["A_op"]
            new_sign_A = step["new_sign_A"]
            action = step["action"]
            new_A = step["new_A"]
            new_Q = step["new_Q"]
            
            # --- PHASE A: CHECK INITIAL SIGN & UPDATE PANEL ---
            new_step_text = Text(f"Step: {{step_num}} / {{n}}", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
            
            if prev_sign_A == "0":
                sign_str = "A is Positive (MSB=0)"
                act_str = "Action: Shift Left, then Subtract M"
                sign_color = GREEN_B
            else:
                sign_str = "A is Negative (MSB=1)"
                act_str = "Action: Shift Left, then Add M"
                sign_color = RED_B
                
            new_cond_text = Text(sign_str, font_size=13, font="Arial", color=sign_color).move_to(cond_text.get_center())
            new_act_text = Text(act_str, font_size=13, font="Arial", color=GOLD_B).move_to(act_text.get_center())
            
            self.play(
                Transform(step_text, new_step_text),
                Transform(cond_text, new_cond_text),
                Transform(act_text, new_act_text),
                trace_items[i].animate.set_color(GRAY_C),
                trace_items[i+1].animate.set_color(YELLOW),
                run_time=0.4
            )
            
            # Highlight MSB of A
            msb_check_highlight = reg_A.boxes[0].copy().set_stroke(YELLOW, width=5).set_fill(YELLOW, opacity=0.15)
            self.play(FadeIn(msb_check_highlight), run_time=0.4)
            self.wait(0.6)
            self.play(FadeOut(msb_check_highlight), run_time=0.3)
            
            # --- PHASE B: SHIFT LEFT ---
            shift_anims = []
            
            # A[0] fades out
            shift_anims.append(FadeOut(reg_A.labels[0]))
            
            # A[1:] shifts left
            for idx in range(1, n):
                shift_anims.append(reg_A.labels[idx].animate.move_to(reg_A.boxes[idx - 1].get_center()))
                
            # Q[0] shifts to A[n-1]
            shift_anims.append(reg_Q.labels[0].animate.move_to(reg_A.boxes[-1].get_center()))
            
            # Q[1:] shifts left
            for idx in range(1, n):
                shift_anims.append(reg_Q.labels[idx].animate.move_to(reg_Q.boxes[idx - 1].get_center()))
                
            # Fade in temporary "0" at Q[n-1]
            temp_q0_label = Text("0", font_size=20, font="Courier New", color=GRAY_B)
            temp_q0_label.move_to(reg_Q.boxes[-1].get_center())
            shift_anims.append(FadeIn(temp_q0_label))
            
            self.play(*shift_anims, run_time=1.0)
            self.wait(0.4)
            
            # Clean swap shifted values
            self.remove(reg_A.labels, reg_Q.labels, temp_q0_label)
            
            reg_A.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(A_shifted, reg_A.boxes)
            ])
            reg_Q.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(Q_shifted, reg_Q.boxes)
            ])
            
            self.add(reg_A.labels, reg_Q.labels)
            self.wait(0.5)
            
            # --- PHASE C: ARITHMETIC (ADD OR SUBTRACT) ---
            # Update info panel
            new_cond_text = Text(f"Perform {{op_type}}", font_size=13, font="Arial", color=WHITE).move_to(cond_text.get_center())
            new_act_text = Text(f"Action: A <- A {{'-' if op_type == 'Subtract' else '+'}} M", font_size=13, font="Arial", color=YELLOW).move_to(act_text.get_center())
            self.play(
                Transform(cond_text, new_cond_text),
                Transform(act_text, new_act_text),
                run_time=0.3
            )
            
            # Create visual math scratchpad
            math_box = RoundedRectangle(
                corner_radius=0.1, width=4.2, height=2.2, stroke_color=YELLOW, stroke_width=2, 
                fill_color="#18181C", fill_opacity=0.95
            )
            math_box.move_to(np.array([-0.5, -1.8, 0.0]))
            math_title = Text(f"Arithmetic Sub-step ({{op_type}})", font_size=11, color=YELLOW, font="Arial").next_to(math_box, UP, aligned_edge=LEFT, buff=0.08)
            
            label_A = Text("A:", font_size=16, color=WHITE)
            value_A = Text(f"{{A_shifted}}", font_size=16, font="Courier New", color=WHITE)
            
            if op_type == "Subtract":
                label_M = Text("+ -M:", font_size=16, color=WHITE)
                value_M = Text(f"{{neg_M_bin}}", font_size=16, font="Courier New", color=WHITE)
            else:
                label_M = Text("+  M:", font_size=16, color=WHITE)
                value_M = Text(f"{{M_bin}}", font_size=16, font="Courier New", color=WHITE)
                
            label_Sum = Text("Sum:", font_size=16, color=YELLOW)
            value_Sum = Text(f"{{A_op}}", font_size=16, font="Courier New", color=YELLOW)
            
            labels_col = VGroup(label_A, label_M, label_Sum).arrange(DOWN, aligned_edge=RIGHT, buff=0.2)
            values_col = VGroup(value_A, value_M, value_Sum).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            values_col.next_to(labels_col, RIGHT, buff=0.3)
            
            math_elements = VGroup(labels_col, values_col)
            math_elements.move_to(math_box.get_center())
            
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
            
            # Flash A boxes to show update (A = A_op)
            flash_animations = [Flash(box, color=YELLOW, run_time=0.6, flash_radius=0.3) for box in reg_A.boxes]
            new_labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(A_op, reg_A.boxes)
            ])
            
            self.play(
                *flash_animations,
                Transform(reg_A.labels, new_labels),
                run_time=0.6
            )
            self.wait(0.8)
            self.play(FadeOut(math_group), run_time=0.5)
            
            # --- PHASE D: SIGN CHECK OF RESULT & SET Q0 ---
            msb_highlight = reg_A.boxes[0].copy().set_stroke(YELLOW, width=5).set_fill(YELLOW, opacity=0.15)
            self.play(FadeIn(msb_highlight), run_time=0.4)
            self.wait(0.5)
            
            if new_sign_A == "1":
                # Result is negative: Set Q0 = 0
                new_cond_text = Text("Result A is Negative (MSB=1)", font_size=13, font="Arial", color=RED_B).move_to(cond_text.get_center())
                new_act_text = Text("Set Q0 <- 0", font_size=13, font="Arial", color=RED).move_to(act_text.get_center())
                
                self.play(
                    Transform(cond_text, new_cond_text),
                    Transform(act_text, new_act_text),
                    run_time=0.3
                )
                self.wait(0.5)
                
                # Flash Q_0 red
                self.play(
                    Flash(reg_Q.boxes[-1], color=RED, run_time=0.6, flash_radius=0.3),
                    reg_Q.labels[-1].animate.set_color(RED_B),
                    run_time=0.6
                )
            else:
                # Result is positive: Set Q0 = 1
                new_cond_text = Text("Result A is Positive (MSB=0)", font_size=13, font="Arial", color=GREEN_B).move_to(cond_text.get_center())
                new_act_text = Text("Set Q0 <- 1", font_size=13, font="Arial", color=GREEN).move_to(act_text.get_center())
                
                self.play(
                    Transform(cond_text, new_cond_text),
                    Transform(act_text, new_act_text),
                    run_time=0.3
                )
                self.wait(0.5)
                
                # Transform Q_0 label from 0 to 1 with green flash
                new_q0_val = Text("1", font_size=20, font="Courier New", color=GREEN_A).move_to(reg_Q.boxes[-1].get_center())
                self.play(
                    Flash(reg_Q.boxes[-1], color=GREEN, run_time=0.6, flash_radius=0.3),
                    Transform(reg_Q.labels[-1], new_q0_val),
                    run_time=0.6
                )
                
            self.play(FadeOut(msb_highlight), run_time=0.3)
            
            # Swap labels to static values with white color
            self.remove(reg_A.labels, reg_Q.labels)
            
            reg_A.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(new_A, reg_A.boxes)
            ])
            reg_Q.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(new_Q, reg_Q.boxes)
            ])
            
            self.add(reg_A.labels, reg_Q.labels)
            
            self.wait(0.8)
            
        # --- PHASE E: POST-CORRECTION STEP ---
        trace_idx = len(steps_data)
        if post_correction["needed"]:
            # Highlight Correction trace
            self.play(
                trace_items[trace_idx].animate.set_color(GRAY_C),
                trace_items[trace_idx+1].animate.set_color(YELLOW),
                run_time=0.4
            )
            
            # Update Info Panel
            new_step_text = Text("Post-Correction", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
            new_cond_text = Text("Final Remainder A is Negative", font_size=13, font="Arial", color=RED_B).move_to(cond_text.get_center())
            new_act_text = Text("Action: Add M to A to restore", font_size=13, font="Arial", color=YELLOW).move_to(act_text.get_center())
            
            self.play(
                Transform(step_text, new_step_text),
                Transform(cond_text, new_cond_text),
                Transform(act_text, new_act_text),
                run_time=0.4
            )
            
            # Highlight MSB of A
            msb_post_highlight = reg_A.boxes[0].copy().set_stroke(YELLOW, width=5).set_fill(YELLOW, opacity=0.15)
            self.play(FadeIn(msb_post_highlight), run_time=0.4)
            self.wait(0.6)
            self.play(FadeOut(msb_post_highlight), run_time=0.3)
            
            # Math Scratchpad for Correction
            math_box_corr = RoundedRectangle(
                corner_radius=0.1, width=4.2, height=2.2, stroke_color=GREEN, stroke_width=2, 
                fill_color="#18181C", fill_opacity=0.95
            )
            math_box_corr.move_to(np.array([-0.5, -1.8, 0.0]))
            math_title_corr = Text("Correction Sub-step (A + M)", font_size=11, color=GREEN, font="Arial").next_to(math_box_corr, UP, aligned_edge=LEFT, buff=0.08)
            
            c_label_A = Text("A:", font_size=16, color=WHITE)
            c_value_A = Text(f"{{post_correction['old_A']}}", font_size=16, font="Courier New", color=WHITE)
            c_label_M = Text("+  M:", font_size=16, color=WHITE)
            c_value_M = Text(f"{{M_bin}}", font_size=16, font="Courier New", color=WHITE)
            c_label_Sum = Text("Sum:", font_size=16, color=GREEN)
            c_value_Sum = Text(f"{{post_correction['new_A']}}", font_size=16, font="Courier New", color=GREEN)
            
            c_labels_col = VGroup(c_label_A, c_label_M, c_label_Sum).arrange(DOWN, aligned_edge=RIGHT, buff=0.2)
            c_values_col = VGroup(c_value_A, c_value_M, c_value_Sum).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            c_values_col.next_to(c_labels_col, RIGHT, buff=0.3)
            
            c_math_elements = VGroup(c_labels_col, c_values_col)
            c_math_elements.move_to(math_box_corr.get_center())
            
            c_divider = Line(
                start=c_labels_col.get_left() + LEFT*0.1,
                end=c_values_col.get_right() + RIGHT*0.1,
                stroke_width=1.5,
                color=WHITE
            )
            c_divider.move_to(np.array([
                (c_labels_col.get_x() + c_values_col.get_x()) / 2,
                (c_labels_col[1].get_y() + c_labels_col[2].get_y()) / 2,
                0
            ]))
            
            math_group_corr = VGroup(math_box_corr, math_title_corr, c_labels_col, c_values_col, c_divider)
            
            self.play(FadeIn(math_group_corr), run_time=0.5)
            self.wait(1.0)
            
            # Flash A and update to corrected value
            flash_corr_anims = [Flash(box, color=GREEN, run_time=0.6, flash_radius=0.3) for box in reg_A.boxes]
            corrected_labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(post_correction["new_A"], reg_A.boxes)
            ])
            
            self.play(
                *flash_corr_anims,
                Transform(reg_A.labels, corrected_labels),
                run_time=0.6
            )
            self.wait(0.8)
            self.play(FadeOut(math_group_corr), run_time=0.5)
            
            # Swap labels
            self.remove(reg_A.labels)
            reg_A.labels = VGroup(*[
                Text(char, font_size=20, font="Courier New", color=WHITE).move_to(box.get_center()) 
                for char, box in zip(post_correction["new_A"], reg_A.boxes)
            ])
            self.add(reg_A.labels)
            self.wait(0.5)
            
            # Update trace pointer
            trace_idx += 1
            
        # Highlight last line of trace (Final Product)
        self.play(
            trace_items[trace_idx].animate.set_color(GRAY_C),
            trace_items[trace_idx+1].animate.set_color(YELLOW),
            run_time=0.4
        )
        
        # Update Info Panel
        new_step_text = Text(f"Done: {{n}} Steps Completed", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
        new_cond_text = Text("Quotient in Q, Remainder in A", font_size=13, font="Arial", color=WHITE).move_to(cond_text.get_center())
        new_act_text = Text(f"Q = {{final_Q}} | A = {{final_A}}", font_size=13, font="Arial", color=GREEN).move_to(act_text.get_center())
        
        self.play(
            Transform(step_text, new_step_text),
            Transform(cond_text, new_cond_text),
            Transform(act_text, new_act_text),
            run_time=0.4
        )
        
        # Draw boxes around remainder and quotient
        rem_box = SurroundingRectangle(reg_A.boxes, color=TEAL, stroke_width=3, buff=0.1)
        quot_box = SurroundingRectangle(reg_Q.boxes, color=ORANGE, stroke_width=3, buff=0.1)
        
        rem_label = Text("Remainder (A)", font_size=12, color=TEAL, font="Arial").next_to(rem_box, DOWN, buff=0.15)
        quot_label = Text("Quotient (Q)", font_size=12, color=ORANGE, font="Arial").next_to(quot_box, DOWN, buff=0.15)
        
        self.play(
            Create(rem_box), FadeIn(rem_label),
            Create(quot_box), FadeIn(quot_label),
            run_time=0.8
        )
        self.wait(1.0)
        
        # Final Summary verification card
        summary_box = RoundedRectangle(
            corner_radius=0.1, width=7.0, height=2.0, stroke_color=GREEN, stroke_width=2, 
            fill_color="#18181C", fill_opacity=0.9
        )
        summary_box.move_to(np.array([-1.2, -1.8, 0.0]))
        summary_title = Text("Verification Summary", font_size=12, color=GREEN, font="Arial").next_to(summary_box, UP, aligned_edge=LEFT, buff=0.08)
        
        q_val_dec = int(final_Q, 2)
        a_val_dec = int(final_A, 2)
        
        verify_line1 = Text(f"Dividend:  {{dividend}}  |  Divisor: {{divisor}}", font_size=14, font="Courier New", color=WHITE)
        verify_line2 = Text(f"Quotient:  {{final_Q}} ({{q_val_dec}})  |  Remainder: {{final_A}} ({{a_val_dec}})", font_size=14, font="Courier New", color=WHITE)
        verify_line3 = Text(f"{{dividend}} = ({{q_val_dec}} * {{divisor}}) + {{a_val_dec}}", font_size=14, font="Courier New", color=GREEN_A)
        
        summary_content = VGroup(verify_line1, verify_line2, verify_line3).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        summary_content.move_to(summary_box.get_center())
        
        self.play(
            FadeOut(info_box), FadeOut(info_title), FadeOut(step_text), FadeOut(cond_text), FadeOut(act_text),
            FadeIn(summary_box), FadeIn(summary_title), FadeIn(summary_content),
            run_time=0.8
        )
        self.wait(3.0)
"""
    
    scene_path = os.path.join(temp_dir, "temp_non_restoring_scene.py")
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Manim scene file '{scene_path}' generated successfully.")

def main():
    print("=" * 60)
    print("   NON-RESTORING DIVISION ALGORITHM MANIM VISUALIZER")
    print("=" * 60)
    print("This program runs the Non-Restoring Division algorithm and creates a step-by-step")
    print("animated demonstration video using Manim.")
    
    # 1. Get inputs
    dividend = get_positive_int_input("\nEnter Dividend Q (e.g. 7): ")
    divisor = get_positive_int_input("Enter Divisor M (e.g. 3): ", allow_zero=False)
    
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
        
    # 3. Trace Non-Restoring division
    print("\nTracing non-restoring division algorithm...")
    n, M_bin, neg_M_bin, Q_bin, steps, post_correction, final_Q, final_A = run_non_restoring_division(dividend, divisor)
    
    print(f"  Calculated optimal bit-width: n = {n} bits")
    print(f"  Dividend Q     : {dividend} (binary: {Q_bin})")
    print(f"  Divisor M      : {divisor} (binary: {M_bin})")
    print(f"  2's Comp of M  : {neg_M_bin}")
    print(f"  Expected Quotient: {dividend // divisor} (binary: {to_bin(dividend // divisor, n)})")
    print(f"  Expected Remainder: {dividend % divisor} (binary: {to_bin(dividend % divisor, n)})")
    if post_correction["needed"]:
        print(f"  Note: Remainder requires post-correction (addition of M) at the end.")
        
    # 4. Define temporary render directory (avoiding apostrophes/quotes to prevent FFmpeg demuxer bugs)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.abspath(os.path.join(script_dir, "..", "non_restoring_temp"))
    os.makedirs(temp_dir, exist_ok=True)
    
    # 5. Generate Manim code inside temp_dir
    generate_manim_file(dividend, divisor, n, M_bin, neg_M_bin, Q_bin, steps, post_correction, final_Q, final_A, temp_dir)
    
    # 6. Add FFmpeg to PATH inside python and run Manim
    print("\nSetting up rendering environment...")
    ffmpeg_dir = r"C:\Users\Abhinav\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin"
    
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"  FFmpeg located and added to environment path: {ffmpeg_dir}")
    else:
        print("  WARNING: FFmpeg directory from winget was not found.")
        print("  We will attempt to run manim using the system PATH.")
        
    scene_path = os.path.join(temp_dir, "temp_non_restoring_scene.py")
    
    print("\nRendering Manim animation. Please wait...")
    cmd = [sys.executable, "-m", "manim", scene_path, "NonRestoringDivision", quality_flag]
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
                
            temp_out_video = os.path.abspath(os.path.join(temp_dir, "media", "videos", "temp_non_restoring_scene", quality_folder, "NonRestoringDivision.mp4"))
            
            # Define final target path inside "non-restoring division"
            target_video_dir = os.path.join(script_dir, "media", "videos", "temp_non_restoring_scene", quality_folder)
            os.makedirs(target_video_dir, exist_ok=True)
            target_out_video = os.path.abspath(os.path.join(target_video_dir, "NonRestoringDivision.mp4"))
            
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
