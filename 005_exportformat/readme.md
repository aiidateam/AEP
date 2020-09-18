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
* `nodes` contains the "objectstore" files per node, organised by UUID: `xxyy-zz...`.

Particularly for large export archives, writing to (export) and reading from (import) `data.json` represents a significant bottle-neck in performance for these processes.

## Proposed Enhancement

We propose to introduce a set of requirements for a new archive format, followed by a concrete implementation of the format, and accompanying export and import functions.

## Detailed Explanation

### Specification Requirements

#### Memory Usage

As an AiiDA user I want to be able to import/export databases regardless of whether the size of the database is larger than my memory.

* Exporting/importing an archive should not at any point require more free disk space than 2x the size of the uncompressed AiiDA data, i.e., the import shouldn’t create too many temporary copies in the import process
* E.g. a repository without files and 16GB of attributes/extras: export & import should work with memory of, say, 1-2 GB
* How to accomplish this?  Import all nodes, then import all links (all in a transaction), then do checks?
* Seb: Currently these checks are done on the frontend level; perhaps it would be faster to do this at the database level

#### UX Performance

As an AiiDA user, I want to be able to import/export 6M nodes in less than 6h, at least in ‘exclusive’ mode.[a]

* Note on the exclusive mode: it is going to be possible to achieve this target if we import directly to the pack files. However, it might not be too safe to do it while AiiDA is being used. But I think this is OK: if you really have a huge import to do, most probably it’s the first thing you do after creating a profile (so before starting the daemon or a verdi shell), or it’s OK to stop working for some hours if you get orders of magnitude speedup.
* There should still be a ‘default’ mode that imports as loose objects and is safe to use for normal use. HOWEVER, this should WARN the user if there are too many objects (threshold to be decided/tested, e.g. 10’000 or 100’000 objects?), saying that it’s better to stop the daemon, import quickly, and then restart using the daemon.[b]

#### Archive size

As an AiiDA user downloading an archive from an online repository, I expect the size of the archive (after decompression) is of the same order of the size when imported in AiiDA (DB+repo), maximum a factor 1.5x

#### Data integrity

As an AiiDA user I don't want imports to lead to inconsistencies in my AiiDA database.

#### Data longevity

As an AiiDA user, I want to be able to inspect and reuse the data I export today in 10 (or more) years time  (perhaps even if AiiDA is no longer maintained)

* [Leopold] To me, this puts a big emphasis on:[c][d][e][f]
  1. Limiting the number of libraries needed to read the export format
  2. Relying only on the most widely used and well established libraries that are likely to be supported for a very long time
  3. A detailed specification of the format
* [Leopold] The old export format does a good job at this - all you need is zip and a JSON parser (you can even open the text files and edit them manually).
Perhaps a mild modification to the more easily streamable json lines format + a direct connection between the zipped files & the disk object store could be a solution
* [Giovanni] See my extensive comment. SQLite is very good for long-term preservation. We should enforce only few (1?) compression algorithm (zlib?)
* Any mandatory (python) requirement should be well maintained and easy to install with pip
Nice to have:
* Transactions As an AiiDA user I don't want partial imports in case an import fails
* Note: I [GP] think it’s ok if some space gets occupied on disk, e.g. in the import process, but then remains unaccounted for if the import fails (but nodes, instead, SHOULD NOT appear). In this case, there should be simple operations (full repack, or in most cases just a `clean_storage` of the disk-objectstore container) to reclaim that space, similarly to when objects are deleted).
* Inspection As a user I want to be able to inspect the content of an export file to know:
* how many nodes, computers, users, groups there are (GP: and also how many objects, important to warn the user about the time it will take)
* check whether a given set of uuids is in the export file
* list all uuids
* for developers: given an object hashkeys, know whether it's there
* Be able to extract subsets/single nodes from a big export file (or at least single objects)
* NOTE: probably this feature will be useful for the progress bar feature
* User interface (suggested by Giovanni) As a user, I want to be able to get an interactive progress information (progress bar) that with some approximate accuracy tells me how long the whole process will take (both for imports and for exports)
* It’s OK if it’s off by a factor of 2-3[g]
* It should be optional[h][i][j]
* If activated, shouldn’t make the import or export significantly slower
* NOTE: probably this feature will require the possibility to inspect the content of an export file
* Delta increments and future push/pull interface (Giovanni) As a user, I would like to be able to easily create export files on one profile to mirror one profile onto another, just transferring the missing nodes/objects.
* This will allow for efficient push/pull in the future.
* In the end it does not need to be implemented via export files, but if it is it’s easier to write the push/pull code around it, without the need for custom code.

## Suggestions

Simon: Consider zarr format - update on hdf5 with better concurrent access
Gio: Let's take the simplest & most robust solution that fits our needs. zarr seems a bit oriented towards storing n-dimensional arrays.
Leopold: If the export file contains an sqlite database, then we need to specify for each archive version, which sqlite version (or the disk object store version <> AiiDA version) it is compatible with.[k][l]
Gio: I suggest to drop the tar.gz format since you have to unzip the entire file to know what it contains
Gio: We could store node-level jsons in disk object store + a list of uuid<>hashkey
Leo: If you're already making your export file a database (object store sqlite), why spend so much thought on how to serialize the data from postgres rather than just dumping it into the sqlite database as well?[m][n]
Leo: Here another interesting resource on possible data formats (e.g. avro) https://www.oreilly.com/library/view/google-bigquery-the/9781492044451/ch04.html#loading_data_efficiently
   * pro avro: [o]
pre-defined (JSON) schemas => no per-record overhead; 
binary => smaller file size, faster reading
RPC support => can be used a bit like a database
   * pro json lines: human-readable; simple
Casper: A regular zip file has intelligent indexing, if I remember correctly, making it easy to utilize for inspection purposes, however, it does not account for the content to zip. I.e., we would probably still have to decide on the “information”/”inner” format.

## Concrete proposals

* JSON lines + files version (easiest to browse without special tools; not the most performant)
  * store nodes, links, groups in nodes.jsonl, links.jsonl, groups.jsonl JSON lines format
  * store file repository in a folder structure similar to how it is done now (can be added directly to the zip file without ever creating folder structure on the file system)

* Sqlite/packfiles version

* Hybrid version: create JSON files, but store them in the object store. Just keep a minimal JSON index (e.g. a mapping uuid -> hashkey) - could also be stored in multiline json, even if in many cases one might have to load it all in memory.

## Comments

[a] I know we can never have these requirements very precise and they will always be a vague estimate, but won't this also rely a lot on the machine being used. Is this target of 1Mnodes/hour for a standard laptop, a workstation or a dedicated AiiDA server?

[b] For this requirement, it then becomes crucial that we can really introspect an archive very fast to get a rough sense of the size of the contents. Ideally by scanning on the file, but if this is too slow, we might need to create some "index" file with some stats that our commands typically use. This also goes back to the `verdi export inspect` command and making that as efficient as possible.

[c] Agreed on all three points. However, your confusion (in a private email) that we shouldn't use SQLite does not hold. Indeed, looking at your points: (a) SQLite is in the standard python library, no dependencies required (I use SQLAlchemy because I'm lazy, but I could drop it in disk-objectstore and have 0 dependencies).
(b) SQLite is a very stable and robust format. They have a dedicated page: https://www.sqlite.org/lts.html, intend to support the format at least until 2050, and SQLite is  the recommended by the US Library Of Congress for the preservation of digital content.
(c) Indeed, this is important to write down clearly.

The requirement boils down to: given a SHA of an object, get the content. If uncompressed, you just do a SELECT in SQLite, get the offset and the length, and then f=open(pack_file, 'rb'); f.seek(offset); content=f.read(length). If it's compressed, you just need to uncompress with standard libraries (zlib). I agree, though, that we shouldn't use exoteric compression libraries in the export format (OK instead for internal use if wanted).

[d] Great - thanks for checking, I think this makes sqlite a valid choice. 
However, I do think we still need to weigh it against JSON. Being able to simply open a JSON file in a text editor and manipulate it (even without needing to know anything about the format specification) is an added value that a binary format cannot provide.

And to cite the Library of congress notice on sqlite: "As of this writing (2018-05-29) the only other recommended storage formats for datasets are XML, JSON, and CSV."

[e] As with all these requirements, ultimately they are all tradeoffs. Going for human-readable and introspectable formats will almost guaranteed lead to less efficient formats, both in storage space as well as import/export speed. Although I see your point that you want your data to be usable even after AiiDA is no longer there (people don't like being locked in) I think that realistically this is impractical even with a human-readable format. If you have any reasonably sized archive, although you can directly "read" the data, making any sense out of it without AiiDA will be really difficult. I would therefore be tempted towards a more efficient format even if that means it no longer is directly readable.

[f] Anyway, I think using the disk-objectstore is OK. Look at this issue on how to fetch data without using the library, with (more or less standard) command-line utilities: https://github.com/aiidateam/disk-objectstore/issues/100

[g] Let's not ask the guy who implemented the Windows progress bar to do it then ;)
[h] Sure, but there should still probably always be a minimum of a progress information given to the user of some kind?

[i] No, you might want to have a quiet mode for some usecases (but indeed, probably verdi export should have some info by default)

[j] Having `-q/--quiet` makes sense, I also simply meant the default. It seems here you want to _not_ make it default, which is fine. I was just clarifying/expanding on this point and its connotations.
[k] As I mentioned in an earlier comment, the SQLite guys think hard at long-term support - I don't think relying on SQLite will be the problem
https://www.sqlite.org/lts.html
[l] As a summary - the SQLite guys are very serious, we can typically trust what they do (their fail-safe mode for DB files written on disk is more robust and has less bugs than postgreSQL!)
[m] Managing schema migrations become hard, we bind the export file format to the internal AiiDA schema. We should do the opposite (unless it turns out to be impossibly slow) - fix a very clear schema of the export file, aiming at changing it as little as possible, and then map to a schema that we can optimise for speed
[n] Also, at a node level, it's almost definitely faster to just dump everything in a JSON and write it to disk that to recreate many tables - the DB has to take care of indexes, ACID, avoiding concurrency problems, also when we know nothing of this will happen (e.g. when writing an export file)

[o] If we use Avro, we definitely need to use this library for performance: https://github.com/fastavro/fastavro - still, we should be careful if we need the features of Avro - it's much about schemas, and the largest part of our data will be schema-less - then, just better to dump a JSON per node (and compress it), it will be almost for sure faster.

## Pros and Cons

### Pros

* Reduce import/export time

### Cons

* A new format would be back-incompatible
