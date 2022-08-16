# AEP 008: Proper caching policy for calcjob with RemoteData as output or input node in edge

| AEP number | 008                                                                    |
|------------|------------------------------------------------------------------------|
| Title      | Caching policy for calcjob with RemoteData as output/input node in edge|
| Authors    | [Jusong Yu](mailto:jusong.yu@epfl.ch) (@unkcpz)                        |
| Champions  | Sebastiaan Huber (@sphuber)                                            |
| Type       | S - Standard Track AEP                                                 |
| Created    | 28-June-2022                                                           |
| Status     | WIP                                                                    |

## Background and problems description
There are problems when the `CalcJob` has the `RemoteData` node as its output and the `CalcJob` is then further used for caching. 
The overall goal of this AEP in summary is to have a better caching policy so that the cleaning and modification of caching sources will not have side effect on the cloned calculations and nodes.

As an overview, we are going to solve the following issues:

- Shallow copy on `RemoteData.clone()`
- Invalidate cache after `RemoteData.clean()`
- Hash calculation of `RemoteData`
- Prospective workchain caching

### Shallow copy
Contents of the RemoteData should really be cloned on the remote as well, not just the reference in AiiDA's database.
The new RemoteData node created from caching has the remote folder pointed exactly the same in the remote machine.
This led to that when doing `clean_workdir` from the cached calcjob the remote folder of the original node is also cleaned up and unable to be used for further caching for other subsequent calculations which is not expected.

### Hash calculation of `RemoteData`
The hash of a `RemoteData` is computed based on the absolute filepath on the remote file system. 
This means that two nodes that have identical contents but have different base folders, will have different hashes. 
Ideally, the hash should be calculated based on the hash of all contents, independent of the location on the remote.

### Invalidate cache of the node after clean
When `RemoteData._clean()` is called, an attribute or extra should be set which will cause it to no longer be considered a (fully) valid cache source.
This is something requires discussion along with next item, the invalid tag attribute can be put to either the process node or the RemoteData node. 
But be careful, I said not ‘fully’ valid cache source, since if the CalcJob node is finished with the expected and we want to use it next time from caching, no matter the RemoteData node attached to the CalcJab is cleaned or not, we want next run of the calculation with exactly the same input parameters can using the cache. 
We only don’t want to use the RemoteData as the input of other further calculations (For instance, `PhCalculation` following a `PwCalculation`). 
The catch is that only until the subsequent calculation runs we know that we need to regard it is a valid caching source or not. 

### Prospective workchain caching
If an entire workchain has already been run once, in principle it is not necessary to run its individual calcjobs again and we can simply cache everything. 
Currently, the engine will still execute each step and consider each calcjob individually whether it should be cached. 
If one of the remote folders of the cached jobs has been cleaned in the meantime, the workchain will fail, even though all results are essentially known. 
One might think that we could just add a check that if the workchain with the same inputs exist, we simply clone the entire matched workchain, including everything it ran, without running anything.


## Proposed Enhancement 
The issues mentioned above are more or less related. 

### Shallow copy
I propose to when clone the `CalcJob` node with `RemoteData`, the `RemoteData` cloned with actually open a connection to remote machine and copy the whole remote folder to a new remote repository. 

#### Drawback
As mentioned by Sebastiaan, the cloning will often happen by a daemon worker and so the opening of the transport should go through the transport queue. However, the call for the clone comes somewhere from `Node.store()` and it is not evident how to get access to the transport queue in a "nice" non-hacky way. 
Without looking at the code, I think there is probably some way to schedule a transferring task for the connection needed clone of the RemoteData node. But it is for sure not as easy to implement as it looks like (I’ll update AEP after I have more concret plan on how to do this). 

### Hash calculation of `RemoteData`
I propose we change the hashing of `RemoteData` from based on the absolute filepath on the remote file system to based on computing hashing from the hashing of the calculation process which generates this RemoteData node, since in the production environment the `RemoteData` can only be generated by a calculation process.
For this, we need to prevent generating a RemoteData without a parent process.
(? not sure this is an advantage) I think there is another advantage that the cloned RemoteData with different hashing will never be picked up as the cached source since as the input its hashing is changed.

#### Drawback
When cached from the noumenon, the copied process nodes have different hashing so the RemoteData node of it should be regenerated. 
Not sure it is possible to generate the hashing in the clone phase. 

### Invalidate cache of the node after clean and prospective workchain caching
I’d like to put these two problems together since the workchain caching at the moment is already supported with all the sub-workchains/calcjobs cached. 
The problem comes when invalidating the cache of the RemodeData from a middle step will break the caching of whole workchain as it used to. 

The target of caching is always AiiDA users do not need to run an identical calculation again which waste time and money. 

… (describe two cases of large workchain design using pw+ph and MC3D junfeng/francisco example.)




