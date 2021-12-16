# AEP 004: Infrastructure to import completed calculation jobs

| AEP number | 004                                                          |
|------------|--------------------------------------------------------------|
| Title      | Infrastructure to import completed calculation jobs          |
| Authors    | [Sebastiaan P. Huber](mailto:mail@sphuber.net) (sphuber)     |
| Champions  |                                                              |
| Type       | S - Standard Track AEP                                       |
| Created    | 19-Apr-2020                                                  |
| Last modified | 10-Sep-2021                                               |
| Status     | implemented                                                  |

## Background
When new users come to AiiDA, often they will already have completed many simulations without the use of AiiDA.
Seamlessly integrating those into AiiDA, as if they *would* have been, such that they become directly interoperable and almost indistinguishable from any calculations that will be run with AiiDA in the future, is a feature that is often asked for.
For new users of AiiDA, the absence of this functionality could even be a deal breaker for adopting AiiDA as their new workflow management system.

## Proposed Enhancement
AiiDA core will provide a unified mechanism through which any calculation that has been completed outside of AiiDA can be imported into an AiiDA database, as long as there exists a corresponding `CalcJob` plugin.

## Detailed Explanation
The following statement encapsulates the goal that is to be considered when designing the required functionality and implementation of the mechanism that will allow the import of completed calculation jobs:

> Immigrated calculation jobs should resemble normally run jobs as closely as possible, while still making it extremely clear that they have been imported.

The reasons for this statement are simple.
The goal of this functionality is to be able to work with completed calculation jobs through AiiDA, whether they were actually run through AiiDA or not.
Therefore, the attributes of the nodes that represent the calculation job in the provenance graph, as well as the inputs and outputs should respect the same rules, regardless of the origin of the calculation.
However, since small differences will be unavoidable (as will be explained in greater detail later) and imported calculations *are* different from native ones, it remains important to be able to distinguish them whenever necessary.
Note that with whatever mark imported nodes will be distinguished, this should not be inherited by calculations that use the outputs of imported calculations for their inputs.
The calculations will be linked through the provenance graph and therefore this information will already be included implicitly.

### Desired functionality
* Given an existing folder that contains the outputs of a completed calculation job, one should be able to import it, meaning it should be included in the provenance graph, including attributes, inputs and outputs, as if it had been run through AiiDA.
  The method should account for the possibility that a perfect reconstruction of input nodes from the inputs files will not always be necessarily possible and only a subset of inputs will be able to be parsed.
* The functionality should allow the folder to be on the local filesystem, as well as on a remote file system, as long as the corresponding computer has been configured in AiiDA

### Design considerations
As a first general statement, the import functionality should not allow to import data of arbitrary quality: a lot of AiiDA's business logic surrounding the provenance graph, is written to guarantee its consistency and integrity with respect to the data and their interconnections.
For example, the export functionality does not allow incoherent sub sets of nodes to be exported (for example a process node without its outputs) as, when imported, could lead to a provenance graph that is incomplete or inconsistent.
The import functionality should not be an exception to compromise the integrity of the provenance graph.

The first consideration to be made is the division of labor between `aiida-core` and the code specific plugin in the import process.
A solution that is fully implemented in `aiida-core` is impossible, because it cannot know how to reconstruct the required input data nodes just from the contents of the folder of the completed calculation.
This process is always going to be plugin (and potentially even case) specific and so independent of the final mechanism, this code will always have to be provided by the plugin.
In a sense, its task is the exact inverse of that of the `CalcJob.prepare_for_submission` method: given a set of input files, reconstruct the AiiDA input data nodes.

Since this step will anyway have to be performed by code from the plugin, at that point the most natural way to proceed is to use the existing mechanism of launching a `CalcJob`.
At this point, one has the inputs of the calculation that is to be imported and one just has to run it through AiiDA.
From AiiDA's point of view, the procedure is then almost completely analogous to a normal calculation job run, except that instead of performing, the `upload`, `submit` and `update` tasks, we pretend those have already been executed (which in a way is actually the case) and proceed straight to the `retrieve` step.
By using the same internal mechanism to "launch" a completed calculation job as one would a native one, we ensure that the potential differences in the resulting nodes are reduced to a minimum, conforming to the most important design rule.
In addition, the user of AiiDA can use the same interface with which they are already familiar and will not have to learn a new interface.

The only additional information that has to be communicated to the engine in an import run over a normal run, is the location of the output files that are to be retrieved.
Normally, these files are created in a working directory that is created by the engine and is connected as a `RemoteData` node to the calculation job node through a `CREATE` link.
For an import run, the most natural choice of communicating the location of the output folder to the engine therefore seems to be a `RemoteData` node and simply pass it as one of the inputs.
The base `CalcJob` class would simply define an optional input port `remote_folder` that can take a `RemoteData` node.
The benefits of using the `RemoteData` node is that it combines the two pieces of required information, the absolute path of the folder and the computer on which it resides, into one.
Another option would be to use the `metadata.options` namespace of the `CalcJob` inputs namespace, but there one would have to add at least two fields to host both pieces of information.
The engine, on detecting the `remote_folder` node in the inputs, still runs the pre-submit step, creating the input files from the input nodes and storing them on in the calculation job node's repository, but then instead of proceeding to the `upload` step, sets the `remote_workdir` attribute and procedes to the `retrieve` transport task.
This retrieve task obtains the location of the to be retrieved files and the list of files that should be retrieved from the node.

With this approach, the resulting provenance graph from an imported calculation job will be identical to that of a native run (except that the `remote_folder` will be in an input instead of an output for an imported job), which is exactly the goal.
Altough the difference in the `remote_folder` already provides a way to distinguish imported jobs from normal ones, it requires the checking of links from the node.
It would be useful to have a more efficient way to make the distinction, which is why we propose that imported calculation job nodes will get a special attribute that marks them as such.
This can then be used in queries as well as in the normal API to identify imported calculation jobs.
With the current design of AiiDA, it would have made sense to use a "hidden" extra, just as being used for cached calculation jobs, that get an `_aiida_cached_from` extra.
However, since extras are mutable and can be (accidentally) deleted, this may be too fragile, even though the same problem holds for the caching extra, which, when lost, would also represent significant data loss.
There are plans to create another column on the node table that can be used by AiiDA's engine to set these kinds of internal attributes, but this not yet been implemented.
Given that imported jobs will really only be distinguishable by this attribute, choosing the mutable extras for this is too fragile and so it is better to use an immutable attribute.

Finally, there is the question on the requirements of the `computer` and `code` input.
Currently, the `code` input is required for the `CalcJob` process class and so is the `computer`, which can either be defined indirectly through the `Code` (which always has a direct link to a `Computer`) or through the `metadata.computer` input.
However, since for the import of a completed job, the `Code` is not actually necessary, as it will not actually be used, having this required maybe annoying to the user.
On the other hand, making the code and computer input optional only for imported calculation jobs, directly goes against the design goal of reducing differences between imported and natively run calculation jobs to a minimum.
Not having this information for imported jobs may make analysis of all calculation jobs more complicated (as one can no longer assume all have these inputs) but it also reduces the degree of provenance that is stored.
Then again, since there is no way for the engine to check if the presented `Code` actually corresponds to whatever it was that was run to produce the output files that are to be imported, the user can pass *any* `Code` instance.
The question then becomes whether it is better to not have information at all than to potentially have incorrect information.
Ultimately though, there are a lot ways to lose provenance in AiiDA and it is always up to the user to try and minimize this.
Also in this situation one should probably just instruct the user to be aware of this fact and suggest to construct a `Code` and `Computer` instance that represents the actual run code as closely as possible, as it is in their own best interest.
If we decide to make the `Code` and `Computer` optional, we should be aware of the possibility that there might be plugins out there that rely on the fact that these inputs were required, and so, for example, may try to access them directly in the `prepare_for_submission` method without explicit checks or exception handling.
If this is the case, the proposed import method would not work as the `prepare_for_submission` would except in case of the absence of either inputs.

The last point highlights a direct conflict of two interests: from the perspective of the integrity of the provenance graph, we do not want to accept arbitrary data to be imported, but rather want to require that the parsed input data respects the input spec of the relevant `CalcJob` class.
However, in practical situations (which is ultimately the target of this proposed new functionality), the exact input of some computed output may not always be available anymore and so importing it with well-enough reconstructed inputs will not be possible.
As a first version, it is best to start with a design with strict validation requirements, which can then potentially be relaxed in the future if experience shows that to be acceptable and desirable.


### Design choices
* The import functionality will use the same infrastructure as native calculation job runs as much as possible to reduce the chances from undesirable differences in outcome.
* The user interface to import a completed calculation job will use the same launchers as normal calculation jobs.
  This means that `run` and `submit` of the `aiida.engine.launch` module will be used to import calculations.
  We should see whether `submit` should simply pipe through to `run` under the hood, or whether there is an actual use case of having import jobs be sent to the daemon.
* The location of the output files will be communicated to the engine by means of a `RemoteData` node passed in the inputs under the name `remote_folder`.
* The `Code` input and `Computer` inputs will no longer be required, as long as there is `remote_folder` input which signals an import job.
  It will still be possible to pass a `Code` and/or `Computer` and they will be linked to the job as usual, but there will be no consistency check between them and the files that are to be imported.
  It is the responsibility of the user to make sure that the associated code and computer make sense.
* The created calculation job node, will have an attribute `imported=True`.
* The `aiida-core` package will provide a new entry point group called `aiida.calculations.importers` in which implementations of the `CalcJobImporter` class can be added.
  They can be loaded through a `CalcJobImporterFactory`.
  The class implements a single method called `parse_remote_data` which parses the input files contained within a `RemoteData`, together with optional keyword arguments that are plugin specific, and returns a dictionary of inputs that could be used to launch a job of the associated `CalcJob` plugin.
* For the first implementation, imported calculation jobs will not be considered as a valid cache. In the future, when the functionality has been thoroughly tested, we might relax the constraints and allow caching from imported jobs.

### Naming
The first ever proof of concept to import a completed calculation job into AiiDA, was implemented directly for the `PwCalculation` plugin of `aiida-quantumespresso` by Eric Hontz.
He originally chose the name `PwCalculationImporter` and since then the concept has been referred to with the terms "immigration" and "immigrator".
Here we have decided, however, to rename the operation to "importing" as that reflects better what actually is happening: a completed calculation job is literally imported into an AiiDA database, as one can import nodes from an AiiDA archive.
This also highlights the main disadvantage of the name "import" as it is already used for the ingesting of export archives and could potentially be confused.
However, when explicitly referred to as "calculation job importing" the risk of ambivalence should be minimal, and any alternative names would be a lot less clear.

### User interface and example
Below an example of the user interface that would follow when implementing the presented design.
The `CalcJob` class gets a new classmethod `get_importer`, that can be used to retrieve the associated `CalcJobImporter` class, and will have the following specification:
```python
@classmethod
def get_importer(cls, entry_point_name: str = None) -> CalcJobImporter:
    """Load the `CalcJobImporter` associated with this `CalcJob` if it exists.

    By default an importer with the same entry point as the ``CalcJob`` will be loaded, however, this can be overridden
    using the ``entry_point_name`` argument.

    :param entry_point_name: optional entry point name of a ``CalcJobImporter`` to override the default.
    :return: the loaded ``CalcJobImporter``.
    :raises: if no importer class could be loaded.
    """
```
As stated in the docstring, by default the method will attempt to load the class from the `aiida.calculations.importers` entry point group with the same entry point name as the `CalcJob` class itself.
Alternatively, if the entry point name does not match that of the `CalcJob`, an explicit entry point name can be specified.
The implementation will simply forward the request to the `CalcJobImporterFactory` which will operate just like all other plugin factories and so the user can also opt to use the factory directly.
The `get_importer` method on the `CalcJob` class is just a convenience method as often that is the central point from which the importing process will be thought of and there will typically be just a single importer with the same entry point name.

The `CalcJobImporter` is an abstract class which is defined as follows:
```python
class CalcJobImporter:

    @staticmethod
    @abstractmethod
    def parse_remote_data(remote_data: RemoteData, **kwargs) -> Dict[str, Union[Node, Dict]]:
        """Parse the input nodes from the files in the provided ``RemoteData``.

        :param remote_data: the remote data node containing the raw input files.
        :param kwargs: additional keyword arguments to control the parsing process.
        :returns: a dictionary with the parsed inputs nodes that match the input spec of the associated ``CalcJob``.
        """

```
A plugin package can implement this class for a particular `CalcJob` and register it with an entry point in the `aiida.calculations.importers` group.
The `parse_remote_data` should parse the content of the `remote_data` node and turn them into the dictionary of inputs that would create the outputs that are contained within, were it to be run through the actual `CalcJob`.

From a user perspective, the following is an example of what an actual import of a completed calculation job would look like:
```python
computer = load_computer('localhost')
remote_data = RemoteData('/absolute/path/to/outputs', computer=computer)

inputs = CalcJobPlugin.get_importer().parse_remote_data(remote_data)  # This is functionality that will have to be provided by the specific calculation job plugin
inputs['remote_folder'] = remote_data
results, node = run.get_node(CalcJobPlugin, **inputs)

assert node.get_attribute('imported')
```
Note that despite this unified interface, a single entry point in `verdi` to import a calculation job for an arbitrary entry point might not be trivial.
This is because each `CalcJobImporter` implementation may require any number of custom keyword arguments that cannot necessarily be translated dynamically to command line interface options.
Still, as shown by the example above, the code for importing a job is relatively simple and homogeneous and the user should merely now about the specific keyword arguments which should be documented by the plugin package.

## Pros and Cons

There are no explicit negatives in providing this new functionality, but it does provide a lot of value as it will lower the barrier to the adoption of AiiDA by new users and it reduces the waste of computational resources by preventing completed calculations from having to be recomputed.
However, there are pros and cons in the proposed design of the user interface, which will be discussed in the following.

### Pros
* Reusing the exact infrastructure of native calculation jobs guarantees that the resulting provenance graph is as close to a native run as possible.
* The dedicated `imported` attribute makes it still possible to distinguish imported calculations both in querying as through the API, when necessary.
* Using the same user interface to launch import jobs as for native jobs makes it easier for users to understand it and prevents them from having to learn yet another method, with the corresponding imports.
* By using the same infrastructure *and* interface, the import of jobs can even be seamlessly integrated with existing workchains.
  For example, an existing `BaseRestartWorkChain` will automatically expose the `remote_folder` input port and so the user can even pass this to the workchain and have the calculation imported *through* the workchain, without having to change a single line of code in the workchain itself.
  If one chooses to use a separate interface, this functionality is barred off, unless the workchain code is updated explicitly to accommodate this possibility.
* By purposefully not providing a basic interface for the conversion of output files to inputs nodes in `aiida-core`, we do not run the risk that it is not generic enough for certain calculation job plugins.

### Cons
* The similarity in launching mechanism for native and import calculation jobs may actually be confusing to users. The fact that the only difference is the additional `remote_folder` input node, might go overlooked.
  I actually think this will not be a problem but I am including it here as it has been brought up as a con of the current design by other in private conversations.
  Since one actually have to construct a `RemoteData` and include it in the inputs, I do not think that this happens by accident or to an unexpecting user.
* By purposefully not providing a basic interface for the conversion of output files to inputs nodes in `aiida-core`, we run the risk that the various solutions and their interfaces, that will be designed and provided by the plugins will be wildly disparate.
  This might negate the benefits of the consistent import interface itself in `aiida-core`, by having differing interfaces to create the input nodes themselves, which is a prerequisite step.
