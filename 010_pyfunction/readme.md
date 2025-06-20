# AEP 010: Introducing the `pyfunction` in AiiDA

| AEP number | 010                                   |
| ---------- | ------------------------------------- |
| Title      | Introducing the `pyfunction` in AiiDA |
| Authors       | [Xing Wang](mailto:xingwang1991@gmail.com) (@superstar54) |
| Champions     | [Xing Wang](mailto:xingwang1991@gmail.com) (@superstar54) |
| Type       | S - Standard Track AEP                |
| Created    | 20-Jun-2025                           |
| Status     | Draft                                 |

## Table of Contents

1. [Background](#background)
2. [Proposed enhancement](#proposed-enhancement)

   * [Key features](#key-features)
3. [Implementation details](#implementation-details)

   * [Execution mechanism](#execution-mechanism)
   * [User interface](#user-interface)
   * [Data serialisation and deserialisation](#data-serialisation-and-deserialisation)

     * [Avoiding duplicate serialisers](#avoiding-duplicate-serialisers)
   * [Namespace outputs](#namespace-outputs)
   * [Exit codes](#exit-codes)
4. [Usage examples](#usage-examples)
5. [Design considerations](#design-considerations)

   * [Integration with AiiDA’s architecture](#integration-with-aiidas-architecture)
   * [Limitations and constraints](#limitations-and-constraints)
   * [Future extensions](#future-extensions)
6. [Conclusion](#conclusion)

---

## Background

`calcfunction` lets users wrap Python functions as AiiDA processes, but every input, output and the entire function body must be rewritten to work with `orm.Data` objects, for example using `x.value` or `data.get_list()`. For small scripts or existing codebases this means maintaining two versions of each function: a plain-Python version for non-AiiDA users and a wrapped version for provenance. This duplication can be prohibitive when porting an existing pure Python workflow. The cost is also especially high for users unfamiliar with AiiDA’s data types.

The `pyfunction` helper removes that friction. It lets any regular Python callable run as an AiiDA process, handling the conversion between raw Python types and AiiDA nodes on the fly while keeping full provenance. The result feels like writing ordinary Python while still giving data management, caching, and workflow composition for free.

---

## Proposed enhancement

Add a decorator and helper, `pyfunction`, that turns a plain function into an AiiDA process without rewriting the function body.

### Key features

* **Near zero-modification workflow** – existing functions can be executed directly.
* **Automatic (de)serialisation** – built-in conversion between basic Python types and AiiDA data nodes.
* **Customisable ports** – explicit or inferred input and output port definitions, including dynamic namespace outputs.
* **Exit-code handling** – functions may return an `exit_code` dict or integer to signal controlled failure.
* **Fast local execution** – runs in the daemon worker without file upload or scheduler overhead, making it lighter than `PythonJob`.
* **Compatibility with serializers from `PythonJob`** – the same mechanisms for extending type support are reused.

---

## Implementation details

### Execution mechanism

* The helper builds a `function_data` record containing a pickled version of the callable, port definitions and optional metadata.
* Inputs are converted to AiiDA nodes before the process starts.
* The callable executes inside the AIIDA daemon worker.
* Results are parsed and stored as outputs, and an exit status is applied when requested.

> Note
> The first prototype persists provenance in a `CalcFunctionNode` because it provides caching and querying out of the box. A future version will introduce a dedicated `PyFunctionNode` class. In either case, all serialisation logic lives in `class PyFunction(Process)` and not in the node itself.

### User interface

```python
from aiida_pythonjob import pyfunction

@pyfunction()
def add_string(x: str, y: str):
    return x + y

result = add_string("hello", "world")
print(result)          # -> "helloworld"
```

Decorator parameters allow explicit port schemas and metadata:

```python
sum_diff = pyfunction(
    outputs=["sum", "diff"]
)(lambda x, y: {"sum": x + y, "diff": x - y})
```

### Data serialisation and deserialisation

* Basic Python primitives (`int`, `float`, `str`, `bool`, `list`, `dict`) are converted to standard AiiDA data types automatically.
* For third-party objects, the helper looks for entry points in `aiida.data`.
* Users may supply a `serializers` or `deserializers` mapping to override or extend the defaults, using the same dotted-path keys as `PythonJob`.

#### Avoiding duplicate serialisers

If more than one plugin registers a serialiser for the same dotted class path, ambiguity is resolved via a per-profile JSON file:

```json
{
  "serializers": {
    "ase.atoms.Atoms": "myplugin.ase.atoms.Atoms"
  }
}
```

### Namespace outputs

Set `identifier: "namespace"` in an output port to allow dictionaries with arbitrary keys:

```python
@pyfunction(outputs=[{"name": "result", "identifier": "namespace"}])
def add_one(data: dict[str, int]) -> dict[str, int]:
    return {k: v + 1 for k, v in data.items()}
```

Nested namespace outputs are supported in the same way.

### Exit codes

Return either

```python
{"exit_code": {"status": 300, "message": "invalid data"}}
```

or simply an integer status to set `node.exit_status` and `node.exit_message`.

---

## Usage examples

### Simple chain

```python
from aiida_pythonjob import pyfunction

add = pyfunction()(lambda x, y: x + y)
length = pyfunction()(len)

total = add("hello", "world")
size = length(total)
print(size)   # 10
```

### Multiple outputs

```python
@pyfunction(outputs=["sum", "diff"])
def sum_diff(x: int, y: int):
    return {"sum": x + y, "diff": x - y}
```

### Dynamic namespace

```python
@pyfunction(outputs=[{"name": "structures", "identifier": "namespace"}])
def scale(structure, factors):
    return {f"scaled_{i}": structure.copy().scale(f) for i, f in enumerate(factors)}
```

---

## Design considerations

### Integration with AiiDA’s architecture

* Reuses the core provenance, and other features (e.g., caching) infrastructure.
* Serialiser registry is shared with `PythonJob`.

### Limitations and constraints

* Execution happens in the worker so long running calls block the daemon; enabling submission as a future enhancement is planned.
* A working directory path is not tracked in the provenance. Workflows that rely on the remote folder path should use `PythonJob`.
* Passing data through globals is unsafe because each process is executed in isolation. Users should return data explicitly.

### Future extensions

* Introduce the dedicated `PyFunctionNode` for clarity and possible performance gains.
* Support submission of `pyfunction` processes.
* Community maintained serialiser library.

---

## Conclusion

`pyfunction` provides a lightweight path from plain Python to fully traceable AiiDA workflows.  It eliminates the code duplication required by `calcfunction`. It complements `PythonJob` for local execution, accelerates rapid prototyping, and serves as the default task type in higher-level tooling such as **aiida-workgraph**.
