# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | 008                                                          |
|------------|--------------------------------------------------------------|
| Title      | Built-in support for codes encapsulated in containers        |
| Authors    | [Jusong Yu](mailto:jusong.yu@epfl.ch) (unkcpz)               |
| Champions  |                                                              |
| Type       | S - Standard Track AEP                                       |
| Created    | 02-Nov-2021                                                  |
| Status     | submitted                                                    |

## Background 

In order to keep the provenance of the calculation, AiiDA will record the details of codes that running the calculation.
If the calculation is performed by an external code (e.g. a binary on a remote high-performance computer(HPC)), the code is store as a node with lots of code related information.

The code is always run on some specific computers.
However, the remote computers usually have different architecture, different authenticator method, different job managerment etc. 
Therefore even if the codes run the same version of simulation software (for example, quantum-espresso 6.7), it is still required to dedicately configure code for every different remote computers with devergence settings. 

As for now, codes in AiiDA are represented as link to the existiong executable on a remote computer.
This require to store the full path to the remote executable in the database.
It makes code setting process more delicate to typos which are not easy to be cached locally and not extremly easy to setup, since user need to login to the remote machine to check the full absolute path of the code.
As well, it require that the codes in the remote computer are properly installed.
Above two factors combined will not benifit the provenance keeping in a long term. 
Since nobody can promise that the codes on the remote machine never migrate to new folder and always working properly after recompiling by the HPC administrator.

The last years have seen an increasing adoption of containers (using container technologies such as docker, singularity, shifter or sarus.), including in the HPC domain, where executables are no longer compiled on the target machine but are compiled once and run in a portable, encapsulated environment. 
The encapsulation of the full run-time environment, as well as the availability of global container registries, constitute a major step forward in terms of reproducibility - storing the identifier of the container in the AiiDA graph makes it possible to directly re-run existing workflows without access to the computer where it was originally executed.
Meanwhile, the container code are more non-susceptible to the actual implementation and modification of the remote computer, which make the code setting more easily with less metadata needed.

## Proposed Enhancement 

Above the current computer setup, add an extra container techonologies configuration layer to set the information on how to call and use the virtual technology on the remote computer.
The container code setup will be extremly consiced to only the identity of the image and path to the executable binary are mandatory.
The codes will not bind to any specific computer anymore, but can setup before any paticlar computer is setting.
So that the container codes are able to run on different computers with only one setup, only if the computers have the compatible virtual technologies provided.

## Open Questions

- Do we need to considered another container techonology (besides `SARUS`) when preparing the draft PR?
- Do we need to abstract a container class dedicate for the container technologies setup?
- Store with computer setting or not? Immutable or not?
- Do we (pmi2 compatible) or cscs side (cscs native compatible) maintain a group of images for different simulation codes with optimized high performance? What about the software and libraries with license?
- Do we always use absolute path for the executables in the container or use the container entry point?
- Where to set the [MPI type](https://slurm.schedmd.com/mpi_guide.html) environment variable?
- Pull the images for user or let the user do it by themself?

## Detailed Explanation

### User case

An typical example of slurm job script for running container code in CSCS Eiger:

```bash
#!/bin/bash -l
#SBATCH --job-name="job_name"
#SBATCH --account="mr0"
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=1
#SBATCH --partition=normal
#SBATCH --constraint=mc

#SBATCH --mpi=pmix

sarus pull marvelnccr/quantum-mobile:21.05.1
sarus run --mount=type=bind,source=$PWD,destination=/scratch --workdir /scratch marvelnccr/quantum-mobile:21.05.1 pw.x -in pw.in
```

The `verdi` command and python code to setup and load to run the code.
```python
! verdi computer setup -L eiger ...
! verdi computer container setup ... (TBD) # OR 
! verdi computer configure container-setting ... <COMPUTER-LABAL> # ?

! verdi code setup -L pw-6.7 --imageID=<> --executable-path-in-container=<> --mpi=pmix

code1 = load_code('pw-6.7-cc@sarus@eiger')

! verdi computer configure container-setting ... <COMPUTER-LABAL>

code2 = load_code('pw-6.7-cc@sigularity@eiger')
```

### Desired functionality

- The settings (the path and metadata) of how to run the virtual tech can be configured as an extra setting option for the computer with `verdi computer configure` after the computer setup. 
- Besides the current code entity for `local` and `remote`, there is a new `container` code entity.
It should store the image identity of the container code, and the path to run the binary code inside the container with some metadata about MPI support. 
- For the new `container` code entity, the `_aiidasubmit.sh` script prepared will slightly different from the previous bash scripts created by `local` and `remote` entities.

### Desired choices

- After checking the methods of `Code` class, I prefer to have a subclass of `Code` for this new `container` entity rather than parallel it with `local` and `remote`. Since there are not too little imcompatible with `local` and `remote`, especially the way to call it (`<code>@<virtual-tech>@<computer>` with two `@`) is a big difference.

### Implementation

(?) First, a containter class is created to store the container specific information in the data.
This class is very similar to the current code class for remote codes.
The container will be set to bind to a specific remote computer.

Then, a new class for container code is required to store the container code.
It should not have parameters to bind to the particular remote computer.
To running the code, the command can be very simple with only image id and needed executable options provided.

Redesign of the computer and code setup command line interface in order to set container codes.

## Problems encountered

### How to store the container technology infomation in the database

If the virtual tech are setting with `verdi computer configure`, whether the settings store in the database with computer and unchangable, or it can be changed as ssh/local configuration that can be modified even after the computer is stored in DB and used for certain computation?

### Represent bind volume path in job script  

In order to bind the host directories to the container, the path of inputs files (where in the remote computer the `_aiidasubmit.sh` and `aiida.in` locate) need to be write to `_aiidasubmit.sh` and submit with job manerger. 
However, we can not use the envirenment variable `$PWD` in the script since now we use quote for all the options in the script, the enviroument variable will not be translated if it is inside the quotes. 
Therefore, there are two options for this issue but both need to influence the current structure of job script. 
- Using the absolute path for the bind path of remote host machine. 
The problem is that the job script is generated in the local machine where the aiida daemon running before the remote path created.
- Deprecating the use of quote for every parameters of the command in the job script. 

## Pros and Cons 

### Pros

- There is no need to install or compile simulation code on the remote machine, only if it provide one of a container code.
- The code setup is decoupled from computer setup, which means one setting of code can run the code on different remote machine.
- The provenance is more guaranteed since the images are much more static than the binary compiled.
<!-- - (? marketplace view)This makes providing a bare metal (only with OS, job manager and one of container technology installed) HPC for applications run simulation codes as 3rd party HPC or CPU cycle services for integration possible. -->

### Cons

- There are one more step to configure computer with the container technologies.
- The way to call the code is way more complex.

https://slurm.schedmd.com/mpi_guide.html