# AEP 008: Proper caching policy for calcjob with RemoteData as output or input node in edge

| AEP number | 008                                                          |
|------------|--------------------------------------------------------------|
| Title      | Proper caching policy for calcjob with RemoteData as output or input node in edge          |
| Authors    | [Jusong Yu](mailto:jusong.yu@epfl.ch) (unkcpz)     |
| Champions  |                                                              |
| Type       | S - Standard Track AEP                                       |
| Created    | 28-June-2022                                                  |
| Status     | WIP                                                  |

## Background
There are now two issues when the `CalcJob` has `RemoteData` node as its output and the `CalcJob` is then furthur used for caching. 
First problem is that the `RemoteData` node is only shalow copy with creating a new `RemoteData` node for the new cached node but has the remote folder pointed exactly the same in the remote machine.
This lead to that when doing `clean_workdir` from the cached calcjob the remote folder of the original node also cleaned up and unable to be used for further caching for other subsequent calculation which is not expected.

Another problem when caching with `RemoteData` is, the hash of `RemoteData` node generated from identical two separated run of `CalcJob` are different, which lead to subsequent calculation using `RemoteData` as input is not properly cached from. 
As shown by diagram blow (copy from https://github.com/aiidateam/aiida-core/issues/5178#issuecomment-996536222):
![caching_problem](https://user-images.githubusercontent.com/6992332/146514431-c9634668-6a0d-43ca-8829-4a3a69c16d27.png)

We have `W1` that launches a `PwCalculation` (`Pw1`) which creates a `RemoteData` (`R1`), which is used as input for a `PhCalculation` (`Ph1`). Another `PwCalculation`  (`Pw2`) is run outside of a workchain with the same input `D1`. The hash of `Pw1` and `Pw2` are identical, but the hashes of their `RemoteData`, `R1` and `R2` are different. Now the user launches a new workchain `W1'` which uses the exact same inputs as `W1`. The  `PwCalculation` can now be cached from both `Pw1` and `Pw2` since their hashes are identical. Let's say that `Pw2` is chosen (by chance). This produces `RemoteData` (`R2'`) which has the same hash as `R2` since it is a clone. Now the workchain moves on to running the `PhCalculation`, but it won't find a cache source, because no `PhCalculation` has been run yet with `R2` as an input.

## Proposed Enhancement 
The goal of this proposal is to have a 

## Detailed Explanation 
