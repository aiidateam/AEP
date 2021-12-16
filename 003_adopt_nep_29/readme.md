# AEP 003: Adopt NEP 29

| AEP number | 003                                                          |
|------------|--------------------------------------------------------------|
| Title      | Adopt NEP 29                                                 |
| Authors    | [Carl Simon Adorf](mailto:simon.adorf@epfl.ch) (csadorf)     |
| Champions  | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz), [Sebastiaan Huber](mailto:sebastiaan.huber@epfl.ch) (sphuber) |
| Type       | P - Process                                                  |
| Created    | 14-Jul-2020                                                  |
| Status     | active                                                       |

## Background 

The `aiida-core` package is classified as a hybrid between a library and application, and dependencies are kept as flexible as possible to allow the installation of the package within various Python software environments in combination with other libraries and applications, see [AEP 2](https://github.com/aiidateam/AEP/blob/master/002_dependency_management/readme.md) for details.

The [NumPy project](https://numpy.org/) has accepted the [Numpy Enhancement Proposal 29](https://numpy.org/neps/nep-0029-deprecation_policy.html) (NEP 29), which recommends that *all projects within the scientific Python ecosystem* adopt a common deprecation policy with respect to the range of minimally supported Python and NumPy versions.

## Proposed Enhancement 

This AEP proposes that `aiida-core` adopts the Python and NumPy version support schedule and deprecation policy outlined in NEP 29.
It is strongly recommended that other packages within the AiiDA ecosystem, e.g. plugins, adopt the same policy.

## Detailed Explanation

After this AEP is accepted, `aiida-core` will effectively adopt the policies outlined in NEP 29 on **2021-01-13** and enter a transition period with a slightly adjusted support schedule until then:

| Date           | Python | NumPy | NEP 29 compliant | adjusted
-----------------|--------|-------|------------------|---------
| 2020-09-13     | 3.6+   | 1.17+ | no               | no
| **2021-01-13** | 3.7+   | 1.17+ | yes†             | **yes**‡
| 2021-12-26     | 3.8+   | 1.18+ | yes              | no


The adjusted support schedule reflects that dropping support for Python 3.5 on an adjusted schedule is not really necessary and schedules the drop of support for Python 3.6 to coincide with the scheduled drop of support for NumPy version 1.16 according to NEP 29 at which point AiiDA's support schedule would be in compliance with NEP 29.

†) The current support of NumPy in `aiida-core` is defined as `~=1.17<1.18` which means that in order to be fully compliant with NEP 29, AiiDA will need to add support for later versions of NumPy by then.

‡) The support for Python 3.6 was [previously announced](http://www.aiida.net/download/) to last until 2021-12-23.

## Pros and Cons

### Pros

 * The adoption of NEP 29 will harmonize AiiDA's deprecation policy with other major libraries within the Scientific Python ecosystem. As NEP 29 becomes adopted more broadly, users will have an expectation of the same level of support from AiiDA.
 * The adoption of NEP 29 will reduce the supported range of Python (minor) versions, which will simplify dependency management and testing.
 * The adoption of NEP 29 will remove the need for AiiDA maintainers to maintain their own (custom) support and deprecation schedule.

### Cons

 * The adoption of NEP 29 will slightly reduce the supported range of Python (minor) versions, which might be problematic for users who rely on older Python versions. However, it is important to note that other major libraries, such as NumPy, that are likely required in the same context, will also have likely dropped support for these particular versions.
