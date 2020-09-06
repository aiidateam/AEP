# Base Iterator: a general iterator for aiida processes

| AEP number |                                                          |
|------------|--------------------------------------------------------------|
| Title      | Base Iterator: a general iterator for aiida processes               |
| Authors    | [Emanuele Bosoni](mailto:ebosoni@icmab.es) (@bosonie), [Pol Febrer](mailto:pol.febrer@icn2.cat) (@pfebrer96)|
| Champions  | 
| Type       | S - Standard                                                 |
| Created    | 07-Sept-2020                                                  |
| Status     |                                                        |

## Background

Since the introduction of the `BaseRestartWorkChain`, aiida core is hosting some workchains aimed to facilitate plugin developers in the
implementation of some tasks that are frequently necessary for high-throughput projects.
Similarly to the task of restarting an AiiDA process, we feel that plugin developers might benefit from the introduction of a workchain 
that is able to run the same AiiDA process iteratively, each time changing one or more inputs.

## Proposed Enhancement

We propose to include in aiida-core the `BaseIteratorWorkChain`, a workchain that runs iteratively a given AiiDA process. By default,
the `BaseIteratorWorkChain` knows how to iterate over all the input ports of the given AiiDA process, however it can be extended
to iterate over some custom parameters.


## Detailed Explanation

### Basic implementation decisions

Following the footsteps of the `BaseRestartWorkChain`, we implemented the `BaseIteratorWorkChain` as an abstract class. However sub classes
just need to define the attribute `_process_class` in order to have a working iterator.
This is sufficent to have an iterator that knows how to iterate over the input-ports of `_process_class`, however it can be extended to
iterate over other parameters making use of the attribute `_params_lookup` (see "Supplementary features" section for info).
By default, `BaseIteratorWorkChain` exposes all the inputs of `_process_class` without namespace. The attribute `_expose_inputs_kwargs` can
be used to pass arguments to the `spec.expose_inputs`, allowing the use of namespaces, the exclusion of some ports and so on.

### API design

Once a `MyIterator(BaseIteratorWorkChain)` has been defined (specifing the attributes explained above), its use is very simple. We already said that
it exposes the inputs of `_process_class`, moreover three additional inputs are accepts.
1. `iterate_over`. It is a dictionary ("key", "value")
    where "key" is the name of a parameter we want to iterate over (`str`) and "value" is a `list` with all
    the values to iterate over for the corresponding key. 
    NOTE_1: if "key" is an input port of `_process_class`, we allow "value" to be a list of aiida data types accepted by the "key"; 
    in fact a serializer is applied internally to transorm the values of the list in the corresponding pk. 
    NOTE_2: the `iterate_over` is a dictionary because it is
    possible to iterate over several keywords at the same time. The way the algorithm deals with these
    multiple iterations is decided by the `iterate_mode` input.
2.  `iterate_mode`. orm.Str. Indicates the way the parameters should be iterated.
    Currently allowed values are: 'zip': zips all the parameters together (all parameters should
    have the same number of values - default), 'product': performs a cartesian product of the parameters
    (all possible combinations of parameters and values are explored).
3.  `batch_size`. orm.Int. The maximum number of simulations that should run at the same time.
    Default to 1.
    
### Supplementary features

We list here detailed description of additional fetures that we implemented. They are extentions to the basic idea of iterating over the
input-ports of `_process_class`.

#### The `_params_lookup`
We mentioned that the attribute `_params_lookup` is used to make the workchain aware of additional parameters
we want to allow. In the current implementation, this are its requirement.
It should be a list of dictionaries where each dictionary should have the following keys:
1. group_name: str, optional
          The name of the group of parameters. Currently not used, but it will probably be used
          to show help messages.
2. input_key: str
          The input of the `_process_class` where the parsed values will end up.
3. parse_func: function
            The function that will be used to parse the values for the parameters. The first arguments
            of this function should be the value to parse (as an aiida node) and the full inputs
            AttributeDict that is going to be passed to the process class. Also it should accept the `input_key` and
            `parameter` keyword arguments, which provides the input_key where the parsed value will go
            and the name of the parameter that the function is parsing. Finally, it needs to accept all kwargs
            that you define in the `keys` key (see below).
            It should not modify the inputs AttributeDict in place, but return the parsed value.
            E.g.:
            def parse_myparameters(val, inputs, parameter, input_key, **kwargs):
                ...do your parsing
                return parsed_value
4.  condition: function, optional
            A function that receives the name of the parameter and decides whether it belongs to this group.
            The function should return either `True`, or `False`.
            It will only be used if the key is not explicitly defined in the `keys` key (see below).
            If not provided, it will always return `False`
5.  keys: dict, optional
            A dictionary where each key is a parameter that can be accepted and each value is either
            a dict containing the kwargs that will be passed to `parse_func` or None (same as empty dict).
            Even when a parameter is not defined here, it will be accepted if it fulfills `condition`.

IMPORTANT NOTE_1: The order in `_params_lookup` matters. The workchain will go group by group trying to
match the input parameter. If it matches a certain group, it will settle with it and won't continue to
check the following groups.

IMPORTANT_NOTE_2: In the current implementation, for each parameter in `_params_lookup`, the allowed values
(that will be passed by users in the list of `iterate_over`) are tight to the definition of the `parse_func`,
but, in any case, they will be tranformed internally in aiida data nodes. This means that:
`iterate_over = {Ecut : [100,200]}` will produce during serialization a node Int(100) and Int(200) and store 
the corresponding pk. This allows maximum flexibility to pass any storable object, but has the downside to
create several nodes.

Example SiestaIterator

#### The method `iteration_input`

The method `iteration_input` creates a specific input that will be used for iteration.
In some situations, developers might want to have a workchain where 
the users does not need to specify a particular parameter in `iterate_over`, but still
iterate over this parameter.
For example, in an equation of state workchain, the scales for which
to submit calculations is the parameter one wants to iterate over. However, it is an input
too important to the workchain to hide under `iterate_over`. In fact, without having values
for this parameter, the workchain does not make sense. By using an iteration input, you can create
an input port `scales` that will host the values to iterate over. Moreover, with this approach, one can
provide a default and make the parameter required.
The method `iteration_input` creates a regular aiida input, so one should use this function as if using `spec.input`.
The only difference is that the workchain is then aware that it needs to serialize the list of values
provided here and incorporate it into `iterate_over`.
Apart from all the parameters that `spec.input` accepts, this function accepts two more parameters:
1. input_key: `str`, optional.
            The name of the input were the values for this parameter will end up
            after (optionally) parsing.
2. param parse_func: `function`, optional.
            Function to be used to parse the values for this parameter
            
Note that these two inputs work the same as if you were defining the parameter in `_params_lookup`.
If you don't provide an `input_key`, the iterator will try to look for the parameter in `_params_lookup` to understand how to parse the values.

In many case, the use of `iteration_input` makes the use of `iterate_over` unnecessary. 
The attribute `_iterate_over_port` can be set to false in order to make the port `iterate_over` not required.

Example

#### Flexibility of rewriting methods.

The modular structure of the workchain implementation allows expert users to redefine methods at will. This can be really usefull in many
cases. Two examples:

1. Some methods of `BaseIteratorWorkChain` can be overridden in order to insert analysis of the results of each iteration and even
   introduce some logic that checks weather to keep iterating or not. On this line we see, for instance, the possibility to use
   the `BaseIteratorWorkChain` as core piece to create convergers. Example SiestaConverger

2. The serialization of the port `iterate_over` is done in independent methods of `BaseIteratorWorkChain`. The change of these
   methods allows to easly change the current API if needed.


#### Reuse of inputs

The final attribute that can be selected in the `BaseIteratorWorkChain` is the `_reuse_inputs` attribute. Set to False as a default,
it can be set to True when some created parameters should be reused by the next step instead of always
grabbing the initial user inputs. This attribute assumes meaning only when an analysis of the results that saves new inputs parameters in
`self.ctx.last_inputs` is implemented. A nice use case is the SequentialConverger (), that is a `BaseIteratorWorkChain` having a 
converger as a `_process_class`!

## Important final remarks

The described implementation of the `BaseIteratorWorkChain` is alrady distributed in the aiida-siesta package. A copy of the class code is
also cloned in this folder to welcome here suggestions on how to improve the implementation.
Some methods of `BaseIteratorWorkChain` are very similar in scope to methods of `BaseRestartWorkChain`. Even though we see the similarity of
some functionality of the two workchains we preferred to keep this implementation completly independent by the `BaseRestartWorkChain`. We can discuss
the interplay between the two classes.
