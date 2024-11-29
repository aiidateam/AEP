# AEP 010: Introducing the `PythonJob` in AiiDA

| AEP number | 010                                                          |
|------------|--------------------------------------------------------------|
| Title      | Introducing the `PythonJob` in AiiDA                         |
| Authors    | [Xing Wang](mailto:xingwang1991@gmail.com) (superstar54)     |
| Champions  | [Xing Wang](mailto:xingwang1991@gmail.com) (superstar54)     |
| Type       | S - Standard Track AEP                                       |
| Created    | 28-Nov-2024                                                  |
| Status     | Draft                                                        |


## Table of Contents

1. [Background](#background)  
2. [Proposed Enhancement](#proposed-enhancement)  
   - [Key Features](#key-features)  
3. [Implementation Details](#implementation-details)  
   - [Execution Mechanism](#execution-mechanism)  
   - [User Interface](#user-interface)  
   - [Data Serialization and Deserialization](#data-serialization-and-deserialization)  
     - [Avoiding Duplicate Serializers](#avoiding-duplicate-serializers)  
   - [Handling Files and Folders](#handling-files-and-folders)  
   - [Exit Codes](#exit-codes)  
   - [Namespace Outputs](#namespace-outputs)  
   - [Environment and Dependency Management](#environment-and-dependency-management)  
4. [Usage Examples](#usage-examples)  
5. [Design Considerations](#design-considerations)  
   - [Integration with AiiDA's Architecture](#integration-with-aiidas-architecture)  
   - [Limitations and Constraints](#limitations-and-constraints)  
   - [Future Extensions](#future-extensions)  
6. [Conclusion](#conclusion)


## Background

AiiDA is a powerful platform for managing complex computational workflows and ensuring data provenance. However, it can present a steep learning curve for new users or those with existing computational workflows developed outside of AiiDA. One significant hurdle is the requirement to develop AiiDA plugins to execute codes on remote computers, which involves creating input generators, output parsers, and configuring codes within the AiiDA framework. This process is time-consuming and requires maintaining additional codebases.

Many computational science communities use software packages like ASE (Atomic Simulation Environment) and Pymatgen, which already provide APIs to manage inputs, execute computations, and parse outputs. Requiring developers to adapt their existing packages to AiiDA introduces significant overhead, including maintaining dual codebases and duplicating functionality. Additionally, AiiDA's emphasis on data provenance demands that data conform to its database format, which may differ from formats used by other packages.

These challenges can hinder the adoption of AiiDA, particularly among researchers who lack the resources or expertise to develop custom plugins or who wish to leverage their existing codebases without significant modification.

## Proposed Enhancement

Introduce a new component called `PythonJob` in AiiDA that allows users to deploy their existing Python functions and package APIs to operate jobs on remote computers seamlessly. Users can write standard Python functions using their preferred packages, and `PythonJob` will manage the execution on remote computers, handle data serialization and deserialization, manage data transformations, and ensure comprehensive data provenance within the AiiDA framework.

### Key Features

- **Seamless Integration**: Users can directly use existing Python functions and packages without modification.
- **Remote Execution Management**: `PythonJob` handles data transfer, environment setup, and execution on remote computers.
- **Automatic Data Serialization**: Inputs and outputs are automatically serialized and deserialized, integrating with AiiDA's data types.
- **Data Provenance Tracking**: Full provenance of the computation is recorded in AiiDA's graph, ensuring reproducibility.
- **Flexibility**: Supports custom outputs, dynamic outputs (namespaces), handling of files and folders, and exit codes.

## Implementation Details

### Execution Mechanism

- **Function uploading**: The Python function is inspected, and its source code copied into a runner script(`script.py`), and is transferred to the remote computer, including any necessary imports.
- **Environment Management**: Users can specify environment setup commands (e.g., activating virtual environments, loading modules) in the `metadata`.
- **Data Transfer**: Input data is serialized into `inputs.pickle` file, and is transferred to the remote machine before execution, and output data is serialized into `results.pickle`, and is retrieved after execution completes.
- **Remote Execution**: On the remote machine, the function executes within the prepared environment. A runner script (`script.py`) deserializes inputs, executes the function, and serializes outputs.
- **Data Provenance**: Input and output data is serialized using AiiDA's data types or `PickleData` and stored in the database, ensuring data provenance.

Here is the example `script.py` that runs the `add` function on a remote computer and saves the result to a file:

```python

import pickle

# define the function

def add(x, y):
    z = x + y
    with open("result.txt", "w") as f:
        f.write(str(z))
    return x + y


# load the inputs from the pickle file
with open('inputs.pickle', 'rb') as handle:
    inputs = pickle.load(handle)

# run the function
result = add(**inputs)
# save the result as a pickle file
with open('results.pickle', 'wb') as handle:
    pickle.dump(result, handle)

```

### User Interface

- **Input Preparation**: Users utilize a helper function `prepare_pythonjob_inputs` to package the function, its inputs (`function_inputs`), and other setting parameters (e.g., `computer`, `parent_folder`, `upload_files`, `function_outputs`, and `metadata`).
- **Execution Functions**: Users can execute the `PythonJob` using AiiDA's standard execution functions, such as `run`, `run_get_node`, or `submit`.

### Data Serialization and Deserialization

Users can use standard Python data types for inputs. The `prepare_pythonjob_inputs` function handles the conversion to AiiDA data types. For serialization:

- The function searches for an AiiDA data entry point corresponding to the module and class names (e.g., `ase.atoms.Atoms`).
- If a matching entry point exists, it is used for serialization.
- If no match is found, the data is serialized into binary format using `pickle`.

`PythonJob` searches for data serializers from the `aiida.data` entry points using the module and class names of the data types. To let `PythonJob` find the serializer, users must register the AiiDA data type in their plugin:

```ini
[project.entry-points."aiida.data"]
myplugin.ase.atoms.Atoms = "myplugin.data:AtomsData"
```

This registers a data serializer for `ase.atoms.Atoms`. Standard Python types (e.g., `int`, `float`, `str`, `list`, `dict`) are automatically serialized and deserialized.

#### Avoiding Duplicate Serializers

If multiple plugins register serializers for the same data type, `PythonJob` may raise an error due to ambiguity. To resolve this, users can specify which serializer to use in a configuration file (e.g., `pythonjob.json` in the AiiDA configuration directory):

```json
{
    "serializers": {
        "ase.atoms.Atoms": "myplugin.ase.atoms.Atoms"
    }
}
```

### Handling Files and Folders

- **Uploading Files or Folders**: Users can specify files or folders to upload to the remote working directory using the `upload_files` parameter.
- **Accessing Parent Folder**: Users can specify a `parent_folder` to access files from a previous task, allowing data reuse and chaining of tasks.
- **Retrieving Additional Files**: Users can specify additional files to retrieve from the remote machine after execution using the standard `CalcJob` parameter: `metadata['options']['additional_retrieve_list']`.

### Exit Codes

If the function returns a dictionary containing an `exit_code`, `PythonJob` uses this to set the exit status and message of the process, allowing custom error handling.

Here is an example of a function that handles division by zero and returns an exit code:

```python
def safe_divide(x, y):
    if y == 0:
        return {"result": None, "exit_code": {"status": 400, "message": "Division by zero"}}
    return {"result": x / y}

inputs = prepare_pythonjob_inputs(
    safe_divide,
    function_inputs={"x": 10, "y": 0},
)
result, node = run_get_node(PythonJob, inputs=inputs)
print("Exit status:", node.exit_status)
print("Exit message:", node.exit_message)
```

#### Namespace Outputs

`PythonJob` allows users to define namespace outputs, which are dictionaries with dynamic keys and values returned by a function. Each value in this dictionary is serialized to an AiiDA data node, and the key-value pairs are stored in the database.

**Benefits of using namespace outputs:**

- **Dynamic and Flexible**: The keys and values are not fixed and can change based on the task's execution.
- **Querying**: The data is stored as AiiDA data nodes, allowing for easy querying and retrieval.
- **Data Provenance**: When the data is used as input for subsequent tasks, its origin is tracked.

Example:

```python
from ase.build import bulk

def generate_scaled_structures(structure, factors):
    scaled_structures = {}
    for i, factor in enumerate(factors):
        scaled = structure.copy()
        scaled.set_cell(scaled.cell * factor, scale_atoms=True)
        scaled_structures[f"scaled_{i}"] = scaled
    return {"scaled_structures": scaled_structures}

inputs = prepare_pythonjob_inputs(
    generate_scaled_structures,
    function_inputs={"structure": bulk("Si"), "factors": [0.95, 1.0, 1.05]},
    function_outputs=[{"name": "scaled_structures", "identifier": "namespace"}],
)
result, node = run_get_node(PythonJob, inputs=inputs)
for name, structure in result["scaled_structures"].items():
    print(f"{name}: {structure}")
```

### Environment and Dependency Management

- **Remote Environment Setup**: `PythonJob` can set up the required Python environment on the remote machine by activating virtual environments or using environment modules.

Example of creating a conda environment on a remote computer:

```python
from aiida_pythonjob.utils import create_conda_env

create_conda_env(
    computer="merlin6",             # Remote computer
    env_name="test_pythonjob",      # Name of the conda environment
    modules=["anaconda"],           # Modules to load (e.g., Anaconda)
    pip=["numpy", "matplotlib"],    # Python packages to install via pip
    conda={                         # Conda-specific settings
        "channels": ["conda-forge"],  # Channels to use
        "dependencies": ["qe"]        # Conda packages to install
    }
)
```

### Usage Examples

A simple example of using `PythonJob` to add two numbers:

```python
from aiida.engine import run_get_node
from aiida_pythonjob import PythonJob, prepare_pythonjob_inputs

def add(x, y):
    return x + y

inputs = prepare_pythonjob_inputs(
    add,
    function_inputs={"x": 1, "y": 2},
    computer="localhost",
)
result, node = run_get_node(PythonJob, inputs=inputs)
print("Result:", result["result"])
```

### Design Considerations

#### Integration with AiiDA's Architecture

- **Reusing Existing Infrastructure**: `PythonJob` leverages AiiDA's `CalcJob` infrastructure, including transport, scheduling, and data management.
- **Compatibility with Workflows**: Can be used within AiiDA `WorkChains`, allowing composition of complex workflows.

#### Limitations and Constraints

- **Data Querying**: Data serialized with `pickle` may have limited query capabilities compared to AiiDA's native data types.
- **Environment Management**: Setting up environments on remote computers may introduce errors compared to native AiiDA codes already configured for remote execution.

#### Future Extensions

- **Community-Contributed Serializers**: Development of a registry of serializers for broader data type support.



## Conclusion

The introduction of `PythonJob` represents a significant advancement in making AiiDA more user-friendly and accessible. By allowing users to execute standard Python functions on remote computers while maintaining full data provenance, `PythonJob` reduces the initial setup overhead and encourages broader adoption of AiiDA across diverse computational science and engineering communities. It strikes a balance between flexibility and integration, empowering users to leverage their existing tools within AiiDA's robust workflow and data management framework.