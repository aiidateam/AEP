# Plugin testing toolchain

| AEP number | 001                                                          |
|------------|--------------------------------------------------------------|
| Title      | Plugin testing toolchain                |
| Authors    | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz)|
| Champions  | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz)|
| Type       | S - Standard Track                                           |
| Created    | 10-Sep-2019                                                  |
| Status     | active                                                       |

## Background 
Given that AiiDA has a number of software and service dependencies that can be met in different ways, suggesting an "officially supported" toolchain for testing AiiDA plugins would make the life of plugin developers easier.

Ideally, plugins adopting this toolchain could be tested with new versions of AiiDA automatically, and the result of this test could be displayed in the AiiDA plugin registry.
This would address one of the major current pain points for AiiDA users, namely: will plugin X work with AiiDA version Y?

## Proposed Enhancement 

We propose the following toolchain for testing AiiDA plugins:

 1. running tests inside a controlled Docker environment
 1. using [aiida-docker-stack](https://github.com/aiidateam/aiida-docker-stack) as a base image
 1. using a `Dockerfile` for any necessary modifications on top of aiida-docker-stack
 1. using pytest as the test runner

The goal of this proposal is to address the most pressing issues, reusing existing infrastructure as much as possible.
It also tries to strike a balance between the standardization necessary to enable automating testing,
without restricting the freedom of plugin developers too much.

In the following, we go into detail on each of these points.

### 1. Docker

It seems inevitable to choose a controlled environment for testing.
We could choose others, e.g. travis, azure pipelines, a particular ubuntu version, ... but with the AiiDA lab running on docker (or kubernetes, which again uses docker), docker seems the only sensible choice here.

### 2. Base image

The [aiida docker stack](https://github.com/aiidateam/aiida-docker-stack) is an image that contains AiiDA plus all necessary services, ready to go.

Image sizes:
 * aiida-docker-stack: [612MB](https://hub.docker.com/r/aiidateam/aiida-docker-stack/tags)
 * aiida-docker-base: [518 MB](https://hub.docker.com/r/aiidateam/aiida-docker-base/tags)
 * phusion-baseimage:0.11 : [65 MB](https://hub.docker.com/r/phusion/baseimage/tags)

The size of aiida-docker-base could perhaps still be reduced a bit (see [Dockerfile](https://hub.docker.com/r/aiidateam/aiida-docker-base/dockerfile)) but 612MB should already be acceptable.

### 3. Modifying the setup

If the only modification needed was installing the AiiDA plugin, this section would be trivial.

However, testing AiiDA plugins often requires not just `aiida-core` and the plugin, but also the simulation code the plugin is wrapping.
There are multiple ways to achieve this:

 * Download the source code and compile from scratch. This can take a significant amount of time (but the output could be cached).
 * Download a binary of the code (or a singularity container).
 * Use a mock executable distributed together with the plugin

The advantage of doing this inside a Docker file is that the fully built image can be used for testing


An example `Dockerfile`  can be found [here](https://github.com/aiidateam/aiida-cp2k/blob/develop/Dockerfile).
```docker
FROM aiidateam/aiida-docker-stack

# Install cp2k
RUN apt-get update && apt-get install -y --no-install-recommends  \
    cp2k

# Set HOME variable:
ENV HOME="/home/aiida"

# Install aiida-cp2k
COPY . ${HOME}/code/aiida-cp2k
RUN chown -R aiida:aiida ${HOME}/code

# Install AiiDA
USER aiida
ENV PATH="${HOME}/.local/bin:${PATH}"

# Install aiida-cp2k plugin and it's dependencies
WORKDIR ${HOME}/code/aiida-cp2k
RUN pip install --user .[pre-commit,test]

# Populate reentry cache for aiida user https://pypi.python.org/pypi/reentry/
RUN reentry scan

# Install the cp2k code
COPY .docker/opt/add-codes.sh /opt/
COPY .docker/my_init.d/add-codes.sh /etc/my_init.d/40_add-codes.sh

# Change workdir back to $HOME
WORKDIR ${HOME}

# Important to end as user root!
USER root

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]
```

## Pros and Cons 

### Pros

### Cons
