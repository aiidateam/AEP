# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | 0                                                            |
|------------|--------------------------------------------------------------|
| Title      | AiiDA Enhancement Proposal Guidelines                        |
| Authors    | [Leopold Talirz](mailto:leopold.talirz@epfl.ch),  [Kevin M. Jablonka](mailto:kevin.jablonka@epfl.ch) |
| Champions  |  [Leopold Talirz](mailto:leopold.talirz@epfl.ch),  [Kevin M. Jablonka](mailto:kevin.jablonka@epfl.ch) |
| Status     | active                                                       |
| Type       | P - Process                                                  |
| Created    | 19-Mar-2019                                                  |

## Background 
The AiiDA ecosystem with its plugins is highly complex and design decisions need centralized and documented dicussion. 

## Proposed Enhancement 
The AEP process will be used to propose and discuss new features and design decisions for the AiiDA project. 
This file itself constitutes an AEP and might be used a template for new AEPs. 

## Detailed Explanation 
An AEP should contain the following elements:

* *Title*: Should uniquely identify the proposed enhancment and be short 
* *Header table*: Specifying:
	* AEP number, 
	* title 
	* authors (preferably with contact details)
	* champions (individuals willing to take care of the AEP)
	* status,
	* type 
	* creation data
The status will one of the following:
	* `submitted` - this should be the initial status when submitting the pull request
	* `accepted` — this AEP has been accepted and is currently being implemented
	* `implemented` — this AEP has been implemented
	* `rejected` - this AEP has been rejected and will not be implemented
	* `withdrawn` - this AEP has been withdrawn by the submitter but can be re-submitted if someone is willing to champion it
	* `active` - this AEP is currently under active discussion within the community 
	* `postponed` - this AEP is not longer under active discussion, might be interesting for the project but has no one who is willing to champion it 
The type will be one of the following: 
	* `I - Informational AEP` - describe a design issue or best practices for users. A notable informational PEP is [the Zen of Python](https://www.python.org/dev/peps/pep-0020/)
	* `P - Process AEP` - describe changes to the processes in the AiIDA ecoystem. 
	This might be a change in the decision making or development process (e.g. new standards for commit messages)
	* `S - Standards Track AEP` - describe new features
Toth type and status will be used a pull request label. 
* *Background*: a description of the problem, e.g. containing a snippet of code that show an issue or bad design
* *Proposed Enhancement*: an abstract (1-2 sentences) of the proposed enhancement, in the best case also containing (pseudo)code samples describing the solution
* *Detailed Explanation*: a detailed discussion about all relevant technical information, possible API designs
* *Pros and Cons*: a summary for pros and cons for the proposed enhancement, detailing which possible compatbility issues

### Submission process
1. Use this Markdown file as template to describe the AEP 
2. [Create a fork](https://help.github.com/en/articles/fork-a-repo) of this repository and create a folder with the name of the AEP in lower snake-case and put the markdown file (with the title of the AEP in lower snake-case) into this folder. This folder might also contain supporting material such as figures. 
3. Submit a [pull request](https://help.github.com/en/articles/creating-a-pull-request) 
4. If the pull request is accepted (i.e. the AEP follows the guidelines outlined here) the status will change to `active` and it will also be added to the index on the `README.md` 

## Pros and Cons 

### Pros
* More structured discussion, individuals need to put a bit more thought into proposals
* Better documented decision making process 

### Cons
* More effort needed to submit an enhancement proposal





