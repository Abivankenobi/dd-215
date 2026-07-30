# Computer Arithmetic & Digital Logic Manim Visualizers

An educational suite of interactive command-line programs that solve computer arithmetic and digital design algorithms, tracing their state cycles and compiling premium hardware-level circuit animations using **Manim**.

---

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Suite of Visualizers](#suite-of-visualizers)
  - [1. Booth's Multiplication Algorithm](#1-booths-multiplication-algorithm)
  - [2. Restoring Division Algorithm](#2-restoring-division-algorithm)
  - [3. Non-Restoring Division Algorithm](#3-non-restoring-division-algorithm)
  - [4. Serial Adder Hardware Simulation](#4-serial-adder-hardware-simulation)
  - [5. K-Map Solver & 3D Visualizer](#5-k-map-solver--3d-visualizer)
- [Video Rendering Customizations](#video-rendering-customizations)

---

## Prerequisites

To run these visualizers, you need:
1. **Python 3.8+**
2. **Manim** community version (`pip install manim`)
3. **FFmpeg** (automatically detected by the scripts from your Winget path if available, or should be in your system environment PATH)

---

## Installation

Clone this repository and navigate to the project directory:
```bash
git clone https://github.com/Abivankenobi/dd-215.git
cd dd-215
```

Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

---

## Suite of Visualizers

Every visualizer in this suite is interactive. Running any of the scripts will walk you through setting your inputs, picking your desired video quality, and compiling the video.

### 1. Booth's Multiplication Algorithm
- **Script Location**: `booth's multiplication/booth_visualizer.py`
- **Description**: Visualizes signed 2's complement multiplication.
- **Visual Features**: Placed-left register grids ($A$, $Q$, $Q_{-1}$), an active operation card that expands subtraction mathematically to $+ -M$ (addition of 2's complement value), and a right-aligned scrolling trace checklist history box.
- **How to Run**:
  ```powershell
  python "booth's multiplication/booth_visualizer.py"
  ```

### 2. Restoring Division Algorithm
- **Script Location**: `restoring division/restoring_division_visualizer.py`
- **Description**: Animates unsigned restoring binary division.
- **Visual Features**: Shift Left (SHL) animations sliding bits between registers, subtraction math pads, and conditional decision checks where the quotient bit $Q_0$ flashes Green (positive remainder, set to $1$, no restore) or Red (negative remainder, set to $0$, play restore addition $A + M$).
- **How to Run**:
  ```powershell
  python "restoring division/restoring_division_visualizer.py"
  ```

### 3. Non-Restoring Division Algorithm
- **Script Location**: `non-restoring division/non_restoring_division_visualizer.py`
- **Description**: Traces unsigned non-restoring division.
- **Visual Features**: Alternating conditional operations (SHL + Subtract if $A \ge 0$, SHL + Add if $A < 0$), intermediate sign cell checks, and a post-correction stage that automatically adds the divisor $M$ at the end if the final remainder in $A$ remains negative.
- **How to Run**:
  ```powershell
  python "non-restoring division/non_restoring_division_visualizer.py"
  ```

### 4. Serial Adder Hardware Simulation
- **Script Location**: `serial adder/serial_adder_visualizer.py`
- **Description**: A literal hardware circuit schematic simulation detailing serial addition.
- **Visual Features**:
  * **Shift Registers** A (teal) and B (orange).
  * **Full Adder block** showing inputs and outputs.
  * **Carry D Flip-Flop** displaying the stored carry with a flashing clock input triangle on each clock trigger.
  * **Signal Wires**: Bits are cloned and literally "slide" along connection wires into the Full Adder. The sum bit propagates along a long feedback wire that loops back around to drop into Register A's MSB while the registers shift right.
- **How to Run**:
  ```powershell
  python "serial adder/serial_adder_visualizer.py"
  ```

### 5. K-Map Solver & 3D Visualizer
- **Script Location**: `kmap solver/kmap_visualizer.py`
- **Description**: Solves K-Maps and renders a tabular Quine-McCluskey merge trace alongside visual K-Map grids.
- **Visual Features**:
  * **Flexible Grid Layout**: Automatically scales from a $2 \times 2$ grid (2 variables) up to four $4 \times 4$ grids in a $2 \times 2$ layout (6 variables) matching Gray code selector combinations.
  * **Contiguous & Wrapped loops**: Loops wrap around column/row edges and corners.
  * **3D Plane Links**: Spans groups across grids (5/6 vars) using dashed 3D connecting lines linking the centers of matching loops.
  * **EPI vs. PI Highlights**: Flashes uniquely covered minterm cells and transforms loop stroke colors to **Green** for Essential Prime Implicants and **Blue** for covering Prime Implicants.
- **How to Run**:
  ```powershell
  python "kmap solver/kmap_visualizer.py"
  ```

---

## Video Rendering Customizations

When launching any of the scripts, the program will ask you to select a video quality:
1. **Low Quality (480p, 15fps)**: Recommended for fast development compilation.
2. **Medium Quality (720p, 30fps)**: Balanced output.
3. **High Quality (1080p, 60fps)**: High-resolution production assets.

After compiling, the script will output the video path in the respective visualizer directory's `media/` folder and ask:
`Do you want to open and play the video now? (y/n) [Default: y]`
Entering `y` (or pressing Enter) will launch your system's default media player (e.g. VLC, Windows Media Player) to play the animation instantly.
