# Plugin testing toolchain

| AEP number | 001                                                          |
|------------|--------------------------------------------------------------|
| Title      | Plugin testing toolchain                |
| Authors    | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz)|
| Champions  | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz), [Aliaksandr Yakutovich](mailto:aliaksandr.yakutovich@epfl.ch) (yakutovicha)|
| Type       | S - Standard Track                                           |
| Created    | 10-Sep-2019                                                  |
| Status     | submitted                                                    |

## Background 
Given that AiiDA has a number of software and service dependencies that can be met in different ways, suggesting an "officially supported" toolchain for testing AiiDA plugins would make the life of plugin developers easier.

This comprises two components:
 1. Suggestions on how to test plugins locally (and manually).
 1. Suggestions on how to test plugins on CI platforms, ideally enabling automatic testing of the plugin when a new version of AiiDA is released.

1. Would help to address an important question of AiiDA users, namely: will plugin X work with AiiDA version Y?

## Proposed Enhancement 

We propose the following toolchain for testing AiiDA plugins:

 1. use pytest as the test runner, together with the AiiDA pytest fixtures
 1. run continuous integration tests inside a controlled Docker environment that
    * uses [aiida-docker-stack](https://github.com/aiidateam/aiida-docker-stack) as a base image
    * uses a `Dockerfile` for any necessary modifications on top of aiida-docker-stack

The goal of this proposal is to address the most pressing issues, reusing existing infrastructure as much as possible.
It introduces the minimal standardization necessary to enable automating testing.

In the following, we go into detail on each of these points.

### 0. dependency specification

We should suggest a standard name for the `extra` that installs dependencies necessary for testing.

`aiida-core` uses `testing`, so let's stick with this, e.g.  `pip install aiida-cp2k[testing]`.

### 1. pytest

We've had good experiences with pytest so far, and a survey in 2018 showed that most externally developed plugins were using pytest anyhow. 
The [AiiDA pytest fixtures](https://github.com/aiidateam/aiida-core/pull/3319) make it really easy to set up a code for integration tests.

A usual test setup would be as follows:

`conftest.py`:
```python
import pytest
pytest_plugins = ['aiida.manage.tests.pytest_fixtures']

# ... custom fixtures
```

`test_1.py`:
```python
def test_1(aiida_code):
    qe_code = aiida_code('pw.x', 'quantumespresso.pw')
    # use code ...
```

Note: When plugins include "runnable examples", those can also be included in the test suite:

```python
import click 

def test_example(aiida_code):
    # encapsulate example inside this function
    qe_code = aiida_code('pw.x', 'quantumespresso.pw')
    # use code ...

@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Run simple DFT calculation through a workchain"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)

     test_example(code)

if __name__ == '__main__':
    cli()   # pylint: disable=no-value-for-parameter
```

### 2. Docker

It seems inevitable to provide a controlled environment for testing that easily can be replicated on a wide range of platforms.
We could choose others, e.g. travis, azure pipelines, a particular ubuntu version, ... but with the AiiDA lab running on docker (or kubernetes, which again uses docker), docker seems the only sensible choice here.

### 3. Base image

The [aiida docker stack](https://github.com/aiidateam/aiida-docker-stack) is an image that contains AiiDA plus all necessary services, ready to go.

Image sizes:
 * aiida-docker-stack: [612MB](https://hub.docker.com/r/aiidateam/aiida-docker-stack/tags)
 * aiida-docker-base: [518 MB](https://hub.docker.com/r/aiidateam/aiida-docker-base/tags)
 * phusion-baseimage:0.11 : [65 MB](https://hub.docker.com/r/phusion/baseimage/tags)

The size of aiida-docker-base could perhaps still be reduced a bit (see [Dockerfile](https://hub.docker.com/r/aiidateam/aiida-docker-base/dockerfile)) but 612MB should already be acceptable.

### 4. Modifying the setup

If the only modification needed was installing the AiiDA plugin, this section would be trivial.

However, testing AiiDA plugins often requires not just `aiida-core` and the plugin, but also the simulation code the plugin is wrapping.
There are multiple ways to achieve this:

 * Download the source code and compile from scratch. This can take a significant amount of time (but the output could be cached).
 * Download a binary of the code (or a singularity container).
 * Use a mock executable distributed together with the plugin

One way of doing this is to require plugin developers to put a `Dockerfile` into the root folder of their plugin (or some other standardized location).

A `Dockerfile` could look as follows (see [here](https://github.com/aiidateam/aiida-cp2k/blob/develop/Dockerfile) for earlier attempts):
```docker
# You can select the base image tag when building this image:
# docker build -t aiida-cp2k-docker-stack --build-arg AIIDA_DOCKER_STACK_TAG=1.0.0b6 .
ARG AIIDA_DOCKER_STACK_TAG=latest
FROM aiidateam/aiida-docker-stack:$AIIDA_DOCKER_STACK_TAG

# Install cp2k
RUN apt-get update && apt-get install -y --no-install-recommends  \
    cp2k

# Set HOME variable:
ENV HOME="/home/aiida"

# Copy aiida-cp2k
RUN mkdir -p ${HOME}/plugin
RUN chown -R aiida:aiida ${HOME}/plugin
WORKDIR ${HOME}/plugin

# Important to end as user root!
USER root

# Use phusion baseimage-docker's init system.
CMD ["/sbin/my_init"]
```

The tests would be run by executing something like
```
docker run -v .:/home/aiida/plugin aiida-cp2k-docker-stack -t test-container
docker exec --user aiida test-container pip install --user -e .[pre-commit,testing]
docker exec --user aiida test-container reentry scan
docker exec --user aiida test-container py.test --cov aiida_cp2k --cov-append .
```

## Pros and Cons 

### Pros
 * the AiiDA pytest fixtures make testing full integration runs really easy
 * the docker approach introduces a standardized test environment that can be used on any CI platform (travis, azure pipelines, github actions, ...) as well as locally

### Cons
 * no caching of the modifications on top of the aiida-docker-stack; these would be rebuilt for every test run
 * this adds some boilerplate code inside the `Dockerfile`
 * from the AiiDA registry perspective, there is no way to enforce the *actual* environment used for testing (e.g. plugins could inadvertedly install a different version of aiida-core). one could check this by running a `pip freeze` first, though.

## Open questions
 * are there viable alternatives to using a Dockerfile for performing the "on top" modifications?
