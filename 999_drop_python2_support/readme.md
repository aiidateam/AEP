# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | 999                                                          |
|------------|--------------------------------------------------------------|
| Title      | Drop of support for Python 2.7                               |
| Authors    | [Carl Simon Adorf](mailto:simon.adorf@epfl.ch) (csadorf)     |
| Type       | P - Process                                                  |
| Created    | 15-Nov-2019                                                  |
| Status     | submitted                                                    |

## Background

The AiiDA core package has recently been released in version 1.0 with official support for Python versions 2.7 and >= 3.6.
Python version 2.7 has been deprecated for a while and support will be dropped by 1-Jan-2020.
The AiiDA team has stated previously that the support of AiiDA for Python 2.7 will dropped as of January 2020.

This AEP lays out a concrete roadmap as to how this drop of support will be accomplished while aiming to find a reasonable balance between disruption of user workflows, developer burden, and public appearance of the project.

## Proposed Enhancement

We propose the following schedule:

 * Dec 1 2020: The development of new features with support for Python 2.7 is discontinued.
   Any new features must be released as part of the 2.x line.
 * Jan 1 2020: The support for Python 2.7 is officially discontinued.
   *Important* security and bug fixes are released on the 1.x line.
 * Mar 1 2020: The recommended moratorium on minor releases ends.
 * Jul 1 2020: Security and bug fix releases for the 1.x release line are  discontinued.

The recommended moratorium on minor releases is supposed to reduce the potential for user confusion with respect to a change in feature set or potential backwards incompatibilities.
However, the AiiDA team should revisit this policy with every new feature development and decide whether an immediate release of set feature outweighs the benefits of the moratorium.

## Detailed Explanation

The decision to discontinue the development of new features with support for Python 2.7 with almost immediate effect is highly justified, because this impending change has been announced to the community for a long time.
The support of Python version 2.7 is therefore considered deprecated already as of AiiDA version 1.0.
The announcement within the change log or through the use of programmatic warnings in sense of the emission of `DeprecationWarnings` or similar should therefore be considered as additional reminders to users about this policy.

Furthermore, an expedited deprecation and drop of support for Python 2.7 is warranted, because the Python library ecosystem has rapidly evolved in the past year with many prominent projects not only [pledging to discontinue the support for Python 2.7](https://python3statement.org/), but [actively](https://docs.scipy.org/doc/numpy/release.html#numpy-1-17-0-release-notes) [dropping](https://scikit-learn.org/stable/whats_new.html#version-0-20-0) [that](https://docs.djangoproject.com/en/2.2/releases/2.0/) [support](https://matplotlib.org/3.0.0/api/api_changes.html?highlight=python#api-changes-for-3-0-0) [even in minor releases](https://docs.scipy.org/doc/scipy/reference/release.1.3.0.html) as well.
This has not only massively increased the pressure on users to update their tool chains, but also makes it excruciatingly more difficult to maintain support for Python 2.7 for AiiDA.

There might be some expectation from users that a major version increase may imply a major change in feature set, however, we believe that the potential user confusion is far outweighed by the benefits of the expedited drop of support for Python 2.7.
Furthermore, confusion can be reduced through transparent communication of the policy on the mailing list and as part of the change log.
Finally, confusion might be reduced by postponing the release of the 2.x line until 1-Mar-2020.

## Alternatives

  * Drop of support with the next minor release.

    This policy should be considered since it might be less confusing to users and it could be argued that it [does not violate](https://semver.org/#what-should-i-do-if-i-update-my-own-dependencies-without-changing-the-public-api) the stipulation of [semantic versioning](https://semver.org/#summary).
    Semantic versioning requires a major release for backwards incompatible API changes, however the drop of support of deprecated dependencies does arguably not fall into that category.
    While it is true that many major Python packages decided to drop the support in conjunction with a major version increase, there are also examples to the contrary, for example the Scipy package largely follows semantic versioning and dropped support for Python 3.7 with version 1.3 (see link above).

  * Continue feature development support for Python 2.7 beyond 1-Jan-2020.

    Such a policy would be in direct contradiction to previous announcements and would bind significant amount of development resources.
    Furthermore any new feature could only depend on libraries and other packages that also still support Python version 2.7, which becomes increasingly difficult.

## Pros and Cons

### Pros

  * Discontinuing the development of new features with support for Python 2.7 is easier now then later, since AiiDA version 1.0 was very recently released, presenting a clear cut in terms of feature development.
  * Discontinuing the development of new features with support for Python 2.7 will make it easier to relax dependency requirements and make certain novel feature development possible in the first place.
  * Continuing feature development support beyond Jan-1-2020 violates the AiiDA team's own agenda and will set false expectations within the developer and user community.

### Cons

  * Some users might be confused by the major version increase relatively shortly after the release of version 1.0 and might expect a major change in feature set and possibly backwards incompatible changes.
