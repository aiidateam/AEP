# Efficient object store for the AiiDA repository

| AEP number | 003                                                          |
|------------|--------------------------------------------------------------|
| Title      | Efficient object store for the AiiDA repository              |
| Authors    | [Giovanni Pizzi](mailto:giovanni.pizzi@epfl.ch) (giovannipizzi)|
| Champions  | [Giovanni Pizzi](mailto:giovanni.pizzi@epfl.ch) (giovannipizzi), [Francisco Ramirez](mailto:francisco.ramirez@epfl.ch) (ramirezfranciscof), [Sebastiaan P. Huber](mailto:sebastiaan.huber@epfl.ch) (sphuber)  |
| Type       | S - Standard Track AEP                                       |
| Created    | 17-Apr-2020                                                  |
| Status     | submitted                                                    |

## Background 
AiiDA writes the "content" of each node in two places: attributes in the database, and files
(that do not need fast query) in a disk repository.
These files include for instance raw inputs and outputs of a job calculation, but also other binary or
textual information best stored directly as a file (some notable examples: pseudopotential files,
numpy arrays, crystal structures in CIF format).

Currently, each of these files is directly stored in a folder structure, where each node "owns" a folder whose name
is based on the node UUID with two levels of sharding
(that is, if the node UUID is `4af3dd55-a1fd-44ec-b874-b00e19ec5adf`,
the folder will be `4a/f3/dd55-a1fd-44ec-b874-b00e19ec5adf`).
Files of a node are stored within the node repository folder,
possibly within a folder structure.

While quite efficient when retrieving a single file
(keeping too many files or subfolders in the same folder is 
inefficient), the current implementation suffers of a number of problems
when starting to have hundreds of thousands of nodes or more
(we already have databases with about ten million files).

In particular:
- there is no way to compress files unless the AiiDA plugin does it;
- if a code generates hundreds of files, each of them is stored as an individual file;
- there are many empty folders that are generated for each node, even when no file needs to be stored.

We emphasize that having many inodes (files or folders) is a big problem. In particular:
- a common filesystem (e.g. EXT4) has a maximum number of inodes that can be stored, and we already have
  experience of AiiDA repositories that hit this limit. The disk can be reformatted to increase this limit,
  but this is clearly not an option that can be easily suggested to users.
- When performing "bulk" operations on many files (two common cases are when exporting a portion of the DB,
  or when performing a backup), accessing hundreds of thousands of files is extremely slow. Disk caches
  (in Linux, for instance) make this process much faster, but this works only as long as the system has a lot
  of RAM, and the files have been accessed recently. Note that this is not an issue of AiiDA. Even just running
  `rsync` on a folder with hundreds of thousands of files (not recently accessed) can take minutes or even hours
  just to check if the files need to be updated, while if the same content is in a single big file, the operation
  would take much less (possibly even less than a second for a lot of small files). As a note, this is the reason
  why at the moment we provide a backup script to perform incremental backups of the repository (checking the
  timestamp in the AiiDA database and only transferring node repository folders of new nodes), but the goal would be to rely instead on standard tools like `rsync`.


## Proposed Enhancement 
The goal of this project is to have a very efficient implementation of an "object store" that:
- works directly on a disk folder;
- ideally, does not require a service to be running in the background,
  to avoid to have to ask users to run yet another service to use AiiDA;
- and addresses a number of performance issues mentioned above and discussed more in detail below.

**NOTE**:  This AEP does not address the actual implementation of the object store in AiiDA, but
rather the implementation of an object store to solve a number of performance issues.
The description of the integration with AiiDA will be discussed in a different AEP
(see [PR #7](https://github.com/aiidateam/AEP/pull/7) for some preliminary discussion, written before this AEP).

## Detailed Explanation 
The goal of this AEP is to define some design decisions for a library (an "object store", to be used internally by AiiDA) that,
given a stream of bytes, stores it as efficiently as possible somewhere, assigns a unique key (a "name") to it,
and then allows to retrieve it with that key.

The libary also supports efficient bulk write and read operations
to cover the cases of bulk operations in AiiDA (exporting, importing,
backups).

Here we describe some design criteria for such an object store.
We also provide an implementation that follows these criteria in the
[disk-objectstore](https://github.com/giovannipizzi/disk-objectstore)
repository, where efficiency has also been benchmarked.

### Performance guidelines and requirements

#### Packing and loose objects
The core idea behind the object store implementation is that, instead of writing a lot of small files, these
are packed into a few big files, and an index of some sort keeps track of where each object is in the big file.
This is for instance what also git does internally.

However, one cannot write directly into a pack file: this would be inefficient, especially because of a key requirement:
multiple Unix processes must be able to write efficiently and *concurrently*, i.e. at the same time, without data
corruption (for instance, the AiiDA daemon is composed of multiple
concurrent workers accessing the repository). 
Therefore, as also `git` does, we introduce the concept of `loose` objects (where each object is stored as a different
file) and of `packed` objects when these are written as part of a bigger pack file.

The key concept is that we want maximum performance when writing a new object.
Therefore, each new object is written, by default, in loose format. 
Periodically, a packing operation can be executed, taking loose objects and moving them into packs.

Accessing an object should only require that the user of the library provides its key, and the concept of packing should
be hidden to the user (at least when retrieving, while it can be exposed for maintenance operations like repacking).

#### Efficiency decisions
Here are some possible decisions. These are based on a compromise between
the different requirements, and represent what can be found in the current implementation in the
[disk-objectstore](https://github.com/giovannipizzi/disk-objectstore) package.

- As discussed above, objects are written by default as loose objects, with one file per object. 
  They are also stored uncompressed. This gives maximum performance when writing a file (e.g. while storing 
  a new node). Moreover, it ensures that many writers can write at the same time without data corruption.

- Loose objects are stored with a one-level sharding format: `4a/f3dd55a1fd44ecb874b00e19ec5adf`.
  Current experience (with AiiDA) shows that it is actually not so good to use two
  levels of nesting, that was employed to avoid to have too many files in the same folder. And anyway the core idea of this implementationis that when there are too many loose objects, the user will pack them.
  The number of characters in the first part can be chosen in the library, but a good compromise 
  after testing is 2 (the default, and also the value used internally by git).

- Loose objects are actually written first to a sandbox folder (in the same filesystem),
  and then moved in place with the correct UUID only when the file is closed, with an atomic operation.
  This should prevent having leftover objects if the process dies.
  In this way, we can rely simply on the fact that an object present in the folder of loose objects signifies that the object exists, without needing a centralised place to keep track of them.
  
  Having the latter would be a potential performance bottleneck, as if there are many concurrent
  writers, the object store must guarantee that the central place is kept updated.

- Packing can be triggered by the user periodically, whenever the user wants.
  It should be ideally possible to pack while the object store
  is in use, without the need to stop its use (which would in turn 
  require to stop the use of AiiDA and the deamons during these operations).
  This is possible in the current implementation, but might temporarily impact read performance while repacking (which is probably acceptable).
  Instead, it is *not* required that packing can be performed in parallel by multiple processes
  (on the contrary, the current implementation actually tries to prevent multiple processes trying to perform
  write operations on packs concurrently).

- In practice, this operation takes all loose objects and puts them in a controllable number
  of packs. The name of the packs is given by the first few letters of the UUID
  (by default: 2, so 256 packs in total; configurable). A value of 2 is a good balance
  between the size of each pack (on average, ~4GB/pack for a 1TB repository) and
  the number of packs (having many packs means that, even when performing bulk access,
  many different files need to be open, which slows down performance).

- Pack files are just concatenation of bytes of the packed objects. Any new object
  is appended to the pack (thanks to the efficiency of opening a file for appending).
  The information for the offset and length of each pack is kept in a single SQLite
  database for the whole set of objects, as we describe below.

- Packed objects can optionally be compressed. Note that compression is on a per-object level.
  This allows much greater flexibility, and avoid e.g. to recompress files that are already compressed.
  One could also think to clever logic ot heuristics to try to compress a file, but then store it
  uncompressed if it turns out that the compression ratio is not worth the time
  needed to further uncompress it later.

- API exists both to get and write a single object but also, *importantly*, to write directly
  to pack files (this cannot be done by multiple processes at the same time, though),
  and to read in bulk a given number of objects.
  This is particularly convenient when using the object store for bulk import and
  export, and very fast. Also, it could be useful when getting all files of one or more nodes. Actually, for export files, one could internally 
  use the same object-store implementation to store files in the export file.

  During normal operation, however, as discussed above, we expect the library user to write loose objects,
  to be repacked periodically (e.g. once a week, or when needed).

  Some reference results for bulk operations in the current implementation:
  Storing 100'000 small objects directly to the packs takes about 10s.
  The time to retrieve all of them is ~2.2s when using a single bulk call,
  compared to ~44.5s when using 100'000 independent calls (still probably acceptable).
  Moreover, even getting, in 10 bulk calls, 10 random chunks of the objects (eventually
  covering the whole set of 100'000 objects) only takes ~3.4s. This should demonstrate
  that exporting a subset of the graph should be efficient (and the object store format
  could be used also inside the export file). Also, this should be compared to minutes to hours
  when storing each object as individual files.

- All operations internally (storing to a loose object, storing to a pack, reading
  from a loose object or from a pack, compression) should happen via streaming
  (at least internally, and there should be a public facing API for this).
  So, even when dealing with huge files, these never fill the RAM (e.g. when reading
  or writing a multi-GB file, the memory usage has been tested to be capped at ~150MB).
  Convenience methods are available, anyway, to get directly an object content, if
  the user wants this for simplicty, and knows that the content fits in RAM.

#### Further design choices

- Each given object will get a random UUID as a key (its generation cost is negligible, about
  4 microseconds per UUID).
  It's up to the caller to track this into a filename or a folder structure.
  The UUID is generated by the implementation and cannot be passed from the outside.
  This guarantees random distribution of objects in packs, and avoids to have to
  check for objects already existing (that can be very expensive).

- Pack naming and strategy is not determined by the user. Anyway it would be difficult
  to provide easy options to the user to customize the behavior, while implementing
  a packing strategy that is efficient. Moreover, with the current packing strategy,
  it is immediate to know in which pack to check without having to keep also an index
  of the packs (this, however, would be possible to implement in case we want to extend the behavior,
  since anyway we have an index file). But at the moment it does not seem necessary.

- For each object, the SQLite database contains the following fields, that can be considered
  to be the "metadata" of the packed object: its key (`uuid`), the `offset` (starting
  position of the bytestream in the pack file), the `length` (number of bytes to read),
  a boolean `compressed` flag, meaning if the bytestream has been zlib-compressed,
  and the `size` of the actual data (equal to `length` if `compressed` is false,
  otherwise the size of the uncompressed stream, useful for statistics for instance, or
  to inform the reader beforehand of how much data will be returned, before it starts
  reading, so the reader can decide to store in RAM the whole object or to process it
  in a streaming way).

- A single index file is used. Having one pack index per file, while reducing a bit
  the size of the index (one could skip storing the first part of the UUID, determined
  by the pack naming) turns out not to be very effective. Either one would keep all
  indexes open (but then one quickly hits the maximum number of open files, that e.g.
  on Mac OS is of the order of ~256), or open the index, at every request, that risks to
  be quite inefficient (not only to open, but also to load the DB, perform the query,
  return the results, and close again the file). Also for bulk requests, anyway, this
  would prevent making very few DB requests (unless you keep all files open, that
  again is not feasible).

- We decided to use SQLite because of the following reasons:
  - it's a database, so it's efficient in searching for the metadata
    of a given object;
  - it does not require a running server;
  - in [WAL mode](https://www.sqlite.org/wal.html), allows many concurrent readers and one writer,
    useful to allow to continue normal operations by many Unix processes during repacking;
  - we access it via the SQLAlchemy library that anyway is already
    a dependency of AiiDA, and is actually the only dependency of the
    current object-store implementation.
  - it's quite widespread and so the libary to read and write should be reliable.

- Deletion can just occur efficiently as either a deletion of the loose object, or
  a removal from the index file (if the object is already packed). Later repacking of the packs can be used to recover
  the disk space still occupied in the pack files.

- The object store does not need to provide functionality to modify
  a node. In AiiDA files of nodes are typically only added, and once
  added they are immutable (and very rarely they can be deleted).
  
  If modification is needed, this can be achieved by creation of a new
  object and deletion of the old one, since this is an extremely
  rare operation (actually it should never happen).

- The current packing format is `rsync`-friendly (that is one of the original requirements). 
  `rsync` has a clever rolling algorithm that can divides each file in blocks and
  detects if the same block is already in the destination file, even at a different position. 
  Therefore, if content is appended to a pac file, or even if a pack is "repacked" (e.g. reordering
  objects inside it, or removing deleted objects) this does not prevent efficient
  rsync transfer (this has been tested in the implementation).

- Appending content to a single file does not prevent the Linux disk cache to work efficiently.
  Indeed, the caches are per blocks/pages in linux, not per file.
  Concatenating to files does not impact performance on cache efficiency. What is costly is opening a file as the filesystem
  has to provide some guarantees e.g. on concurrent access.
  As a note, seeking a file to a given position is what one typically does when watching a 
  video and jumping to a different section.

- Packing in general, at this stage, is left to the user. We can decide (at the object-store level, or probably
  better at the AiiDA level) to suggest the user to repack, or to trigger the repacking automatically.
  This can be a feature introduced at a second time. For instance, the first version we roll out could just suggest
  to repack periodically in the docs to repack.
  This could be a good approach, also to bind the repacking with the backing up (at the moment, 
  probably backups need to be executed using appropriate scripts to backup the DB index and the repository
  in the "right order", and possibly using SQLite functions to get a dump).
  As a note, even if repacking is never done, the situation is anyway as the current one in AiiDA, and actually
  a bit better because getting the list of files for a node without files wouldn't need anymore to access the disk,
  and similarly there wouldn't be anymore empty folders created for nodes without files.
  
  In a second phase, we can print suggestions, e.g. when restarting the daemon,
  that suggests to repack, for instance if the number of loose objects is too large. 
  We can also provide `verdi` commands for this.

  Finally, if we are confident that this approach works fine, we can also automate the repacking. We need to be careful
  that two different processes don't start packing at the same time, and that the user is aware that packing will be
  triggered, that it might take some time, and that the packing process should not be killed
  (this might be inconvenient, and this is why I would think twice before implementing an automatic repacking).

### Why a custom implementation of the library
We have been investigating if existing codes could be used for the current purpose.

However, in our preliminary analysis we couldn't find an existing robust software that was satisfying all criteria.
In particular:

- existing object storage implementations (e.g. Open Stack Swift, or others that typically provide a
  S3 or similar API) are not suitable since 1) they require a server running, and we would like to
  avoid the complexity of asking users to run yet another server, and most importantly 2) they usually work 
  via a REST API that is extremely inefficient when retrieving a lot of small objects (latencies can
  be even of tens of ms, that is clearly unacceptable if we want to retrieve millions of objects).

- the closest tool we could find is the git object store, for which there exists also a pure-python
  implementation ([dulwich](https://github.com/dulwich/dulwich)). We have been benchmarking it, but
  the feeling is that it is designed to do something else, and adapting to our needs might not be worth it.
  Some examples of issues we envision: managing re-packing (dulwich can only pack loose objects, but not repack existing packs); this can be done via git itself, but then we need to ensuring that when repacking, objects are not garbage-collected and deleted because they are not referenced within git;
  it's not possible (apparently) to decide if we want to compress an object or not (e.g., in case we want maximum performance at the cost of disk space), but they are always compressed.
  Also we did not test concurrency access and packing of the git repository, which requires some stress test to assess if it works.

- One possible solution could be a format like HDF5. However we need a very efficient hash-table like access
  (given a key, get the object), while HDF5 is probably designed to append data to the last dimension of 
  a multidimensional array. Variables exist, but (untested) probably they cannot scale well
  at the scale of tens of millions.

- One option we didn't investigate is the mongodb object store. Note that this would require running a server
  though (but could be acceptable if for other reasons it becomes advantageous).

Finally, as a note, we stress that an efficient implementation in about 1'000 lines of code has been
already implemented, so the complexity of writing an object store library is not huge (at the cost, however,
of having to stress test ourselves that the implementation is bug-free).

### UUIDs vs SHA hashes

One thing to discuss is whether to replace a random UUID with a strong hash of the content
(e.g. SHA1 as git does, or some stronger hash). 
The clear advantage is that one would get "for free" the possibility to deduplicate identical 
files. Moreover, computation of hashes even for large files is very fast (comparable to the generation of a UUID)
even for GB files.

However, this poses a few of potential problem: 

- if one wants to work in streaming mode, the hash could be computed only at the *end*, 
  after the whole stream is processed. While this is still ok for loose objects, this is a problem
  when writing directly to packs. One possible workaround could be to decide that objects are added
  to random packs, and store the pack as an additional column in the index file.

- Even worse, it is not possible to know if the object already exists before it has been completely received
  (and therefore written somewhere, because it might not fit in memory). Then one would need to perform a search
  if an object with the same hash exists, and possibly discard the file (that might actually have been already written to a pack).
  Finally, one needs to do this in a way that works also for concurrent writes, and does not fail if two processes
  write objects with the same SHA at the same time.

- One could *partially* address the problem, for bulk writes, by asking the user to provide the hash beforehand. However, 
  I think it is a not a good idea; instead, it is better keep stronger guarantees at the library level:
  otherwise one has to have logic to decide what to do if the hash provided by the user turns out to be wrong.

- Instead, the managing of hashing could be done at a higher level, by the AiiDA repository implementation: anyway 
  the repository needs to keep track of the filename and relative path of each file (within the node repository), 
  and the corresponding object-store UUIDs. The implementation could then also compute and store the hash in some
  efficient way, and then keep a table mapping SHA hashes to the UUIDs in the object store, and take care of the
  deduplication.
  This wouldn't add too much cost, and would keep a separation of concerns so that the object-store implementation can be simpler, 
  give higher guarantees, be more robust, and make it simpler to guarantee that data is not corrupted even for concurrent access.

## Pros and Cons 

### Pros
* Is very efficient also with hundreds of thousands of objects (bulk reads can read all objects in a couple of seconds).
* Is rsync-friendly, so one can suggest to use directly rsync for backups instead of custom scripts.
* An implementation exists, seems to be very efficient, and is
  relatively short (and already has tests with 100% coverage,
  including concurrent writes, reads, and one repacking process, and checking on three platforms: linux, mac os, and windows).
* It does not add any additional python depenency to AiiDA, and it
  does not require a service running.
* It can be used also for the internal format of AiiDA export files,
  and this should be very efficient, even to later retrieve just
  a subset of the files.
* Implements compression in a transparent way.
* It shouldn't be slower than the current AiiDA implementation in writing
  during normal operation, since objects are stored as loose objects.
  Actually, it might be faster for nodes without files, as no disk
  access will be needed anymore.

### Cons
* Extreme care is needed to convince ourselves that there are no
  bugs and no risk of corrupting or losing the users' data.
* Object metadata must be tracked by the caller in some other database.
  Similarly, deduplication via SHA hashes is not implemented and need to be
  implemented by the caller.
* It is not possible anymore to access directly the folder of a node by opening
  a bash shell and using `cd` to go the folder,
  e.g. to quickly check the content. 
  However, we have `verdi node repo dump`
  so direct access should not be needed anymore, and actually this
  might be good to prevent that people corrupt by 
  mistake the repository.
