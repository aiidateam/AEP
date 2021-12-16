# AEP 006: Efficient object store for the AiiDA repository

| AEP number | 006                                                          |
|------------|--------------------------------------------------------------|
| Title      | Efficient object store for the AiiDA repository              |
| Authors    | [Giovanni Pizzi](mailto:giovanni.pizzi@epfl.ch) (giovannipizzi)|
| Champions  | [Giovanni Pizzi](mailto:giovanni.pizzi@epfl.ch) (giovannipizzi), [Francisco Ramirez](mailto:francisco.ramirez@epfl.ch) (ramirezfranciscof), [Sebastiaan P. Huber](mailto:sebastiaan.huber@epfl.ch) (sphuber) [Chris J. Sewell](mailto:christopher.sewell@epfl.ch) (chrisjsewell)  |
| Type       | S - Standard Track AEP                                       |
| Created    | 17-Apr-2020                                                  |
| Status     | implemented                                                  |

## Background 
AiiDA 0.x and 1.x write the "content" of each node in two places: attributes in the database, and files (that do not need fast query) in a file repository on the local file system.
These files include for instance raw inputs and outputs of a job calculation, but also other binary or textual information best stored directly as a file (some notable examples: pseudopotential files, numpy arrays, crystal structures in CIF format).

In AiiDA 0.x and 1.x, each of these files is directly stored in a folder structure, where each node "owns" a folder whose name is based on the node UUID with two levels of sharding; if the node UUID is `4af3dd55-a1fd-44ec-b874-b00e19ec5adf`, the folder will be `4a/f3/dd55-a1fd-44ec-b874-b00e19ec5adf`.
Files of a node are stored within the node repository folder, possibly within a folder structure.

While quite efficient when retrieving a single file (keeping too many files or subfolders in the same folder is inefficient), the current implementation suffers of a number of problems when a large number of files are stored.

In particular:
- there is no way to compress files unless the AiiDA plugin does it;
- if a code generates hundreds of files, each of them is stored as an individual file;
- there are many empty folders that are generated for each node, even when no file needs to be stored.

We emphasize that having many inodes (files or folders) is a big problem.
In particular:
- a common filesystem (e.g. EXT4) has a maximum number of inodes that can be stored, and we already have experience of AiiDA repositories that hit this limit.
  The disk can be reformatted to increase this limit, but this is clearly not an option that can be easily suggested to users.
- When performing "bulk" operations on many files (two common cases are when exporting a portion of the DB, or when performing a backup), accessing hundreds of thousands of files is extremely slow.
  Disk caches (in Linux, for instance) make this process much faster, but this works only as long as the system has a lot of RAM, and the files have been accessed recently.
  Note that this is not an issue of AiiDA.
  Even just running `rsync` on a folder with hundreds of thousands of files (not recently accessed) can take minutes or even hours just to check if the files need to be updated, while if the same content is in a single big file, the operation would take much less (possibly even less than a second for a lot of small files).
  As a note, this is the reason why at the moment we provide a backup script to perform incremental backups of the repository (checking the timestamp in the AiiDA database and only transferring node repository folders of new nodes), but the goal would be to rely instead on standard tools like `rsync`.


## Proposed Enhancement 
The goal of this proposal is to have a very efficient implementation of an "object store" (or, more correctly, a key-value store) that:
- works directly on a folder on the local file system (could optionally be a remote file system that is mounted locally);
- ideally, does not require a service to be running in the background, to avoid to have to ask users to run yet another service to use AiiDA;
- and addresses a number of performance issues mentioned above and discussed more in detail below.

**NOTE**:  This AEP does not address the actual implementation of the object store within AiiDA, but rather the implementation of an object-store-like service as an independent package, to solve a number of performance issues.
This is now implemented as part of the [disk-objecstore](https://github.com/aiidateam/disk-objectstore) package that will be used by AiiDA from version 2.0.

The integration with AiiDA will be described in AEP 007.

## Detailed Explanation 

**NOTE**: This document discusses the reasoning behind the implementation of the `disk-objectstore`.
The implementation details reflect what is in the libary as of version 0.6.0 (as of late 2021).
It should *not* be considered as a documentation of the `disk-objectstore` package (as the implementation choices might be adapted in the future), but rather as a reference of the reason for the introduction of the package, of the design decisions, and of why they were made.

The goal of this AEP is to define some design decisions for a library (an "object store", to be used internally by AiiDA) that, given a stream of bytes, stores it as efficiently as possible somewhere, assigns a unique key (a "name") to it, and then allows it to be retrieved using that key.

The library also supports efficient bulk write and read operations to cover the cases of bulk operations in AiiDA (exporting, importing and backups).

Here we describe some design criteria for such an object store.
We also provide an implementation that follows these criteria in the [disk-objectstore](https://github.com/giovannipizzi/disk-objectstore) repository, where efficiency has also been benchmarked.

### Performance guidelines and requirements

#### Packing and loose objects
The core idea behind the object store implementation is that, instead of writing a lot of small files, these are packed into a few big files, and an index of some sort keeps track of where each object is in the big file.
This is for instance what also git does internally.

However, one cannot write directly into a pack file: this would be inefficient and also not robust, especially because of a key requirement: multiple Unix processes (interactive shells, daemon workers, jupyter notebooks, etc.) must be able to write efficiently and *concurrently* without data corruption.
Therefore, as also `git` does, we introduce the concept of "loose" objects (where each object is stored as a different file) and of "packed" objects, objects that are concatenated to a small number of pack files.

The key concept is that we want maximum performance when writing a new object.
Therefore, each new object is written, by default, as a loose object. 
Periodically, a packing operation can be executed (in a first version this will be triggered manually by the users and properly documented; in the future, we might think to automatic triggering this based on performance heuristics), moving loose objects into packs.

Accessing an object should only require that the user of the library provides its key, and the concept of packing should be hidden to the user (at least when retrieving, while it can be exposed for maintenance operations like repacking).

#### Efficiency decisions
Here follows a discussion of some of the decisions that were made in the implementation.
These are based on a compromise between the different requirements, and represent what can be found in the current implementation in the [disk-objectstore](https://github.com/giovannipizzi/disk-objectstore) package.

- As discussed above, objects are written by default as loose objects, with one file per object.
  They are also stored uncompressed.
  This gives maximum performance when writing a file (e.g. while storing a new node).
  Moreover, it ensures that many writers can write at the same time without data corruption.

- Loose objects are stored with a one-level sharding format: `4a/f3dd55a1fd44ecb874b00e19ec5adf`.
  Current experience (with AiiDA) shows that it is actually not so good to use two levels of nesting, which was employed to avoid having too many files in the same folder.
  And anyway the core idea of this implementationis that when there are too many loose objects, the user will pack them.
  The number of characters in the first part can be chosen in the library, but a good compromise after testing is 2 (the default, and also the value used internally by git).

- Loose objects are actually written first to a sandbox folder (in the same filesystem), and then moved in place with the correct UUID only when the file is closed, with an atomic operation.
  This should prevent having leftover objects if the process dies.
  In this way, we can rely simply on the fact that an object present in the folder of loose objects signifies that the object exists, without needing a centralised place to keep track of them.
  
  Having the latter would be a potential performance bottleneck, as if there are many concurrent writers, the object store must guarantee that the central place is kept updated (and e.g. using a SQLite database for this - as it's used for the packs - is not a good solution because only one writer at a time can act on a SQLite database, and all others have to wait and risk to timeout).

- Packing can be triggered by the user periodically, whenever they want.
  Here, and in the following, packing means bundling loose objects in a few "pack" files, optionally compressing the objects.
  A key requirement is that it should be possible to pack while the object store is in use, without the need to stop its use (which would in turn require to stop the use of AiiDA and the deamons during these operations).
  This is possible in the current implementation, but might temporarily impact read performance while repacking (which is probably acceptable).
  Instead, it is *not* required that packing can be performed in parallel by multiple processes (on the contrary, the current implementation actually tries to prevent multiple processes trying to perform write operations on packs at the same time: i.e., only a single packer process should perform the operation at any given time).

- In practice, this packing operation takes all loose objects and puts them in a controllable number of packs.
  The name of the packs is given by an integer.
  A new pack is created when all previous ones are "full", where full is defined when the pack size goes beyond a threshold (by default 4GB/pack).
  This size is a good compromise: it's similar to a "movie" file, so not too big to deal with (can fit e.g. in a disk, people are used to deal with files of a few GBs) so it's not too big.
  At the same time it is big enough so that even for TB-large repositories, the number of packs is of the order of a few tens, and therefore this solves the issue of having millions of files.

- Pack files are just a concatenation of bytes of the packed objects.
  Any new object is appended to the pack, making use of the efficiency of opening a file for appending.
  The information for the offset and length of each pack is kept in a single SQLite database for the whole set of objects, as we describe below.

- Packed objects can optionally be compressed.
  Note that compression is on a per-object level.
  The information on whether an object is compressed or not is stored in the index.
  When the users ask for an object, they always get back the uncompressed version (so they don't have to worry if objects are compressed or not when retrieving them).
  This allows much greater flexibility, and avoids, e.g., having to make the decision to avoid recompressing files that are already compressed or where compression would give little to no benefit.
  In the future, one could also think of clever logic or heuristics to try to compress a file, but then store it uncompressed if it turns out that the compression ratio is not worth the time needed to further uncompress it later.
  At the moment, one compression will be chosen and used by default (currently zlib, but in issues it has been suggested to use more modern formats like `xz`, or even better [snappy](https://github.com/google/snappy) that is very fast and designed for purposes like this).
  The compression library is already an option, and which one to use is stored in the JSON file that contains the settings of the object-store container.

- A note on compression: the user can always compress objects first, and then store a compressed version of them and take care of remembering if an object was stored compressed or not.
  However, the implementation of compression directly in the object store, as described in the previous point, has the two advantages that compression is done only while packing, so there is no performance hit while just storing a new object, and that is completely transparent to the user (while packing, the user can decide to compress data or not; then, when retrieving an object from of the object store, there will not be any difference - except possibly speed in retrieving the data - because the API to retrieve the objects will be the same, irrespective of whether the object has been stored as compressed or not; and data is always returned uncompressed).

- API exists both to get and write a single object but also, *importantly*, to write directly to pack files (this cannot be done by multiple processes at the same time, though), and to read in bulk a given number of objects.
  This is particularly convenient when using the object store for bulk import and export, and it is very efficient.
  Also, it could be useful when getting all files of one or more nodes.
  Actually, for export files, one could internally use the same object-store implementation to store files in the export file.

  During normal operation, however, as discussed above, we expect the library user to write loose objects, to be repacked periodically (e.g. once a week, or when needed).

  Some reference results for bulk operations in the current implementation: Storing 100'000 small objects directly to the packs takes about 10s.
  The time to retrieve all of them is \~2.2s when using a single bulk call, compared to \~44.5s when using 100'000 independent calls (still probably acceptable).
  Moreover, even getting, in 10 bulk calls, 10 random chunks of the objects (eventually covering the whole set of 100'000 objects) only takes \~3.4s.
  This should demonstrate that exporting a subset of the graph should be efficient.
  Also, this should be compared to the minutes up to hours it will take to store all objects as individual files.

- All operations internally (storing to a loose object, storing to a pack, reading from a loose object or from a pack, compression) should happen via streaming (at least internally, and there should be a public facing API for this).
  So, even when dealing with huge files, these never fill the RAM (e.g. when reading or writing a multi-GB file, the memory usage has been tested to be capped at \~150MB).
  Convenience methods are available, anyway, to directly get the entire content of an object, if the user wants this for simplicity, and knows that the content fits in RAM.

#### Further design choices

- The key of an object will be its hash.
  For each container, one can decide which hash algorithm to use; the default one is `sha256`, which offers a good compromise between speed and avoiding risk of collisions.
  Once an object is stored, it's the responsibility of the `disk-objectstore` library to return the hash of the object that was just stored.

- Using a hash means that we automatically get deduplication of content: if an object is asked to be written, once the stream is received, if the library detects that the object is already present, it will still return the hash key but not store it twice.
  So, from the point of view of the end application (AiiDA), it does not need to know that deduplication is performed: it just has to send a sequence of bytes, and store the corresponding hash key returned by the library.

- The hashing library can be decided for each container and is configurable; however, for performance reasons, in AiiDA it will be better to decide and stick to only one algorithm.
  This will allow to compare e.g. two different repositories (e.g. when sharing data and/or syncing) and establish if data already exists by just comparing the hashes.
  If different hash algorithms are instead used by the two containers, one needs to do a full data transfer of the whole container, to discover if new data needs to be transfered or not.

- Pack naming and strategy is not determined by the user.
  Anyway it would be difficult to provide easy options to the user to customize the behavior, while implementing a packing strategy that is efficient.
  Which object is in which pack is tracked in the SQLite database.
  Possible future changes of the internal packing format should not affect the users of the library, since users only ask to get an object by hash key, and in general they do not need to know if they are getting a loose object, a packed object, from which pack, etc.

- For each object, the SQLite database contains the following fields, that can be considered to be the "metadata" of the packed object: its `hashkey`, the `offset` (starting position of the bytestream in the pack file), the `length` (number of bytes to read), a boolean `compressed` flag, meaning if the bytestream has been zlib-compressed, and the `size` of the actual data (which is equal to `length` if `compressed` is false, or the size of the uncompressed stream otherwise).
The latter is useful for statistics for instance, or to inform the reader beforehand of how much data will be returned, before it starts reading, so the reader can decide to store the whole object in RAM or to process it in a streaming way.
  In addition, it tracks the number of the pack in which the object is stored.

- We decided to use SQLite because of the following reasons:
  - it's a database, so it's efficient in searching for the metadata of a given object;
  - it does not require a running server;
  - in [WAL mode](https://www.sqlite.org/wal.html), allows many concurrent readers and one writer, useful to allow to continue normal operations by many Unix processes during repacking;
  - we access it via the SQLAlchemy library that anyway is already a dependency of AiiDA, and is actually the only dependency of the current object-store implementation;
  - it's quite widespread and so the libary to read and write should be reliable;
  - SQLite has a clear [long-term support planning](https://www.sqlite.org/lts.html).

- Deletion can be performed efficiently by simply deleting the loose object, or removing the entry from the index file if the object is already packed.
  Later repacking of the packs can be used to recover the disk space still occupied in the pack files.
  It is hard to find a better strategy that does not require manual repacking but gives all other guarantees especially for fast live operations (as a reference, also essentially all databases do the same and have a "vacuum" operation that is in a sense equivalent to the concept of repacking here).

- The object store does not need to provide functionality to modify an object.
  In AiiDA, files of nodes are typically only added, and once added they are immutable (and very rarely they can be deleted).
  
  If modification is needed, this can be achieved by creation of a new object and deletion of the old one, but this is expected to be a extremely rarely needed operation.

- The current packing format is `rsync`-friendly, which is one of the original requirements.
  `rsync` has a clever rolling algorithm that divides each file in blocks and detects if the same block is already in the destination file, even at a different position.
  Therefore, if content is appended to a pack file, or even if a pack is "repacked" (e.g. reordering objects inside it, or removing deleted objects) this does not prevent efficient rsync transfer (this has been tested in the implementation).

- Since the `disk-objectstore` works on a normal file system, it is possible to use also other tools, e.g. [`rclone`](https://rclone.org), to move the data to some different backend (a "real" object store, Google Drive, or anything else).

- Appending content to a single file does not prevent the Linux disk cache to work efficiently.
  Indeed, the caches are per blocks/pages in linux, not per file.
  Concatenating to files does not impact performance of cache efficiency.
  What is costly is opening a file, as the filesystem has to provide some guarantees e.g. on concurrent access.
  As a note, seeking a file to a given position is what one typically does when watching a video and jumping to a different section, which is an efficient operation.

- Packing in general, at this stage, is left to the user.
  We can decide (at the object-store level, or probably better at the AiiDA level) to suggest the user to repack, or to trigger the repacking automatically.
  This can be a feature introduced at a second time.
  For instance, the first version we roll out could just suggest to repack periodically in the docs.
  This could be a good approach, also to bind the repacking with the backups (at the moment, probably backups need to be executed using appropriate scripts to backup the DB index and the repository in the "right order", and possibly using SQLite functions to get a dump).

- As a note: even if repacking is never done by the user, the situation is anyway improved with respect to the current one in AiiDA:
  - an index of files associated with an AiiDA node will now be stored in the AiiDA DB, so getting the list of files associated to a node without content will no longer need access to the disk;
  
  - empty folders created for nodes without files will no longer be created;

  - automatic deduplication of the data is now done transparently.
  
  In a second phase, we can print suggestions, e.g. when restarting the daemon, that suggests to repack, for instance if the number of loose objects is too large.
  We will also provide `verdi` commands to facilitate the user in these maintenance operations.

  Finally, in the future if we are confident that this approach works fine, we can also automate the repacking.
  We need to be careful that two different processes don't start packing at the same time, and that the user is aware that packing will be triggered, that it might take some time, and that the packing process should not be killed (this might be inconvenient, and this is why I would think twice before implementing an automatic repacking).

### Why a custom implementation of the library
We have been investigating if existing codes could be used for the current purpose.
However, in our preliminary analysis we couldn't find an existing robust software that was satisfying all criteria.
In particular:

- existing object storage implementations (e.g. Open Stack Swift, or others that typically provide a S3 or similar API) are not suitable since 1) they require a server running, and we would like to avoid the complexity of asking users to run yet another server, and most importantly 2) they usually work via a REST API that is extremely inefficient when retrieving a lot of small objects (latencies can be even of tens of ms, which is clearly unacceptable if we want to retrieve millions of objects).

- the closest tool we could find is the git object store, for which there exists also a pure Python implementation ([dulwich](https://github.com/dulwich/dulwich)).
  We have been benchmarking it, but the feeling is that it is designed to do something else, and adapting to our needs might not be worth it.
  Some examples of issues we envision: managing re-packing (dulwich can only pack loose objects, but not repack existing packs); this can be done via git itself, but then we need to ensure that when repacking, objects are not garbage-collected and deleted because they are not referenced within git.
  It's not possible (apparently) to decide if we want to compress an object or not (e.g., in case we want maximum performance at the cost of disk space), but they are always compressed.
  Also we did not test concurrency access and packing of the git repository, which requires some stress test to assess if it works.

- One possible solution could be a format like HDF5.
  However we need a very efficient hash-table like access (given a key, get the object), while HDF5 is probably designed to append data to the last dimension of a multidimensional array. Variables exist, but (untested) probably they cannot scale well at the scale of tens of millions.

- One option we didn't investigate is the mongodb object store.
  Note that this would require running a server though (but could be acceptable if for other reasons it becomes advantageous).

## Pros and Cons 

### Pros
* Is very efficient also with hundreds of thousands of objects (bulk reads can read all objects in a couple of seconds).
* Is rsync-friendly, so one can suggest to use directly rsync for backups instead of custom scripts.
* A library (`disk-objectstore`) has already been implemented, seems to be very efficient, and is relatively short (and already has tests with 100% coverage, including concurrent writes, reads, and one repacking process, and checking on three platforms: linux, mac os, and windows).
* It does not add any additional Python dependency to AiiDA, and it does not require a service running.
* Implements compression in a transparent way.
* It shouldn't be slower than the current AiiDA implementation in writing during normal operation, since objects are stored as loose objects.
  Actually, it might be faster for nodes without files, as no disk access will be needed anymore, and automatically provides deduplication of files.

### Cons
* Extreme care is needed to convince ourselves that there are no bugs and no risk of corrupting or losing the users' data.
  This is clearly non trivial and requires a lot of work.
  Note, however, that if packing is not performed, the performance will be the same as the one currently of AiiDA, that stores essentially only loose objects.
  Risks of data corruption need to be carefully assessed mostly while packing.
* Object metadata must be tracked by the caller in some other database (e.g. AiiDA will have, for each node, a list of filenames and the corresponding hash key in the disk-objectstore).
* It is not possible anymore to access directly the folder of a node by opening a bash shell and using `cd` to go the folder, e.g. to quickly check the content.
  However, we have `verdi node repo dump` so direct access should not be needed anymore, and actually this might be good to prevent that people corrupt by mistake the repository.
