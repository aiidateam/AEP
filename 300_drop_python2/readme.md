# Schedule for drop of support of Python 2.7

| AEP number | 300                                                          |
|------------|--------------------------------------------------------------|
| Title      | Schedule for drop of support for Python 2.7                  |
| Authors    | [Carl Simon Adorf](mailto:simon.adorf@epfl.ch) (csadorf)     |
| Champions  | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz)    |
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

 * Dec 1 2019: The development of new features with support for Python 2.7 is discontinued.
 * Jan 1 2020: The support for Python 2.7 is officially discontinued.
   *Important* security and bug fixes are released on the last AiiDA minor release line with Python 2.7 support.
 * Jul 1 2020: Security and bug fix releases on the last AiiDA minor release line with Python 2.7 support are discontinued.

## Detailed Explanation

The decision to discontinue the development of new features with support for Python 2.7 with almost immediate effect is highly justified, because this impending change has been announced to the community for a long time.
The support of Python version 2.7 is therefore considered deprecated already as of AiiDA version 1.0.
The announcement within the change log or through the use of programmatic warnings in sense of the emission of `DeprecationWarnings` or similar should therefore be considered as additional reminders to users about this policy.

Furthermore, an expedited deprecation and drop of support for Python 2.7 is warranted, because the Python library ecosystem has rapidly evolved in the past year with many prominent projects not only [pledging to discontinue the support for Python 2.7](https://python3statement.org/), but [actively](https://docs.scipy.org/doc/numpy/release.html#numpy-1-17-0-release-notes) [dropping](https://scikit-learn.org/stable/whats_new.html#version-0-20-0) [that](https://docs.djangoproject.com/en/2.2/releases/2.0/) [support](https://matplotlib.org/3.0.0/api/api_changes.html?highlight=python#api-changes-for-3-0-0) [even in minor releases](https://docs.scipy.org/doc/scipy/reference/release.1.3.0.html) as well.
This has not only massively increased the pressure on users to update their tool chains, but also makes it excruciatingly more difficult to maintain support for Python 2.7 for AiiDA.

There might be some expectations from users that the drop of support for Python 2.7 warrants a major version change, however this is arguably not supported by the stipulations of semantic versioning.
Semantic versioning requires a major release for backwards incompatible API changes, however the drop of support of deprecated dependencies does arguably not fall into that category.
While it is true that many major Python packages decided to drop the support in conjunction with a major version increase, there are also examples to the contrary, for example the Scipy package largely follows semantic versioning and dropped support for Python 2.7 with [version 1.3](https://docs.scipy.org/doc/scipy/reference/release.1.3.0.html).

Furthermore, the release of aiida-core version 1.0 represents a major milestone for the AiiDA project in terms of increase of stability and maturity.
It would be highly confusing to users to release a version 2.0 relatively shortly after that, since users can reasonably expect that version 2.0 might represent a larger change in feature set and introduces backwards incompatible changes.

## Alternatives

  * Increase the major version

    This policy should be considered since many other projects within the Python ecosystem tied their drop of support for Python 2.7 to a major version update.

  * Continue feature development support for Python 2.7 beyond 1-Jan-2020.

    Such a policy would be in direct contradiction to previous announcements and would bind significant amount of development resources.
    Furthermore any new feature could only depend on libraries and other packages that also still support Python version 2.7, which becomes increasingly difficult.

## Pros and Cons

### Pros

  * Discontinuing the development of new features with support for Python 2.7 is easier now then later, since AiiDA version 1.0 was very recently released, presenting a clear cut in terms of feature development.
  * Discontinuing the development of new features with support for Python 2.7 will make it easier to relax dependency requirements and make certain novel feature development possible in the first place.
  * Continuing feature development support beyond Jan-1-2020 violates the AiiDA team's own agenda and will set false expectations within the developer and user community.

### Cons

  * Some users might be confused that the support for Python version 2.7 was dropped in a minor release because they incorrectly assume that this would require a major version update according to semantic versioning.
