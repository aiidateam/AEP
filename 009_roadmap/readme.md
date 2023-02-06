# AEP 009: Implement a formal AiiDA Roadmap

| AEP number |                       000                       |
| ---------- | ----------------------------------------------- |
| Title      | AiiDA Enhancement Proposal (AEP) Guidelines     |
| Authors    | [Chris Sewell](https://github.com/chrisjsewell) |
| Champions  | [Chris Sewell](https://github.com/chrisjsewell) |
| Type       | P - Process                                     |
| Created    | 06-Feb-2023                                     |
| Status     | draft                                           |

## Background

The AiiDA ecosystem is diverse and multi-faceted and, as such, requires a clear roadmap to ensure that work on the project is coordinated and able to deliver on its goals.

Currently, <https://github.com/orgs/aiidateam/projects/3> provides an initial attempt to define a roadmap.
However, ...

Note, there is also <https://github.com/aiidateam/aiida-core/wiki/GSoC-2023-Projects>, which contains projects for GSoC 2023.
This should be aligned with the roadmap.

## Proposed Enhancement

An abstract (1-2 sentences) of the proposed enhancement, ideally containing (pseudo)code samples describing the solution. ...

## Detailed Explanation

### The purpose of the roadmap

The AiiDA roadmap should serve two purposes:

1. It communicates our goals and priorities to users and stakeholders.
2. It underpins building a clear and agreed plan for work on AiiDA within the team.

The roadmap is effectively an exercise in prioritization.
Roadmap reviews should be performed periodically (at least once per month), to ensure the roadmap reflects the current state of the AiiDA ecosystem, and its core goals.

The roadmap should incur minimal overhead, and should be easy to maintain, read, and contribute to.

### Distinction from AEPs and repository issues

The roadmap is not a replacement for AEPs or issues on the AiiDA repositories.

AEPs are used to describe the implementation of a new feature or design choice, whereas roadmap items should not be concerned with the implementation, but rather the "why not the how".
As such, most AEPs will be linked to one or more roadmap items, which they look to resolve.

Issues on the AiiDA repositories are used to describe bugs or feature requests, on that repository.
Roadmap items are used to describe the goals of the AiiDA ecosystem as a whole.
As such, roadmap items will be linked to one or more issues, AEPs and pull-requests, that will provide full or partial solutions to the item.

### The roadmap structure

The roadmap will be maintained in a new repository: `aiidateam/team-compass`.

Each roadmap item will be a GitHub issue on that repository, with a label corresponding to its state (see below).
The initial issue comment should follow the roadmap item structure, as detailed below.

There MUST NOT be more that 20 `active` roadmap items at any time.
This is to ensure that the team can focus on a manageable number of items at any time.

Each `active` item should be assigned at least one person, who is responsible for monitoring and driving the item forward.
All `active` items should be present on a GitHub project board, which will order the items by priority, and will be reviewed at least once per month.

### Roadmap item specification

The roadmap is comprised of items.

A roadmap item MUST describe an aspect of the AiiDA ecosystem that we wish to improve, in a manner that can be understood by non-technical users.

The item SHOULD NOT include a concrete solution.
A roadmap item "is the why not the how", it will link to one or more issues, AEPs and pull-requests, that will provide full or partial solutions to the item.
The roadmap item will be closed, during roadmap reviews, when it is deemed fully resolved.

Each item SHOULD be rankable, relative to other items.
All `active` items will be placed in a list of priority, which may be altered during roadmap reviews.

Each item SHOULD be categorised as one of the following:

- `defect`: Address an issue that is already causing failures within the AiiDA ecosystem.
- `usability`: An improvement to the AiiDA ecosystem, that addresses either improving a current feature, or adding a new feature.
- `future`: Addresses a change required to keep the AiiDA ecosystem future proof. For example, upgrading to a new version of a dependency.
- `dev`: A change to the AiiDA ecosystem, that will aide development. For exampe, changes to deployment or testing infrastructures.

Each item MUST be in one of the following states:

- `proposed`: The item has been proposed but not yet processed.
- `rejected`: The item was rejected by the team.
- `active`: The item is active in the roadmap.
- `resolved`: The item was successfully resolved. The issues for these items should also be closed.
- `postponed`: The item was not rejected but is not currently part of the active items.

### Roadmap item structure

Each item SHOULD be written in Markdown and follow the structure denoted below.
The goal is for the writing process to have minimal overhead, and that the item is understandable as early as possible.

#### Heading

The top-level heading should be no longer than 50 characters, and provide a concise description of the item.

It should be prepended with the item category, in the form:

- `Defect: `
- `Usability: `
- `Future: `
- `Dev: `

From the title should be clear for users/stakeholders what the item addresses.

#### Motivation

Provide a brief description of what the current problem is, that needs to be resolved, and how its resolution would improve the AiiDA ecosystem.

The motivation may contain one or more use cases.

#### Desired Outcome

Provide a description that can be used to decide if the roadmap item has been resolved.

#### Impact

This section should comment on the impact of resolving the item. For example, how many users will it affect.

#### Complexity

This section should comment on the complexity of resolving the item, and make a rough estimate as to the amount of work/time it would take to reach the desired outcome.

#### Background

This section is optional.

The section should describe details of previous thought and work done around solving the issue.
For example, it could outline current workarounds to the problem, and why they are not ideal, and/or what solutions have been proposed previously (and why they were rejected).

#### Progress

This section should be continually updated, with links to ongoing work around the item.
For example, open/closed issues, PRs and AEPs.

It should provide information to help understand if the item is progressing and/or what is blocking its resolution.

#### Resolution

When an item is move to the `resolved` state, this section should be added, to explain how it was resolved and/or why it is considered resolved.

## Pros and Cons

...
