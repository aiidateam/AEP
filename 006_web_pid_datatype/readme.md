# (Web) AiiDA PIDData type

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
of data which comes from the outside but is persistent.

For example: Large files will be duplicated on disk, for every minor change to them. 
If a file should be part of the provenance it has to be stored in the repository also.

If one starts from external data sources, if it is an AiiDA database one would have to import
it and export the part which one needs and continue from that. Not so nice if one needs only a
small part from a large database. There is also currently no AiiDA intrinsic way to keep the
provenance from other data on the internet which has persistent identifiers and links.
The current way would be to download that data and store it in the repository as a single file
data, or some other AiiDA datatype and then continue with calcfunctions. 
A lot of work, which every user does different and some not at all, this causes data nodes to appear out
of nowhere, with only 'goodwill' provenance information in the extras, and other annotations set by the user.
This is also not so practical for large files, because one ends of having these large 'starting' files
inside potential future export of the current projects data.

There are better ways to deal with such things:
* One would be to store difference in changes for large files (not part of this proposal and also has drawbacks)
* For external sources one could look at features of [git-annex](https://git-annex.branchable.com/) for example,
which stores a soft link for large files and only downloads them when they are needed. 

## Proposed Enhancement

One could implement a new datatype (similar to git-annex features), which only stores the PID (persistent links) of the data source in the database
with some additional metadata (which might be available on the website it self), so that no large files are stored in the database and repository. So it represents persistent data somewhere else,
which can be used within the AiiDA system without it becoming part of the database or repository, while keeping the provenance.
This datatype should have some functionally to automatically download the (remote, web) data if it is needed (within a calcfunction) and cache the data
locally (outside the repository and database) for use, so that is downloaded only once, and does not become part of any AiiDA exports.
This functionality is needed, to be make code using this data object runnable and reproducible.

Maybe add an option to also add this data to the repository, if wanted.

### Proposals
Maybe one could also think here about special subclasses, like specialized for data with PIDs and persistent URLs or AiiDA exports. 

## Pros and Cons

For implementing an additional datatype.

### Pros

* Reduce repository size (significantly)
* Enable easy provenance keeping of external data persistent sources of all kinds (like some data on materials cloud or elsewhere)
* Provides a clear way, standard within AiiDA on how to keep the provenance to external persistent data.


### Cons

* The same could be used for non persistent links, which would not be good for long term provenance
* It could even be miss used to do such things with local files (so no persistence at all). One might be able to think implement some checks here.

