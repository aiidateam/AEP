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

For the beginners and even for the experienced AiiDA user, setting up computers and codes is still a tidious mission.
If using the interactive mode, although it is good that options are prompt up and user can set for every options one by one carefully, it requires to go through all options even some are not necessary and time consuming for the similar setup that have shared options with other code/computer setup.
AiiDA provide the non-interactive mode to set up the computer/code from a config yaml file, which lower the burden for users who need to set up the computer/code next time. 
However, the non-interactive mode requires a yaml file as the input and not clear which options are mandatory and let alone it is not clear which default value will be used without checking the command help message or even the source code.
Let alone for the computer setup it is a two stage process, user need to set up the compture for attributes which are common information for the computer that are store in the database using `verdi computer setup`. 
Then running `verdi computer configuration <transport> <label>` to set up information of computer that are specific to user or required to modified after the node store in the database.

The computer/code can be set up from a YAML file, and we provide repository [`aiida-code-registry`](https://github.com/aiidateam/aiida-code-registry) to store the YAML files for public computers and codes to share with others.
Need to mention that the interactive setup command can accept a URL of a remote YAML file for setup.
This makes it possible to not download/clone the `aiida-code-registry` repo to using the YAML to setup computer/code.

## Current problems

### Compture setup and configuration

It requires two steps to setup an runnable computer, by running `verdi computer setup` and then `verdi computer configuration`.
The design behind is to separate the computer related data into user-specific and user-agnostic parameters. 
The user can change the user-specific parameters even after the computer setup is run and the computer is set in the profile instead override database and break the provenance.
The issue comes from following aspects.

First, parameters are not well grouped such as `use_double_quotes` is set in the setup step but should go to the configure step since it only affect how job script is generated.
Second, it is not clear neither from command line prompt or from in the config file, which parameters are necessary to setup and which can be fine to use the default value in most cases.

Moreover, the computer setup/configure interface is limited for the parameters what is knewn and defined in advance in aiida-core. 
For parameters such as slurm partition, which is write in slurm job script to designate the partition to use or the slurm account parameters that even not used by all the slurm settings, those parameters can currently only set in the `prepend_text` of the computer setup, not allowed to be changed upon user.
But they are very user specific parameter.

In [aiidalab-widgets-base](https://github.com/aiidalab/aiidalab-widgets-base/blob/master/aiidalab_widgets_base/computational_resources.py), there is a `ComputationalResourceSetup` widget which used to set up the computer/code in AiiDAlab.
It uses the concept that the setup and configuration are separated and the SSH connection can be set afterwards or reset even after the computer is stored in the database.
But in the actual implementation, it has a dedicate ssh computer setup section for allowing user to change the SSH information (generating a new keypairs and upload, but keep the computer configuration unchanged) if they need to reset the SSH without setup the computer again.
It is not compatible with the design of computer setup/configuration.
The idealist goal is that with minial input of SSH options, the computer configuration API can be used to update the SSH connection information.

### aiida-code-registry

The `aiida-code-registry` is the repository for users upload and share the YAML files of computer/code setup. 
It is obvious that a github repository is not very easy to use for quick iteration of file upload and download and for visualize or even search for the configurations are needed. 
To using a configure file, user has to either open the file online by go into the folder or clone the repo and config computer/code from the local file.
This should be a mild issue since all needed is a more well designed web page that user can have a glimpse of all YAML files and even can search for one from browser. 

In terms of upload, GitHub repo has an advantage that the files can be easily reviewed before visible to the public and to be reuse. 
But who should review the config files? It is always necessary to review the config files? 
In most case, one remote machine is only accessible by a small group of people. 
Are they responsible for make sure the config file is valid to be used.
Is which level the test can be run for the config file?
In other aspect, the GitHub is not very friendly if user need to upload the new files. 
They have to open a pull request to make the change, which can be done from GitHub web interface, but need some trick to upload folders.

The next issue is how to easily get the YAML config file to upload to `aiida-code-repository` or simply just store locally for future use.
It must be a cli command to accomplish this trivial task which already mentioned in https://github.com/aiidateam/aiida-core/issues/3521 and partially addressed by https://github.com/aiidateam/aiida-core/pull/5860.

## Goals and proposed Enhancement

### computer/code export CLI commands

- verdi computer create as new interface replace the verdi setup.

### Setup computer/code from template type config files

- j2 template -> prompt for user inputs -> regular YAML -> computer/code create
- computer/code create support create from j2 template file.

### Registry page to show/upload new configures

- From start only maintain one file named with domain name for every domain in aiida-core-registry to store all information of computer/code setup. (TOML/YAML/json) 
- Upload the new entities can be done by add/change the file through GitHub interface. 
- This basically solve the issue for how to make user easily contribute the new config without much effort on designing web interface to upload and for reviewing.
- For the advanced user, it can be a bonus design if the folder can be download and store in the local `.aiida` folder and for setuping much easily with from reading the folder if it exist. The proof of concept see https://github.com/aiidateam/aiida-code-registry/pull/62. Not only the config of one code/computer setup but all computer/code configs of a profile can be exported into a particular format that can be store in the aiida config folder. It can be then shared and for easy load the configs. The idea is bring up by ltailz.

However, this move the effort to showing and for how to using the config. 
In current aiida-code-registry, the YAML file can be found from the repository and opened to be used for computer/code setup in AiiDA directly. 
If for each domain, there is one file for all setup, we need provide a way to parse these information back to template or YAML file so can be used.
A new and well designed code registry page is needed to make this possible.
It should looks the same as [AiiDA plugin registry](https://aiidateam.github.io/aiida-registry/) with extra functionalities that the config file can be parsed back from information given and can be a pure YAML/j2 page having a specific URL to be downloaded or for setup the code directly.
It can be very useful that the command for setup computer/code directly show in this page (toggle to hide/show) and user can copy and paste to setup.

- It also good to have a well designed web page that list all the template config files and user can search for the config files they need. It need to easy to copy and better to generate a url with only the raw template data that can directly pass to command for setup.

## Roadmap of the implamentation

- The first step would be to make it able to export the setup from database for both computer and code with the data stored in the database and for the computer configure data.
- Then I'll implement setup from template file.
- After the template system is matural, rearranging the `aiida-code-registry` to using the template/YAML mix config and cumulate all configure files into a TOML file for every domain.
- Design the web page to parse and show the YAML/j2 config file back in the new code registry page.

## Pros and Cons 

### Pros
* The public discussion of enhancement proposals lets the entire AiiDA community see what developments lie ahead
  and allows those interested to actively participate in shaping them
* AEPs provide basic guidance on how to "make a case" for an enhancement such that it can be seriously discussed
  before investing efforts in its implementation
* The corresponding pull requests provide a public record of the decision process in case questions arise later

### Cons
* Introduce new command for code/computer setup and coexist with old setup command may bring complicity to new user and not familiar for old user.
