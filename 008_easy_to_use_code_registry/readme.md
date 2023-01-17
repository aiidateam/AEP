# AEP 008: AiiDA code registry for easy setup of computer/code

| AEP number | 008                                                          |
|------------|--------------------------------------------------------------|
| Title      | New aiida-code-registry for easy code/computer setup                  |
| Authors    | [Jusong Yu](mailto:jusong.yu@psi.ch) (unkcpz) |
| Champions  | [Jusong Yu](mailto:jusong.yu@psi.ch) (unkcpz) |
| Type       | P - Process                                                  |
| Created    | 08-Jan-2023                                                  |
| Status     | draft                                                  |

## Background 

- computer/code setup is not convinient in AiiDA
For the beginners and even for the experienced AiiDA user, setting up computers and codes is still a tidious mission.
If using the interactive mode, although it is good that options are prompt up and user can set for every options one by one carefully, it requires to go through all options even some are not necessary and time consuming for the similar setup that have shared options with other code/computer setup.
AiiDA provide the non-interactive mode to set up the computer/code from a config yaml file, which lower the burden for users who need to set up the computer/code next time. 
However, the non-interactive mode requires a yaml file as the input and not clear which options are mandatory and let alone it is not clear which default value will be used without checking the command help message or even the source code.
Let alone for the computer setup it is a two stage process, user need to set up the compture for attributes which are common information for the computer that are store in the database using `verdi computer setup`. 
Then running `verdi computer configuration <transport> <label>` to set up ...

- we have aiida-code-registry for the purpose that user can store the config files for future setup and for sharing

## Problems of current aiida-core-registry

- aiidalab-widgets-base using aiida-code-registry as database provide widget to setup computer/code but lack of flexibility for very detail parameters.
- lack of capability to export the config file to store for future setup and for sharing purpose.

## Goals and proposed Enhancement

- new subcommand `bytemplate` for `verdi code create bytemplate <entrypoint>` which read from j2 template and dynamically create options ask for inputs and create config file and pass to `verdi code create <entrypoint>`.
- Same concept can be used for computer setup and computer configuration as well. To induce the complexity, it better to have `verdi computer create` to replace `verdi computer setup` as well.

- In aiida-code-registry, users are encourage to upload the template for computer/code setup. 
- It also good to have a well designed web page that list all the template config files and user can search for the config files they need. It need to easy to copy and better to generate a url with only the raw template data that can directly pass to command for setup.

- verdi command to export the config files. Attampts are https://github.com/aiidateam/aiida-core/pull/5860 and https://github.com/aiidateam/aiida-core/pull/3616
- not only the config of one code/computer setup but all computer/code configs of a profile can be exported into a particular format that can be store in the aiida config folder. It can be then shared and for easy load the configs. The idea is bring up by ltailz in https://github.com/aiidateam/aiida-code-registry/pull/62.

## Roadmap of the implamentation



## Pros and Cons 

### Pros
* The public discussion of enhancement proposals lets the entire AiiDA community see what developments lie ahead
  and allows those interested to actively participate in shaping them
* AEPs provide basic guidance on how to "make a case" for an enhancement such that it can be seriously discussed
  before investing efforts in its implementation
* The corresponding pull requests provide a public record of the decision process in case questions arise later

### Cons
* Introduce new command for code/computer setup and coexist with old setup command may bring complicity to new user and not familiar for old user.
