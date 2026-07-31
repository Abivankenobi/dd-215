import os
import sys
import subprocess
import json
import shutil

def get_positive_int_input(prompt):
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
            return val
        except ValueError:
            print("Error: Please enter a valid integer.")

def get_min_bits_unsigned(val_a, val_b):
    """
    Calculate the minimum number of bits required to represent the sum of 
    val_a and val_b without overflow (minimum 4 bits).
    Since it's an n-bit addition, we want n bits to cover both inputs.
    If the sum overflows n bits, that's fine, the serial adder's final DFF holds the carry.
    So we choose n to fit both inputs.
    """
    max_val = max(val_a, val_b)
    for n in range(4, 32):
        if max_val < (1 << n):
            return n
    return 8  # fallback default

def to_bin(val, bits):
    """Convert an integer to its unsigned binary representation of length 'bits'."""
    return bin(val)[2:].zfill(bits)

def run_serial_addition(val_a, val_b):
    """
    Trace the Serial Addition algorithm step-by-step.
    Returns: (n_bits, A_bin, B_bin, steps_data, final_sum_bin, final_carry)
    """
    n = get_min_bits_unsigned(val_a, val_b)
    
    A_bin = to_bin(val_a, n)
    B_bin = to_bin(val_b, n)
    
    steps = []
    
    A_str = A_bin
    B_str = B_bin
    C_val = 0
    
    for cycle in range(1, n + 1):
        # LSBs are at the end of the binary strings
        a_bit = int(A_str[n - 1])
        b_bit = int(B_str[n - 1])
        cin = C_val
        
        sum_bit = a_bit ^ b_bit ^ cin
        cout_bit = (a_bit & b_bit) | (cin & (a_bit ^ b_bit))
        
        # Shift Register A: sum_bit enters MSB, LSB is discarded
        A_next = str(sum_bit) + A_str[:-1]
        
        # Shift Register B: '0' enters MSB, LSB is discarded
        B_next = "0" + B_str[:-1]
        
        steps.append({
            "cycle": cycle,
            "old_A": A_str,
            "old_B": B_str,
            "a_bit": str(a_bit),
            "b_bit": str(b_bit),
            "cin": str(cin),
            "sum_bit": str(sum_bit),
            "cout_bit": str(cout_bit),
            "new_A": A_next,
            "new_B": B_next,
            "new_cin": str(cout_bit)
        })
        
        # Update states
        A_str = A_next
        B_str = B_next
        C_val = cout_bit
        
    return n, A_bin, B_bin, steps, A_str, C_val

def generate_manim_file(val_a, val_b, n, A_bin, B_bin, steps, final_sum_bin, final_carry, temp_dir):
    """Write the temp_serial_adder_scene.py file containing the Manim code in the temp_dir."""
    
    steps_repr = repr(steps)
    
    code = f"""# Generated Manim code for Serial Adder Algorithm
from manim import *
import numpy as np

# Config data
val_a = {val_a}
val_b = {val_b}
n = {n}
A_bin = "{A_bin}"
B_bin = "{B_bin}"
final_sum_bin = "{final_sum_bin}"
final_carry = {final_carry}

steps_data = {steps_repr}

class SerialAdder(Scene):
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
        title = Text("Serial Adder Hardware Simulation", font_size=28, color=BLUE, font="Arial")
        title.to_edge(UP, buff=0.3)
        
        subtitle = Text(
            f"Input A = {{val_a}} ({{A_bin}})   |   Input B = {{val_b}} ({{B_bin}})", 
            font_size=15, color=WHITE, font="Arial"
        )
        subtitle.next_to(title, DOWN, buff=0.15)
        
        self.play(Write(title), FadeIn(subtitle))
        self.wait(0.5)
        
        # 2. Register Layout
        reg_A = create_register("Register A (Accumulator / Sum)", n, TEAL)
        reg_B = create_register("Register B (Addend)", n, ORANGE)
        
        registers = VGroup(reg_A, reg_B)
        reg_A.move_to(np.array([-2.5, 1.5, 0.0]))
        reg_B.move_to(np.array([-2.5, -0.5, 0.0]))
        
        # Initialize text labels in registers using index loops
        reg_A.labels = VGroup(*[
            Text(A_bin[idx], font_size=20, font="Courier New", color=WHITE).move_to(reg_A.boxes[idx].get_center()) 
            for idx in range(n)
        ])
        reg_B.labels = VGroup(*[
            Text(B_bin[idx], font_size=20, font="Courier New", color=WHITE).move_to(reg_B.boxes[idx].get_center()) 
            for idx in range(n)
        ])
        
        self.play(
            FadeIn(reg_A), 
            FadeIn(reg_B), 
            FadeIn(reg_A.labels), 
            FadeIn(reg_B.labels), 
            run_time=0.8
        )
        
        # 3. Hardware Blocks
        # Full Adder (FA) Box
        fa_box = Rectangle(width=2.2, height=1.6, stroke_color=BLUE, fill_color="#18181C", fill_opacity=0.9)
        fa_box.move_to(np.array([1.2, 0.5, 0.0]))
        fa_label = Text("Full Adder", font_size=14, color=BLUE, font="Arial").move_to(fa_box.get_center() + UP*0.4)
        fa_expr = Text("S = A ⊕ B ⊕ Cin\\nCout = AB + Cin(A⊕B)", font_size=9, font="Courier New", color=GRAY_A).move_to(fa_box.get_center() + DOWN*0.2)
        fa_group = VGroup(fa_box, fa_label, fa_expr)
        
        # Carry D Flip-flop (DFF) Box
        dff_box = Rectangle(width=1.8, height=1.0, stroke_color=PURPLE, fill_color="#18181C", fill_opacity=0.9)
        dff_box.move_to(np.array([1.2, -1.8, 0.0]))
        dff_label_title = Text("Carry DFF", font_size=12, color=PURPLE, font="Arial").next_to(dff_box, UP, buff=0.08)
        dff_stored_title = Text("Stored carry:", font_size=9, color=GRAY_B, font="Arial").move_to(dff_box.get_center() + UP*0.22)
        dff_label = Text("0", font_size=24, font="Courier New", color=PURPLE_A).move_to(dff_box.get_center() + DOWN*0.18)
        
        # DFF Clock Input Triangle
        clk_triangle = Triangle(stroke_color=PURPLE, stroke_width=2).scale(0.08).rotate(-PI/2).move_to(dff_box.get_left())
        
        dff_group = VGroup(dff_box, dff_label_title, dff_stored_title, dff_label, clk_triangle)
        
        self.play(FadeIn(fa_group), FadeIn(dff_group), run_time=0.8)
        
        # 4. Connecting Signal Wires
        # Wire A (LSB of Reg A to FA top-left input)
        wire_A = Arrow(
            start=reg_A.boxes[-1].get_right(), 
            end=fa_box.get_left() + UP*0.4, 
            stroke_color=GRAY_D, stroke_width=2, buff=0.05
        )
        label_wire_A = Text("a_i", font_size=10, color=TEAL).next_to(wire_A.get_center(), UP*0.5).shift(LEFT*0.2)
        
        # Wire B (LSB of Reg B to FA middle-left input)
        wire_B = Arrow(
            start=reg_B.boxes[-1].get_right(), 
            end=fa_box.get_left() + DOWN*0.1, 
            stroke_color=GRAY_D, stroke_width=2, buff=0.05
        )
        label_wire_B = Text("b_i", font_size=10, color=ORANGE).next_to(wire_B.get_center(), UP*0.5).shift(LEFT*0.2)
        
        # Wire Cin (DFF output to FA bottom-left input)
        wire_cin = Arrow(
            start=dff_box.get_top() + LEFT*0.4, 
            end=fa_box.get_bottom() + LEFT*0.4, 
            stroke_color=GRAY_D, stroke_width=2, buff=0.05
        )
        label_wire_cin = Text("Cin", font_size=10, color=PURPLE).next_to(wire_cin.get_center(), LEFT*0.5)
        
        # Wire Cout (FA carry-out to DFF carry input)
        wire_cout = Arrow(
            start=fa_box.get_bottom() + RIGHT*0.4, 
            end=dff_box.get_top() + RIGHT*0.4, 
            stroke_color=GRAY_D, stroke_width=2, buff=0.05
        )
        label_wire_cout = Text("Cout", font_size=10, color=RED_B).next_to(wire_cout.get_center(), RIGHT*0.5)
        
        # Wire Sum Feedback Path: from FA Sum output (right) looping back to Reg A serial input (left)
        p1 = fa_box.get_right()
        p2 = p1 + RIGHT * 0.6
        p3 = np.array([p2[0], reg_A.boxes[0].get_top()[1] + 0.8, 0.0])
        p4 = np.array([reg_A.boxes[0].get_top()[0], p3[1], 0.0])
        p5 = reg_A.boxes[0].get_top()
        
        sum_wire = VMobject(color=GRAY_D, stroke_width=2)
        sum_wire.set_points_as_corners([p1, p2, p3, p4, p5])
        
        # Add an arrowhead at the end of the sum feedback wire dropping into Reg A
        sum_arrowhead = Arrow(start=p4, end=p5, stroke_color=GRAY_D, stroke_width=2, buff=0.05)
        label_wire_sum = Text("Sum Feedback (s_i)", font_size=10, color=GREEN_B).next_to(p4, UP*0.4).shift(RIGHT*1.5)
        
        self.play(
            Create(wire_A), FadeIn(label_wire_A),
            Create(wire_B), FadeIn(label_wire_B),
            Create(wire_cin), FadeIn(label_wire_cin),
            Create(wire_cout), FadeIn(label_wire_cout),
            Create(sum_wire), Create(sum_arrowhead), FadeIn(label_wire_sum),
            run_time=1.0
        )
        
        # 5. Bottom Info Panel (Logic Description)
        info_box = Rectangle(
            width=4.0, height=1.6, stroke_color=GRAY_D, stroke_width=1, 
            fill_color="#18181C", fill_opacity=0.85
        )
        info_box.to_edge(DL, buff=0.5).shift(UP * 0.1)
        info_title = Text("CURRENT OPERATION", font_size=11, color=GRAY_B, font="Arial")
        info_title.next_to(info_box, UP, aligned_edge=LEFT, buff=0.08)
        
        step_text = Text("Clock Cycle: --", font_size=13, font="Arial", color=WHITE)
        cond_text = Text("Inputs: a_i=--, b_i=--, Cin=--", font_size=13, font="Arial", color=WHITE)
        act_text = Text("Outputs: s_i=--, Cout=--", font_size=13, font="Arial", color=YELLOW)
        
        texts_group = VGroup(step_text, cond_text, act_text).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        texts_group.move_to(info_box.get_center())
        
        self.play(FadeIn(info_box), FadeIn(info_title), FadeIn(texts_group))
        
        # 6. Right Trace Panel
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
            c_num = step["cycle"]
            trace_items.append(Text(f"Cycle {{c_num}}: Add LSBs & Shift", font_size=13, font="Arial", color=GRAY))
        trace_items.append(Text("Final Sum", font_size=13, font="Arial", color=GRAY))
        
        trace_panel = VGroup(*trace_items).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        trace_panel.move_to(trace_box.get_center())
        
        self.play(FadeIn(trace_box), FadeIn(trace_title_label), FadeIn(trace_panel))
        
        # Highlight "Initial State"
        self.play(trace_items[0].animate.set_color(YELLOW), run_time=0.3)
        self.wait(1.0)
        
        # Loop through Clock Cycles
        for idx, step in enumerate(steps_data):
            cycle = step["cycle"]
            old_A = step["old_A"]
            old_B = step["old_B"]
            a_bit = step["a_bit"]
            b_bit = step["b_bit"]
            cin = step["cin"]
            sum_bit = step["sum_bit"]
            cout_bit = step["cout_bit"]
            new_A = step["new_A"]
            new_B = step["new_B"]
            new_cin = step["new_cin"]
            
            # --- PHASE A: UPDATE INFO PANEL & HIGHLIGHT ACTIVE BITS ---
            new_step_text = Text(f"Clock Cycle: {{cycle}} / {{n}}", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
            new_cond_text = Text(f"Inputs: a_i={{a_bit}}, b_i={{b_bit}}, Cin={{cin}}", font_size=13, font="Arial", color=WHITE).move_to(cond_text.get_center())
            new_act_text = Text(f"Outputs: s_i={{sum_bit}}, Cout={{cout_bit}}", font_size=13, font="Arial", color=YELLOW).move_to(act_text.get_center())
            
            self.play(
                step_text.animate.become(new_step_text),
                cond_text.animate.become(new_cond_text),
                act_text.animate.become(new_act_text),
                trace_items[idx].animate.set_color(GRAY_C),
                trace_items[idx+1].animate.set_color(YELLOW),
                run_time=0.4
            )
            
            # Highlight source cells: Reg A LSB, Reg B LSB, DFF state
            src_highlights = VGroup(
                reg_A.boxes[-1].copy().set_stroke(YELLOW, width=4).set_fill(YELLOW, opacity=0.15),
                reg_B.boxes[-1].copy().set_stroke(YELLOW, width=4).set_fill(YELLOW, opacity=0.15),
                dff_box.copy().set_stroke(YELLOW, width=4).set_fill(YELLOW, opacity=0.15)
            )
            self.play(FadeIn(src_highlights), run_time=0.4)
            self.wait(0.6)
            self.play(FadeOut(src_highlights), run_time=0.3)
            
            # --- PHASE B: SIGNAL PROPAGATION TO FULL ADDER ---
            # Create flying bit clones (changed ORANGE_A to ORANGE)
            a_clone = Text(a_bit, font_size=18, font="Courier New", color=TEAL_A).move_to(reg_A.boxes[-1].get_center())
            b_clone = Text(b_bit, font_size=18, font="Courier New", color=ORANGE).move_to(reg_B.boxes[-1].get_center())
            cin_clone = Text(cin, font_size=18, font="Courier New", color=PURPLE_A).move_to(dff_box.get_center())
            
            self.play(
                a_clone.animate.move_to(fa_box.get_left() + UP*0.4),
                b_clone.animate.move_to(fa_box.get_left() + DOWN*0.1),
                cin_clone.animate.move_to(fa_box.get_bottom() + LEFT*0.4),
                run_time=0.8
            )
            
            # Flash FA to show computation
            self.play(
                FadeOut(a_clone), FadeOut(b_clone), FadeOut(cin_clone),
                Flash(fa_box, color=BLUE, flash_radius=0.5),
                run_time=0.5
            )
            self.wait(0.2)
            
            # --- PHASE C: OUTPUT PROPAGATION ---
            sum_out = Text(sum_bit, font_size=18, font="Courier New", color=GREEN_A).move_to(fa_box.get_right())
            cout_out = Text(cout_bit, font_size=18, font="Courier New", color=RED_B).move_to(fa_box.get_bottom() + RIGHT*0.4)
            
            self.play(FadeIn(sum_out), FadeIn(cout_out), run_time=0.4)
            
            # Propagate Cout to DFF and Sum along loop path
            self.play(
                MoveAlongPath(sum_out, sum_wire),
                cout_out.animate.move_to(dff_box.get_center()),
                run_time=1.2
            )
            self.wait(0.3)
            
            # --- PHASE D: CLOCK TRIGGER & REGISTER SHIFTING ---
            # Flash clock triangle input on DFF to show active clock edge
            self.play(Flash(clk_triangle, color=YELLOW, flash_radius=0.2), run_time=0.3)
            
            shift_anims = []
            
            # Register A Shifting: LSB fades, other elements move right, sum_out moves to MSB
            shift_anims.append(FadeOut(reg_A.labels[-1]))
            for cell_idx in range(n - 1):
                shift_anims.append(reg_A.labels[cell_idx].animate.move_to(reg_A.boxes[cell_idx + 1].get_center()))
            shift_anims.append(sum_out.animate.move_to(reg_A.boxes[0].get_center()))
            
            # Register B Shifting: LSB fades, other elements move right, '0' enters MSB
            shift_anims.append(FadeOut(reg_B.labels[-1]))
            for cell_idx in range(n - 1):
                shift_anims.append(reg_B.labels[cell_idx].animate.move_to(reg_B.boxes[cell_idx + 1].get_center()))
            
            new_b_msb = Text("0", font_size=20, font="Courier New", color=GRAY_B).move_to(reg_B.boxes[0].get_center())
            shift_anims.append(FadeIn(new_b_msb))
            
            # Carry DFF value update: DFF flashes, updates stored carry label
            shift_anims.append(Flash(dff_box, color=PURPLE, flash_radius=0.4))
            new_dff_label = Text(cout_bit, font_size=24, font="Courier New", color=PURPLE_A).move_to(dff_box.get_center())
            shift_anims.append(dff_label.animate.become(new_dff_label))
            shift_anims.append(FadeOut(cout_out))
            
            self.play(*shift_anims, run_time=1.0)
            self.wait(0.5)
            
            # Clean swap register labels for next cycle
            self.remove(reg_A.labels, reg_B.labels, sum_out, new_b_msb)
            
            reg_A.labels = VGroup(*[
                Text(new_A[idx], font_size=20, font="Courier New", color=WHITE).move_to(reg_A.boxes[idx].get_center()) 
                for idx in range(n)
            ])
            reg_B.labels = VGroup(*[
                Text(new_B[idx], font_size=20, font="Courier New", color=WHITE).move_to(reg_B.boxes[idx].get_center()) 
                for idx in range(n)
            ])
            
            self.add(reg_A.labels, reg_B.labels)
            
            self.wait(0.8)
            
        # --- END OF LOOP: FINAL SUMMARY ---
        # Highlight "Final Sum" trace
        self.play(
            trace_items[-2].animate.set_color(GRAY_C),
            trace_items[-1].animate.set_color(YELLOW),
            run_time=0.4
        )
        
        # Update Info Panel
        new_step_text = Text("Serial Addition Complete", font_size=13, font="Arial", color=WHITE).move_to(step_text.get_center())
        new_cond_text = Text(f"Final Sum: {{final_sum_bin}}", font_size=13, font="Arial", color=GREEN).move_to(cond_text.get_center())
        new_act_text = Text(f"Final Carry: {{final_carry}}", font_size=13, font="Arial", color=PURPLE_B).move_to(act_text.get_center())
        
        self.play(
            step_text.animate.become(new_step_text),
            cond_text.animate.become(new_cond_text),
            act_text.animate.become(new_act_text),
            run_time=0.4
        )
        
        # Highlight Register A sum
        sum_outline = SurroundingRectangle(reg_A.boxes, color=GREEN, stroke_width=3, buff=0.1)
        sum_label = Text("Final Sum (Register A)", font_size=12, color=GREEN, font="Arial").next_to(sum_outline, DOWN, buff=0.15)
        self.play(Create(sum_outline), FadeIn(sum_label), run_time=0.8)
        self.wait(1.0)
        
        # Summary Card in center-bottom
        summary_box = RoundedRectangle(
            corner_radius=0.1, width=7.0, height=2.0, stroke_color=GREEN, stroke_width=2, 
            fill_color="#18181C", fill_opacity=0.9
        )
        summary_box.move_to(np.array([-1.2, -1.8, 0.0]))
        summary_title = Text("Verification Summary", font_size=12, color=GREEN, font="Arial").next_to(summary_box, UP, aligned_edge=LEFT, buff=0.08)
        
        sum_val_dec = int(final_sum_bin, 2)
        total_sum_expected = val_a + val_b
        
        verify_line1 = Text(f"Operand A: {{val_a}} ({{A_bin}})  |  Operand B: {{val_b}} ({{B_bin}})", font_size=14, font="Courier New", color=WHITE)
        verify_line2 = Text(f"Sum output: {{final_sum_bin}} ({{sum_val_dec}})  |  Final carry: {{final_carry}}", font_size=14, font="Courier New", color=WHITE)
        verify_line3 = Text(f"{{val_a}} + {{val_b}} = {{total_sum_expected}}", font_size=14, font="Courier New", color=GREEN_A)
        
        summary_content = VGroup(verify_line1, verify_line2, verify_line3).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        summary_content.move_to(summary_box.get_center())
        
        self.play(
            FadeOut(info_box), FadeOut(info_title), FadeOut(texts_group),
            FadeIn(summary_box), FadeIn(summary_title), FadeIn(summary_content),
            run_time=0.8
        )
        self.wait(3.0)
"""
    
    scene_path = os.path.join(temp_dir, "temp_serial_adder_scene.py")
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Manim scene file '{scene_path}' generated successfully.")

def main():
    print("=" * 60)
    print("   SERIAL ADDER HARDWARE ALGORITHM MANIM VISUALIZER")
    print("=" * 60)
    print("This program runs a Serial Adder circuit simulation and creates a step-by-step")
    print("animated demonstration video using Manim.")
    
    # 1. Get inputs
    val_a = get_positive_int_input("\nEnter Operand A (Augend) (e.g. 5): ")
    val_b = get_positive_int_input("Enter Operand B (Addend) (e.g. 6): ")
    
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
        
    # 3. Trace serial addition algorithm
    print("\nTracing serial addition...")
    n, A_bin, B_bin, steps, final_sum, final_carry = run_serial_addition(val_a, val_b)
    
    print(f"  Calculated optimal bit-width: n = {n} bits")
    print(f"  Operand A      : {val_a} (binary: {A_bin})")
    print(f"  Operand B      : {val_b} (binary: {B_bin})")
    print(f"  Expected Sum   : {val_a + val_b} (binary: {bin(val_a + val_b)[2:]})")
    print(f"  Final Carry-out: {final_carry}")
    
    # 4. Define temporary render directory (avoiding apostrophes/quotes to prevent FFmpeg demuxer bugs)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.abspath(os.path.join(script_dir, "..", "serial_temp"))
    os.makedirs(temp_dir, exist_ok=True)
    
    # 5. Generate Manim code inside temp_dir
    generate_manim_file(val_a, val_b, n, A_bin, B_bin, steps, final_sum, final_carry, temp_dir)
    
    # 6. Add FFmpeg to PATH inside python and run Manim
    print("\nSetting up rendering environment...")
    ffmpeg_dir = r"C:\Users\Abhinav\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin"
    
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"  FFmpeg located and added to environment path: {ffmpeg_dir}")
    else:
        print("  WARNING: FFmpeg directory from winget was not found.")
        print("  We will attempt to run manim using the system PATH.")
        
    scene_path = os.path.join(temp_dir, "temp_serial_adder_scene.py")
    
    print("\nRendering Manim animation. Please wait...")
    cmd = [sys.executable, "-m", "manim", scene_path, "SerialAdder", quality_flag]
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
                
            temp_out_video = os.path.abspath(os.path.join(temp_dir, "media", "videos", "temp_serial_adder_scene", quality_folder, "SerialAdder.mp4"))
            
            # Define final target path inside "serial adder"
            target_video_dir = os.path.join(script_dir, "media", "videos", "temp_serial_adder_scene", quality_folder)
            os.makedirs(target_video_dir, exist_ok=True)
            target_out_video = os.path.abspath(os.path.join(target_video_dir, "SerialAdder.mp4"))
            
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
