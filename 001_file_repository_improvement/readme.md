# Improved file repository

| AEP number | 001                                                             |
|------------|-----------------------------------------------------------------|
| Title      | Improved file repository                                        |
| Authors    | [Sebastiaan P. Huber](mailto:sebastiaan.huber@epfl.ch) (sphuber)|
| Champions  | [Sebastiaan P. Huber](mailto:sebastiaan.huber@epfl.ch) (sphuber) [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz)|
| Type       | S - Standard                                                    |
| Created    | 18-Oct-2019                                                     |
| Status     | submitted                                                       |

## Background
The persistent state of a node in the provenance graph is stored across two resources.
The relational database and a file repository.
Currently, the only possible implementation of the file repository is a file system that is local to the AiiDA instance.
A local file system is not always the most suitable solution for the storage of many and/or large files, as is the case for the repository in many use-cases.
Providing the possibility to have the repository be hosted on another machine as well as potential other implementations in addition to a file system, would be desirable.
In addition, currently there is no record of what files are present in a node's repository in the database.
This means that in order to determine what files a node contains, one has to directly inspect it's repository folder.
For a local file system this is not a problem, however, when offering the possibility of remotely hosted repositories, indexing the contents of a node's repository becomes more expensive.
A potential solution is to store an index of the repository contents for a given node in the database.
Only when the actual content of a repository object needs to be fetched will the cost of the remote connection be incurred.
The downside of the approach is clearly the added cost in storage within the database.

## Proposed Enhancement
Create an abstract file repository interface that can be used to store files with optional (virtual) directory hierarchies.
This interface should be implemented for a local file system and ideally for a remote file system and Swift object store.
This interface can be used by nodes to store their files.

## Detailed Explanation

### Properly abstract the concept of the repository
Currently the integration of the repository is tightly coupled to the implementation of the ORM.
This makes it difficult to provide different repository implementations.
The first step then would be to abstract the repository concept and write a generic interface to list, create, get and delete objects in it.
Since it is envisioned that solutions will be implemented that are not necessarily file system based, it is important that the interface does not implicitcly bake-in file-system-only concepts.
We propose to talk exclusively about "objects" in the repository.
An object can then refer to a directory or a file.
These objects can then also have metadata, such as creation time, modification time, owner, permissions etc.

### Store index of node repository contents in database
When storing a file in the repository for a node, instead of the node directly passing this to the repository interface, it should go through a node-repository manager.
This class is the gateway between the node and its repository.
When storing an object for a node in the repository, it will first request the configured repository to store the object with the given name.
When successful, the repository will return a key that is the unique identifier for the stored object.
This key is then used to create an entry in the node repository index table to register its existence.

### API to control bundling and compression of multiple objects of a node's repository
Each node can have associated files with arbitrary hierarchy.
Often these files do not have to be accessed very often and so it may be more beneficial to bundle and compress the files.
This will save space (and inodes in the case of a file system) at the cost that accessing any particular file now comes with the overhead of uncompressing and unpacking all files.
For files stored on a remote machine, the cost of unpacking will be compensated by a reduced transfer time.
Since for the most part repository files are not used very often, I propose that for the initial implementation we always bundle and compress.
In the future, this behavior may be improved by allowing it to be configurable per node class or even instance.

### Sketch of classes and tables
The following database classes will be required, in Django syntax:
```
class DbRepository(m.Model):
    """Table of available and used repositories.

    Attributes:
    * name: Human readable label that also corresponds to the appropriate key in the config
    * uuid: UUID associated with the repository upon creation

    """
    name = m.CharField(max_length=255, unique=True, blank=False)
    uuid = UUIDField(auto=False, version=AIIDANODES_UUID_VERSION)


class DbFile(m.Model):
    """Table of files stored in the repository.

    Attributes:
    * uuid: Automatically uniquely generated
    * key: fully qualified identifier to define location within repository
    * repository: foreign key to `DbRepository` table

    """
    uuid = UUIDField(auto=True, version=AIIDANODES_UUID_VERSION)
    key = m.CharField(max_length=255)
    repository = m.ForeignKey('DbRepository', related_name='files', on_delete=m.PROTECT)
    nodes = m.ManyToManyField(DbNode, symmetrical=False, related_name='files', through='DbNodeFile')


class DbNodeFile(m.Model):
    """Join table of repository files and node.

    Attributes:
    * uuid: Automatically uniquely generated
    * node: Id of the corresponding DbNode entry
    * file: Id of the corresponding DbFile entry, can be null in the case of a directory
    * path: Relative path within the node's virtual hierarchy, must have trailing slash if directory
    * metadata: Any file metadata such as permissions and ownership

    """
    uuid = UUIDField(auto=True, version=AIIDANODES_UUID_VERSION)
    node = m.ForeignKey('DbNode', related_name='dbnodefiles', on_delete=m.CASCADE)
    file = m.ForeignKey('DbFile', related_name='dbnodefiles', on_delete=m.PROTECT, null=True)
    path = m.CharField(max_length=255, db_index=True)
    metadata = m.JSONB(default='{}')

    class Meta:
        unique_together = ('node', 'path')

```

The new ORM classes necessary for the `Repository` interface and `NodeRepositoryManager` gateway:
```

class Repository(object):
    """Represents a repository in which a node can write objects."""


    def list_objects(self, key=None):
        """Return a list of the objects contained in this repository, optionally in the given sub directory.

        :param key: fully qualified identifier for the object within the repository
        :return: a list of `File` named tuples representing the objects present in directory with the given key
        """

    def list_object_names(self, key=None):
        """Return a list of the object names contained in this repository, optionally in the given sub directory.

        :param key: fully qualified identifier for the object within the repository
        :return: a list of `File` named tuples representing the objects present in directory with the given key
        """

    def open(self, key, mode='r'):
        """Open a file handle to an object stored under the given key.

        :param key: fully qualified identifier for the object within the repository
        :param mode: the mode under which to open the handle
        """

    def get_object(self, key):
        """Return the object identified by key.

        :param key: fully qualified identifier for the object within the repository
        :return: a `File` named tuple representing the object located at key
        """

    def get_object_content(self, key, mode='r'):
        """Return the content of a object identified by key.

        :param key: fully qualified identifier for the object within the repository
        :param mode: the mode under which to open the handle
        """

    def put_object_from_tree(self, path, key=None, contents_only=True):
        """Store a new object under `key` with the contents of the directory located at `path` on this file system.

        :param path: absolute path of directory whose contents to copy to the repository
        :param key: fully qualified identifier for the object within the repository
        :param contents_only: boolean, if True, omit the top level directory of the path and only copy its contents.
        """

    def put_object_from_file(self, path, key):
        """Store a new object under `key` with contents of the file located at `path` on this file system.

        :param path: absolute path of file whose contents to copy to the repository
        :param key: fully qualified identifier for the object within the repository
        """

    def put_object_from_filelike(self, handle, key, mode='w', encoding='utf8', force=False):
        """Store a new object under `key` with contents of filelike object `handle`.

        :param handle: filelike object with the content to be stored
        :param key: fully qualified identifier for the object within the repository
        :param mode: the file mode with which the object will be written
        :param encoding: the file encoding with which the object will be written
        :param force: boolean, if True, will skip the mutability check
        """

    def delete_object(self, key):
        """Delete the object from the repository.

        :param key: fully qualified identifier for the object within the repository
        """


class NodeRepositoryManager(object):
    """Gateway between a `Node` instance and a `Repository`

```
Both the `Node` class as well as the `NodeRepositoryManager` should provide the same interface as the `Repository` class.
Each `Node` instance will then instantiate a `NodeRepositoryManager` instance in its constructor and all repository calls will pipe through to the manager.
This will then call through to the `Repository`.
In the case of mutating actions, such as `put` or `delete`, the manager will first delegate the call to the `Repository` and upon success effectuate the changes on the database, in the case of `put`, or vice versa in the case of `delete`.
The repository methods of `Node` and `NodeRepositoryManager` will need to pass in an additional argument if multiple repositories become supported.

## Pros and Cons

### Pros
* Abstracting the repository interface allows for having more options that gives more freedom to users.
  High-throughput projects may require a remote file system or object store solution to be able to support the quantities of data that are produced.
* The node repository index makes it faster to determine what objects are contained in its repository
* The node repository index allows to provide a uniform set of repository object metadata across repository implementations
* Allowing the bundling and compression of repository objects reduces the load on file system solutions in terms of required space and inodes.
* A cleanly separated repository interface paves the way to enabling multiple repositories per profile.

### Cons
* Storing an index of all objects in a node's repository has a non-negligible overhead in database load as well as storage space.
* The implementation of storing and retrieving objects from the repository becomes more complicated with the addition of bundling and compressing.
* The storage of files in the repository becomes even more opaque for the user.
  In the case of an object store this is necessary and not even a downside, but for users only using a local file system, this may be unintuitive.
  However, even in the current situation the user is not supposed to directly access or interact with the repository on the local file system.

## Open questions
* Should the full configuration of a `Repository` be stored in its database entry, or the database just keeps a reference of known repositories.
  Connection details for each one are then kept in the `config.json` as is currently the case.