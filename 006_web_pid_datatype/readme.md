# New (web) AiiDA PIDData type

| AEP number | 006 Web PID datatype                                              |
|------------|-------------------------------------------------------------------|
| Title      | Implement an additional datatype for possible large data with PIDs|
| Authors    | [Jens Bröder](mailto:j.broeder@fz-juelich.de) (broeder-j)         |
| Champions  | [Giovanni Pizzi](mailto:giovanni.pizzi@epfl.ch) (giovannipizzi)   |
| Type       | S - Standard                                                      |
| Created    | 04-Oct-2021                                                       |
| Status     | submitted                                                             |

## Background

Currently, AiiDA is not so good in keeping track of the provenance of large files and
of data which comes from the outside (internet) but is persistent, i.e it is a published with an persistent, resolvable identifier and meant to stay there for a long time.

For example: Large files will be duplicated on disk, for every minor change to them. 
If a file should be part of the provenance it has to be stored in the repository also.

If one starts from external data sources, if it is an AiiDA database one would have to import
it and export the part which one needs and continue from that. Not so nice if one needs only a
small part from a large data(base/set). There is also currently no AiiDA intrinsic way to keep the
provenance from other data on the internet which has persistent identifiers and links.
The current way would be to download that data and store it in the repository as a single file
data, or some other AiiDA datatype(s) and continue with `CalcFunctions`. 
A lot of work, which every user does different and some not at all, this causes data nodes to appear out
of nowhere, with only 'goodwill' provenance information in the extras, and other annotations set by the user.
This is also not so practical for large files, because one ends of having these large 'starting' files
inside potential future export of the current projects data.

There are better ways to deal with such things:
* One would be to store difference in changes for large files (not part of this proposal and also has drawbacks)
* For external sources one could look at features of [git-annex](https://git-annex.branchable.com/) for example,
which stores a soft link for large files and only downloads them when they are needed (which motivated this proposal).
But this can solve some of the issues with `large` files if they come from external sources. 

## Proposed Enhancement

One could implement a new datatype (similar to git-annex features), which only stores the PID (persistent links) of the data source in the database
with some additional metadata (which might be available on the website it self), so that no large files are stored in the database and repository. So it represents persistent data somewhere else,
which can be used within the AiiDA system without it becoming part of the database or repository, while keeping the provenance.
This datatype should have some functionally to automatically download the (remote, web) data if it is needed (within a calcfunction) and cache the data
locally (outside the repository and database) for use, so that it is downloaded only once, and does not become part of any AiiDA exports.
This functionality is needed, to be make code using this data object runnable and reproducible.

Maybe add an option to also add this data to the repository, if wanted.

### Proposals
The PIDData would be very basic and provide the data 'as is' to you. If there are some more common use cases for certain data one might subclass the PIDData and add special functions which can deal better with the special given data, or how it is accessed. So far I could not think here of such a common important use case and in a first implementation I would not go for such things, but it is something which might be kept in mind (like something specialized for data with PIDs, certain metadata standards, persistent URLs or AiiDA exports). 

### Example use cases:

### 1. (Main use case) small subset of data needed from (large) persistent external Data:

Starting from a (single) persistent huge file (especially non AiiDA data) on the web, one is interested in only a few data points to do further work. Currently, one would store this as a `SinglefileData`, write a `CalcFunction` to extract that data and continue from there. Where one got the `SingleFileData` from one could store in the extras. The `SingleFileData` would be in any export unless one excludes it explicitly manually. If one does not want to store the `SingleFileData`, one would not run a `CalcFunction` and create the extracted node without provenance connection in the database (or with more work a dummy connection) and some information in the extras how they came to be. This is not fully automatized and user depended.

The new format would replace this `SinglefileData` as a soft link in the database and repo (the `PIDData` node), i.e the first time one executes the `CalcFunction` to extract the data, it will be downloaded and the extracted data points within a `CalcFunction` will have clear provenance (because the `PIDData` is input) in the data base how they came to be without doing something 'manual' in addition. So this is fully automated and nothing generic to a users AiiDA usage style.

If one uses the same `PIDData` node again in some other `CalcFunction` it should use the local instance and not download the linked data again. If one gives this script to somebody else, he can run the same thing and reproduce the work. If one provides an AiiDA export, it contains just the new work, plus the PIDData node. People using this export could reuse the `PIDData` node (it would do the download again on their machine).

### 2. Use case, reusing data from other AiiDA databases: 
One wants to run a simple post processing data evaluation on some large data(bases) through AiiDA and record the provenance. Lets say this is one or several AiiDA databases. Currently, one would have to import these AiiDA databases into the work database, or load them into a temporary database export the nodes one needs (with or without the full provenance), and import them into the work database. If one would like the provenance and needs all `last results` child nodes one has the full external database in the end in the work database. After this import one would write a `CalcFunction` taking all needed child nodes to create the inputs for the (post) process steps one likes to do. Here the provenance is really nicely kept, but again if one publishes this data, where does one cut the provenance graph? If one cuts it, one would again have to manual provide some extra information on where these `starting` nodes came from and how (i.e the link to the DOI would not be per default in the database, maybe with verdi import url it is?). Therefore, one can only manual keep the provenance and for a machine agent this probably breaks.

This use case is more tricky and I am not sure so what best to do here yet (since I think it is not so nice yet).
Anyways, with the `PIDdata`, one could do the `import export, (delete)` of the aiida databases inside a `CalcuFunction` (with only the PIDData types as input) and return the result nodes. Now one can safely remove this imported database without loosing provenance, or one could export now only the small AiiDA graph with the `PIDData`, `CalcFunction` and results nodes to import it into the work database.

An other way could also be to extract the needed information from the export files by some other means inside a `CalcFunction`, without doing an import (because the databases are to large maybe).

The same thing could be done also now already (without the PIDData), by writing a `CalcFunction` which takes strings nodes with the PIDs as inputs, does the whole thing and outputs the needed data nodes. But here it would not be clear that the `string nodes` represent external data sources. A concrete example would be here to run (optimade) queries on several AiiDA data bases on the web (which have persistent identifiers) without downloading the databases themselves. So at least for data within AiiDA databases exposed through the web there can be other good solutions for this problem on the server/API side and maybe then it is not an `issue` that it is not clear that the base input nodes do not represent soft links to external data.

### 3. use case, Data with certain access rights:
Depending on the (external) Data access rights or license one does not want (or is allowed) that data to end up in the AiiDA repo or database in the first place. In this case the `PIDData` (download) would only work for people which machines have the rights to access the remote persistent data, but there would still be some provenance about it in the Database, without manually cutting AiiDA graphs prior publication). This may not be true, because extraction information will be in the `CalcFunction`, which might contain more information than allowed. On the other hand one can always 'mask' code in the provenance through imports from somewhere.

The `PIDData` is also probably not a general solution for all of these types of problems, because from the CIF file case for example we know that this issue can be more complicated and also require the removal of some `JobCalculation` because some `restricted` data is in raw input files, i.e require large provenance graph cuts.
(Generating all this 'to cut' provenance, i.e the data, run calcs, remove calcs from provenance inside a single CalcFunction with `PIDData` as input and `save` data as output is probably over stretched). A `general` way to `collapse` part of the provenance graph without loosing the information how it was generated may be a better idea for such problems.

## Pros and Cons

For implementing an additional datatype.

### Pros

* Reduce repository size (possible significantly)
* Enable easy provenance keeping of external data persistent sources of all kinds (like some data on materials cloud or elsewhere)
* Provides a clear way, standard within AiiDA on how to keep the provenance to external persistent data.


### Cons

* The same could be used for non persistent links, which would not be good for long term provenance
* It could even be miss used to do such things with local files (so no persistence at all). One might be able to implement some checks here, or allow only `real` pids.

