# Requirements Document

## Introduction

This feature adds an algorithm comparison interface to the MDVRP system, enabling users to compare the performance of different algorithms (GA, PSO, ACO) on the same scenario. Users can select a scenario, choose multiple algorithms, run them simultaneously, and view comparative results including cost, computation time, routes, and visual analytics.

## Glossary

- **MDVRP_System**: The Multi-Depot Vehicle Routing Problem system consisting of Vue.js frontend, SpringBoot backend, and Python algorithm service
- **Algorithm_Service**: The Python Flask service that executes MDVRP algorithms (GA, PSO, ACO)
- **Comparison_Page**: The new Vue.js frontend page for comparing algorithm performance
- **Scenario**: A specific MDVRP problem instance with defined depots, customers, and constraints
- **Algorithm_Result**: The solution returned by an algorithm including routes, total cost, computation time, and convergence data
- **Comparison_Report**: A structured data object containing results from multiple algorithms for the same scenario
- **GA**: Genetic Algorithm
- **PSO**: Particle Swarm Optimization algorithm
- **ACO**: Ant Colony Optimization algorithm

## Requirements

### Requirement 1: Scenario Selection

**User Story:** As a user, I want to select a scenario for algorithm comparison, so that I can evaluate different algorithms on the same problem instance.

#### Acceptance Criteria

1. THE Comparison_Page SHALL display a list of available scenarios
2. WHEN a user selects a scenario, THE Comparison_Page SHALL load the scenario details including depot and customer information
3. THE Comparison_Page SHALL display the selected scenario's basic information (number of depots, number of customers, total demand)
4. WHEN no scenarios exist, THE Comparison_Page SHALL display a message prompting the user to create a scenario first

### Requirement 2: Algorithm Selection

**User Story:** As a user, I want to select multiple algorithms to compare, so that I can evaluate their relative performance.

#### Acceptance Criteria

1. THE Comparison_Page SHALL display checkboxes for available algorithms (GA, PSO, ACO)
2. THE Comparison_Page SHALL allow users to select at least two algorithms for comparison
3. WHEN fewer than two algorithms are selected, THE Comparison_Page SHALL disable the comparison execution button
4. THE Comparison_Page SHALL allow users to select all three algorithms simultaneously
5. WHERE an algorithm has configurable parameters, THE Comparison_Page SHALL provide input fields for those parameters

### Requirement 3: Parallel Algorithm Execution

**User Story:** As a user, I want the system to run multiple algorithms on the same scenario, so that I can obtain comparable results.

#### Acceptance Criteria

1. WHEN the user initiates comparison, THE MDVRP_System SHALL execute all selected algorithms on the same scenario data
2. THE MDVRP_System SHALL send identical depot, customer, and constraint data to each algorithm
3. WHEN algorithms are executing, THE Comparison_Page SHALL display a progress indicator showing which algorithms are running
4. THE MDVRP_System SHALL record the start time and end time for each algorithm execution
5. IF an algorithm execution fails, THEN THE MDVRP_System SHALL continue executing remaining algorithms and record the failure
6. WHEN all algorithms complete, THE MDVRP_System SHALL aggregate results into a Comparison_Report

### Requirement 4: Cost Comparison Display

**User Story:** As a user, I want to see total cost comparison between algorithms, so that I can identify which algorithm produces the most cost-effective solution.

#### Acceptance Criteria

1. THE Comparison_Page SHALL display total cost for each algorithm in a comparison table
2. THE Comparison_Page SHALL highlight the algorithm with the lowest total cost
3. THE Comparison_Page SHALL display cost differences as both absolute values and percentages relative to the best solution
4. THE Comparison_Page SHALL display a bar chart comparing total costs across algorithms
5. WHEN an algorithm fails, THE Comparison_Page SHALL display "N/A" or an error indicator for that algorithm's cost

### Requirement 5: Computation Time Comparison

**User Story:** As a user, I want to see computation time comparison between algorithms, so that I can evaluate the trade-off between solution quality and execution speed.

#### Acceptance Criteria

1. THE Comparison_Page SHALL display computation time for each algorithm in seconds
2. THE Comparison_Page SHALL highlight the fastest algorithm
3. THE Comparison_Page SHALL display a bar chart comparing computation times across algorithms
4. THE Comparison_Page SHALL calculate and display the time difference between the fastest and slowest algorithms
5. THE Comparison_Page SHALL display computation time with precision to three decimal places

### Requirement 6: Route Metrics Comparison

**User Story:** As a user, I want to compare route-level metrics between algorithms, so that I can understand how different algorithms structure their solutions.

#### Acceptance Criteria

1. THE Comparison_Page SHALL display the number of routes generated by each algorithm
2. THE Comparison_Page SHALL display the average route cost for each algorithm
3. THE Comparison_Page SHALL display the maximum route cost for each algorithm
4. THE Comparison_Page SHALL display vehicle utilization statistics for each algorithm
5. THE Comparison_Page SHALL present route metrics in a comparison table with sortable columns

### Requirement 7: Visual Route Comparison

**User Story:** As a user, I want to see visual representations of routes from different algorithms, so that I can visually compare solution structures.

#### Acceptance Criteria

1. THE Comparison_Page SHALL display route visualizations for each algorithm side by side
2. THE Comparison_Page SHALL use consistent colors and styling across all algorithm visualizations
3. THE Comparison_Page SHALL display depot locations, customer locations, and routes on each visualization
4. WHEN a user hovers over a route, THE Comparison_Page SHALL highlight that route and display its details
5. THE Comparison_Page SHALL allow users to toggle individual algorithm visualizations on and off

### Requirement 8: Convergence Comparison

**User Story:** As a user, I want to compare convergence behavior between algorithms, so that I can understand how quickly each algorithm approaches optimal solutions.

#### Acceptance Criteria

1. WHERE algorithms provide convergence data, THE Comparison_Page SHALL display a line chart showing cost evolution over iterations
2. THE Comparison_Page SHALL plot convergence curves for all algorithms on the same chart with different colors
3. THE Comparison_Page SHALL display iteration numbers on the x-axis and cost values on the y-axis
4. THE Comparison_Page SHALL include a legend identifying each algorithm's convergence curve
5. WHEN an algorithm does not provide convergence data, THE Comparison_Page SHALL exclude that algorithm from the convergence chart

### Requirement 9: Comparison Report Export

**User Story:** As a user, I want to export comparison results, so that I can share findings or include them in reports.

#### Acceptance Criteria

1. THE Comparison_Page SHALL provide an export button for downloading comparison results
2. THE Comparison_Page SHALL support exporting comparison data in JSON format
3. THE Comparison_Page SHALL support exporting comparison data in CSV format
4. THE exported file SHALL include all comparison metrics (costs, times, route counts, convergence data)
5. THE exported file SHALL include scenario information and execution timestamp
6. WHEN export is initiated, THE Comparison_Page SHALL generate the file and trigger a browser download

### Requirement 10: Comparison History

**User Story:** As a user, I want to save comparison results, so that I can review past comparisons and track algorithm performance over time.

#### Acceptance Criteria

1. WHEN a comparison completes, THE MDVRP_System SHALL save the Comparison_Report to the database
2. THE Comparison_Report SHALL include scenario ID, selected algorithms, execution timestamp, and all result metrics
3. THE Comparison_Page SHALL provide a history view showing past comparisons
4. WHEN viewing comparison history, THE Comparison_Page SHALL display comparison date, scenario name, and algorithms compared
5. WHEN a user selects a historical comparison, THE Comparison_Page SHALL load and display the saved comparison results

### Requirement 11: Error Handling

**User Story:** As a user, I want clear error messages when comparisons fail, so that I can understand what went wrong and take corrective action.

#### Acceptance Criteria

1. IF the Algorithm_Service is unavailable, THEN THE MDVRP_System SHALL display an error message indicating service unavailability
2. IF an algorithm execution times out, THEN THE MDVRP_System SHALL display a timeout error for that specific algorithm
3. IF an algorithm returns invalid data, THEN THE MDVRP_System SHALL display a data validation error
4. WHEN partial results are available (some algorithms succeed, others fail), THE Comparison_Page SHALL display successful results and error indicators for failed algorithms
5. THE Comparison_Page SHALL provide actionable error messages with suggestions for resolution

### Requirement 12: Responsive Layout

**User Story:** As a user, I want the comparison interface to work on different screen sizes, so that I can view comparisons on various devices.

#### Acceptance Criteria

1. THE Comparison_Page SHALL adapt its layout for desktop screens (≥1024px width)
2. THE Comparison_Page SHALL adapt its layout for tablet screens (768px-1023px width)
3. THE Comparison_Page SHALL adapt its layout for mobile screens (<768px width)
4. WHEN screen width is insufficient for side-by-side visualizations, THE Comparison_Page SHALL stack visualizations vertically
5. THE Comparison_Page SHALL maintain readability of comparison tables on all screen sizes
