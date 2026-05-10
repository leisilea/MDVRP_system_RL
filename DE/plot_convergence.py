#!/usr/bin/env python3
"""
Plot convergence curves for GA-MDVRP with and without RouteFinder initialization
Uses existing compiled Java classes
"""

import re
import subprocess
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

def parse_convergence_from_output(output_text):
    """
    Parse convergence data from GA output
    Returns: list of (generation, best_distance) tuples
    """
    convergence = []
    
    # Parse Generation 0
    match = re.search(r'Generation: 0\s+\|\s+Population size: \d+\s+\|\s+Average total distance: ([\d.]+)', output_text)
    if match:
        avg_dist = float(match.group(1))
        convergence.append((0, avg_dist))
    
    # Parse every 10 generations
    pattern = r'Generation: (\d+)\s+\|\s+Best distance: ([\d.]+)'
    for match in re.finditer(pattern, output_text):
        gen = int(match.group(1))
        best_dist = float(match.group(2))
        convergence.append((gen, best_dist))
    
    return convergence

def run_ga_bat(use_routefinder=False):
    """
    Run GA-MDVRP using batch file
    """
    if use_routefinder:
        print("Running with RouteFinder initialization...")
        cmd = ['cmd', '/c', 'java', '-cp', 'bin;lib/*', 'MainCLI', 
               'data/problems/p21', 'data/solutions/p21_test_rf.res',
               '../../../RL4CO_Integration/p21_ga_initial_population.json']
    else:
        print("Running with random initialization...")
        cmd = ['cmd', '/c', 'java', '-cp', 'bin;lib/*', 'MainCLI', 
               'data/problems/p21', 'data/solutions/p21_random.res']
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd='.', timeout=1800)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    
    return result.stdout

def plot_convergence_comparison():
    """
    Run both GA variants and plot convergence comparison
    """
    print("=" * 60)
    print("GA-MDVRP Convergence Comparison (1200 Gen, 20 Seeds)")
    print("=" * 60)
    print("\nNote: This will run 2 full GA runs (1200 generations each)")
    print("RouteFinder initialization: 20 seed individuals (20% of population)")
    print("Estimated time: ~3-5 minutes total\n")
    
    # Run random initialization
    print("\n1. Running with random initialization...")
    random_output = run_ga_bat(use_routefinder=False)
    if not random_output:
        print("Failed to run random initialization")
        return
    
    random_convergence = parse_convergence_from_output(random_output)
    print(f"   Captured {len(random_convergence)} data points")
    
    # Run RouteFinder initialization
    print("\n2. Running with RouteFinder initialization...")
    rf_output = run_ga_bat(use_routefinder=True)
    if not rf_output:
        print("Failed to run RouteFinder initialization")
        return
    
    rf_convergence = parse_convergence_from_output(rf_output)
    print(f"   Captured {len(rf_convergence)} data points")
    
    # Plot comparison
    print("\n3. Plotting convergence curves...")
    plt.figure(figsize=(12, 7))
    
    if random_convergence:
        gens_random, dists_random = zip(*random_convergence)
        plt.plot(gens_random, dists_random, 'b-o', label='Random Initialization', 
                 linewidth=2, markersize=4, alpha=0.7)
        print(f"   Random - Initial: {dists_random[0]:.2f}, Final: {dists_random[-1]:.2f}")
        improvement_random = ((dists_random[0] - dists_random[-1]) / dists_random[0]) * 100
        print(f"   Random - Improvement: {improvement_random:.2f}%")
    
    if rf_convergence:
        gens_rf, dists_rf = zip(*rf_convergence)
        plt.plot(gens_rf, dists_rf, 'r-s', label='RouteFinder Initialization', 
                 linewidth=2, markersize=4, alpha=0.7)
        print(f"   RouteFinder - Initial: {dists_rf[0]:.2f}, Final: {dists_rf[-1]:.2f}")
        improvement_rf = ((dists_rf[0] - dists_rf[-1]) / dists_rf[0]) * 100
        print(f"   RouteFinder - Improvement: {improvement_rf:.2f}%")
    
    # Calculate advantage
    if random_convergence and rf_convergence:
        final_advantage = ((dists_random[-1] - dists_rf[-1]) / dists_random[-1]) * 100
        print(f"\n   Final solution advantage: {final_advantage:.2f}% better with RouteFinder")
    
    # Add BKS reference line
    bks = 5474.84
    plt.axhline(y=bks, color='g', linestyle='--', linewidth=2, label=f'BKS = {bks}')
    
    plt.xlabel('Generation', fontsize=12)
    plt.ylabel('Best Distance', fontsize=12)
    plt.title('GA-MDVRP Convergence Comparison (P21, 1200 Gen, 20 Seeds)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=11, loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = 'convergence_comparison_1200gen_20seeds.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n4. Plot saved to: {output_path}")
    
    print("\n" + "=" * 60)
    print("Comparison complete!")
    print("=" * 60)

if __name__ == '__main__':
    plot_convergence_comparison()
