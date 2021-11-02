# AiiDA Enhancement Proposal (AEP) Guidelines

| AEP number | 008                                                          |
|------------|--------------------------------------------------------------|
| Title      | Built-in support for codes encapsulated in containers        |
| Authors    | [Jusong Yu](mailto:jusong.yu@epfl.ch) (unkcpz)                    |
| Champions  |                                                              |
| Type       | S - Standard Track AEP                                                  |
| Created    | 02-Nov-2021                                                  |
| Status     | submitted                                                       |

## Background 

In order to keep the provenance of the calculation, AiiDA will record the details of codes that running the calculation.
If the calculation is performed by an external code (e.g. a binary on a remote high-performance computer(HPC)), the code is store as a node with lots of code related information.

The code is always run on some specific computers.
However, the remote computers usually have different architecture, different authenticator method, different job managerment etc. 
Which lead to for every code run the same version of simulation software (for example, quantum-espresso 6.7), it is still required to dedicately configure code for every computer with remote computer related settings. 

As for now, codes in AiiDA are represented as link to the existiong executable on a remote computer.
This require to store the full path to the remote executable in the database.
It makes code setting process more delicate to typos and not extremly easy to do, since user need to login to the remote machine to check the full absolute path of the code.
As well, it require that the codes in the remote computer are properly installed.
Above two factors combined will not benifit the provenance keeping in a long term. 
Since nobody can promise that the codes on the remote machine never migrate to new folder and always working properly after recompiling by the HPC administrator.

The last years have seen an increasing adoption of containers (using technologies such as docker, singularity, shifter or sarus. In this proposal I call them virtual tech(s)), including in the HPC domain, where executables are no longer compiled on the target machine but are compiled once and run in a portable, encapsulated environment. 
The encapsulation of the full run-time environment, as well as the availability of global container registries, constitute a major step forward in terms of reproducibility - storing the identifier of the container in the AiiDA graph makes it possible to directly re-run existing workflows without access to the computer where it was originally executed.
Meanwhile, the container code are more non-susceptible to the actual implementation and modification of the remote computer, which make the code setting more easily with less metadata needed.

## Proposed Enhancement 

Above the current computer setup, add an extra virtual technologies configuration layer to set the information on how to call and use the virtual technology on the remote computer.
The container code setup will be extremly consiced to only the identity of the image and path to the executable binary are mandatory.
The codes will not bind to any specific computer anymore, but can setup before any paticlar computer is setting.
So that the code can be run on different computers with only one setup, only if the computers have the compatible virtual technologies provided.

## Detailed Explanation

### User case

```python
! verdi computer setup -L eiger ...
! verdi computer configure container-setting ... <COMPUTER-LABAL>

! verdi code setup -L pw-6.7 --imageID=<> --executable-path-in-container=<> --PMI2=<>

code1 = load_code('pw-6.7-container@sarus@eiger')

! verdi computer configure container-setting ... <COMPUTER-LABAL>

code2 = load_code('pw-6.7-container@sigularity@eiger')
```

### Desired functionality

- The settings (the path and metadata) of how to run the virtual tech can be configured as an extra setting option for the computer with `verdi computer configure` after the computer setup. 
- Besides the current code entity for `local` and `remote`, there is a new `container` code entity.
It should store the image identity of the container code, and the path to run the binary code inside the container with some metadata about MPI support. 
- For the new `container` code entity, the `_aiidasubmit.sh` script prepared will slightly different from the previous bash scripts created by `local` and `remote` entities.

A typical submit script with slurm is like this:

```sh
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

sarus run --mount=type=bind,source=/scratch/e1000/jyu/test/aou/u342/ou,destination=/scratch -w /scratch marvelnccr/quantum-mobile:21.05.1 mpirun -n 4 pw.x -in pw.in
```

### Desired choices

- After checking the methods of `Code` class, I prefer to have a subclass of `Code` for this new `container` entity rather than parallel it with `local` and `remote`. Since there are not too little imcompatible with `local` and `remote`, especially the way to call it (`<code>@<virtual-tech>@<computer>` with two `@`) is a big difference.

## Problems encountered

-  If the virtual tech are setting with `verdi computer configure`, whether the settings store in the database with computer and unchangable, or it can be changed as ssh/local configuration that can be modified even after the computer is stored in DB and used for certain computation?
- In order to bind the host directories to the container, the path of inputs files (where in the remote computer the `_aiidasubmit.sh` and `aiida.in` locate) need to be write to `_aiidasubmit.sh` and submit with job manerger. 
However, we can not use the envirenment variable `$PWD` in the script since now we use quote for all the options in the script, the enviroument variable will not be translated if it is inside the quotes. 
Therefore, the we need to write the absolute path of remote folder in to the `_aiidasubmit.sh`.

## Pros and Cons 

### Pros

- There is no need to install or compile simulation code on the remote machine, only if it provide one of a virtual tech.
- The code setup is decoupled from computer setup, which means one setting of code can run the code on different remote machine.
- The provenance is more guaranteed since the virtual images are much more static than the binary compiled.
- (? marketplace view)This makes providing a bare metal (only OS, job manager and one virtual tech) HPC for aiidalab as 3rd party HPC or CPU cycle services for integration possible.

### Cons

- There are even one more step to configure computer with the virtual tech.
- The way to call the code is more complex.