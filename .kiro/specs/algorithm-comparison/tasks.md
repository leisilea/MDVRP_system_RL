# Implementation Plan: Algorithm Comparison Feature

## Overview

This implementation plan creates a comprehensive algorithm comparison interface for the MDVRP system. The feature enables users to select a scenario, run multiple algorithms (GA, PSO, ACO) in parallel, and compare their performance through interactive visualizations and detailed metrics.

The implementation follows the existing three-tier architecture:
- Backend (Spring Boot): Orchestration service for parallel algorithm execution
- Frontend (Vue.js): Comparison page with interactive charts and visualizations
- Database (MySQL): Persistent storage for comparison results

## Tasks

- [x] 1. Investigate and fix Flask-SpringBoot communication issue
  - Reproduce the reported issue where GA and PSO algorithms cannot be called
  - Examine the Flask response format and SpringBoot deserialization process
  - Identify any recent changes that may have caused the regression
  - Test end-to-end communication with all three algorithms (GA, PSO, ACO)
  - Fix any serialization/deserialization issues in the communication layer
  - Verify that existing algorithm execution works correctly before adding comparison feature
  - _Requirements: 3.1, 3.2, 11.1_
  - _Note: This is a critical prerequisite - comparison feature depends on working algorithm execution_

- [x] 2. Create database schema for comparison results
  - [x] 2.1 Create comparison_result table migration
    - Write SQL migration script for comparison_result table
    - Include fields: id, scenario_id, execution_time, algorithms_compared, best_algorithm, best_cost, fastest_algorithm, fastest_time, create_time
    - Add foreign key constraint to scenario table with CASCADE delete
    - Add index on (scenario_id, execution_time) for efficient history queries
    - _Requirements: 10.1, 10.2_
  
  - [x] 2.2 Create algorithm_result table migration
    - Write SQL migration script for algorithm_result table
    - Include fields: id, comparison_id, algorithm, success, total_cost, compute_time, num_routes, routes (TEXT/JSON), convergence (TEXT/JSON), error_message
    - Add foreign key constraint to comparison_result table with CASCADE delete
    - Add index on comparison_id for efficient result retrieval
    - _Requirements: 10.1, 10.2_
  
  - [-]* 2.3 Write property test for database schema
    - **Property 20: Comparison Result Round-Trip**
    - **Validates: Requirements 10.1, 10.2, 10.5**
    - Test that comparison data saved to database can be retrieved with identical values

- [x] 3. Implement backend data models and DTOs
  - [x] 3.1 Create ComparisonRequest DTO
    - Define ComparisonRequest class with scenarioId, algorithms list, and params map
    - Add validation annotations (@NotNull, @Size, etc.)
    - _Requirements: 2.1, 2.2, 3.1_
  
  - [x] 3.2 Create AlgorithmResult DTO
    - Define AlgorithmResult class with algorithm, success, totalCost, computeTime, numRoutes, routes, convergence, error fields
    - Add JSON serialization annotations
    - _Requirements: 3.6, 4.1, 5.1_
  
  - [x] 3.3 Create ComparisonResult DTO
    - Define ComparisonResult class with id, scenarioId, scenarioName, executionTime, results list, summary
    - Include nested ComparisonSummary class with statistics
    - _Requirements: 3.6, 4.1, 5.1_
  
  - [x] 3.4 Create ComparisonResult and AlgorithmResult entities
    - Define JPA entities for database persistence
    - Add appropriate annotations (@Entity, @Table, @Column, relationships)
    - _Requirements: 10.1, 10.2_

- [x] 4. Implement backend comparison service layer
  - [x] 4.1 Create AlgorithmExecutor utility class
    - Implement wrapper for single algorithm execution with timeout handling
    - Measure execution time accurately using System.nanoTime()
    - Handle errors gracefully and return standardized AlgorithmResult
    - Configure timeout (default: 300 seconds)
    - _Requirements: 3.4, 3.5, 11.2_
  
  - [x] 4.2 Implement ComparisonService.executeComparison method
    - Load scenario data (depots and customers) from database
    - Create CompletableFuture for each selected algorithm
    - Execute algorithms in parallel using CompletableFuture.allOf()
    - Collect results (or errors) from all futures
    - Call aggregateResults to compute summary statistics
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6_
  
  - [ ]* 4.3 Write property test for parallel execution
    - **Property 3: Identical Input Data Distribution**
    - **Validates: Requirements 3.1, 3.2**
    - Test that all algorithms receive identical scenario data
  
  - [ ]* 4.4 Write property test for fault isolation
    - **Property 5: Fault Isolation**
    - **Validates: Requirements 3.5**
    - Test that one algorithm failure doesn't affect others
  
  - [x] 4.5 Implement ComparisonService.aggregateResults method
    - Calculate summary statistics (cost range, time range, success/failure counts)
    - Identify best performer (lowest cost) and fastest algorithm
    - Calculate cost differences and percentages
    - Create ComparisonResult with all aggregated data
    - _Requirements: 3.6, 4.2, 4.3, 5.2, 6.1, 6.2, 6.3_
  
  - [ ]* 4.6 Write property test for result aggregation
    - **Property 6: Result Aggregation Completeness**
    - **Validates: Requirements 3.6**
    - Test that all results are included in aggregated report
  
  - [ ]* 4.7 Write property test for best performer identification
    - **Property 7: Best Performer Identification**
    - **Validates: Requirements 4.2, 5.2**
    - Test that system correctly identifies lowest cost and fastest algorithm
  
  - [ ]* 4.8 Write property test for cost difference calculation
    - **Property 8: Cost Difference Calculation**
    - **Validates: Requirements 4.3**
    - Test that cost differences are calculated correctly (absolute and percentage)
  
  - [x] 4.9 Implement ComparisonService.saveComparison method
    - Save ComparisonResult entity to database
    - Save all AlgorithmResult entities linked to comparison
    - Handle database errors gracefully (log but don't fail request)
    - _Requirements: 10.1, 10.2_
  
  - [x] 4.10 Implement ComparisonService.getHistory method
    - Query comparison_result table with optional filters (scenarioId, date range)
    - Return list of ComparisonSummary objects
    - Order by execution_time descending (most recent first)
    - _Requirements: 10.3, 10.4_
  
  - [x] 4.11 Implement ComparisonService.getById method
    - Load ComparisonResult by ID from database
    - Load all associated AlgorithmResult records
    - Return complete ComparisonResult DTO
    - _Requirements: 10.5_
  
  - [x] 4.12 Implement ComparisonService.exportComparison method
    - Support JSON and CSV export formats
    - Include all metrics, scenario info, and execution timestamp
    - Generate byte array for file download
    - _Requirements: 9.2, 9.3, 9.4, 9.5_
  
  - [ ]* 4.13 Write property test for export completeness
    - **Property 14: Export Completeness**
    - **Validates: Requirements 9.4, 9.5**
    - Test that exported files contain all required data

- [x] 5. Implement backend comparison controller
  - [x] 5.1 Create ComparisonController class
    - Add @RestController and @RequestMapping("/api/comparison") annotations
    - Add @CrossOrigin for CORS support
    - Inject ComparisonService dependency
    - _Requirements: All API requirements_
  
  - [x] 5.2 Implement POST /api/comparison/execute endpoint
    - Accept ComparisonRequest in request body
    - Validate that at least 2 algorithms are selected
    - Call ComparisonService.executeComparison
    - Return ComparisonResult wrapped in Result object
    - Handle errors with appropriate HTTP status codes
    - _Requirements: 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  
  - [ ]* 5.3 Write unit tests for execute endpoint
    - Test successful comparison with 2 algorithms
    - Test successful comparison with 3 algorithms
    - Test validation error when fewer than 2 algorithms selected
    - Test partial success (some algorithms fail)
    - _Requirements: 2.3, 3.5, 11.4_
  
  - [x] 5.4 Implement GET /api/comparison/history endpoint
    - Accept optional query parameters: scenarioId, startDate, endDate
    - Call ComparisonService.getHistory with filters
    - Return list of ComparisonSummary objects
    - _Requirements: 10.3, 10.4_
  
  - [x] 5.5 Implement GET /api/comparison/{id} endpoint
    - Extract comparison ID from path variable
    - Call ComparisonService.getById
    - Return ComparisonResult or 404 if not found
    - _Requirements: 10.5_
  
  - [x] 5.6 Implement POST /api/comparison/{id}/export endpoint
    - Extract comparison ID from path variable
    - Accept format parameter (json or csv)
    - Call ComparisonService.exportComparison
    - Return file download response with appropriate Content-Type
    - _Requirements: 9.1, 9.2, 9.3, 9.6_

- [ ] 6. Checkpoint - Backend implementation complete
  - Ensure all backend tests pass
  - Test API endpoints manually using Postman or curl
  - Verify database schema is created correctly
  - Verify parallel algorithm execution works as expected
  - Ask the user if questions arise

- [x] 7. Implement frontend API service layer
  - [x] 7.1 Create comparison.js API module
    - Implement executeComparison(scenarioId, algorithms, params) function
    - Implement getComparisonHistory(scenarioId, startDate, endDate) function
    - Implement getComparisonById(id) function
    - Implement exportComparison(id, format) function
    - Use axios for HTTP requests with proper error handling
    - _Requirements: All API requirements_
  
  - [ ]* 7.2 Write unit tests for API service
    - Test successful API calls
    - Test error handling for network failures
    - Test error handling for validation errors

- [-] 8. Implement frontend comparison page component
  - [ ] 8.1 Create ComparisonPage.vue component
    - Set up component structure with template, script, and style sections
    - Define data properties: scenarios, selectedScenario, selectedAlgorithms, algorithmParams, comparisonResult, loading, error
    - Implement loadScenarios() method to fetch available scenarios
    - Implement selectScenario(scenarioId) method to load scenario details
    - Implement toggleAlgorithm(algorithm) method for checkbox handling
    - Implement executeComparison() method to trigger comparison
    - Add validation to disable execute button when fewer than 2 algorithms selected
    - Display loading indicator during execution
    - Display error messages when comparison fails
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.3, 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ]* 8.2 Write property test for algorithm selection validation
    - **Property 2: Algorithm Selection Validation**
    - **Validates: Requirements 2.3**
    - Test that execute button is disabled when fewer than 2 algorithms selected
  
  - [ ]* 8.3 Write unit tests for ComparisonPage
    - Test scenario loading and selection
    - Test algorithm checkbox toggling
    - Test execute button enable/disable logic
    - Test error display

- [ ] 9. Implement frontend comparison metrics table component
  - [ ] 9.1 Create ComparisonMetricsTable.vue component
    - Accept results prop (array of AlgorithmResult objects)
    - Accept highlightBest prop (boolean)
    - Display table with columns: Algorithm, Total Cost, Computation Time, Routes, Status
    - Highlight best cost and fastest time when highlightBest is true
    - Calculate and display percentage differences relative to best
    - Format computation time to 3 decimal places
    - Display "N/A" or error indicator for failed algorithms
    - Implement sortable columns
    - Make table responsive for different screen sizes
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.5, 11.4, 12.1, 12.2, 12.3, 12.5_
  
  - [ ]* 9.2 Write property test for time precision formatting
    - **Property 9: Time Precision Formatting**
    - **Validates: Requirements 5.5**
    - Test that computation times are formatted to exactly 3 decimal places
  
  - [ ]* 9.3 Write property test for failed algorithm display
    - **Property 11: Failed Algorithm Display**
    - **Validates: Requirements 4.5, 11.4**
    - Test that failed algorithms show error indicators instead of metrics
  
  - [ ]* 9.4 Write unit tests for metrics table
    - Test rendering with successful results
    - Test rendering with mixed success/failure
    - Test highlighting of best performers
    - Test percentage calculation
    - Test sorting functionality

- [ ] 10. Implement frontend comparison charts component
  - [ ] 10.1 Create ComparisonCharts.vue component
    - Accept results prop (array of AlgorithmResult objects)
    - Install and configure Chart.js or ECharts library
    - Implement bar chart for total cost comparison
    - Implement bar chart for computation time comparison
    - Implement line chart for convergence curves (multi-line)
    - Implement radar chart for multi-dimensional metrics
    - Add legend to identify each algorithm
    - Use consistent colors across all charts
    - Handle missing convergence data gracefully
    - Make charts responsive for different screen sizes
    - _Requirements: 4.4, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5, 12.1, 12.2, 12.3_
  
  - [ ]* 10.2 Write property test for convergence data conditional rendering
    - **Property 12: Convergence Data Conditional Rendering**
    - **Validates: Requirements 8.1, 8.5**
    - Test that algorithms without convergence data are excluded from convergence chart
  
  - [ ]* 10.3 Write unit tests for charts component
    - Test chart rendering with complete data
    - Test chart rendering with missing convergence data
    - Test chart responsiveness

- [ ] 11. Implement frontend route comparison visualization component
  - [ ] 11.1 Create RouteComparisonView.vue component
    - Accept results prop (array of AlgorithmResult objects)
    - Create multiple map instances (one per algorithm) using existing MapView component
    - Display maps side by side on desktop, stacked on mobile
    - Use consistent colors and styling across all maps
    - Display depot locations, customer locations, and routes on each map
    - Implement route highlighting on hover with route details tooltip
    - Add toggle buttons to show/hide individual algorithm visualizations
    - Implement synchronized zoom/pan controls (optional enhancement)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 12.1, 12.2, 12.3, 12.4_
  
  - [ ]* 11.2 Write property test for responsive layout adaptation
    - **Property 19: Responsive Layout Adaptation**
    - **Validates: Requirements 12.4**
    - Test that visualizations stack vertically on narrow screens
  
  - [ ]* 11.3 Write unit tests for route visualization
    - Test map rendering for each algorithm
    - Test toggle functionality
    - Test responsive layout switching

- [ ] 12. Implement frontend comparison history component
  - [ ] 12.1 Create ComparisonHistory.vue component
    - Implement list view of past comparisons
    - Display comparison date, scenario name, and algorithms compared
    - Add filters for date range and scenario
    - Implement click handler to load historical comparison
    - Display loading state while fetching history
    - Handle empty history state with appropriate message
    - _Requirements: 10.3, 10.4, 10.5_
  
  - [ ]* 12.2 Write unit tests for history component
    - Test history list rendering
    - Test filtering functionality
    - Test loading historical comparison
    - Test empty state display

- [ ] 13. Implement frontend export functionality
  - [ ] 13.1 Add export button to ComparisonPage
    - Add export dropdown button with JSON and CSV options
    - Implement exportComparison(format) method
    - Call comparison API service to download file
    - Trigger browser download with appropriate filename
    - Display success/error message after export
    - _Requirements: 9.1, 9.2, 9.3, 9.6_
  
  - [ ]* 13.2 Write property test for export format support
    - **Property 13: Export Format Support**
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5**
    - Test that both JSON and CSV exports are supported and contain all data
  
  - [ ]* 13.3 Write unit tests for export functionality
    - Test JSON export
    - Test CSV export
    - Test error handling

- [ ] 14. Add comparison page to frontend routing
  - [ ] 14.1 Update router configuration
    - Add route for /comparison path pointing to ComparisonPage component
    - Add route for /comparison/history path pointing to ComparisonHistory component
    - Update navigation menu to include comparison link
    - _Requirements: All frontend requirements_
  
  - [ ] 14.2 Update navigation menu
    - Add "Algorithm Comparison" menu item
    - Add icon for comparison feature
    - Ensure proper navigation highlighting

- [ ] 15. Implement comprehensive error handling
  - [ ] 15.1 Add error handling in ComparisonService
    - Handle algorithm service unavailable errors
    - Handle algorithm timeout errors
    - Handle invalid result data errors
    - Handle database save failures gracefully
    - Log all errors with appropriate context
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [ ] 15.2 Add error display in frontend components
    - Display service unavailable errors with actionable messages
    - Display timeout errors for specific algorithms
    - Display validation errors with suggestions
    - Show partial results when some algorithms succeed
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ]* 15.3 Write property test for timeout error handling
    - **Property 17: Timeout Error Handling**
    - **Validates: Requirements 11.2**
    - Test that algorithm timeouts are recorded and other algorithms continue
  
  - [ ]* 15.4 Write property test for invalid data error handling
    - **Property 18: Invalid Data Error Handling**
    - **Validates: Requirements 11.3**
    - Test that invalid algorithm responses are caught and recorded as errors

- [ ] 16. Checkpoint - Frontend implementation complete
  - Ensure all frontend components render correctly
  - Test user interactions (scenario selection, algorithm selection, execution)
  - Verify charts and visualizations display properly
  - Test responsive layout on different screen sizes
  - Test export functionality
  - Ask the user if questions arise

- [ ] 17. Integration testing and end-to-end validation
  - [ ] 17.1 Write end-to-end integration test
    - Test complete flow: select scenario → select algorithms → execute → view results
    - Test comparison with 2 algorithms (GA + PSO)
    - Test comparison with 3 algorithms (GA + PSO + ACO)
    - Test partial failure scenario (one algorithm fails)
    - Test history save and retrieval
    - Test export functionality
    - _Requirements: All requirements_
  
  - [ ]* 17.2 Write property test for scenario selection
    - **Property 1: Scenario Selection Loads Complete Data**
    - **Validates: Requirements 1.2, 1.3**
    - Test that selecting a scenario loads all depot and customer data
  
  - [ ]* 17.3 Write property test for execution time recording
    - **Property 4: Execution Time Recording**
    - **Validates: Requirements 3.4**
    - Test that execution time equals difference between start and end timestamps
  
  - [ ]* 17.4 Write property test for route metrics calculation
    - **Property 10: Route Metrics Calculation**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Test that route count, average cost, and max cost are calculated correctly
  
  - [ ]* 17.5 Write property test for comparison persistence
    - **Property 15: Comparison Persistence**
    - **Validates: Requirements 10.1, 10.2**
    - Test that completed comparisons are saved to database with all data
  
  - [ ]* 17.6 Write property test for historical comparison retrieval
    - **Property 16: Historical Comparison Retrieval**
    - **Validates: Requirements 10.5**
    - Test that saved comparisons can be loaded and displayed correctly

- [ ] 18. Performance optimization and final polish
  - [ ] 18.1 Optimize parallel execution performance
    - Configure appropriate thread pool size for CompletableFuture
    - Tune timeout values based on testing
    - Add connection pooling for algorithm service HTTP calls
    - _Requirements: 3.3_
  
  - [ ] 18.2 Optimize frontend rendering performance
    - Implement lazy loading for charts (render only when visible)
    - Optimize map rendering for multiple instances
    - Add debouncing for filter inputs in history view
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [ ] 18.3 Add loading states and progress indicators
    - Show progress for each algorithm during execution
    - Display which algorithms are running, completed, or failed
    - Add skeleton loaders for charts and tables while loading
    - _Requirements: 3.3_
  
  - [ ] 18.4 Polish UI/UX
    - Ensure consistent styling across all components
    - Add smooth transitions and animations
    - Improve accessibility (ARIA labels, keyboard navigation)
    - Test and fix any responsive layout issues
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 19. Final checkpoint - Complete feature validation
  - Run all unit tests and property tests
  - Run end-to-end integration tests
  - Manually test complete user flow
  - Verify all requirements are met
  - Test on different browsers and screen sizes
  - Verify Flask-SpringBoot communication is stable
  - Ask the user for final review and feedback

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP delivery
- Task 1 is critical and must be completed first - the comparison feature depends on working algorithm execution
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and provide opportunities for user feedback
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and integration points
- The implementation follows existing patterns in the codebase for consistency
- All code should be production-ready with proper error handling and logging
