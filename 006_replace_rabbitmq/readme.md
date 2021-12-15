# Remove the dependence on RabbitMQ

| AEP number | 000                                                          |
|------------|--------------------------------------------------------------|
| Title      | Remove the dependence on RabbitMQ                            |
| Authors    | [Martin Uhrin](mailto:martin.uhrin@epfl.ch) (muhrin), [Chris J. Sewell](mailto:christopher.sewell@epfl.ch) (chrisjsewell)|
| Champions  | [Martin Uhrin](mailto:martin.uhrin@epfl.ch) (muhrin), [Chris J. Sewell](mailto:christopher.sewell@epfl.ch) (chrisjsewell)|
| Type       | S - Standard Track AEP                                       |
| Created    | 09-Dec-2021                                                  |
| Status     | submitted                                                    |

## Background

Currently AiiDA uses RabbitMQ as the communication backbone for the daemon.  RabbitMQ is used to queue up tasks, send action messages (asking a worker to pause/play/kill a process) and to send broadcasts informing any listeners of a state change that occurred in a process (e.g. a parent AiiDA process can listen for the termination of its child).

While providing some useful features and functionalities, the use of RabbitMQ comes with a few drawbacks and problems:
1.  Setting up AiiDA is made more complicated as an OS level service needs to be installed.
2.  There is no API to introspect RabbitMQ queues to determine what is and what isn't being worked on.
3.  Desynchronisation between the database state sometimes happens (e.g. a process is still in a non-terminal state but there is no corresponding RabbitMQ message queued, and therefore the process will never continue).
4.  RabbitMQ is [making changes](https://github.com/rabbitmq/rabbitmq-server/pull/2990) that will see tasks timed out within 30 minutes.  This is not controllable from user space and, what's more, it has been [made clear](https://github.com/rabbitmq/rabbitmq-server/discussions/3345) that long-running tasks are not the intended use case for RabbitMQ.

## Proposed Enhancement 
This AEP proposes to drop RabbitMQ replacing it by a suitable stand in that does not rely on an external service but retains the core properties (e.g. reliability, responsiveness, scalability, etc).

## Detailed Explanation 

For now this AEP does not propose a concrete alternative but rather fleshes out the requirements which will inform the choice/implementation of a RabbitMQ replacement.

### Original requirements

The design of the current (RMQ based) system was designed to meet the following requirements:
1. The messaging system should be able to handle three types of communication:
   1. Task queues (e.g. for a client to submit a process to be run by a worker)
   2. Remote Procedure Calls (e.g. asking a process to pause/play/kill)
   3. Broadcasts (e.g. a parent listening for the termination of a child)
2. An AiiDA process should only ever be ran by one worker at a time
3. An error can lead to an AiiDA process never running but should not lead to the process being executed by multiple workers simultaneously ([elaboration](#requirement-3))
4. The messaging system should be able to handle both long running tasks (days) and many short running tasks (seconds), some of which may be dependent, without unnecessary delays (at most seconds) ([elaboration](#requirement-4))
5. The messaging system should not lead to CPU load when nothing is happening (e.g. as a result of frequent polling)
6. The daemon running processes and the user submitting them should be able to be on separate machines with communication handled by standard protocols (e.g. TCP/IP)
7. The memory requirements of the system (both RAM and disk) should not grow over time beyond that which is proportionate to the number of processes actively running (i.e. messages referencing terminated or deleted process should be guaranteed to be removed in a timely manner)
8. It should be possible to dynamically scale the number of workers to accommodate an increase or decrease in the load on the daemon and for the user to control the permitted load on their machine.


### Changes to requirements

It is not clear that if need requirement 6.  Currently, it is not possible to run a daemon on a separate machine from the AiiDA database, principally because the repository assumes that the files are stored on the machine where the AiiDA API calls are being made.  This may be possible if an object store backend (e.g. S3) were to be implemented but it's not clear that this will ever be done as the current model of one AiiDA instance per user is prevalent.

## Pros and Cons 

Pros and cons of dropping RMQ:

### Pros
* Installing AiiDA would become simpler, not requiring the installation of an OS service
* Monitoring which processes are queued or actively running would be possible
* Depending on the implementation, load-balancing could be greatly simplified (doing away with the need to tune number of worker _and_ slots per worker)

### Cons
* We may need to develop some in-house code to replace RMQ
* Any new system will need to be thoroughly tested to ensure that the requirements are met.  This will be challenging for rare failure modes and situations that require large amounts of processes to be submitted/running.


## Supplemental Information

### Requirements elaborations

In order to keep the requirements succinct and quick to read for someone new coming to this AEP I will use this section to give more details where needed.

#### Requirement 3

In order to deal with possible race conditions, any concurrent system must make a choice between one of two strategies. In such systems one can only guarantee one or other of the following:

1. A task will run at least once, but possibly more times. This is the most appropriate choice for systems that have tasks that are idempotent and where the resources consumed by a task not a concern. Clearly, this choice is not a good fit for AiiDA.
2. A task will run zero or one time. This is pretty much the only choice that makes sense for AiiDA.

While adopting strategy 2 AiiDA should make it as easy as possible for a user to see and relaunched tasks that failed to execute at all.


#### Requirement 4

The need to be able to support long and short duration jobs efficiently creates a tension, particularly with regards to requirement 5.  Essentially, a polling based solution would likely end up using a non-trivial amount of CPU if it were tuned to support very short jobs with many dependencies (e.g. [CIF cleaning workflows]((https://github.com/chrisjsewell/aiida-process-coordinator/discussions/4#discussioncomment-1296748)) of Sebastiaan).  RabbitMQ and other message brokers, get around this using some kernel level socket event hooks,effectively allowing them to eliminate polling and achieve realtime responsiveness.