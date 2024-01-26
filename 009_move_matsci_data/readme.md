# Move materials science data types out of AiiDA core

| AEP number | 009                                                          |
|------------|--------------------------------------------------------------|
| Title      | Move materials science data types out of AiiDA core          |
| Authors    | [Marnik Bercx](mailto:marnik.bercx@epfl.ch) (mbercx)         |
| Champions  | [Marnik Bercx](mailto:marnik.bercx@epfl.ch) (mbercx)         |
| Type       | S - Standard Track AEP                                       |
| Created    | 6-Dec-2021                                                   |
| Status     | submitted                                                    |

## Background

Many of the data types that currently ship with `aiida-core` are closely related to the field of materials science.
To push the adoption of AiiDA in other domains, there is a longstanding discussion on moving these data types out of `aiida-core` into one or several plugin packages.
Moreover, several issues have already been raised regarding the usage of the current data types, which would potentially require backwards-incompatible changes to improve.

## Proposed Enhancement 

This AEP discusses moving the materials science data types out of the `aiida-core` package into separate plugin package(s).
As this move is an opportune moment to make changes to these classes, each will be discussed in detail to identify flaws and redesign them.

## Detailed Explanation 

### New plugin package(s)

First question to hash out is if we want to move the data type plugins related to materials science to a single plugin package or several.
Below is a list of data type entry points that need to find a new home (from [[#2686]](https://github.com/aiidateam/aiida-core/issues/2686)):

- [ ] `array.bands`
- [ ] `array.kpoints`
- [ ] `array.projection`
- [ ] `array.trajectory`
- [ ] `cif`
- [ ] `orbital`
- [ ] `structure`
- [X] `upf` -> Already moved to `aiida-pseudo`

Other code to consider moving:

* The corresponding tools in `aiida.tools.data`.
* The importers in `aiida.toold.dpimporters`.
* The resources and translators in the REST API.

### Desired changes

#### `BandsData`

Related Issues:

* BandsData refers to deprecated property of KpointsData [[#2900]](https://github.com/aiidateam/aiida-core/issues/2900)
* BandsData: suggestion for improvements [[#2847]](https://github.com/aiidateam/aiida-core/issues/2847)
* verdi data bands show broken [[#3283]](https://github.com/aiidateam/aiida-core/issues/3283)
* Give an option to bands export to normalize or not with the sum of distances [[#232]](https://github.com/aiidateam/aiida-core/issues/232)

#### `KpointsData`

Related issues:

* Supporting multiple offsets in KpointsData [[#4644]](https://github.com/aiidateam/aiida-core/issues/4644)
* Define KpointsData via constructor [[#3287]](https://github.com/aiidateam/aiida-core/issues/3287)
* KpointsData mesh doesn't work in BandsData [[#500]](https://github.com/aiidateam/aiida-core/issues/500)

#### `TrajectoryData`

* verdi data trajectory show broken [[#2435]](https://github.com/aiidateam/aiida-core/issues/2435)

#### `CifData`

* "verdi data structure export -F cif" prints a weird CIF [[#3304]](https://github.com/aiidateam/aiida-core/issues/3304)

#### `StructureData`

Related issues:

* Modes for StructureData.get_composition() [[#1643]](https://github.com/aiidateam/aiida-core/issues/1643)
* StructureData: Add export to PDB files [[#157]](https://github.com/aiidateam/aiida-core/issues/157)
* Support for magnetic structure [[#4866]](https://github.com/aiidateam/aiida-core/issues/4866)
* [cwf] Enriched StructureData or similar [[#38]](https://github.com/aiidateam/aiida-common-workflows/issues/38)

Other questions to resolve:

* If we want to work with subclasses to add certain properties, e.g. `MagneticStructureData`, can a plugin developer just use the parent `StructureData` as the input type?
* How to deal with cases where we want to potentially have two different migrations for a certain class, e.g. `KpointsData` -> `KpointsListData` and `KpointsMeshData`.

### Executing the move

After redesigning each class and adding it to its new plugin package, we need to execute a migration in `aiida-core` to adapt the entry point as well as the way the data is stored.

Question: How should we properly deprecate this?
If we make changes to the API, just migrating the data nodes will most likely break existing code.
But what is the deprecation pathway for the user if we add a warning?
For new nodes they can simply use the new entry point from the materials science plugin package.
But for already existing nodes, perhaps there should be a way of optionally migrating them?
Since not everyone will want to migrate / adapt their code immediately, maybe there should also be a flag to disable the deprecation warning.

An ideal test case for this procedure is `UpfData`, which already has a redesigned class in `aiida-pseudo`.

## Pros and Cons

### Pros
* The `aiida-core` package will be more domain-agnostic, promoting its adoption in other fields.
* Good opportunity to redesign the materials science data types.
* Moving the data types into a new lightweigth repository will make it easier to maintain.

### Cons
* Required migration and possible backwards incompatible changes in usage can be intrusive to both users and plugin developers.
* Currently there is no way to migrate data types in plugin packages.
