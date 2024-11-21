# AEP 010: Replace RabbitMQ 

| AEP number | 010                                                          |
|------------|--------------------------------------------------------------|
| Title      | Replace RabbitMQ                                             |
| Authors    | [Jusong Yu](mailto:jusong.d.yu@gmail.com) (unkcpz)           |
| Champions  | [Jusong Yu](mailto:jusong.d.yu@gmail.com) (unkcpz)           |
| Type       | S - Standard Track AEP                                       |
| Created    | 08-11-2024                                                   |
| Status     | draft                                                        |

## Background 

The AEP is an extension of concrete implementation design to what described in [AEP #PR30: Replace RabbitMQ](https://github.com/aiidateam/AEP/pull/30).
The two AEP can be merged after.

This AEP is copied from the design note of the tool for replacing the RabbitMQ + kiwipy.
I call this tool [`tatzelwurm`](https://github.com/unkcpz/tatzelwurm) in this documentation.

### -- start here --
The initial goal of the tool is to replace the use of RabbitMQ as message broker in [AiiDA](https://aiida.net).
The tool however can be more generic as a lightweight task broker that handle the task distribution and task state persistent store with tasks are workflows orchestrated by different programming languages.

> ![Note] 
> - "worker" and "runner" are used interchangeably.
> - most of time "coordinator" is the "server".
> - sometimes the "process", "mission" and "task" is used interchangeably.

### When we say replace RMQ what we are talking about?

When we say replace RMQ, we are talking about remove `kiwipy` as the communicator in AiiDA, it is a strong denpendency of AiiDA through the [`plumpy`](https://github.com/aiidateam/plumpy). 
The `plumpy` is the real internal engine implementation on top of which the `aiida-core` extent the `Process` to be `ProcessFunction`, `CalcJob` and `WorkChain`. 
Meanwhile, the `plumpy` also define the base interfaces on how to persistent store the `Process` state so that can be recovered from checkpoints. 
The `plumpy` need `kiwipy` to provide interface to talk to the RabbitMQ service to manage the process running on the specific event loop of a worker's interpretor (the event loop is then under the management of `aiida-core` inside a daemon runner). 

The connections between `plumpy` and `kiwipy` is actually not too many as I originally thought, the `plumpy` treat `kiwipy` as a so called "Communicator".
The most important interface is `add_task_subscriber` which register an async function (coroutine) that upon consuming message from RMQ the worker side decide how to deal with the `Process`. 
Two parts use this `add_task_subscriber` interface.

- The `Process` can be `launch` or `continue` by the `ProcessLauncher` registered with its `__call__` (queue up tasks). 
- The `Process` itself when initilized, will registered the `message_reciever` to listen to queue when there are action signals to `play`, `pause` or `kill` the `Process`.

The reason why we should not rely on 3rd-part message broker is not only that the extra service is hard to deploy, but also we use it in an inproper way.
I will show more detail in the legacy architecture description below.
RabbitMQ as a message broker is design for large distribute system runs for microservices and usually involve with a lot of machines. 
The way AiiDA using RabbitMQ as communicator is unilateral from actioner to workers, where the workers can only talk back to the aiida kernel through ack. 
It requires more communication in direction from workers to AiiDA kernel, such as worker's load information and tasks health information.
With new system, I want to bring in the bileteral communication between the `actioner` and `worker` (the terminologies are defined in the following sections).
In AiiDA case, the common scenario is that there are not too many clients (workers/actioners) talk to server (coordinator), thus it requires a very neat implementation that can add more bussiness logic around but still kept lightweight. 

### Long-stand issues targeted

Couple of issues that we are not able to solve because of the limitation of using RMQ, the tool proposed is targeting on them:

- [#88: Limit number of jobs in TOSUBMIT state](https://github.com/aiidateam/aiida-core/issues/88)
- [#1397: Deadlock when creating many processes](https://github.com/aiidateam/aiida-core/issues/1397)
- [in wiki: RabbitMQ version to use with AiiDA (<=3.8.14)](https://github.com/aiidateam/aiida-core/wiki/RabbitMQ-version-to-use)

### Legacy architecture

It is worth to have a look at the legacy architecture when using RabbitMQ + kiwipy as message broker system for task control.
The figure shows the liftspan of a task from being generated to it is running on a worker. 

![The architecture summary of the legacy task launch and controlling system design](./misc/tatzelwurm-arch-legacy-arch.svg)

The user has access to the "actioner" to control the state of a task.
The actioner in AiiDA context is the CLI or the API to communicate with the backend when a task state requires to be changed.
Typically, here is how a task from it is generated to it is being run at "worker".
Firstly, user create an AiiDA "Process" (`ProcessFunction`, `CalcJob` or `WorkChain`), in the context here we call it a "task".
The task object is stored in the task pool.
At the same time, a message is sent through the message broker and message is taken by a worker so the worker knows there is a task to be proceeded. 
Finally, the worker construct the task from task pool and run it in its event loop.

The task consists of its state and how it will involve over the time, so when it just created the task is in its initial state.
The real entity of the task is stored in the task pool, which in the AiiDA context it is the persistent data storage i.e database + disk-objectstore.
For the task pool, the task can be deserialized and run by the "worker". (althrough the task pool has all the information to recover a task to run, but it contains the borrowed reference to the environment or source plugin instance, this will be further described in the other post hopefully).
To let the worker run a task after submitting the task, a message is passing around at the same time through the communicator, which is what I am going to improve by replace the backend design with `tatzelwurm`.
Two message management patterns are used which are [publisher-subscriber pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/publisher-subscriber) (?in the context of RMQ it is a work queues?) and [remote procedure call (RPC)/broadcast](https://www.rabbitmq.com/tutorials/tutorial-six-python).

The pub/sub pattern is applied between actioner and multiple workers. 
The actioner is the publisher that will send the message about which task should be run.
The workers are the subscribers that take the message and then process on the task. 
**However**, here comes the problem with pub/sub pattern. 
After the publisher send a message to the subscriber, it expect an acknowledge from subscriber to tell that the task is taken and is proceeded. 
If the message is not passing to the subscriber, the publisher has the responsibility to send the message to make the task being taken by other worker.
The task in AiiDA can take hours and even days to run to its terminated state and until the acknowledgement message be sent to the publisher. 
The RabbitMQ is designed for the ligth message and the default timeout for delivery acknowledgement of RMQ is 30 mins.
Meanwhile, the timeout is not recommended to be changed.

The RPC and broadcast patterns can be described together. 
They are applied between actioner and the tasks instance directly. 
The different between RPC and broadcast is that RPC is 1-to-1 while broadcast is in 1-to-N mode. 
It is not a mistake to use RPC in the AiiDA scenario but there is [a note on RPC](https://www.rabbitmq.com/tutorials/tutorial-six-python#a-note-on-rpc) in the RabbitMQ documentation that "when in doubt avoid RPC. If you can, you should use an asynchronous pipeline".
I extend the discussion on secion [_Is RPC/broadcast really needed in AiiDA?_](#is-rpc-and-broadcast-really-needed).
From the architecture figure, it is interesting to see that the direct interaction between actioner and task acrossing the worker is a bit awkward since the interaction across the boundary of worker.
This makes the cancellation handling of tasks hard to reasoning, which need to be handled in the case when the heartbeat is missing.
You'll find that in the new design, I try to give/ask worker for more responsibility to handle the cancellaition and notification back to the actioner. 

### New architecture

The new design is sketched in the figure below, where I replace "communicator" to "coordinator" by giving more explicit role.

![The architecture summary of the new design](./misc/tatzelwurm-arch-tatz-arch.svg)

The RMQ as message broker is replaced with the `tatzelwurm`.
The tatzelwurm play two major roles: a) the queue system and b) the message broker.
The queue system is to manage which task should be run first and should be run by which worker.
The massege broker is for the coordinator need to communicate between the actioner and worker for results and operations exchange.

Two tables are stored in the disk, a) the task table b) worker table. 
By tables lookup, the coordinator can then decide which worker to run which task.

The worker has types and will only get certain type of tasks.
The goal is to distinguish the synchronous task which can block the running thread from asynchronous task that can just added to the runtime and run concurrently.

![Running a single task](./misc/tatzelwurm-arch-UML-lifetime.svg)

The UML shows the life span of how different components coorperate to run a single task.
The coordinator has its own persistent table maintainance.
By move coordinator away from task pool, the architecture lower the access requirement to database therefore increase the performance.

The message is passing between different entity over tcp wire, which for future design that the worker and actioner can be run on other machine.
Different message types for different operation purposes are summarized at [Message Types section](#message-types).

Internally the messages are passing through channels and I tries to apply the actor pattern as possible to get high throughput in concurrent scenario.
The interface with the coordinator alone is re-interpreted and abstracted as messages.
Therefore in principle the actioner and worker can be implemented in any programming language by just follow the massege protocol.
However, it is not trivial to implement all the communication needed from handshake to get notification back and forth between entities. 
The `kiwipy` in AiiDA servers as the role to provide the wrappered methods to talk between different components over RabbitMQ.
Therefore, `kiwipy` is the interface for actioner and worker on bundle the operations to talk to RMQ, as the replacement, in `tatzelwurm` I should provide the python interface with methods ready to be used for sending and consuming certain type of MessagePack meesage.

## Other solution or exist tools?

First, it is worth to mention the major two goals of having a standalone tool are:
- Not rely on an extra service to start before running AiiDA.
- Tasks (AiiDA processes) can be assigned properly to workers, which indicates a requirement for small scheduler system for AiiDA.

It was discussed in https://github.com/aiidateam/AEP/pull/30#discussion_r813895745, better to look for tools that ready to use.
What were mentioned are [Apache Kafka](https://kafka.apache.org/), [faust-streaming](https://github.com/faust-streaming), [MQTT](https://mqtt.org/) and [Celery](https://docs.celeryq.dev/en/stable/getting-started/introduction.html).

- Apach Kafka: for event streaming, require service to start. (servirce required)
- MQTT: is a messaging protocol in low bandwidth environments. (no queue system + overkill for low bandwidth)
- faust-streaming: require Kafka as event streaming backend. (Kafka services required, it is like kiwipy but for Kafka)
- Celery: this is a task queue. (For event streaming it requires a message broker, RMQ, Redis, SQS .., For persistent, it requires a results store.)

The `tatzelwurm` is tailored for AiiDA use cases specifically with message streaming/broke, lightwight queue system and persistent with KV store in disk in design.
It is lightweight but will meet all the requirements for AiiDA.
The tools above are for machines to machines scenario which required for huge message passing around millios of microservices and that is why those are overkill.
We are not targeting to that but for AiiDA with required architecture as described above. 

## Design details

In this section, I futher extend on the details of the new architecture.

The related design patterns are:
- [pub/sub](https://learn.microsoft.com/en-us/azure/architecture/patterns/publisher-subscriber).
- [actor with tokio](https://ryhl.io/blog/actors-with-tokio/)

Not all but quite a bit are inspired by:

- https://github.com/chrisjsewell/aiida-process-coordinator
- https://github.com/chrisjsewell/aiida-process-coordinator/discussions/4
- https://github.com/chrisjsewell/aiida-process-coordinator/issues/7#issuecomment-943361982
- The initial [AEP PR#30: Remove the dependence on RabbitMQ](https://github.com/aiidateam/AEP/pull/30)

### The components

1. Task coordinator

The coordinator plays two major roles. 
It is a message broker that communicate with workers connected and meanwhile it is a queue system that knows **when** to send **which** task to run on **which** worker with load balencing.

In order to replace RMQ for queuing the tasks and recover the tasks state after reboot the machine, it needs the functionality to persistent the task list on the disk. 
Different from RMQ which lack of API to introspect task queues to determine the task list and task priorities, the coordinator has the task table with task can be tagged with multiple properties such as priority and it blocking type.

Here are requirements for the coordinator:

- It runs as a server and waiting for messages from/to actioner/workers. The workers are clients that can run on a python interpreter with an event loop and the actioner can send message to trigger the operation to send bundled messages to workers.
- The server will listen for incoming tasks, manage worker connections (handshake and monitoring the heartbeat of the worker), and handle the load balencing of tasks to workers.
- There are cases the workers will closed without finishing its tasks, when this happened coordinator need to know the state change of workers and resend the unfinished tasks to another worker. 
- The task coordinator implement persistent task queuing so that tasks can be recovered after a machine reboot. The go to solution I can see is using an embeded DB like `RocksDB` or use `Redis` with its RDB+AOL. 
- For task queue persistence (continue of the point above): the embedeb DB only allowed one connection and this connection is from the coordinator (therefore, only the coordinator is directly communicate to the embedeb DB). Tt communicates with the worker and when worker responds, coordinater should updates tasks (e.g. `pending`, `in_progress`, `completed`) into the serialized task data. (More details are discussed in later sections.) 

The lifetime of coordinator service is bind to the workers.
If the AiiDA use case, the coordinator should start when the first worker being started and dropped when all the workers are dropped.

2. Worker

The worker is responsible for running python functions (or more generic if the I can provide message interface by having core part in low-level language. I believe it is then not hard to build on top the wrapper to different languages, such as Julia and Lua).
In the context of plumpy, it is for running python coroutines by place the coroutines to the event loop that bind to the worker interpretor. 
There are two ways of implementing the worker, one is having the worker as client and implemented in python, the harder way is implement worker in rust and expose the interface to python using `pyo3`.
(? May possible to further seperate define the functionalitios of worker. It needs to communicate and running things. The communicate port is de/serializing the data and this port can definitly use the API exposed through `pyo3` here.)
For simplicity, the worker should first implemented in Python that can strat an event loop and has `add_task_subscriber` method to push coroutines to the event loop. 
It will make the replacement in AiiDA straightforward.

Here are requirements for the worker:

- Workers communicate with the rust server, getting messages from server and trigger the subscribed functions/coroutines to run on its own thread.
- Each worker runs an event loop in Python, which waits for messages from the rust server. 
- Upon receiving a message, the worker loads and executes the task. It should acknowledge back to coordinator that it get the task and keep on update the state of task running so the coordinator knows its loading. 
- The first time when the worker start, it need to register to the coordinator a long-live task subscriber through handshake and say it is ready for launching the task and continuing the task. This subscriber will be removed with closing the worker or the coordinator is gone.
- Each real task (corresponding to the `Process` in plumpy) is proceeded individually. Once a task is completed, its state is marked as terminated and remove from coordinator's task booking. 
- Only one worker working on a single task at a time. The worker will automatic requeue the tasks if the worker died for whatever reason.

3. Actioner

There is always a guy look into system from outside and try to make some actions. 
In the context of AiiDA, it is us the regular user who is willing to launch, pause, resume, and kill the process.
I call it actioner. 
The actioner will send the bundle of operations through a defined message that follow certain protocol to the coordinator. Coordinator then send or broadcast the message to workers and take actions to manipulate the tasks.

### Two tables

The coordinator should grab two tables to operate on its tasks.
The two tables are workers table which record the workers state information and the tasks table which record the states of tasks.

Everytime when the coordinator "look at" two tables, it needs to make the decision on what operation needs to be take for a task.
An actor called "assigner" runs concurrently and check two tables periodically.
In every lookup, it loop over all ready to run tasks and pick a worker with lowest load from sepecific type and ask the worker to pick the task (by deserializing from task pool) to run.

The worker table has keys that is the uuid of worker.
Every item is a worker registred record the current state and meta-info of the worker. 

The worker current state and meta-info include:

- The worker type that distinguish on what type task can be consumed by the worker.
- The load that is the number of tasks running in the worker.
- The number of tasks limit, above which the worker will not be sent with more tasks to consume.
- The lease expired time, after which the worker will be regarded as dead. The field is update by the heartbeat sent from worker.

The task table has keys that is the uuid of tatks.
Every item is a task mirror which has its archetype in the task pool.
The mirrored entity include the state and meta-info:

- The task type that distinguish on which type of worker it can send to.
- The priority of the task which is an integer the higher the value the first will be send to the corresponded worker.
- The worke uuid where the task is send to.
- The lease expired time after which if the worker not step to terminated state and the corresponded worker is dead after lease expired the task will be re-assigned.

For performance, the tables are in memory.
But meanwhile we want tasks state are reboot proof which require the task table has a backup can in disk that can be used to recover the table to memory.
For store such a persistent storage, see the section [persistent queue state to disk](#persistent-queue-state-to-disk) for more discussion.

### Task states transition

The task has its states and the state will be changed upon signal send and receive between actioner/worker/assigner.
The task in `tatzelwurm` has its own states transition logic and may different from states definition from its real entity in task pool (e.g. in AiiDA).
In `tatzelwurm` the state is for managing the state transition by the operation applied and is a marker to know if the upcoming operation is valid to take.

- `Created`: ( x -> `Ready`, x -> `Pause`) when the task entity is push to task pool and its existence signal registered to the coordinator. In this state, the assigner will **NOT** trigger this task to run.
- `Ready`: (`Created` -> x, x -> `Submit`, x -> `Pause`, `Pause` -> x) is the only state that will be picked by the assigner and send to worker to be proceeded.
- `Submit`: (`Ready` -> x, x -> `Run`, `x` -> `Pause`) after assigner send it to a worker and worker not yet start working on it.
- `Pause`: (`Created` -> x, `Ready` -> x, `Submit` -> x, `Run` -> x) is a buffer and fallback state that hold the assigner to assign it to worker. It waits for a signal from actioner to resume. If the task is in `Run` state and the worker lost heartbeat, the coordinator will transite it to `Pause`.
- `Run`: (`Submit` -> x) the worker is working on it. (TBD, submit and run seems redundant. Meanwhile the assign task is a tight loop which may not quick response to running ack message from worker. But the sepration of states leave a implementation port for future features support.)
- `Terminated(exit_code)` (`Run` -> x) the worker finish on it and send the signal back. The exit_code 0 for complete, -1 for killed and other positive number for except with certain exit code.

### Message types

(TBD)
In the whole design, the message is used to communicate between different entities. 
I want to have two different types of message for two purposes:

- On the one hand, for messages passing between clients and server over tcp stream and require serialize and deserialize.
- On the other hand, for in-processing communications only the message is passing through channels and can contain oneshot channel for ack which can not be serialized.

For the tcp communication over wires, the message will be send and will triggle a bundle of operations on two side.
I call this message type `ExMessage`, where "Ex" for "external".
This type of message is already contain abstraction of operation and become interfaces for communication between clients and the coordinator.

For the in-processing communication that use shared memory over mpsc or oneshot channels, the message contains the atomic operation on for example manipulating worker and task table.
I call this message type `IMessage`, where "I" for "internal".

```rust
#[derive(Serialize, Deserialize, Debug)]
pub enum XMessage {
    // dummy type for fallback general unknown type messages
    BulkMessage(String),

    // The Uuid is the task uuid, record_id is for task pool
    TaskLaunch {
        task_id: Uuid,
        record_id: String,
    },

    // hand shake message when the msg content is a string
    // <-> between server and clients
    HandShake(String),

    // Heartbeat with the port as identifier
    // <-> between server and clients
    HeartBeat(u16),

    // Notify to coordinator that worker changes state of task
    TaskStateChange{id: Uuid, from: TaskState, to: TaskState},
}

#[derive(Debug)]
pub enum IMessage {
    // dummy type for fallback general unknown type messages
    BulkMessage(String),

    // The Uuid is the task uuid
    // dispatcher using worker's tx handler -> worker's rx, after table lookup
    TaskLaunch(Uuid), 

    // Operation act on worker table
    WorkerTableOp {
        op: TableOp,
        id: Uuid,
    },

    // Operation act on worker table
    TaskTableOp {
        op: TableOp,
        id: Uuid,
        from: TaskState,
        to: TaskState,
    },
}
```

There is a typical case that one bundled operation relys on both.
When dispatch a task to worker by two table lookup, an internal message `IMessage::TaskLaunch(Uuid)` first fired from a dispatch which runs concurrently.
The message is relayed to worker client by parsing the message and convert it to an external message with type `ExMessage::TaskLaunch(Uuid)`, which send to the correspond worker.

(Needs polish) For `TaskLaunch`, in experimenting with a mocked task pool, I found that it required to passing message with both task id in the coordinator's table and the record it in the DB so the worker knows which task's real entity to recorver from.
If multiple task pools are going to be supported in the future, the task pool also needs to be registered and has a identity to reach the agreement between actioner and workers.
For the first implementation, only `record_id` is passing with the `task_id` of the table.
The record_id is the id of the corresponded DB index for finding the node to recorver task from.

(This paragragh need to be changed. It makes little sense to distinguish message based on transition type. Makes more sense to just to have regular message type and the type when it can not be serialized. The codec is independent of message difinition.)

### Proactive task assignment

The major different between the legacy design and the new design will be the way how tasks are assigned.

- legacy design: worker take from queue channel.
- new: coordinator hold a booking. In every tcp stream with worker the coordinator look at bookings and push the task to worker. 

In the new design, the coordinator not only just fan-out the mission and wait it to be consumed when new mission created. 
It also waits for the response that the mission is taken and wait for the message that the mission is finished. 
The coordinator needs to frequently look at the booking and decide which to do with each worker. 

But what is the driven force and the frequency for coordinator to look at the booking? 
If booking check is too often, since everytime the coordinator look at the booking it has some cost, the overhead raised by too many lookup. 
On the contrary, less often booking check will cause the tasks not efficiently assigned and therefore jams the pipeline.
To ensure the good rate of throughput and avoid leaving workers to unnessesary idle, the booking checking is happened in the following cases:

- when it is certain that the state of table is changed such as new task/worker registred and task terminated.
- in the certain interval it ask itself to chek the booking and keep things ongoing.

It requires to benchmark the performance of booking check on a very big table and decide which should be the proper default interval for booking check.

### Task priorities and task types

The goals of this design are:

- By making the "driverabl" tasks (e.g. inner child workflow or unit task) complete first, the workers are not blocked by the slots limit as legacy RMQ design. 
- It can have a max number of tasks for certain tag and the tag counting can then be used to limit the resources usage, see the section [_Info to task to limit the maximum number to run on remote](#info-to-task-to-limit-the-maximum-number-to-run-on-remote) for details. 
- The workchain start running again once the child process the workchain is waiting for reached the terminated state (Seb's CIF cleaning).
- In a regular load (?definition required after implementation and bench) only one worker required for the non-blocking processes, and number of worker controller is for blocking running workers.

The task send to the coordinator need to have a priority field to distinguish from its type and high priority tasks should run before the worker start to consume the low priority task.
The purpose in the context of AiiDA is that the workchain itself is not a runnable process but the processes it encapsulates such as `CalcJob` and `ProcessFunction` are runnable.
The workchain can be nested, therefore the inner workchain should have higher priority so that the outer workchain can be run first. 

(TBD) In the design, the processes have different categories which fall into different topic when the worker need to pick up to run.
The fundamental tasks e.g. `CalcJob` and `ProcessFunction` that not rely on the completion of other process are in the topic 'baseproc-a' (`ProcessFunction`) and 'baseproc-b' (`CalcJob`), and they have the same running priority `0`.
The reason to distinguish the base runnable processes is for future improvement, where we can have dedicated interperetor to run blocking CPU-bound processes. 
For the workchain the process is bind with topic 'compproc', it should have a stack of calling order to know if it is called from another workchain.
The most outside workchain is given the priority value `1` and the value increase when it goes deeper to ensure that inner process will be picked by the coordinator to send to worker first.

There are chances that the blocking process will starving the workers but it required to be solved if we can separate dedicated threads/runners for such tasks and having regular workers only to push running event loop forward. 
Based on the topic, it can have dedicated worker that only to consuming 'baseproc-a' topic for running `ProcessFunction`.
While for the `CalcJob` and `WorkChain` they can all push to be run in the same async runtime.

### Persistent queue state to disk

The processes state record booking or a.k.a task queue should be able to persistently stored in the disk between the restart session.
In order to maximize the performance for high-throughput, the running task booking is in memory. 
For persistent, when the coordinator shutdown, the current task booking is writen to the file as booking database (BDB) for recover the booking of next restart.
However, there is possibility that the coordinator may not gracefully shutdown. 
As a backup solution of such scenario, the append only file (AOF) is keeping the logs of every booking change and can be used to reconstruct full booking before shutdown.
These two mechanism are exclusively used for the newly restart of coordinator. 
If the coordinator is gracefully shutdown, BDB is written for recovering the next coordinator session and the AOF file will be cleaned up and log events will only for recording the new running session.

The disadvantage of this design is the size AOF can grown fast in the high-throughput if the coordinator runs for a long time. 
In the scale of monthes running, the AOF can be extremely large and it is then expensive to rerun events to recover the booking).
The enhancement can be the BDB is dumped to the disk from memory periodicly and remove the events happened until the dump period so the AOF only contain the events for recovering from dumped BDB.

### When and what to communicate between coordinator and workers

The [comment](https://github.com/aiidateam/AEP/pull/30#discussion_r766481043) enphasize that run a task zero or one time makes more sense for AiiDA since resounces consumed by AiiDA is always a concern in terms of running heavy calculation on the remote.
In order to make task completion information more verbose so the coordinator can make good decision on whether send the task to other workers, the worker need to communicate two times back to coordinator, one when the worker get the task assigned, it reply back it will running on it, then when the task is complete it need to send back again to say the task is real done.
The coordinator will keep the list of running tasks and ensure no duplicate tasks are send to other workers. 
The AiiDA has its DB that also hold the process completion information, and this information will be synchronize with coordinator whenever coordinator restart or manually triggered when needed. 
When the tasks is really completed, it is safe to be removed from the running tasks list and coordinator can assign new to workers.
This strategy is different from but better than the current RMQ solution, where when a process submitted, a request to run the process is sent to RMQ which will then send the task to a worker (worker get the message and put it in its event loop). To guarantee that each task will be executed, RMQ will wait for the worker to confirm the task is done or not. 
If the task is not done, RMQ will send the task to another worker if the previous worker was detected to miss the heartbeat and regarded as "died worker". 
Two times communication mitigate the problem that coordinator need to keep task on the queue until it finished.

Therefore for worker, it has following communication scenario:

- Handshake: for security purpose, talk to coordinator to show it is a valid worker. Bidirectional communication.
- Heartbeat: monodirectional communication from worker to coordinator. It requires write half from stream.
- Task assign: worker get a mission ID from coordinator, reply when it create the mission from ID (push to its own event loop). Bidirectional communication.
- Task terminate: worker finish the mission, send an ack to coordinator so coordinator can make the booking and assign more missions to worker. 

As corresponding, the coordinator needs to:

- Handshake: get to know new worker is willing to connect, authorize it. Bidirectional communication.
- Heartbeat: monodirection from worker, and coordinator is only read from stream to check the worker is alive.
- Assign task: send mission Id to the lowest load worker, and change the mission state to assigning. When worker reply with on processing, coordinator update state to "running".
- Complete task: worker will send a message when the mission complete, the coordinator need then update the process state to complete (delete from list).

(TBD) whether coordinator needs to keep heartbeat and notify workers that it is alive to update the booking?
In essence, when worker realize coordinator is dead, it need to do be shutdown gracefully.

### Data frame and serialization

- **Decision**: framed data (if rust, using `codec`, if python using `asyncio` stream). 
- **Decision**: de/serialize message, using `MessagePack` for extensibility and simplicity.

Since I need to take care of bytes over wire with async, I need to transfer framed data.
I decide to use `tokio_util::codec` to frame the data.
For the protocol, instead of design a new one, using `MessagePack` and wrap `struct` into it can be easy to start.
The MessagePack is like JSON but a binary message which can be more efficient in transportation.
If in future we find the message between clients and coordinator is always simple, we can change to using self designed protocol such as redis-like protocol (after the prototyping, I realized there are different type of messages and therefore let's just use msgpack.).
If we find in the future we need more big chunk of data to communicate, the MessagePack can fit for storing more complicate format.

### How to deal with missions when worker is "dead"

Related isuses: https://github.com/aiidateam/aiida-core/issues/5278

- (TBD) **Decision**: implement the lease to tasks for simplicity which requires only logic in the communication level.

The worker keep on sending heartbeat, when it missed one, coordinator can regard it as "dead".
Then there is a problem that the worker may still hold the access to the remote resources and to the database. 
Unexpected things may happen if the mission is re-assigned to other worker at the same time.

This is not an uncommon scenario in the distribution system design.
There are following solutions that we can keep on investigating and comparing:

- leases: the coordinator can only send the mission to other worker when the original worker miss the heartbeat and the lease of task expired.
- task cancellation: when heartbeat missed, coordinator send cancellation to worker and worker need to gracefully cancel all running missions. 
- quorum-based consensus protocol: (mentioned by ChatGPT, I don't understand how it works.)
- Idempotency and atomic on resource manipulating: if the operations on resources (remote HPC or database) are idempotency, then it doesn't matter if the operations happen multiple times. But in AiiDA, this is not guranteed especially for the remote calculations which may have two `sbatch` submit in the same folder (maybe I am wrong?). For the DB, the issue of duplicate output port as mentioned is exactly what happened.
- tag and version on the operations: if the operation is not idempotency, then if same resource is manipulated by the different workers then giving version or tag to make sure it is not duplicately running same operation can be a solution, but this require the tag feature in the DB and in the transport plugin. 

The lease idea is for every task when it is in running state, the lease will only returned when the worker that working on it has miss 10 heartbeat.
When the lease is expired, the task can be taken by other worker. 
It requires more test and benchmark to see if this approach robust enough for our use case.

### Is rpc (and broadcast) really needed?

- **Decision**: don't use rpc but asynchronous pipeline and let the worker manage tasks.

In legacy (current) `aiida-core`, during the lifetime of a task (an aiida process), it has a rpc channel attached. 
The rpc channel has worker side as server to respose the rpc calls from actioner which is the user's CLI.
The only function registered on the rpc is the `message_reciever` which answers to three remote operations i.e. `kill`, `pause` and `play`.
The rpc is a common pattern when differnt components require to interact with each other in an asynchronous manner, but misuse may lead to unclear code.

In `aiida-core` use case, this rpc pattern is overkill.
Instead, what we really need is a listener of the process that knows what operation to take for the process, depend on the message received. 
This listener can skip runner and interact with coordinator (as legacy design where every process has a rpc subscriber to RMQ).
This listener can interact with worker and let the worker to deal with communication with coordinator. 
But is it possible to add more hierachy the communication logic?

I think the better solution is having runner in between of the process and coordinator to avoid coordinator have direct control of processes.

In the proof of concept of `aiida-process-coordinator`, it uses a dict to handle the signal to the specified process.
It is possible (and I think it is better) to use channel for the runner to manage sending signal to operate on processes.
By using signal it futher decouple the runner and processes.

The new design has pros and cons:
- Pros 1: processes are grouped under runner which makes runner management (restart and cancellation) transparent.
- Pros 2: coordinator get less load on monitoring processes and therefore can handle larger throughput. 
- Cons 1: the runner has a bit more responsibility then before.
- Cons 2: the broadcast should go runner by runner. 

Let's look at the process kill operation as a typical example that reveal the new design is better.
In legacy design, the kill signal directly send to process and process register the operation to the runner's event loop to be executed.
The control flow goes from coordinator to deepest process and back to runner to ask runner to kill itself.
In the new design, the kill signal send to runner, and the runner then manage the close of the process. 
The control flow goes from coordinator -> runner -> process which is easy to reasoning and every two parts can be isolated to debug.

### One glimpse multiple tasks assignment

When dispatch tasks to workers, there are two ways of updating worker table.
First is after every task assignment, I check the worker table again to get the latest one and to assign task using the new table.
Second is to do only one glimpse on the worker table and use this table to assign all the tasks in a loop.
The different between two strategies are during the tasks assignement, the worker table will be update in-time.
The worker table can also changed if there are short running tasks that finish during assignments. 

The decision was made mostly for less table lookup and to make the assignment more easy to predict.
For debug purpose, it is easy to just print out two tables and see if the assignment works as expected.

### Info to task to limit the maximum number to run on remote

A very [old issue](https://github.com/aiidateam/aiida-core/issues/88) was not able to be solved because the lack of process assignment strategy.
At the moment, there is no way to count the number of tasks are running on the remote resources. 
When assigning the remote run task (`CalcJob` in AiiDA context) to worker, it requires to add a check on the limit amout of jobs are able to run on the remote.
If such type of tasks exceed the limit, no more task that bind to certain remote (marked by some tag, let's say scheduler distinguished) should be assigned to the worker until some tasks are completed later.

### Gracefully kill a task shutdown runner

- [Issue #2985 not gracefully killed](https://github.com/aiidateam/aiida-core/issues/2985)
- [Issue when only CMD interpreter runner closed](https://github.com/aiidateam/aiida-core/issues/2711)

When task is killed, it requires to

1. Go through all the sub-process and schedule cancelling coroutines.
1. Change the DB record for the task (by aiida-core).
1. When all cancelling finished, close the event loop and mark the process as killed in the table.

### Advantages of Rust Over Python in asynchronous programming

If you read to here, I think we can start a serious conversation.

I can image people from the team may against it because they may not at the moment very familiar with Rust and Rust is well-known for its steep learning curve for beginners.
However, the effort is well worth it: 
Rust’s design is incredibly robust for complex and performance-intensive applications, especially when it comes to asynchronous programming. 
Building a package from scratch might seem challenging, but with a clear design, understanding of an impleentation is independent of which programming language is chosen.
Therefore, I think it is better to choose a programming language that suit for the tool.
For high concurrency requirements, the handy programming languages available are Golang, Erlang (used by RMQ) and Rust etc.

In the initial goal of language design, Rust was putting [fearless concurrency](https://blog.rust-lang.org/2015/04/10/Fearless-Concurrency.html) in its core, with the help of concepts like ownership and lifetime.
Over the year, from AiiDA team the developers worked on engine were very suffered from debugging the code with `asyncio`, more or less I believe.

Instead of go into details of comparing the Rust v.s. Python in async programming which I'll give another doc with examples.
I summarize following strong reasons drive me to make such decision:

- Performance wise, Python has GIL and therefore not able to provide real CPU parallelism. The bottleneck of AiiDA at the moment is from DB access, but it is not the excuse to compromise on performance for design.
- Developers efficiency wise, I tried python from start, but I spend more time on figuring out how to frame stream to MassagePack in python even though I am more familiar with python. In python the mpsc and oneshot patterns which comes with tokio as commonly used patterns, but has to implemented by hand with asyncio prime tools.
- User friendliness wise, we want the future AiiDA is a `verdi` binary can download and run, without set up python environment. It is achievable with Rust.
- If the project done with python, if not me, there will be other people want to rewrite it in other language. If it writen in Rust, the only possibility within 10 years is rewriting it again in Rust.
- With using Rust, [I believe I am able to finish this projet, not just start it](https://www.youtube.com/watch?v=Z3xPIYHKSoI).

## Experiments required before start

These are collection and short summary of awswers from ChatGPT 4o, which give the hints for tools and technique stacks where I should look and clear the path before start.
I don't fully trust so the experimentals required.

### Can I run a python coroutine in the thread that spawned in the rust side?

ChatGPT points that:

1. Python's GIL must be acquired before interacting with Python objects from Rust. (first prepares the Python interpretor by `pyo3::prepare_freethreaded_python()` and then `Python::with_gil()`)
2. Set up an asyncio event loop. This requires to run inside the thread `asyncio.get_event_loop` and in the loop call `run_until_complet` of the coroutine from the task handler.

Comments: 

- The key point to check is make sure not new thread is created for each coroutine but the thread/event_loop has the lifetime of worker (this is the new design after move from `tornado` to `asyncio` which can only support one event loop, so probably with handle thread by rust every process can again run on their own event loop??). 
- It may also be possible (better) to turn the python coroutine into a rust future and then using tokio runtime to poll the future to complete. This require the crate `pyo3_asyncio` as bridge to pass python's coroutine to rust tokio runtime. 

### The interface for worker and actioner

(more details require discussion)

- worker and actioner are independent of central design, since the interface can be very flexible as messages and therefore make the use of the system programming language agnostic.
- But it anyway requires real implementation for the actioner and worker.
- although the create provide example of worker and actioner by rust, in its first real world use case in AiiDA, the python interface is must to have thing.
- The interface is the kiwipy as for the RMQ. 
- In the repo, the interface is put as separate crates and provide with python as must have, and probably with julia and lua in plan.

### Running the server by ..?

The Rust application after compiled will be a binary.
There may be two ways to run it from AiiDA:

- Get the binary with install the pyo3 wrapper lib and put the binary of corresponding OS architecture to the python bin path. In AiiDA maybe keep on using circus to mornitoring the start services.
- Expose the API and have a python coordinator "main" as `main.rs` which is less than 100 lines. Not sure about the performance since python has GIL!!

## TBD

- Q: Is it better to store checkpoint in a seperate (in legacy it is with process node) table or even in a separate resource? 
    - A (@unkcpz): The checkpoint contains two types of information, which are the information to recover the task and the information of task running state. The info to recover the task from task pool should be in the task pool. But the information about running state should be in the other entity with more fast access. These two information are well decoupled.
    - But this change require more design change in the AiiDA.

- Q: Who should create (create means initialize the instance, store it is the "DB" and set to the created state) the task? Coordinator or worker or actioner (in legacy it is actioner)? 
    - A (@unkcpz): It should still be the actioner, the architecture overview explain it well.
    - One of the goal is to make the use of the task broker language agnostic and fit for the workflow of orchestrated in different programming languages.

## Performance tips

If the performance become bottleneck and after the benchmark it shows the the bottleneck is not from architecture and implementation.
There are some underlined crates and tools to use as the alternative for message passing or DB management.

- [Rkyv](https://github.com/rkyv/rkyv) for zero-copy deserialization as alternative to msgpack.
- [dashmap](https://github.com/xacrimon/dashmap) as alternative of HashMap if in-memory store with mutex map is used.
