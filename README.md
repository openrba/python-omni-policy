# python-omni-policy
Declarative data store, API, and documentation for the sentinel-omni-policy for Hashicorp Terraform.  This repo includes the following components:

- **The omni-policy cli tool** (executable) - for fetching, creating, merging, extending and bulk updating all data pertaining to Hashicorp Terraform providers and resources.
- **/config** (directory) - contains folders and associated resources in YAML format for all Terrafrom providers with a status of "enabled" in providers.yaml
- **config/providers.yaml** (configuration) - YAML file containing a merged map of all Terraform providers, descriptions, url and status.  New providers merged by the cli tool will get a default value of "disabled".  If using the sentinel-omni-policy and you want to permit use of a provider by Terraform, change the status of that provider to "enabled".
- **/data** (directory) - contains folders and associated resources in JSON format for easier consumption through github API and sentinel.  All data in this directory will update when the omni-policy cli tool is envoked.

## What is the purpose
This repository contains a complete data snapshot of all Hashicorp Terraform providers, resources and resource attributes.  This data has been extended by key/value pairs that allow for policy to be declared in an easy YAML format.  The sentinel-omni-policy repository contains the sentinel policy that reads this data and applies the policy in real time to Terraform Enterprise.  This allows non-developer security personnel to manage the policy in a more comprehensive and natural way.

## Example Usage
Configuration YAML files are provided for all Terrafrom 'providers' that have been enabled in the providers.yaml file.  Within the config directory the resource type is in a config/$provider/$resource_name.yaml format.  Those yaml files look like the following.

```
aws_iot_thing:
    status: ASSESS
    subcategory: IoT
    layout: aws
    page_title: 'AWS: aws_iot_thing'
    description: Creates and manages an AWS IoT Thing.
    arguments:
        name:
            description: The name of the thing.
            required: true
            policy: '<market>-<businessUnit>-[0-9][0-9]'
            notes: 'Any special notes you want to return if the policy check fails'
        attributes:
            description: Map of attributes of the thing.
            required: false
            policy: ''
            notes: ''
        thing_type_name:
            description: The thing type name.
            required: false
            policy: ['this','that']
            notes: ''
    attributes:
        default_client_id:
            description: The default client ID.
        version:
            description: The current version of the thing record in the registry.
        arn:
            description: The ARN of the thing.
    timeouts: {}
```

## How it works
 This sentinel policy can be used against any provider, resource and argument that Terraform supports.  For each resource being modified in Terraform it does a lookup of the omni-policy map for that resource located at [python-omni-policy](https://github.com/openrba/python-omni-policy) and applies a set of rules based on certain keys provided by that map.  The following keys are used by this policy:

 - **status** (resource) - Status is a key-value pair at the resource level that indicates the current ring level of the resource.  Ring levels are a continuation of the excellent work of the thoughworks techradar that organizes technologies into five distinct classifications e.g REJECT,HOLD,ASSESS,TRIAL,ADOPT. Using the input parameter min_ring, the sentinel policy applies a mandatory access control method to permit anything at that ring level or higher.  For example a min_ring value of "ASSESS" would permit any resource at a ring level of ASSESS,TRIAL, and ADOPT.

- **required** (argument) - Required is a key-value pair at the argument level of a resource that indicates whether the argument is required or not.  This policy uses this key from the [python-omni-policy](https://github.com/openrba/python-omni-policy) map for the resource to assure the argument is present in any resource being created through Terraform.

- **policy** (argument) - Policy is a key-value pair at the argument level that indicates the policy to be applied to the argument's value when passed through the policy.  It includes the following capabilities:
    - **string-match** - Exact match of an argument's value against a specific string and is the simpliest form of enforcing a specific value.  Example: `standard` matches only "standard".
    - **list-match** - Exact match of an argument's value against *any* of a list of strings.  Example: `['standard','basic']` would match either "standard" or "basic".
    - **regex-match** - A regex match of an argument's value against a specific regex expression.  This value must start with a `^` or a string-match will occur.  Example: `^[a-z].` would validate that the argument must contain any number of lowercase alpha characters.
    - **convention-match** - A match that expects a naming convention that includes lookup fields.  Fields will be looked up against the custom.json map in [python-omni-policy](https://github.com/openrba/python-omni-policy) that contains allowed_values for a particular field.  Example: the value of `<market>-<businessUnit>-[0-9][0-9]` will match to `us-core-01` assuming `us` is an allowed_value for market and `core` is allowed_value for businessUnit in your custom.json.

-> **NOTE:** Any modification to an existing YAML file currently requires a run of the omni-policy cli tool to update, merge and generate the json data in the API.  It is expected that this process get put in a simple CI engine such as GitHub actions to perform this automatically on merge.  Until then, you may run this tool manually on your clone after updating any YAML configuration.
 