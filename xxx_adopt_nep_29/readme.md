# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | XXX                                                          |
|------------|--------------------------------------------------------------|
| Title      | Adopt NEP 29                                                 |
| Authors    | [Carl Simon Adorf](mailto:simon.adorf@epfl.ch) (csadorf)     |
| Champions  | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz)    |
| Type       | P - Process                                                  |
| Created    | 14-Jul-2020                                                  |
| Status     | submitted                                                    |

## Background 

The aiida-core package is classified as a hybrid between a library and application and dependencies are kept as flexible as possible to allow the installation of the package within various Python software environments in combination with other libraries and applications, see [AEP 2](https://github.com/aiidateam/AEP/blob/master/002_dependency_management/readme.md) for details.

The [NumPy project](https://numpy.org/) has accepted the [NEP 29](https://numpy.org/neps/nep-0029-deprecation_policy.html), which recommends that *all projects within the scientific Python ecosystem* adopt a common deprecation policy with respect to the range of minimally supported Python and Numpy versions.

## Proposed Enhancement 

This AEP proposed that the AiiDA ecosystem adopts the deprecation policy outlined in NEP 29.

## Pros and Cons

### Pros

 * The adoption of NEP 29 will harmonize AiiDA's deprecation policy with other major libraries within the Scientific Python ecosystem. As NEP 29 becomes more and more adopted, users will have an expectation of this level of support from AiiDA.
 * The adoption of NEP 29 will reduce the supported range of Python (minor) versions, which will simplify dependency management and testing.
 * The adoption of NEP 29 will remove the need for AiiDA maintainers to maintain their own (custom) support and deprecation schedule.

### Cons

 * The adoption of NEP 29 will slightly reduce the supported range of Python (minor) versions, which might be problematic for users who rely on older Python versions; however it is important to note that other major libraries, such as NumPy, that are likely required in the same context, will also have likely dropped support for these particular versions.
