# AEP 009: Improved Docker images

| AEP number | 009                                                             |
|------------|-----------------------------------------------------------------|
| Title      | Improved Docker images                                          |
| Authors    | [Jusong Yu](mailto:jusong.yeu@gmail.com) (unkcpz)               |
| Champions  | [Jusong Yu](mailto:jusong.yeu@gmail.com) (unkcpz)               |
| Type       | S - Standard                                                    |
| Created    | 16-July-2023                                                    |
| Status     | implemented                                                     |


## Background and problem description

AiiDA provides and maintains a Docker image to offer a clean and isolated environment that is easy to setup for users and developers.
However, the the current Docker stack has a number of problems and limitations:
- The `aiidateam/aiida-prerequisites` image, on which it is based, is not maintained and updated regularly.
  (Partly because the `aiidalab-docker-stack` replaced `aiida-prerequisites` with `jupyter/minimal-notebook` as its base image.)
- The image is not able to run on `linux/arm64` architecture, therefore not able to run on Apple M1 chip which is now widely is use by the community.
- The RabbitMQ and PostgreSQL services are not properly installed and configured inside the container, causing the user to have to start them manually.
As a result, it is not straightforward to create a container and start using AiiDA, as evidenced by the [length of the documentation](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/run_docker.html#intro-get-started-docker).

One of the main reasons for providing a Docker image with `aiida-core` was to provide a base image for the `aiidalab-docker-stack` to build on.
However, thanks to the fantastic work by @csadorf, the Docker stack of the `aiidalab` organization is now built on top of `jupyter/minimal-notebook` instead of `aiidateam/aiida-core`.
The [`aiidalab-docker-stack`](https://github.com/aiidalab/aiidalab-docker-stack) comes in four variants:

- `base` – A minimal image that comes with AiiDA pre-installed and an AiiDA profile set up.
- `base-with-services` – Like `base`, but the services required by AiiDA (PostgreSQL and RabbitMQ) are installed in the container and automatically launched on startup.
- `lab` – Like `base`, but uses the AiiDAlab home app as the primary interface (the standard JupyterLab interface is also available).
- `full-stack` – Our most comprehensive image, like `lab`, but also comes with services pre-installed and launched.

Due to the switch to `jupyter/minimal-notebook` as the base image, the `aiida-prerequisites` image has become superfluous.
And since the `aiidalab` organization no longer needs `aiida-prerequisites`, they no longer have a reason to maintain it.
This poses a problem for the `aiidateam/aiida-core` image, which currently uses `aiida-prerequisites` as a base, and therefore effectively is also no longer maintained.
However, there is still a need for a maintained Docker image with a basic AiiDA setup, but the images of the `aiidalabe-dockers-stack` are not suitable:

- The `lab` and `full-stack` images are mostly designed to provide AiiDAlab, which is not necessary for a simple AiiDA setup.
- The `base` and `base-with-services`, in contrast, only provides AiiDA, however, the use `jupyter/minimal-notebook` as a base image has multiple downsides:
  * The `jupyter/minimal-notebook` starts a jupyter notebook as the main service of the container, and maps its corresponding port
  * A known issue from using [jupyter/minimal-notebook](https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html#jupyter-minimal-notebook) as the base image, the system user name default set to `jovyan` and can only be changed by running container as `root`.
    If the container starts as the `root` user, it is hard to set start-up scripts to configure AiiDA for the system user of the container.
    In addition, `root` will be the default user to login, which increases the complexity to integrate vscode with the container.
  * It is not possible to easily keep the latest `aiida-core` version.
    When a new version of `aiida-core` is released, or new fixes are pushed to `main`, users will have to wait for `aiidalab-docker-stack` uploads a new build that includes the new features and fixes.
- It can be confusing to have to use an image from the `aiidalab` organization on Docker hub, instead of `aiidateam`.
  Although the docker hub namespaces `aiidateam` and `aiidalab` are all managed by us, we still try to not confuse and mix up the images with these two different namespaces.
- The services required by AiiDA are not automatically started and stopped in a graceful manner on container startup and shutdown.
  The services are configured and started inside the container using `before-notebook.d` and `after-notebook.d` scripts.
  However, the services are not started and stopped gracefully, where the container will exit with an error if the services are not started properly and the services are not stopped properly when the container is stopped.

## Goals

1. Archive `aiidateam/aiida-prerequisites`

2. Provide Docker images with the `aiida-core` repository, which contain a minimal but functional AiiDA setup that is deployed to the `aiidateam` Docker hub namespace.

3. Images support both `linux/amd64` and `linux/arm64`, and include basic system tools: `vim`, `git`, `conda`/`mamba` for quick development environment setup.

4. Docker run command will start the container and provide a ready to use AiiDA environment for users to use.


## Proposed enhancement

### Provide new Docker images

Two new Docker images will be maintained within the `aiida-core` repository and pushed to the `aiidateam` docker/ghcr hub namespace:

- `aiidateam/aiida-core-base`: Image contains just `aiida-core` installed, which can be used with independent RabbitMQ & PostgreSQL services, e.g., through `docker-compose`.
- `aiidateam/aiida-core-with-services`: Image built on top of `aiida-core-base` that includes the automatic and graceful starting and stopping of RabbitMQ & PostgreSQL services.

### Hide `base` and `base-with-services` images from docker hub and ghcr

These images are used as base images for other images and are not intended for use for regular users.
The main purposes of these images included but were not limited to:
- As a base image for the aiidalab docker stack that is able to be deployed to the cloud for tutorial or testing, refer to [aiidalab-on-azure](https://github.com/aiidalab/aiidalab-on-azure).
- For quick and clean development environment build and launch.
- As the container for codespace environment for vscode remote development.
- As the base image for further service integration, such as `aiidalab-docker-stack` and `qe-input-generator`.

### Use `ubuntu` as base image

Using `ubuntu` as the base image, instead of `jupyter/minimal-notebook`, solves the problems of having the useless jupyter notebook service active and the fixing of the system user name.
It is worthwhile to mention that the `phusion/baseimage` was used as the base image for `aiidateam/aiida-core` (from `aiidateam/aiida-prerequisite`) before.
The reason to use `phusion/baseimage` was to have an `init` system inside the container which can help to start and stop the services gracefully.
Moreover, the `phusion/baseimage` was the image that solved the [zombie process problem](https://blog.phusion.nl/2015/01/20/docker-and-the-pid-1-zombie-reaping-problem/) of the `ubuntu` base image.
The zombie process problem of `ubuntu` base image can also be solved by using `s6-overlay` as the system service manager (See section [s6-overly](#use-s6-overlay-as-system-service-manager) for details).

### Use `s6-overlay` as system service manager

[s6-overlay](https://github.com/just-containers/s6-overlay) is an easy-to-install (just extract a tarball or two!) set of scripts and utilities allowing you to use existing Docker images while using s6 as a pid 1 for your container and process supervisor for your services.
It can:
- be used on top of any Docker image
- provide users with a turnkey s6 installation that will give them a stable pid 1, a fast and orderly init sequence and shutdown sequence, and the power of process supervision and automatically rotated logs.

### Have a runner for arm64 CI build test

A runner for an arm64 CI test was registered on `buildjet.io`.
To avoid the runner being used unnessary, the arm64 CI test will only be triggered when the trigger comes from the main `aiidateam/aiida-core` repo.

### Container image upload to ghcr.io and docker.io

The container images are uploaded to both docker hub and `ghcr.io`.
`ghcr.io` is used also as the test image registry, which means the PR will build the image and upload it to `ghcr.io` for testing.
Name of the PR tag will be `pr-<PR number>`, the image will be uploaded to `ghcr.io` with the tag `pr-<PR number>`.
The image will be uploaded to docker hub only when the PR is merged to the main branch or the tag `v*` is pushed to the main branch.
The tags of the image of release image will be `vX.X.X` and `X.X.X` as aiida-core version, along with `postgresql-X.X.X` and `python-X.X.X` as the version of PostgreSQL and Python.

## Design discussion

### Disadvantages

The main disadvantage of this new docker stack is that `s6` requires many files (some even empty) in the `.docker` folder, which may be confusing for future maintenance.

### What tools/packages should be included/pre-installed in the image

The following system requirements will be included in the images:

- [x] vim
- [x] git
- [x] ssh
- [x] conda/mamba
- [ ] pytest
- [x] psql (in `aiida-core-with-services`)

The reasoning here is that system requirements that are commonly used should come pre-installed.
This because installing them might not be straight forward as they require root permissions.
Other dependencies, such as Python dependencies, are left up to the user to install as anyway they will have to install specific AiiDA plugins for their purposes.
These dependencies can easily be installed in user space using conda (which comes preinstalled) and `pip`.

### RabbitMQ version

There is a notorius incompatibility of `aiida-core` with RabbitMQ versions newer than `3.8.15` (See the [problem of message timeout in queue](https://github.com/aiidateam/aiida-core/wiki/RabbitMQ-version-to-use)).
I chose to install the latest version of RabbitMQ nevertheless but counteract it by setting the `consumer_timeout` config parameter to 1000 hours to avoid the problem.
The reason is that install the RabbitMQ from binary package has to [compatible with the system erlang version](https://www.rabbitmq.com/which-erlang.html) which will break the `< 3.8.15` version of RabbitMQ.
It is also not possible to install RabbitMQ from conda-forge because the arm64 version of RabbitMQ is not available on conda-forge.

### How to start the services

`s6-overlay` supports two ways to start services:
- `oneshot`: for services that only need to be started once
- `longrun`: for services that need to be started and kept running.

RabbitMQ is started as a `longrun` service with `rabbitmq-server` without the `-d` option, which means the service will be started and kept running in the background and restarted when the service is stopped.

PostgreSQL is started as a `oneshot` service with `pg_ctl -D /var/lib/postgresql/data start` which means the service will be started once and stopped when the container is stopped.
This is mostly because I don't know how to start PostgreSQL as a `longrun` service.

The AiiDA daemon is started as a `oneshot` service with `verdi daemon start` and is stopped with `verdi daemon stop`.
The reason is that after the container is started with `docker run -it <image> bash`, the user will see an interactive bash shell with an AiiDA daemon that is running.

`s6-overlay` supports starting services in a specific order.
The dependencies of the services are depicted below (nested services will be started before the parent service):

```
- aiida-daemon-start (main)
    - aiida-prepare
        - postgresql
            - postgresql-init
        - postgresql-prepare (check if postgresql is ready)

- rabbitmq (independent)
    - rabbitmq-init
```
