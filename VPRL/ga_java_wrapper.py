"""
Enhanced GA_Java Wrapper with initial solution support and convergence tracking
"""

import os
import re
import time
import subprocess
import tempfile
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from .solution_converter import Route, SolutionConverter


@dataclass
class ConvergencePoint:
    """Convergence tracking data point"""
    generation: int
    best_cost: float
    timestamp: float  # Seconds since start


class GAJavaWrapper:
    """Enhanced wrapper for GA_Java with VRPL integration"""
    
    def __init__(self, java_home: Optional[str] = None):
        """
        Initialize GA_Java wrapper
        
        Args:
            java_home: Java installation path (optional)
        """
        self.java_home = java_home
        self.java_cmd = self._find_java()
        self.ga_mdvrp_path = self._find_ga_mdvrp_path()
        
        # Check Java environment
        self._check_java()
    
    def _find_java(self) -> str:
        """Find Java executable"""
        if self.java_home:
            java_cmd = os.path.join(self.java_home, 'bin', 'java')
            if os.path.exists(java_cmd):
                return java_cmd
        return 'java'
    
    def _find_ga_mdvrp_path(self) -> str:
        """Find GA-MDVRP project path"""
        # Assume VPRL is in project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ga_mdvrp_path = os.path.join(
            current_dir,
            '../system_test/ga_mdvrp_reproduction/GA-MDVRP'
        )
        return os.path.abspath(ga_mdvrp_path)
    
    def _check_java(self):
        """Check Java environment"""
        try:
            result = subprocess.run(
                [self.java_cmd, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_info = result.stderr.split('\n')[0]
            print(f"[OK] Java environment: {version_info}")
        except FileNotFoundError:
            raise RuntimeError(
                "Java not found! Please install JDK 11 or higher\n"
                "Download: https://www.oracle.com/java/technologies/downloads/"
            )
        except Exception as e:
            raise RuntimeError(f"Java check failed: {e}")
    
    def solve_with_initial_solutions(
        self,
        instance_data,
        initial_solutions: Optional[List[Route]] = None,
        vrpl_ratio: float = 0.5,
        convergence_interval: int = 10) -> Dict:
        """
        Solve MDVRP with optional initial solutions and convergence tracking
        
        Args:
            instance_data: MDVRP instance (MDVRPInstance object or file path)
            initial_solutions: Initial routes from VRPL (optional)
            vrpl_ratio: Ratio of initial solutions in population
            convergence_interval: Report best cost every N generations
            
        Returns:
            Solution dictionary with convergence_data
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"GA-MDVRP (Java) with VRPL Enhancement")
        print(f"{'='*60}")
        
        # Determine instance file
        if isinstance(instance_data, str) and os.path.exists(instance_data):
            problem_file = instance_data
            instance_name = os.path.basename(problem_file)
            temp_file_created = False
        else:
            # Create temporary Cordeau file
            problems_dir = os.path.join(self.ga_mdvrp_path, 'data', 'problems')
            os.makedirs(problems_dir, exist_ok=True)
            
            # Create temp file and write data
            fd, problem_file = tempfile.mkstemp(
                suffix='.dat',
                dir=problems_dir
            )
            
            try:
                with os.fdopen(fd, 'w') as f:
                    self._write_cordeau_format(f, instance_data)
            except Exception as e:
                os.close(fd)
                raise RuntimeError(f"Failed to write Cordeau format: {e}")
            
            instance_name = os.path.basename(problem_file)
            temp_file_created = True
        
        # Write initial solutions if provided
        init_file_path = None
        if initial_solutions and len(initial_solutions) > 0:
            init_file_path = self._write_initial_solution_file(
                routes=initial_solutions,
                instance_name=instance_name
            )
            print(f"Initial solutions: {len(initial_solutions)} routes")
            print(f"VRPL ratio: {vrpl_ratio * 100:.1f}%")
        else:
            print("No initial solutions provided, using random initialization")
        
        try:
            # Run GA_Java
            print(f"Starting GA_Java...")
            result = self._run_java_solver(
                problem_name=os.path.relpath(problem_file, self.ga_mdvrp_path)
            )
            
            # Note: Output is already printed in real-time by _run_java_solver
            
            if result.returncode != 0:
                print(f"\n[WARNING] GA_Java returned non-zero status: {result.returncode}")
                if result.stderr:
                    print(f"Error output: {result.stderr}")
            
            # Parse results
            total_cost = self._extract_cost_from_output(result.stdout)
            routes = self._extract_routes_from_output(result.stdout)
            convergence_curve = self._parse_convergence_output(
                result.stdout,
                interval=convergence_interval,
                start_time=start_time
            )
            
        except subprocess.TimeoutExpired:
            print(f"[WARNING] GA_Java execution timeout (60 minutes)")
            total_cost = float('inf')
            routes = []
            convergence_curve = []
        except Exception as e:
            print(f"[WARNING] Execution error: {e}")
            import traceback
            traceback.print_exc()
            total_cost = float('inf')
            routes = []
            convergence_curve = []
        finally:
            # Cleanup
            if temp_file_created and os.path.exists(problem_file):
                try:
                    os.unlink(problem_file)
                except:
                    pass
            if init_file_path and os.path.exists(init_file_path):
                try:
                    os.unlink(init_file_path)
                except:
                    pass
        
        compute_time = time.time() - start_time
        
        result_dict = {
            'algorithm': 'VPRL-Enhanced GA-MDVRP',
            'total_cost': total_cost,
            'compute_time': compute_time,
            'routes': routes,
            'num_vehicles': len(routes),
            'convergence_curve': convergence_curve,
            'ga_iterations': len(convergence_curve) * convergence_interval if convergence_curve else 0
        }
        
        print(f"\n{'='*60}")
        print(f"Solving completed")
        print(f"  Total cost: {total_cost:.2f}")
        print(f"  Routes: {len(routes)}")
        print(f"  Compute time: {compute_time:.2f}s")
        print(f"  Convergence points: {len(convergence_curve)}")
        print(f"{'='*60}\n")
        
        return result_dict
    
    def _write_initial_solution_file(
        self,
        routes: List[Route],
        instance_name: str) -> str:
        """
        Write initial solutions to file for GA_Java
        
        Args:
            routes: List of routes
            instance_name: Instance name
            
        Returns:
            Path to initial solution file
        """
        # Create initial_solutions directory
        init_dir = os.path.join(self.ga_mdvrp_path, 'data', 'initial_solutions')
        os.makedirs(init_dir, exist_ok=True)
        
        # Generate filename
        filepath = os.path.join(init_dir, f"{instance_name}.init")
        
        # Write file
        SolutionConverter.write_initial_solution_file(
            routes=routes,
            filepath=filepath,
            instance_name=instance_name
        )
        
        print(f"Initial solution file written: {filepath}")
        return filepath
    
    def _run_java_solver(self, problem_name: str):
        """Run Java solver with real-time output"""
        out_dir = os.path.join(self.ga_mdvrp_path, 'out')
        
        if os.path.exists(out_dir):
            cmd = [
                self.java_cmd,
                '-cp', out_dir,
                'MainCLI',
                problem_name
            ]
        else:
            src_dir = os.path.join(self.ga_mdvrp_path, 'src')
            cmd = [
                self.java_cmd,
                '-cp', src_dir,
                'MainCLI',
                problem_name
            ]
        
        # Use Popen for real-time output
        print(f"[INFO] Starting Java process with real-time output...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
            cwd=self.ga_mdvrp_path
        )
        
        # Collect output while printing in real-time
        stdout_lines = []
        stderr_lines = []
        
        try:
            # Read stdout in real-time
            for line in process.stdout:
                print(line, end='')  # Print immediately
                stdout_lines.append(line)
            
            # Wait for process to complete
            process.wait(timeout=3600)  # 60 minutes
            
            # Read any remaining stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                stderr_lines.append(stderr_output)
                if process.returncode != 0:
                    print(f"\n[STDERR] {stderr_output}")
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise
        
        # Create result object compatible with subprocess.run
        class Result:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        
        return Result(
            returncode=process.returncode,
            stdout=''.join(stdout_lines),
            stderr=''.join(stderr_lines)
        )
    
    def _parse_convergence_output(
        self,
        output: str,
        interval: int = 10,
        start_time: float = None) -> List[ConvergencePoint]:
        """
        Parse convergence data from GA_Java output
        
        Args:
            output: GA_Java stdout
            interval: Reporting interval
            start_time: Start timestamp
            
        Returns:
            List of ConvergencePoint objects
        """
        convergence_curve = []
        
        try:
            # Pattern: "Generation: 10  |  Best distance: 589.23"
            pattern = r'Generation:\s*(\d+)\s*\|.*?Best.*?distance[:\s]+([\d.]+)'
            matches = re.findall(pattern, output, re.IGNORECASE)
            
            for match in matches:
                generation = int(match[0])
                best_cost = float(match[1])
                timestamp = time.time() - start_time if start_time else 0.0
                
                convergence_curve.append(ConvergencePoint(
                    generation=generation,
                    best_cost=best_cost,
                    timestamp=timestamp
                ))
            
            if convergence_curve:
                print(f"[INFO] Parsed {len(convergence_curve)} convergence points")
            else:
                print(f"[WARNING] No convergence data found in output")
                
        except Exception as e:
            print(f"[WARNING] Failed to parse convergence data: {e}")
        
        return convergence_curve
    
    def _extract_cost_from_output(self, output: str) -> float:
        """Extract total cost from output"""
        try:
            pattern = r'Total distance best solution:\s*([\d.]+)'
            match = re.search(pattern, output)
            if match:
                cost = float(match.group(1))
                print(f"[INFO] Extracted cost: {cost}")
                return cost
            else:
                pattern2 = r'Total distance.*?:\s*([\d.]+)'
                match2 = re.search(pattern2, output)
                if match2:
                    cost = float(match2.group(1))
                    print(f"[INFO] Extracted cost (backup pattern): {cost}")
                    return cost
        except Exception as e:
            print(f"[WARNING] Failed to extract cost: {e}")
        
        print(f"[WARNING] Could not extract cost, returning 0")
        return 0.0
    
    def _extract_routes_from_output(self, output: str) -> List[Dict]:
        """Extract routes from output"""
        routes = []
        try:
            pattern1 = r'Depot(\d+):\s*\[([^\]]+)\]'
            matches1 = re.findall(pattern1, output)
            
            if matches1:
                for depot_id_str, customers_str in matches1:
                    depot_id = int(depot_id_str) - 1
                    customers = [int(c.strip()) - 1 for c in customers_str.split(',') if c.strip()]
                    
                    if customers:
                        routes.append({
                            'depot_id': depot_id,
                            'vehicle_id': len(routes) + 1,
                            'customers': customers,
                            'cost': 0
                        })
                print(f"[INFO] Extracted {len(routes)} routes")
            else:
                print(f"[WARNING] No routes found in output")
                
        except Exception as e:
            print(f"[WARNING] Failed to extract routes: {e}")
        
        return routes
    
    def _write_cordeau_format(self, f, instance_data):
        """
        Write Cordeau format file
        
        Args:
            f: File handle
            instance_data: MDVRPInstance object
        """
        # Header: type vehicles_per_depot num_customers num_depots
        vehicles_per_depot = int(instance_data.depot_vehicles[0])  # Assume same for all
        f.write(f"2 {vehicles_per_depot} {instance_data.num_customers} {instance_data.num_depots}\n")
        
        # D/Q parameters (max_distance and capacity for each depot)
        # Java expects integers, so convert floats to ints
        for i in range(instance_data.num_depots):
            max_dist = int(instance_data.max_route_distances[i])
            capacity = int(instance_data.depot_capacities[i])
            f.write(f"{max_dist} {capacity}\n")
        
        # Customers (id, x, y, service_duration, demand)
        # Java expects all integers
        for i in range(instance_data.num_customers):
            customer_id = i + 1
            x = int(instance_data.customers_coords[i, 0])
            y = int(instance_data.customers_coords[i, 1])
            demand = int(instance_data.demands[i])
            f.write(f"{customer_id} {x} {y} 0 {demand}\n")
        
        # Depots (id, x, y)
        # Java expects all integers
        for i in range(instance_data.num_depots):
            depot_id = instance_data.num_customers + i + 1
            x = int(instance_data.depots_coords[i, 0])
            y = int(instance_data.depots_coords[i, 1])
            f.write(f"{depot_id} {x} {y}\n")
