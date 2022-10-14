# Infrastructure to easily run shell commands through AiiDA

| AEP number | 009                                                          |
|------------|--------------------------------------------------------------|
| Title      | Infrastructure to easily run shell commands through AiiDA    |
| Authors    | [Sebastiaan P. Huber](mailto:mail@sphuber.net) (sphuber)     |
| Champions  |                                                              |
| Type       | S - Standard Track AEP                                       |
| Created    | 15-Dec-2021                                                  |
| Status     | submitted                                                    |

## Background
Computational workflows take all sorts of forms and can consist of steps that are wildly varying in nature, from running optimized compiled codes on (remote) high-performance computing platforms, to running simple shell commands.
The former are considered first-class citizens in AiiDA and are therefore well supported and easy to use.
However, the execution of simple shell commands on the local machine are notoriously complicated to be run through AiiDA.

Due to the focus that AiiDA puts on provenance, its workflow system requires to extensively declare the interface of the command to be run and to wrap inputs and outputs in Python objects that are representable as nodes in the provenance graph.
These requirements force the user to write a lot of boilerplate code just to be able to run a simple shell command.

In other workflow systems, invoking shell commands take center stage and are often the most important use case.
Combined with a smaller focus on provenance, the resulting interface for running shell commands is typically a lot simpler and more dynamic compared to AiiDA.
Typically, the user can even specify the execution through simple markup files.
An example of such a definition may look like the following:
```yaml
rule diff:
    input:
        a: "file_a.txt"
        b: "file_b.txt"
    output:
        "output.txt"
    shell:
        "diff {input.a} {input.b} > {output}"
```

Trying to replicate this in AiiDA currently is a lot more complex.
The [`aiida-diff` plugin](https://github.com/aiidateam/aiida-diff) actually does this using a `CalcJob`, and the size of the package shows the complexity that is required.
Granted, this plugin package serves as an example and so is somewhat artificially complex, but the point stands.
Running a shell command through AiiDA is not trivial.
Given the fact that running shell commands are standard operations for many computational workflows, AiiDA is currently not a viable option as a workflow system for a great many use cases.

## Functionality requirements

This AEP proposes to add functionality to AiiDA's engine API that make it easy for users to run arbitrary shell commands, while maintaining provenance.
The design of the new functionality should satisfy the following requirements:

* It should be possible to run any shell command that is available on the machine where AiiDA runs or one of the remote computers that are configured.
* The user should be able to run a shell command from an interactive shell or Jupyter notebook in a dynamic manner.
  That is to say that it should not be required to register entry points, define modules that are added to the Python path, or restart the daemon.
* The user should be able to define the command line arguments to be passed to the command.
* The shell command should be able to be run from within an AiiDA workflow (either within a `WorkChain` or a `workfunction`) and so should be able to be run by a daemon worker.
* The provenance of the shell command execution should be kept as if it were a calculation process.
  That is to say that the execution should be represented by a calculation node in the provenance graph.
  The command line arguments should be attached as inputs nodes, and any generated output should be attached as output nodes.
  The solution should strive to make the input and output node specification as granular as possible, i.e., input arguments that specify files should ideally be stored as individual `SinglefileData` nodes.
  Directories should be represented by `FolderData` nodes.


## Proposed solution

This AEP proposes to introduce a new decorator `shellfunction`.
This `shellfunction` operates similar to a `calcfunction` as in it can decorate a Python function, which when executed, will be represented by a process node in the provenance graph.
The main difference between the `shellfunction` and the `calcfunction` is that the latter requires an actual implementation of the function, because that defines the data mutation that is performed.
The `shellfunction`, however, doesn't necessarily have to define any data mutation, because that is provided by the shell command that it wraps.
The minimum requirement is simply that the `shellfunction` specified exactly what shell command should be invoked.


## User interface and examples

### Running a shell command
The most simple example is to run a shell command without any arguments:

```python
from aiida_shell import launch_shell_job
results, node = launch_shell_job('date')
print(results['stdout'].get_content())
```
Which should print something like `Thu 17 Mar 2022 10:49:52 PM CET`.

### Running a shell command with arguments
To pass arguments to the shell command, pass them as a list to the `arguments` keyword:

```python
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'date',
    arguments=['--iso-8601']
)
print(results['stdout'].get_content())
```
which should print something like `2022-03-17`.

### Running a shell command with files as arguments
For commands that take arguments that refer to files, pass those files using the `nodes` keyword.
The keyword takes a dictionary of `SinglefileData` nodes.
To specify where on the command line the files should be passed, use placeholder strings in the `arguments` keyword.
```python
from io import StringIO
from aiida.orm import SinglefileData
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'cat',
    arguments=['{file_a}', '{file_b}'],
    nodes={
        'file_a': SinglefileData(StringIO('string a')),
        'file_b': SinglefileData(StringIO('string b')),
    }
)
print(results['stdout'].get_content())
```
which prints `string astring b`.

### Running a shell command with files as arguments with specific filenames
The keys in the `nodes` dictionary can only use alphanumeric characters and underscores.
The keys will be used as the link label of the file in the provenance graph, and as the filename in the temporary directory in which the shell command will be executed.
Certain commands may require specific filenames, for example including a file extension, e.g., `filename.txt`, but this cannot be used in the `nodes` arguments.
To specify explicit filenames that should be used in the running directory, that are different from the keys in the `nodes` argument, use the `filenames` argument:
```python
from io import StringIO
from aiida.orm import SinglefileData
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'cat',
    arguments=['{file_a}'],
    nodes={
        'file_a': SinglefileData(StringIO('string a')),
    },
    filenames={
        'file_a': 'filename.txt'
    }
)
print(results['stdout'].get_content())
```
which prints `string a`.

The output filename can be anything except for `stdout`, `stderr` and `status`, which are reserved filenames.

### Passing other `Data` types as input
The `nodes` keyword does not only accept `SinglefileData` nodes, but it accepts also other `Data` types.
For these node types, the content returned by the `value` property is directly cast to `str`, which is used to replace the corresponding placeholder in the `arguments`.
So as long as the `Data` type implements this `value` property it should be supported.
Of course, whether it makes sense for the value of the node to be used directly as a command line argument for the shell job, is up to the user.
Typical useful examples, are the base types that ship with AiiDA, such as the `Float`, `Int` and `Str` types:
```python
from aiida.orm import Float, Int, Str
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'echo',
    arguments=['{float}', '{int}', '{string}'],
    nodes={
        'float': Float(1.0),
        'int': Int(2),
        'string': Str('string'),
    },
)
print(results['stdout'].get_content())
```
which prints `1.0 2 string`.
This example is of course contrived, but when combining it with other components of AiiDA, which typically return outputs of these form, they can be used directly as inputs for `launch_shell_job` without having to convert the values.
This ensures that provenance is kept.

### Defining output files
When the shell command is executed, AiiDA captures by default the content written to the stdout and stderr file descriptors.
The content is wrapped in a `SinglefileData` node and attached to the `ShellJob` with the `stdout` and `stderr` link labels, respectively.
Any other output files that need to be captured can be defined using the `outputs` keyword argument.
```python
from io import StringIO
from aiida.orm import SinglefileData
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'sort',
    arguments=['{input}', '--output', 'sorted'],
    nodes={
        'input': SinglefileData(StringIO('2\n5\n3')),
    },
    outputs=['sorted']
)
print(results['sorted'].get_content())
```
which prints `2\n3\n5`.

### Defining output files with globbing
When the exact output files that will be generated and need to be captured are not known in advance, one can use globbing.
Take for example the `split` command, which split a file into multiple files of a certain number of lines.
By default, each output file will follow the sequence `xa`, `xb`, `xc` etc. augmenting the last character alphabetically.
These output files can be captured by specifying the `outputs` as `['x*']`:
```python
from io import StringIO
from aiida.orm import SinglefileData
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'split',
    arguments=['-l', '1', '{single_file}'],
    nodes={
        'single_file': SinglefileData(StringIO('line 0\nline 1\nline 2\n')),
    },
    outputs=['x*']
)
print(results.keys())
```
which prints `dict_keys(['xab', 'xaa', 'xac', 'stderr', 'stdout'])`.

### Defining a specific computer
By default the shell command ran by `launch_shell_job` will be executed on the localhost, i.e., the computer where AiiDA is running.
However, AiiDA also supports running commands on remote computers.
See the [documentation of `aiida-core`](https://aiida.readthedocs.io/projects/aiida-core/en/latest/howto/run_codes.html#how-to-set-up-a-computer) for instructions to setting up and configuring a remote computer.
To specify what computer to use for a shell command, pass it as an option to the `metadata` keyword:
```python
from aiida.orm import load_computer
from aiida_shell import launch_shell_job
results, node = launch_shell_job(
    'date',
    metadata={'options': {'computer': load_computer('some-computer')}}
)
print(results['stdout'].get_content())
```
Here you can use `aiida.orm.load_computer` to load the `Computer` instance from its label, PK or UUID.


### Workflow demonstration

As the final demonstration for this AEP, let's see how multiple shell jobs can easily be integrated into a workflow using a `workfunction`.
In the following example, we will define a `workfunction` that calls three different types of shell jobs.

1. A starting input file is split into files of two lines using `split`;
2. The resulting files have the last line removed using `head`;
3. Finally, the single-line files are concatenated to produce a single output file.

The code could look as follows:
```python
from io import StringIO
from aiida.engine import workfunction
from aiida.orm import SinglefileData
from aiida_shell import launch_shell_job


@workfunction
def workflow(single_file):

    results, node = launch_shell_job(
        'split',
        arguments=['-l', '2', '{single_file}'],
        nodes={'single_file': single_file},
        outputs=['x*']
    )

    files_truncated = {}

    for key, single_file in sorted(results.items()):

        if not key.startswith('x'):
            continue

        results, node = launch_shell_job(
            'head',
            arguments=['-n', '1', '{single_file}'],
            nodes={'single_file': single_file},
        )
        files_truncated[key] = results['stdout']

    results, node = launch_shell_job(
        'cat',
        arguments=[f'{{{key}}}' for key in files_truncated.keys()],
        nodes=files_truncated,
    )

    return results

# Create input file with the numbers 0 through 9, one number per line.
single_file = SinglefileData(StringIO('\n'.join([str(i) for i in range(10)])))
workflow(single_file)
```

When we call the `workflow` function with the initial input file, the workflow is run and a `WorkFunctionNode` is produced in the provenance graph.
It accurately records its sole input and the produced output file.
In addition, the calls to the `shellfunction`s are also explicitly represented with `CALL` links, as shown in the graphic representation below.
![Workflow provenance graph](provenance.svg "Workflow provenance graph")

## Implementation details

The design presented in this AEP has been implemented in the plugin package [`aiida-shell`](https://github.com/sphuber/aiida-shell).
The functionality to running an arbitrary shell command on any computer is achieved through a `CalcJob` implementation called `ShellJob`:
```python
class ShellJob(CalcJob):
    """Implementation of :class:`aiida.engine.CalcJob` to run a simple shell command."""

    FILENAME_STATUS: str = 'status'
    FILENAME_STDERR: str = 'stderr'
    FILENAME_STDOUT: str = 'stdout'
    DEFAULT_RETRIEVED_TEMPORARY: list[str] = [FILENAME_STATUS, FILENAME_STDERR, FILENAME_STDOUT]

    @classmethod
    def define(cls, spec: CalcJobProcessSpec):
        """Define the process specification.

        :param spec: The object to use to build up the process specification.
        """
        super().define(spec)
        spec.input_namespace('nodes', valid_type=Data, required=False, validator=cls.validate_nodes)
        spec.input('filenames', valid_type=Dict, required=False, serializer=to_aiida_type)
        spec.input('arguments', valid_type=List, required=False, serializer=to_aiida_type)
        spec.input('outputs', valid_type=List, required=False, serializer=to_aiida_type, validator=cls.validate_outputs)
        spec.inputs['code'].required = True

        options = spec.inputs['metadata']['options']
        options['parser_name'].default = 'core.shell'
        options['resources'].default = {'num_machines': 1, 'tot_num_mpiprocs': 1}

        spec.outputs.dynamic = True

```
It can be run like any other calculation job:
```python
from aiida.engine import run
inputs = {
    'code': load('split@localhost'),
    'arguments': ['-l', '2', '{single_file}'],
    'nodes': {'single_file': SinglefileData(StringIO('line 0\nline 1\nline 2\n'))},
    'outputs': ['x*']
}
run(ShellJob, **inputs)
```
The `to_aiida_type` serializer on the input ports takes care of automatically converting the inputs to the corresponding AiiDA data type.

The `stdout` and `stderr` file descriptors are automatically redirected to the `stdout` and `stderr` files in the working directory.
In addition, the exit status of the shell command is written to the `status` file.
These files are retrieved by default and parsed by the `ShellParser`, which is the default parser for the `ShellJob`.
The content of the `stdout` and `stderr` files are attached as `SinglefileData` output nodes.
Any additional output files, specified by the `outputs` input, are also attached as `SinglefileData` nodes.

Even though the `ShellJob` and `ShellParser` essentially provide all the necessary functionality, they are not easy to use for users who have no experience with AiiDA.
Most importantly, they require that a `Computer` and `Code` are configured before they can be used.
This problem is addressed by the `launch_shell_job` utility function.
It is a simple wrapper whose main function is to automatically configure a `Computer` and a `Code` for the specified shell command if no explicit code has been specified.
In addition, it will allow users to pass filepaths in the `nodes` input namespace and the wrapper will automatically convert them to a `SinglefileData` node.
This prevents a user from having to import this class and understand how it works.

## Design choices

The design of the implementation was guides by the following principles:

#. The interface should provide as much flexibility in the Python API as possible but make it fully optional.
   That is to say, for the majority of users who do not need advanced behavior, it should be dead easy to use and the syntax should be as clean and readable as possible.
   A good rule-of-thumb I think is that it should be possible to declare it in a static markup language.
#. There seems to be a need to be able to run shell commands on machines other than localhost.
   This would clearly make the interface more complex, as users will have to define a "computer" and so this will take additional configuration, but this might be worth the additional flexibility.
   Again, making sure this is optional and not requiring this complexity for users that don't need it is of utmost importance.
#. Whenever possible, the running of shell commands should not require the implementation of custom Python code that needs to be registered through entry points or be made importable.
   This includes allowing the shell jobs to be runnable through the daemon without having to restart the interpreter that is launching them, nor the daemon itself.


## Refused alternative designs

One of the first designs of the implementation leveraged the `calcfunction` functionality.
It provided a `shellfunction` decorator that would turn a Python function into a `calcfunction` that would run a shell command:
```python
from aiida.engine import shellfunction

@shellfunction(command='split', output_filenames=['x*'])
def split():
    """Run the ``split`` command."""

arguments = List(['-l', '2', '{single_file}'])
file_split = split(arguments=arguments, single_file=single_file)
```

This design had a number of disadvantages:

* Since the `shellfunction` leveraged a `calcfunction` under the hood, it could only be run on the `localhost` computer.
* The interface of having to define an empty Python function to represent a shell-command, which is only invoked afterwards, felt counter intuitive to many test users.

To solve the limitation of running shell commands only on the localhost, the improved implementation swapped the `calcfunction` for the `CalcJob` as the vehicle.
The downside of this approach, however, was that to run the `ShellCalcJob`, a `Computer` and `Code` have to be configured first, adding a barrier for users to get started easily.
This was addressed by the `launch_shell_job` utility function that takes care of setting up these resources automatically if not provided.
Having a single function that allows a user to define everything also solved the idiosyncracy of the `shellfunction` of having to define an empty Python function before invoking it.
