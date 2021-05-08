# Extending the AiiDA REST API

| AEP number | 006                                                              |
|------------|------------------------------------------------------------------|
| Title      | Extending the AiiDA REST API towards workflow management                          |
| Authors    | [Ninad Bhat](mailto:bhat.ninadmb@gmail.com) (NinadBhat) |
| Champions  | [Leopold Talirz](mailto:leopold.talirz@epfl.ch) (ltalirz) |
| Type       | S - Standard                                                     |
| Created    | 27-April-2021                                                     |
| Status     | draft                                                        |


## Background

AiiDA comes with a built-in REST API (based on the flask microframework) that provides access to the provenance graph stored automatically with any workflow execution. In order to enable the integration of AiiDA as a workflow backend into new or existing web platforms, we plan to extend the REST API to support workflow management.

## Proposed Enhancement

The Proposal is to make three additions to AiiDA REST API.

1. Add validation of the QueryBuilder JSON using JSON schema
2. Add authentication/authorisation
3. Add POST methods to /users, /computers, /nodes and /groups endpoints
4. Add a new /processes endpoint


## Detailed Explanation

### Schema Validation
Currently, only the `/querybuilder` endpoint accepts `POST` requests (implemented in [PR #4337](https://github.com/aiidateam/aiida-core/pull/4337)).
The current implementation only checks if the posted JSON is a `dict` (see [L269](https://github.com/aiidateam/aiida-core/blob/develop/aiida/restapi/resources.py#L269)).

Adding a JSON Schema Validation has the following advantages:
- Standardise the input format required
- Better error messages when invalid post requests are made

### Authorisation
The post method will allow users to edit AiiDA entities. Hence, it is essential to verify if the user has the relevant authorisations to make the changes.

### Post methods
The post endpoints will be implemented in the following order:

1. /users
2. /computers
3. /groups
4. /nodes

Below, we provide JSON schemas for validating `POST` requests to these endpoints:

#### 1. /users

```

    {
        "first_name": {
          "description": "First Name of the user",
          "type": "string"
          },
        "last_name": {
          "description": "Last Name of the user",
          "type": "string"
          },
        "institution": {
          "description": "Name of the institution",
          "type": "string"
          },
        "email": {
          "description": "Email Address of the User",
          "type": "string"
          }
      }
```

#### 2. /computers

```

    {
       "name": {
        "description": "Used to identify a computer. Must be unique.",
        "type": "string"
        },
       "hostname": {
         "description": "Label that identifies the computer within the network.",
         "type": "string"
         },
       "scheduler_type": {
         "description": "Information of the scheduler (and plugin) that the computer uses to manage jobs.",
         "type": "string"
         },
       "transport_type": {
         "description": "information of the transport (and plugin) required to copy files and communicate to and from the computer.",
         "type": "string"
         },
        "metadata": {
          "description": "General settings for these communication and management protocols."
          "type": "string"
        },
    }


```

#### 3. /groups
```

      {
        "label": {
          "description": "Used to access the group. Must be unique"
          "type": "string"
        },
        "type_string":  {
          "description": ""
          "type": "string"
        },
        "user_id": {
          "description": "Id of users in the group."
          "type": "string"
        },         
      }

```


#### 4. /nodes

```
[
  node1:
  {
    "node_type": {
      "description": "Type of data the node is"
      "type": "string"
    },
    "process_type": {
      "description": "Specific plugin the node uses"
      "type": "string"
    }
    "attributes": {
      "description": "attributes of the node"
      "type": "object"
    },
    "extras": {
      "description": ""
      "type": "object"
    },
    "user_id": {
      "description": "Id of the user creating the node."
      "type": "string"
    },
    "computer_id": {
      "description": "Id of computer associated with the node."
      "type": "string"
    }

  }
  node2:
  {
    ...
  }


]


```

### Adding /processes endpoint
The /processes will allow access to current processes and also addition of new processes through GET and POST methods, respectively.

## Pros and Cons

### Pros
1. Will allow workflow management AiiDA REST API through process endpoint
2. Should enable integration of AiiDA workflows into generic web platforms

### Cons
1. Development time spent on extending API
2. Increased maintenance effort for the REST API for changes in the ORM

The second point could be minimized by aiming for a single source for the attributes of the ORM entities that is used both by the python API and the REST API.
