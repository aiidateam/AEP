# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | 0                                                            |
|------------|--------------------------------------------------------------|
| Title      | AiiDA Enhancement Proposal (AEP) Guidelines                  |
| Authors    | [Kevin M. Jablonka](mailto:kevin.jablonka@epfl.ch), [Leopold Talirz](mailto:leopold.talirz@epfl.ch)|
| Champions  | [Kevin M. Jablonka](mailto:kevin.jablonka@epfl.ch), [Leopold Talirz](mailto:leopold.talirz@epfl.ch)|
| Status     | active                                                       |
| Type       | P - Process                                                  |
| Created    | 19-Mar-2019                                                  |

## Background 
The AiiDA ecosystem with its plugins is growing beyond the bounds of EPFL
and would benefit from a public discussion of design issues that can bring 
all stakeholders to the table, while also serving as a documentation of the decision process.

See also [PEP-1](https://www.python.org/dev/peps/pep-0001/) for the rationale behind
introducing enhancement proposals for the python project. 

## Proposed Enhancement 
The AEP process will be used to propose and discuss new features and design decisions for the AiiDA project. 
This file itself constitutes an AEP and can be used a template for new AEPs. 

## Detailed Explanation 
An AEP should contain the following elements:

### Title

Should be short and uniquely identify the proposed enhancement

### Header table

A table containing:
  * AEP number: numbered consecutively by submission date
  * title
  * authors: preferably with GitHub user names
  * champions: individuals willing to take care of implementing the AEP
  * status: one of
    * `submitted` - this should be the initial status when submitting the pull request to the AEP repository
    * `active` - the pull request for this AEP has been merged and the AEP is currently under active discussion within the community 
    * `postponed` - this AEP is no longer under active discussion, might be interesting for the project but has no one who is willing to champion it 
    * `accepted` - this AEP has been accepted and is currently being implemented
    * `rejected` - this AEP has been rejected and will not be implemented
    * `implemented` - this AEP has been implemented
    * `withdrawn` - this AEP has been withdrawn by the submitter but can be re-submitted if someone is willing to champion it
  * type: one of
    * `S - Standard Track AEP`: describes new features or changes to AiiDA
    * `I - Informational AEP`: describes design issues or best practice. A notable informational PEP is [the Zen of Python](https://www.python.org/dev/peps/pep-0020/)
    * `P - Process AEP`: describes changes to processes in the AiiDA ecoystem, such as a change to the decision making or development process (e.g. new standards for commit messages)
  * creation date

Both type and status should be used as labels when making a new pull request for an AEP.

### Background

A description of the problem, e.g. containing a snippet of code that show an issue or bad design.

### Proposed Enhancement

An abstract (1-2 sentences) of the proposed enhancement, ideally containing (pseudo)code samples describing the solution.

### Detailed Explanation

A detailed discussion about all relevant technical information, possible API designs.

### Pros and Cons

A summary for pros and cons for the proposed enhancement, detailing e.g. which possible compatibility issues may arise.

### Submission process

![AEP submission process](aep_diagram.png) 

1. [Fork](https://help.github.com/en/articles/fork-a-repo) this repository
2. Create a folder with the title of the AEP in lower [snake-case](https://en.wikipedia.org/wiki/Snake_case)
   and put a [Markdown](https://guides.github.com/features/mastering-markdown/) file with the title of the AEP in lower case inside this folder.
     * You may use the `aep_guidelines.md` as a template.
     * You may want to include additional files relevant to your enhancement proposal.
3. Submit a [pull request](https://help.github.com/en/articles/creating-a-pull-request) to the AEP repository
4. Then, the pull request will be reviewed. If the pull request is accepted the status will change to `active` and it will be added to the AEP index in the `README.md` 

## Pros and Cons 

### Pros
* Public discussion of design goals and implementation that is open to input from the entire AiiDA community
* Structures the discussion, providing basic guidance on how to "make a case" for an enhancement
* Public record of decision process 

### Cons
* Slightly increased overhead compared to an informal Google doc
