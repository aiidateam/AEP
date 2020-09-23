# New Export Format

| AEP number | 005                                                              |
|------------|------------------------------------------------------------------|
| Title      | Implement a new archive export format                            |
| Authors    | [Chris Sewell](mailto:christopher.sewell@epfl.ch) (chrisjsewell) |
| Champions  | [Chris Sewell](mailto:christopher.sewell@epfl.ch) (chrisjsewell) |
| Type       | S - Standard                                                     |
| Created    | 18-Sept-2020                                                     |
| Status     | submitted                                                        |

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

Particularly for large export archives, writing to (export) and reading from (import) `data.json` represents a significant bottle-neck in performance for these processes, both in respect to memory usage and process speed.

## Proposed Enhancement

The goal of this project is to first develop a set of agreed requirements for a new archive format, followed by a concrete implementation of the format, and accompanying export and import functions.

## Detailed Explanation

### User Requirements

The following is a list of the key user requirements that a new export format must address:

1. Process Speed: As an AiiDA user, I want to be able to import/export millions of nodes within hours

2. Process Memory Usage: As an AiiDA user, I want to be able to import/export databases regardless of whether the size of the database is larger than my memory.

3. Archive Size: As an AiiDA user, downloading an archive from an online repository, I expect the size of the archive (after decompression) is of the same order of the size when imported in AiiDA (DB+repo)

4. Data Integrity: As an AiiDA user I don't want imports to lead to inconsistencies in my AiiDA database.

5. Data Accessibility: As an AiiDA user, I want to be able to inspect and reuse the data I export today in 10 (or more) years time

### Design requirements

The following design requirements then derive from the above user requirements.

#### Import/Export Process

Naturally, the speed of export/import will be dependant on the the computational hardware under which the process is run.
An initial target though would be approximately one million nodes per hour, on a standard workstation with four CPU cores.

The user may run these processes in one of two modes, which may affect the process performance:

* Default mode, can be run whilst the database is being used, i.e. there is one or more daemons running.
* Exclusive mode, requires that the database is not in use.

In exclusive mode it would be possible to import directly to the new object-store pack files,
whereas in default mode the objects would be required to be imported as loose objects.

It would also be highly desirable to be able to introspect an archive before import, to feedback an estimate of the process time to the user and provide dynamic progress reporting (e.g. a progress bar). This process reporting should aim to be accurate to within a factor of approximately 2-3.
The introspections scan(s) should take an insignificant amount of time, relative to the actual import/export, and so may necessitate that the archive has a central index, from which to query statistics (see below).
This introspection could also provide a warning when the default mode is preferable over the exclusive mode, based on a threshold object limit.

Exporting/importing an archive should not at any point require more free disk space than 2x the size of the uncompressed AiiDA data, i.e., the import shouldn’t create too many temporary copies in the import process. For example, a repository without files and 16GB of attributes/extras: export & import should work with memory of approximately 1-2 GB.

To ensure the data integrity of the final archive or imported database, the interaction with the SQL database should desirably be processed during a single transaction, which can be rolled back in case of import failures.
Similarly for the object-store, failed imports should not leave large occupied portions of disc space, which can not reclaimed.

#### Archive Accessibility

To mitigate the risk of archives becoming inaccessible, due to future technology deprecations, the following considerations should be made when selecting the archive format,

1. The default read/write tool should rely on only a minimal set of well established libraries, with clear long-term support goals.
2. The format should have a detailed specification, sufficient for third-parties to design independent read/write tools.

The archive format and tools should also provide a standalone means (outside of AiiDA) to inspect the archive file for common information such as:

* The number of database objects, by category (nodes, users, computers, groups, etc)
* The UUID set contained in the archive
* The number of object-store objects and potentially a set of object hash keys.
* Extract subsets/single nodes

It should also be considered how the archive format relates to the internal AiiDA schema, which will likely change over time, with complex schema migrations.
Ideally the archive format should be independent of this schema, with a clear schema that changes very infrequently.

#### Additional Features

An additional feature to consider would be delta increments, such that an existing archive file could be amended during an export.
This may allow for a push/pull interface for "syncing" an archive file to a particular AiiDA profile.

### Proposals

#### Modification of the current JSON format

The key pro for the current single JSON format is that it is highly stable, future-proof and accessible;
the file can be opened/read by any standard file editor tool, and directly inspected/edited by the user.

For small archives, this is most probably the best solution.
However, when considering large archives, single JSON are an extremely poor database format;
they must be read in full to access any data and don't support concurrency or ACID (atomicity, consistency, isolation, durability) transactions.

To support this, one could consider extending the current format to move towards a "NoSQL" database type implementation, splitting the JSON into multiple files (see for example [MongoDB](https://en.wikipedia.org/wiki/MongoDB)).

For example, node-level JSONs could be stored in the disk object store, together with a minimal index of UUID -> Hashkey mappings.
At a node level, dumping data into a JSON and writing to disk, would also likely be faster than recreating database tables that must handle indexes, ACID, avoiding concurrency problems, etc.
When writing an export file, these issues should not necessarily be present.

[JSON streaming](https://en.wikipedia.org/wiki/JSON_streaming) technologies, such as JSONL, also allow for JSON to be streamed, without the need to read the full file into memory.
It is unclear though if this would actually provide any performance gains, since in many cases the full JSON will still need to be loaded into memory.

#### SQLite database

SQL database storage will likely offer a much more efficient format, both in storage space as well as import/export speed.

Of the SQL formats, SQLite likely offers the best solution:

* It is the most simple, being stored as a single file
* It is in the standard Python library, mitigating long-term support issues.
* It is a very stable and robust format, with a clear long-term support plan until at least until 2050 (see <https://www.sqlite.org/lts.html>)

The main drawback of using SQL is that it is a binary format and so inherently not directly human-readable.
The format specification must be known before reading, and also SQLite version should be preserved within the archive.

#### Other database proposals

[Zarr](https://zarr.readthedocs.io) is a relatively new update of the HDF5 format, with better concurrent access.
However, it appears more oriented towards storing n-dimensional arrays and it long-term stability/support is unclear.

[Apache Avro](https://en.wikipedia.org/wiki/Apache_Avro) is another data storage format that utilises JSON, and has some purported benefits:

* Pre-defined (JSON) schemas => no per-record overhead
* Binary => smaller file size, faster reading
* Remote Procedure Call (RPC) i support => can be used a bit like a database

Again the long-term stability/support of this format may be an issue.

#### Object-store

The current implementation stores file repositories in a folder structure. These can be added directly to the zip file without ever creating folder structure on the file system.
As with the JSON database, this format is highly accessible and stable, but not necessarily performant.

The alternative approach would be to use the newly implemented "packfile" object-store, with coordinating SQLite database.
The pros and cons of this approach have been previously assessed in <https://github.com/aiidateam/AEP/pull/11>.

### Archive compression

For portability, it is desirable that the full archive be contained within a single zipped file.

Currently the archive is allowed to be compressed *via* a number of different algorithms (zip, tar.gz).
For data longevity though, it is desirable that only a single compression algorithm should be enforced.

This zip format should also desirably allow for content inspection without fully unzipping the file.

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
