# AEP 005: Improved export archive format

| AEP number | 005                                                              |
|------------|------------------------------------------------------------------|
| Title      | Improved export archive format                                   |
| Authors    | [Chris Sewell](mailto:christopher.sewell@epfl.ch) (chrisjsewell) |
| Champions  | [Giovanni Pizzi](mailto:giovanni.pizzi@epfl.ch) (giovannipizzi)  |
| Type       | S - Standard                                                     |
| Created    | 18-Sep-2020                                                      |
| Status     | implemented                                                      |

## Background

The current implementation of the export archive is a zipped folder containing:

```
export.aiida/
  metadata.json
  data.json
  nodes/
    xx/
      yy/
        zz.../
    ...
```

such that:

* `metadata.json` contains the aiida version, export version and other global data.
* `data.json` contains all requisite information from the SQL Database.
* `nodes` contains the "object store" files per node, organised by UUID: `xxyy-zz...`.

This format has two principal shortcomings:

1. The file repository is inefficiently stored.
   Each file is written as a single, uncompressed file, which requires a large number of [inode](https://en.wikipedia.org/wiki/Inode) metadata objects and leads large bottlenecks content indexing.
2. For the validity of `data.json` to be determined, the entire content has to be read into memory, which becomes a limiting factor for export size.

Particularly for large export archives (many millions of nodes), writing to (export) and reading from (import) `data.json` represents a significant bottle-neck in performance for these processes, both in respect to memory usage and process speed.

## Proposed Enhancement

The goal of this enhancement is to replace the current archive format with one that allows for reading and writing of large archives, without significant degradation in performance.

The proposal first outlines a set of agreed requirements for a new archive format, followed by proposals for a concrete implementation of the format, and accompanying export and import functions.

## Detailed Explanation

### User Requirements

The following is a list of the key user requirements that a new export format must address:

1. Process Speed: As an AiiDA user, I want to be able to import/export millions of nodes within hours.

2. Process Memory Usage: As an AiiDA user, I want to be able to import/export databases regardless of whether the size of the database is larger than the available memory.

3. Archive Size: As an AiiDA user, downloading an archive from an online repository, I expect the size of the archive (after decompression) to be of the same order as the size when imported in AiiDA (DB+repo).

4. Data Integrity: As an AiiDA user I do not want imports to lead to inconsistencies in my AiiDA database.

5. Data Longevity: As an AiiDA user, I expect to be able to inspect and reuse the data I export today for at least 10 years into the future (ideally longer).

6. Data Introspectability: As an AiiDA user, I expect to be able to obtain rough statistics about the archive, such as the total number of nodes, almost instantaneously.

### Design requirements

The following design requirements then derive from the above user requirements.

#### Import/Export Process

Naturally, the speed of export/import will be dependant on the the computational hardware under which the process is run.
An initial target though would be approximately one million nodes per hour on a standard workstation with four CPU cores.

The user may run these processes in one of two modes, which may affect the process performance:

* Default mode, can be run whilst the database is being used, i.e. there is one or more daemon running, and/or one or more verdi shells running or python scripts being executed via `verdi run`.
* Exclusive mode, requires that the database and file repository are not in use.

In exclusive mode it would be possible to import directly to the new object-store pack files (that has a significant performance boost when importing data involving hundreds of thousands of files in the AiiDA repository or more), whereas in default mode the objects would be required to be imported as loose objects (which is always safe to do even during concurrent access to the repository).

It would also be highly desirable to be able to introspect an archive before import, to feedback an estimate of the process time to the user and provide dynamic progress reporting (e.g. a progress bar).
This process reporting should aim to be accurate to within a factor of approximately 2-3.
The introspections scan(s) should take an insignificant amount of time, relative to the actual import/export, and so may necessitate that the archive has a central index, from which to query statistics (see below).
This introspection could also provide a warning when the default mode is preferable over the exclusive mode, based on a threshold object limit.

Exporting/importing an archive should not at any point require more free disk space than 2x the size of the uncompressed AiiDA data, i.e., the import shouldn’t create too many temporary copies in the import process.
For example, a repository without files and 16GB of attributes/extras: export & import should not require more than approximately 32GB of free disk space.
Additionaly, the export & import should not require the full archive to be read into memory at any point; both processes should peak at no more than ~2GB of used RAM, irrespective of the database or archive size.

To ensure the data integrity of the final archive or imported database, the interaction with the SQL database should desirably be processed during a single transaction, which can be rolled back in case of import failures.
Similarly for the object-store, failed imports should not leave large occupied portions of disk space which can not be reclaimed (or at least, if large occupied portions of disk space are left behind, there should be a clear message indicating to the user how to reclaim it, ideally in an efficient way).

#### Single File Archive

For portability and space management, it is a requirements that the archive be a single (possibly zipped) file.
This compression should be intrinsic to the format specification, such that read, write and data introspection processes act on and are benchmarked against the zipped archive.

Currently the archive is allowed to be compressed *via* two standard compression algorithms (`zip` and `tar.gz`).
For data longevity, only these standard, well supported compression algorithm should be utilised.

This zip format should also desirably allow for content inspection without fully unzipping the file.

#### Archive Longevity and Accessibility

To mitigate the risk of archives becoming inaccessible, due to future technology deprecations, the following considerations should be made when selecting the archive format:

1. The default read/write tool should rely on only a minimal set of well established libraries, with clear long-term support goals.
2. The format should have a detailed specification, sufficient for third-parties to design independent read/write tools.

The archive format and tools should also provide a standalone means (outside of AiiDA) to inspect the archive file for common information such as:

* the number of database objects, by category (nodes, users, computers, groups, etc)
* the UUID set contained in the archive
* the number of object-store objects and potentially a set of object hash keys

These operation should be very fast and should not be significantly affected by archive size, ideally scaling with O(1) or O(log N) complexity, for N nodes.

It should also be considered how the archive format relates to the internal AiiDA schema, which will likely change over time, with complex schema migrations.
Ideally the archive format should be independent of this schema, with a well-defined and versioned schema that changes very infrequently.

### Proposals

#### Modification of the current JSON format

The key advantage of the current single JSON format is that it is highly stable, future-proof and accessible;
the file can be opened/read by any standard file editor tool, and directly inspected/edited by the user.

For small archives, this is most probably the best solution.
However, when considering large archives, single and large JSON-files are an extremely poor database format;
they must be read in full to access any data and don't support concurrency or ACID (atomicity, consistency, isolation, durability) transactions.

To support this, one could consider extending the current format to move towards a "NoSQL" database type implementation, splitting the JSON into multiple files (see for example [MongoDB](https://en.wikipedia.org/wiki/MongoDB)).

For example, node-level JSONs could be stored in the disk object store, together with a minimal index of UUID -> Hashkey mappings.
At a node level, dumping data into a JSON and writing to disk, would also likely be faster than recreating database tables that must handle indexes, ACID, avoiding concurrency problems, etc.
When writing an export file, these issues should not necessarily be present.

[JSON streaming](https://en.wikipedia.org/wiki/JSON_streaming) technologies, such as JSONL, also allow for JSON to be streamed, without the need to read the full file into memory.
This would overcome the current limitation in memory usage, that the full JSON must be read into memory,
but it is unclear yet as to how performant this would be.

#### SQLite database

SQL database storage will likely offer a much more efficient format, both in storage space requirement as well as import/export speed.

Of the SQL formats, SQLite likely offers the best solution:

* It is the most simple, being stored as a single file.
* It is in the standard Python library, mitigating long-term support issues.
* It is a very stable and robust format with a clear long-term support plan until at least until 2050 (see <https://www.sqlite.org/lts.html>).

The main drawback of using SQL is that it is a binary format and so inherently not directly human-readable.
The format specification must be known before reading, and also SQLite version should be preserved within the archive.

#### Other database proposals

[Zarr](https://zarr.readthedocs.io) is a relatively new standardized format based on the highly stable HDF5 format, with focus on much improved concurrent access.
However, it appears more oriented towards storing n-dimensional arrays and it long-term stability/support is unclear.

[Apache Avro](https://en.wikipedia.org/wiki/Apache_Avro) is another data storage format that utilises JSON, and has some purported benefits:

* Pre-defined (JSON) schemas => no per-record overhead
* Binary => smaller file size, faster reading
* Remote Procedure Call (RPC) support => can be used a bit like a database

The long-term stability/support of this format may be an issue.

#### Object-store

The current implementation stores file repositories in a folder structure.
These can be added directly to the zip file without ever creating a folder structure on the file system.
As with the JSON database, this format is highly accessible and stable, but not necessarily performant.

The alternative approach would be to use the newly implemented "packfile" object-store, in combination with a  SQLite database that contains the index.
The pros and cons of this approach have been previously assessed in <https://github.com/aiidateam/AEP/pull/11>.

## Pros and Cons

For implementing a new format.

### Pros

* Reduce import/export time
* Reduce memory requirements
* Provide a clear specification

### Cons

* Would be back-incompatible
* Would most likely increase the complexity of the archive format
* Would most likely reduce human-readability and direct introspection
