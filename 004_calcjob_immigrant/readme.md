# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | 004                                                          |
|------------|--------------------------------------------------------------|
| Title      | Infrastructure to immigrate completed calculation jobs       |
| Authors    | [Sebastiaan P. Huber](mailto:mail@sphuber.net) (sphuber)     |
| Champions  |                                                              |
| Type       | S - Standard Track AEP                                       |
| Created    | 19-Apr-2020                                                  |
| Status     | submitted                                                    |

## Background
When new users come to AiiDA, often they will already have completed many simulations without the use of AiiDA.
Seamlessly integrating those into AiiDA, as if they *would* have been, such that they become directly interoperable and almost indistinguishable from any calculations that will be run with AiiDA in the future, is a feature that is often asked for.
For new users of AiiDA, the absence of this functionality could even be a deal breaker for adopting AiiDA as their new workflow management system.

## Proposed Enhancement
AiiDA core will provide a unified mechanism through which any calculation that has been completed outside of AiiDA, as long as there exists a corresponding `CalcJob` plugin, can be immigrated into an AiiDA database.

## Detailed Explanation
The following statement encapsulates the goal that is to be considered when designing the required functionality and implementation of the mechanism that will allow the immigration of completed calculation jobs:

> Immigrated calculation jobs should resemble normally run jobs as closely as possible, while still making it extremely clear that they have been immigrated

The reasons for this statement are simple.
The goal of this functionality is to be able to work with completed calculation jobs through AiiDA, whether they were actually run through AiiDA or not.
Therefore, the attributes of the nodes that represent the calculation job in the provenance graph, as well as the inputs and outputs should respect the same rules, regardless of the origin of the calculation.
However, since it small differences will be unavoidable (as will be explained in greater detail later) and immigrated calculations *are* different from native ones, it remains important to be able to distinguish them whenever necessary.
Note that with whatever mark immigrated nodes will be distinguished, this should not be inherited by calculations that use the outputs of immigrated calculations for their inputs.
The calculations will be linked through the provenance graph and therefore this information will already be included implicitly.

### Desired functionality
* Given an existing folder that contains the outputs of a completed calculation job, one should be able to immigrate it, meaning it should be included in the provenance graph, including attributes, inputs and outputs, as if it had been run through AiiDA. The method should account for the possibility that a perfect reconstruction of input nodes from the inputs files will not always be necessarily possible and only a subset of inputs will be able to be parsed.
* The functionality should allow the folder to be on the local filesystem, as well as on a remote file system, as long as the corresponding computer has been configured in AiiDA

### Design considerations
As a first general statement, the immigration functionality should not allow to import data of arbitrary quality: a lot of AiiDA's business logic surrounding the provenance graph, is written to guarantee its consistency and integrity with respect to the data and their interconnections.
For example, the export functionality does not allow incoherent sub sets of nodes to be exported (for example a process node without its outputs) as, when imported, could lead to a provenance graph that is incomplete or inconsistent.
The immigration functionality should not be an exception to compromise the integrity of the provenance graph.

The first consideration to be made is the division of labor between `aiida-core` and the code specific plugin in the immigration process.
A solution that is fully implemented in `aiida-core` is impossible, because it cannot know how to reconstruct the required input data nodes just from the contents of the folder of the completed calculation.
This process is always going to be plugin (and potentially even case) specific and so independent of the final mechanism, this code will always have to be provided by the plugin.
In a sense, its task is the exact inverse of that of the `CalcJob.prepare_for_submission` method: given a set of input files, reconstruct the AiiDA input data nodes.

Since this step will anyway have to be performed by code from the plugin, at that point the most natural way to proceed is to use the existing mechanism of launching a `CalcJob`.
At this point, one has the inputs of the calculation that is to be immigrated and one just has to run it through AiiDA.
From AiiDA's point of view, the procedure is then almost completely analogous to a normal calculation job run, except that instead of performing, the `upload`, `submit` and `update` tasks, we pretend those have already been executed (which in a way is actually the case) and proceed straight to the `retrieve` step.
By using the same internal mechanism to "launch" a completed calculation job as one would a native one, we ensure that the potential differences in the resulting nodes are reduced to a minimum, conforming to the most important design rule.
In addition, the user of AiiDA can use the same interface with which they are already familiar and will not have to learn a new interface.

The only additional information that has to be communicated to the engine in an immigration run over a normal run, is the location of the output files that are to be retrieved.
Normally, these files are created in a working directory that is created by the engine and is connected as a `RemoteData` node to the calculation job node through a `CREATE` link.
By simply creating this `RemoteData` from the pre-existing output folder in an immigration run and attaching it as an output of the calculation in the usual way, the retrieval and parse steps that follow proceed exactly as in a normal run.
On top of that, by using the `RemoteData` concept, the required functionality of supporting output folders on both local as well as remote file systems is automatically fulfilled.

The most natural choice of communicating the location of the output folder to the engine would therefore be a `RemoteData` node and simply pass it in as one of the inputs.
The base `CalcJob` class would simply define an optional input port `immigrate_remote_folder` that can take a `RemoteData` node.
The benefits of using the `RemoteData` node is that it combines the two pieces of required information, the absolute path of the folder and the computer on which it resides, into one.
Another option would be to use the `metadata.options` namespace of the `CalcJob` inputs namespace, but there one would have to add at least two fields to host both pieces of information.
The engine, on detecting the `immigrate_remote_folder` node in the inputs, still runs the pre-submit step, creating the input files from the input nodes and storing them on in the calculation job node's repository, but then instead of proceeding to the `upload` step, adds a `CREATE` link to the `immigrate_remote_folder` input and procedes to the `retrieve` transport task.
Note that the input link, that normally would be created between the `immigrate_remote_folder` and the calculation job node, because it was an actual input, has to be removed, since otherwise this would break the acyclicity of the DAG.

With this approach, the resulting provenance graph from an immigrated calculation job will be identical to that of a native run, which is exactly the goal.
However, sometimes it is still necessary to be able to distinguish between the two.
Therefore, immigrated calculation job nodes will get a special attribute that marks them as such.
This can then be used in queries as well as in the normal API to identify immigrated calculation jobs.
With the current design of AiiDA, it would have made sense to use a "hidden" extra, just as being used for cached calculation jobs, that get an `_aiida_cached_from` extra.
However, since extras are mutable and can be (accidentally) deleted, this may be too fragile, even though the same problem holds for the caching extra, which, when lost, would also represent significant data loss.
There are plans to create another column on the node table that can be used by AiiDA's engine to set these kinds of internal attributes, but this not yet been implemented.
Given that immigrated jobs will really only be distinguishable by this attribute, choosing the mutable extras for this is too fragile and so it is better to use an immutable attribute.

Finally, there is the question on the requirements of the `computer` and `code` input.
Currently, the `code` input is required for the `CalcJob` process class and so is the `computer`, which can either be defined indirectly through the `Code` (which always has a direct link to a `Computer`) or through the `metadata.computer` input.
However, since for the immigration of a completed job, the `Code` is not actually necessary, as it will not actually be used, having this required maybe annoying to the user.
On the other hand, making the code and computer input optional only for immigrated calculation jobs, directly goes against the design goal of reducing differences between immigrated and natively run calculation jobs to a minimum.
Not having this information for immigrated jobs may make analysis of all calculation jobs more complicated (as one can no longer assume all have these inputs) but it also reduces the degree of provenance that is stored.
Then again, since there is no way for the engine to check if the presented `Code` actually corresponds to whatever it was that was run to produce the output files that are to be immigrated, the user can pass *any* `Code` instance.
The question then becomes whether it is better to not have information at all than to potentially have incorrect information.
Ultimately though, there are a lot ways to lose provenance in AiiDA and it is always up to the user to try and minimize this.
Also in this situation one should probably just instruct the user to be aware of this fact and suggest to construct a `Code` and `Computer` instance that represents the actual run code as closely as possible, as it is in their own best interest.

The last point highlights a direct conflict of two interests: from the perspective of the integrity of the provenance graph, we do not want to accept arbitrary data to be imported, but rather want to require that the parsed input data respects the input spec of the relevant `CalcJob` class.
However, in practical situations (which is ultimately the target of this proposed new functionality), the exact input of some computed output may not always be available anymore and so immigrating it with well-enough reconstructed inputs will not be possible.
As a first version, it is best to start with a design with strict validation requirements, which can then potentially be relaxed in the future if experience shows that to be acceptable and desirable.


### Design choices
* The immigration functionality will use the same infrastructure as native calculation job runs as much as possible to reduce the chances from undesirable differences in outcome.
* The user interface to immigrate a completed calculation job will use the same launchers as normal calculation jobs. This means that `run` and `submit` of the `aiida.engine.launch` module will be used to immigrate calculations.
* The location of the output files will be communicated to the engine by means of a `RemoteData` node passed in the inputs under the name `immigrate_remote_data`.
* The `immigrate_remote_data` input will **not** receive an input link like it would normally, but instead gets a `CREATE` link with the label `remote_data`.
* The `Code` input remains required on the base `CalcJob` node and the documentation will instruct the user to create a `Code` instance that represents the actually run code as closely as possible.
* The created calculation job node, will have an attribute `immigrated=True`.

### Open questions
* Should an immigrated calculation be considered as a valid node by the caching mechanism?
* Should we provide a standardized interface for the code that reconstructs the inputs given a folder with input files for a given calculation job plugin, or do we leave this completely up to the plugins?

### User interface and example
Below an example of the user interface that would follow when implementing the presented design:

    computer = load_computer('localhost')
    remote_data = RemoteData('/absolute/path/to/outputs', computer=computer)

    inputs = get_inputs_from_folder(remote_data)  # This is functionality that will have to be provided by the specific calculation job plugin
    inputs['immigrate_remote_data'] = remote_data
    results, node = run.get_node(CalcJobClass, **inputs)

    assert node.get_attribute('immigrated')

## Pros and Cons

There are no explicit negatives in providing this new functionality, but it does provide a lot of value as it will lower the barrier to the adoption of AiiDA by new users and it reduces the waste of computational resources by preventing completed calculations from having to be recomputed.
However, there are pros and cons in the proposed design of the user interface, which will be discussed in the following.

### Pros
* Reusing the exact infrastructure of native calculation jobs guarantees that the resulting provenance graph is as close to a native run as possible.
* The dedicated `immigrated` attribute makes it still possible to distinguish immigrated calculations both in querying as through the API, when necessary.
* Using the same user interface to launch immigration jobs as for native jobs makes it easier for users to understand it and prevents them from having to learn yet another method, with the corresponding imports.
* By using the same infrastructure *and* interface, the immigration of jobs can even be seamlessly integrated with existing workchains.
  For example, an existing `BaseRestartWorkChain` will automatically expose the `immigrate_remote_data` input port and so the user can even pass this to the workchain and have the calculation immigrated *through* the workchain, without having to change a single line of code in the workchain itself.
  If one chooses to use a separate interface, this functionality is barred off, unless the workchain code is updated explicitly to accommodate this possibility.
* By purposefully not providing a basic interface for the conversion of output files to inputs nodes in `aiida-core`, we do not run the risk that it is not generic enough for certain calculation job plugins.

### Cons
* The similarity in launching mechanism for native and immigration calculation jobs may actually be confusing to users. The fact that the only difference is the additional `immigrate_remote_folder` input node, might go overlooked.
  I actually think this will not be a problem but I am including it here as it has been brought up as a con of the current design by other in private conversations.
  Since one actually have to construct a `RemoteData` and include it in the inputs, I do not think that this happens by accident or to an unexpecting user.
* By purposefully not providing a basic interface for the conversion of output files to inputs nodes in `aiida-core`, we run the risk that the various solutions and their interfaces, that will be designed and provided by the plugins will be wildly disparate.
  This might negate the benefits of the consistent immigration interface itself in `aiida-core`, by having differing interfaces to create the input nodes themselves, which is a prerequisite step.