# Backend Engine PRD

# **Core Principles**

- **Modularity:** Separate shared functionalities, methodology logic, and configuration data for maintainability and scalability.
- **Version Control:** Ensure backward compatibility by supporting multiple versions of each methodology.
- **Extensibility:** Provide a clear structure for adding new methodologies or versions without disrupting existing implementations.
- **User-Focused Design:** Offer an intuitive API and structured outputs for seamless integration into developer workflows.
- **Data Decoupling:** Store methodology-specific parameters (e.g., emission factors) in versioned configuration files to simplify updates.
- **Error Transparency:** Deliver clear, structured error and warning responses while maintaining traceability through logging.

# **High-Level Package Structure**

```
sequestrae-engine/
  ├── core/                          # Shared functionality across methodologies
  │   ├── biochar_properties.py      # H/C ratio, permanence calculations
  │   ├── input_validation.py        # Input validation and preprocessing
  │   ├── utilities.py               # JSON I/O, logging, error handling
  │   ├── constants.py               # Global constants (e.g., CO2 equivalence factors)
  ├── data/                          # Shared input data framework and methodology-specific configurations
  │   ├── input_schema.json          # Predefined input schema (shared across frameworks)
  │   ├── puro_earth/                # Puro.earth-specific configurations
  │   │   ├── v3.json
  │   ├── verra/                     # Verra-specific configurations
  │   │   ├── v1.json
  │   │   ├── v2.json
  │   ├── riverse/                   # Riverse-specific configurations
  │   │   ├── v1.json
  ├── methodologies/                 # Implementation of methodologies
  │   ├── abstract_methodology.py    # Abstract base class for methodologies
  │   ├── factory.py                 # Dynamically loads methodology versions
  │   ├── puro_earth_v3.py           # Implements Puro Earth v3 logic
  │   ├── verra_v1.py                # Implements Verra v1 logic
  │   ├── verra_v2.py                # Implements Verra v2 logic
  │   ├── templates/                 # Templates for adding new methodologies
  ├── examples/                      # Example use cases and Jupyter notebooks
  └── tests/                         # Unit and integration test
```

# **Component Details**

## **Core Modules**

The `core/` directory contains reusable functionality shared across all methodologies, ensuring consistency and reducing duplication.

### **Biochar Properties**

The `biochar_properties.py` module provides general-purpose utilities for biochar-specific properties, independent of any particular methodology.

**Responsibilities:**

- **H/C Ratio Analysis:**
  - Calculate the hydrogen-to-carbon (H/C) molar ratio, a key indicator of biochar stability.
  - Used as an input for methodology-specific permanence calculations.
- **General Biochar Metrics:**
  - Provide reusable functions for metrics such as:
  - Bulk density.
  - Ash content.
  - …

### **Input Validation**

The `input_validation.py` module enforces a **shared input schema** defined in `data/input_schema.json`, ensuring data consistency across methodologies.

**Responsibilities:**

- **Schema Validation:**
  - Validate input data against the predefined schema, ensuring compliance with required fields, data types, and value ranges.
- **Handling Missing Data:**
  - Assign default values to optional fields where appropriate.
  - Raise structured warnings for incomplete inputs.
- **Delegation of Framework-Specific Validation:**
  - After initial schema validation, pass inputs to the relevant methodology’s `validate_inputs()` method for framework-specific checks (e.g., feedstock eligibility).

### **Utilities**

The `utilities.py` module provides shared utility functions that support the overall functionality of the backend.

**Responsibilities:**

- **JSON I/O:**
  - Read and write configuration, input, and result files in JSON format.
- **Logging:**
  - Set up consistent logging for errors, warnings, and runtime events.
- **Error Handling:**
  - Provide standardized error reporting for validation and calculation workflows.

### **Constants**

The `constants.py` module stores global constants used across the engine to ensure consistency.

**Examples of Constants:**

- **CO₂ Equivalence Factors:**
  - Conversion factors for methane (CH₄) and nitrous oxide (N₂O) to CO₂ equivalents.
- **Default Units:**
  - Standardized units for emissions, feedstock quantities, etc.

## **Methodologies**

The `methodologies/` directory contains all framework-specific logic and the shared abstract base class for consistency.

### **Abstract Methodology Class**

The `abstract_methodology.py` module defines a shared abstract base class (`BaseMethodology`) that all methodology implementations inherit from.

**Purpose:**

- Enforce consistency across methodology implementations.
- Provide reusable scaffolding for common tasks.

**Responsibilities:**

- Input Validation Interface:
  - Mandate the implementation of a `validate_inputs()` method to enforce framework-specific rules (e.g., feedstock eligibility, H/C ratio thresholds).
- Lifecycle Analysis Interface:
  - Define a `calculate_removals()` method for lifecycle analysis, which methodologies override to compute net CO₂ removals.
- Metadata Interface:
  - Include a `get_metadata()` method to provide framework details, such as name and version.
- Output Standardization:
  - Provide a `format_output()` method to ensure all methodologies produce outputs in a consistent format, facilitating comparisons across frameworks.

### **Methodology Implementations**

Each methodology module, such as `puro_earth_v3.py` or `verra_v1.py`, extends the `BaseMethodology` class to implement framework-specific logic. While methodologies may vary in their requirements and rules, all modules share common responsibilities:

- **Input Validation**
  - Each methodology implements the `validate_inputs()` method to enforce its framework-specific rules. This includes:
    - **Feedstock Eligibility:** Checking that feedstocks meet framework-specific sustainability criteria (e.g., acceptable types, sources, and processing methods).
    - **Biochar Properties:** Ensuring biochar meets minimum standards (e.g., H/C ratio thresholds, ash content limits).
    - **Operational Boundaries:** Validating that production and application conditions (e.g., temperatures, use cases) align with the framework’s requirements.
  - Outputs include:
    - Structured error messages for invalid inputs.
    - Warnings for suboptimal but acceptable conditions.
- **Lifecycle Analysis**
  - The `calculate_removals()` method computes net CO₂ removals by integrating:
    - **Baseline Emissions:** Avoided emissions from alternative biomass fates (e.g., landfill methane emissions).
    - **Project Emissions:** Emissions generated during feedstock processing, transportation, and biochar application.
    - **Permanence Factors:** Framework-specific adjustments for biochar stability over time (e.g., decay models or thresholds).
  - The results include a detailed breakdown of emissions and net removals.
- **Metadata**
  - Each module provides metadata about the framework via the get_metadata() method, including:
    - Framework name and version.
    - Key assumptions (e.g., calculation boundaries, default values for missing data).

**Outputs**

- All outputs are standardized using the `format_output()` method from the base class to ensure consistency across methodologies. Outputs typically include:
  - Framework name and version.
  - Net CO₂ removals with units.
  - Detailed breakdown of lifecycle emissions (e.g., baseline emissions, project emissions, leakage).
  - Warnings or informational messages.
- **Framework-Specific Rules**
  - While the overall structure is shared, each methodology implements rules unique to its framework. For example:
    - Puro.earth: Emphasizes H/C ratio thresholds for permanence and simplified lifecycle assessments.
    - Verra: Includes more detailed permanence decay models and stricter feedstock sustainability criteria.
    - Future methodologies may introduce new concepts (e.g., carbon credit aggregation, hybrid use cases).

### **Methodology Factory**

The `factory.py` module dynamically manages methodologies and their versions.

- **Registry system:** Maps methodologies and their versions to corresponding modules.
- **Dynamic loading:** Routes user requests to the correct methodology version.
- **Backward compatibility:** Ensures existing projects continue to use earlier versions.

Example usage:

```python
from sequestrae.methodologies.factory import MethodologyFactory

# Load Verra v2
methodology = MethodologyFactory.get_methodology("verra", "v2")
validation_report = methodology.validate_project(project_data)
results = methodology.calculate_removals(project_data)
```

## **Data Configurations**

The `data/` directory stores methodology-specific parameters in versioned JSON files.

```
data/
  ├── input_schema.json          # Defines the shared input structure used by all methodologies
  ├── verra/
  │   ├── v1.json                # Configuration for Verra version 1
  │   ├── v2.json                # Configuration for Verra version 2
  ├── puro_earth/
  │   ├── v3.json                # Configuration for Puro.earth version 3
  ├── riverse/
  │   ├── v1.json                # Configuration for Riverse version 1
```

### **Shared Input Schema**

The `input_schema.json` file defines the structure, required fields, and validation rules for project input data. It ensures that all methodologies consume a consistent input format, simplifying validation and enabling cross-framework comparisons.

Purpose:

- Consistency: Standardizes input across all frameworks.
- Validation: Acts as the foundation for initial schema validation in `input_validation.py`.
- Extensibility: Allows easy addition of optional fields for future methodologies.

Example fields in `input_schema.json`:

```json
{
  "project_metadata": {
    "project_name": "string",
    "location": "string",
    "start_date": "date",
    "end_date": "date",
    "framework_version": "string"
  },
  "feedstock": {
    "type": "string",
    "moisture_content": "number",
    "energy_content": "number"
  },
  "production": {
    "technology_type": "string",
    "temperature": "number",
    "yield_efficiency": "number"
  },
  "biochar_properties": {
    "h_c_ratio": "number",
    "ash_content": "number"
  },
  "application": {
    "application_rate": "number",
    "application_area": "number",
    "use_case": "string"
  },
  "lifecycle_data": {
    "baseline_emissions": "number",
    "project_emissions": "number",
    "leakage_risks": "number"
  }
}
```

### **Methodology-Specific Configurations**

Each methodology has its own configuration files stored in versioned subdirectories. These files contain framework-specific parameters, such as thresholds, emission factors, and eligible feedstocks.

Example Configuration File (Verra v2):

```json
{
  "emission_factors": {
    "transport": 0.02,
    "pyrolysis": 0.1
  },
  "permanence": {
    "h_c_threshold": 0.7,
    "default_factor": 0.9
  },
  "approved_feedstocks": ["wood", "agricultural_waste"]
}
```

Key elements:

- Emission factors:
  - Framework-specific coefficients for calculating emissions (e.g., transport, pyrolysis).
- Permanence parameters:
  - H/C thresholds, decay factors, or other indicators of carbon stability.
- Approved feedstocks:
  - Lists of eligible feedstock types that meet sustainability criteria.
- Methodology-specific params.

The `templates/` directory provides boilerplate code to ensure consistency and simplify adding new methodologies.

# **Input and Output**

### Input format

The platform accepts **JSON-based inputs**, validated against the shared `input_schema.json`. These inputs are processed by the `input_validation.py` module and further validated by methodology-specific rules.

Example:

```json
{
  "project_metadata": {
    "project_name": "Example Biochar Project",
    "location": "USA",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "framework_version": "v2"
  },
  "feedstock": {
    "type": "wood",
    "moisture_content": 12.5,
    "energy_content": 18.3
  },
  "production": {
    "technology_type": "pyrolysis",
    "temperature": 600,
    "yield_efficiency": 30.5
  },
  "biochar_properties": {
    "h_c_ratio": 0.6,
    "ash_content": 2.5
  },
  "application": {
    "application_rate": 10,
    "application_area": 50,
    "use_case": "soil"
  },
  "lifecycle_data": {
    "baseline_emissions": 15.0,
    "project_emissions": 5.0,
    "leakage_risks": 2.0
  }
}
```

**Input validation process:**

- Schema validation:
  - The `input_validation.py` module ensures compliance with `input_schema.json`, checking field existence, data types, and valid ranges.
- Methodology-specific validation:
  - Inputs are passed to the selected methodology’s `validate_inputs()` method for additional checks (e.g., feedstock eligibility, H/C ratio thresholds).
- Error and warning handling:
  - Errors: Critical issues (e.g., missing required fields, invalid feedstock types) halt the process and return structured error messages.
  - Warnings: Non-critical issues (e.g., suboptimal feedstock conditions) are included in the output.

### **Output Format**

The platform generates standardized JSON outputs, with optional conversion to a Pandas DataFrame for analytical workflows. Outputs include:

- Framework Metadata: Name and version of the methodology.
- Net CO₂ Removals: Total removals with detailed lifecycle breakdowns.
- Warnings: Structured messages for any issues identified during validation.

Default JSON output example:

```json
{
  "framework": "Verra",
  "version": "v2",
  "net_removals": 95.6,
  "units": "tonnes CO2eq",
  "breakdown": {
    "feedstock_emissions": 2.4,
    "transport_emissions": 1.0,
    "process_emissions": 1.2,
    "permanence_factor": 0.9
  },
  "warnings": [
    "Feedstock is acceptable but suboptimal for maximum carbon removal."
  ]
}
```

For analytical workflows, the output can be converted to a Pandas DataFrame:

```python
import pandas as pd

# Example conversion
data = {
    "framework": "Verra",
    "version": "v2",
    "net_removals": 95.6,
    "breakdown": {
        "feedstock_emissions": 2.4,
        "transport_emissions": 1.0,
        "process_emissions": 1.2,
        "permanence_factor": 0.9
    }
}
df = pd.json_normalize(data, sep="_")
print(df)
```

### **Error and Warning Structure**

Errors are returned as structured JSON objects, specifying the issue and location in the input. Example:

```json
{
  "error": {
    "field": "feedstock.type",
    "message": "Invalid feedstock type: 'plastic'. Allowed types are ['wood', 'agricultural_waste']."
  }
}
```

Warnings are included in the output to highlight non-critical issues. Example:

```json
{
  "warnings": [
    "Feedstock moisture content is higher than optimal (ideal < 10%)."
  ]
}
```

# **Testing**

- **Unit Tests:** Validate core functionalities and individual methodology modules.
- **Integration Tests:** Test interactions between core modules and methodologies.
- **Edge Case Tests:** Ensure predictable behavior with unusual inputs.
- **Real-World Validation:** Compare results with published projects (e.g., Puro Earth).

---

# Planning

## Week 1: Foundation Setup

### Goal

Establish the foundational structure and implement core utilities to support methodology development.

### **Tasks**

**Directory and File Structure**

- Create the project structure: `core/`, `data/`, `methodologies/`, `tests/`, `examples/`
- Add placeholder files for:
- `core/`:
  - `biochar_properties.py`
  - `input_validation.py`
  - `utilities.py`
  - `constants.py`
- `methodologies/`:
  - `abstract_methodology.py`
  - `factory.py`
- `templates/`
- `data/`: Create `input_schema.json` (draft) and subdirectories for `verra/`, `puro_earth/`.

**Environment Setup**

- Configure `requirements.txt` with core dependencies: `pytest`, `pydantic`, `jsonschema`, `logging`, `pandas` , `numpy`

**Core Utilities**

- Implement `utilities.py`:
  - JSON I/O for configuration and results.
  - Logging setup using Python’s logging module.
- Implement `constants.py`:
  - Define global constants (e.g., CO₂ equivalence factors, default units).

**Testing Setup:**

- Add a basic testing framework using `pytest`.
- Write unit tests for:
  - JSON I/O (valid/invalid JSON handling).
  - Logging functionality.

### **Deliverables**

- Fully functional directory structure with placeholder files.
- Implemented and tested `utilities.py`and `constants.py`

## Week 2: Input Validation Framework

1. Develop `utilities.py`:
   - JSON I/O for configuration file handling
   - Logging setup using Python's logging module
2. Develop `constants.py`:
   - Define global constants (e.g., CO₂ equivalence factors, default units)

### Goal

Develop the input validation system using the shared `input_schema.json` and lay the groundwork for methodology-specific validation.

### Tasks

**Shared Input Schema**

- Draft and finalize `data/input_schema.json`:
  - Include fields for `project_metadata`, `feedstock`, `production`, `biochar_properties`, `application`, and `lifecycle_data`.

**Input Validation Module**

- Implement `input_validation.py`:
  - Add schema validation logic using `jsonschema`.
  - Include support for handling missing optional fields (default values, warnings).
  - Raise errors for critical issues (e.g., invalid or missing required fields).

**Integration with Methodology Logic**

- Add placeholder logic in `factory.py` to pass validated inputs to methodology-specific `validate_inputs()` methods.

**Testing**

- Write unit tests for `input_validation.py`:
  - Test compliance with `input_schema.json`.
  - Validate edge cases (e.g., missing optional fields, invalid types).

### **Deliverables**

- Finalized `input_schema.json`.
- Implemented and tested `input_validation.py`.

## **Week 3: Abstract Methodology and Methodology Factory**

### **Goal**

Define the abstract base class and enable dynamic loading of methodologies via the factory.

### **Tasks**

**Abstract Methodology Class**

- Implement `abstract_methodology.py`:
  - Define `BaseMethodology` with required methods:
    - `validate_inputs()`, `calculate_removals()`, `get_metadata()`, `format_output()`.

**Methodology Factory**

- Implement `factory.py`:
  - Add a registry mapping methodologies and versions to their respective classes.
  - Implement logic for dynamically instantiating methodology classes based on input.

**Testing**

- Write unit tests for:
  - Dynamic loading of placeholder methodologies via `factory.py`.
  - Abstract class enforcement (e.g., unimplemented methods should raise `NotImplementedError`).

### **Deliverables**

- Fully implemented and tested `abstract_methodology.py` and `factory.py`.

## **Week 4: Puro.earth Methodology**

### **Goal**

Implement the Puro.earth v3 methodology, including validation logic and lifecycle analysis.

### **Tasks**

**Puro.earth Configuration**

- Populate `data/puro_earth/v3.json`:
  - Include emission factors, H/C thresholds, and feedstock eligibility criteria.

**Validation Logic**

- Implement `puro_earth_v3.py`:
  - Extend `BaseMethodology` and implement `validate_inputs()` with framework-specific rules.
  - Validate feedstock type, H/C ratio, and production conditions.

**Lifecycle Analysis**

- Implement `calculate_removals()` in `puro_earth_v3.py`:
  - Use configuration parameters to compute baseline emissions, project emissions, and net CO₂ removals.

**Testing**

- Write unit tests for `puro_earth_v3.py`:
  - Test validation logic against valid and invalid project data.
  - Verify lifecycle analysis calculations for sample inputs.

### **Deliverables**

- Implemented and tested `puro_earth_v3.py` and `data/puro_earth/v3.json`.

## **Week 5: Verra Methodology – Validation Logic**

### **Goal**

Implement validation logic for Verra v1 methodology.

### **Tasks**

**Verra Configuration**

- Populate `data/verra/v1.json`:
- Include emission factors, stricter feedstock eligibility criteria, and permanence parameters.

**Validation Logic**

- Implement `validate_inputs()` in `verra_v1.py`:
  - Validate feedstock eligibility, sustainability criteria, and H/C thresholds.
  - Add warnings for borderline or suboptimal conditions.

**Testing**

- Write unit tests for:
  - Validation logic against Verra-specific rules.
  - Error and warning handling for edge cases.

### **Deliverables**

- Implemented and tested `verra_v1.py` (validation logic).
- Completed data/verra/v1.json.

## **Week 6: Verra Methodology – Lifecycle Analysis**

### **Goal**

Complete lifecycle analysis for Verra v1 methodology.

### **Tasks**

**Lifecycle Logic**

- Implement `calculate_removals()` in `verra_v1.py`:
  - Include permanence decay modeling and leakage adjustments.
  - Compute baseline emissions, project emissions, and net CO₂ removals.

**Cross-Framework Simulation:**

- Test compatibility between Puro.earth and Verra for shared inputs.
- Ensure consistent handling of outputs via `format_output()`.

**Testing**

- Write unit tests for:
  - Lifecycle analysis calculations.
  - Output format consistency.

### **Deliverables**

- Fully implemented and tested `verra_v1.py`.

## **Week 7: Edge Cases and Integration Testing**

### **Goal**

Validate system behavior for edge cases and complete integration testing.

### **Tasks**

**Edge Case Testing**

- Test borderline values for feedstock properties, H/C ratios, and emissions.
- Validate error and warning handling across methodologies.

**Integration Testing**

- Test full workflows for Puro.earth and Verra, from input validation to output generation.
- Validate dynamic methodology loading in `factory.py`.

**Real-World Data Testing**

- Use sample projects from public registries to validate outputs against expected results.

### **Deliverables**

- Fully tested integration of Puro.earth and Verra methodologies.
- Validated system behavior for edge cases.

## **Week 8: Documentation and Feedback**

### **Goal**

Prepare the platform for internal use and gather feedback for refinement.

### **Tasks**

**Documentation**

- Add docstrings to all modules and methods.
- Write a `README.md` with:
  - Overview of the engine structure.
  - Usage examples for Puro.earth and Verra methodologies.

**Internal Review**

- Share the platform for review and collect feedback.
- Prioritize refinements based on user feedback.

**Iterative Improvements**

- Address feedback and finalize the codebase.

### **Deliverables**

- Complete documentation and usage guides.
- Finalized and reviewed platform.
