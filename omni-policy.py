#!/usr/bin/python

import requests
from collections.abc import Mapping,MutableMapping
from contextlib import suppress
import pathlib
import os
import base64
import json
import yaml
import re
import traceback
import sys

def merge_dictionaries(dct, merge_dct, add_keys=True):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.

    This version will return a copy of the dictionary and leave the original
    arguments untouched.

    The optional argument ``add_keys``, determines whether keys which are
    present in ``merge_dict`` but not ``dct`` should be included in the
    new dict.

    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Returns:
        dict: updated dict
    """

    dct = dct.copy()
    if not add_keys:

        merge_dct = {
            k: merge_dct[k]
            for k in set(dct).intersection(set(merge_dct))
        }

    for k in merge_dct.keys():
        
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], Mapping)):
            
            dct[k] = merge_dictionaries(dct[k], 
                                        merge_dct[k], 
                                        add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct

def open_yaml(file_path):
    """ Open YAML file return dictionary.

    This version will return a dictionary populated with the contents of the
    YAML document or an empty dictionary if YAML is invalid or file is not
    found.

    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Returns:
        dct (dict): updated dict
    """

    try:
        with open(file_path, 'r') as stream:
            try:
                result = yaml.safe_load(stream)
            except:
                result = {}
    except:
        result = {}
    finally:
        return result

def write_yaml(file_path,dct):
    """ Convert dictionary to YAML and write file at path.

    This version will take a dictionary and write a YAML file at path.

    Args:
        path (string): path of the file to write
        dct (dict): The dictionary to convert to YAML

    Returns:
        result (bool): whether the file oepration was successful.
    """

    try:
        file_dir = os.path.dirname(file_path)
        pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)
    
        yaml.dump(dct, 
                open(file_path, 'w'),
                indent=4, 
                sort_keys=False,
                default_flow_style=False)
        
        result = True
    except:
        result = False
    finally:
        return result

def delete_keys_from_dict(dct, keys):
    """ Recursively delete keys from a nested disctionary.

    This version will take a dictionary and transverse down through
    it at all levels looking for the list of keys and deleting them
    when it finds them.

    Args:
        keys (list): list of keys to delete
        dct (dict): The dictionary to delte keys from
    """
    # Used to remove binary blobs from dictionary so it can be 
    # converted into json.

    for key in keys:
        with suppress(KeyError):
            del dct[key]
    for value in dct.values():
        if isinstance(value, MutableMapping):
            delete_keys_from_dict(value, keys)

def write_json(file_path,dct):
    """ Convert dictionary to json and write file at path.

    This version will take a dictionary and write a json file at path.

    Args:
        path (string): path of the file to write
        dct (dict): The dictionary to convert to json

    Returns:
        result (bool): whether the file oepration was successful.
    """

    try:
        file_dir = os.path.dirname(file_path)
        pathlib.Path(file_dir).mkdir(parents=True, exist_ok=True)
    
        with open(file_path, 'w') as f:
            json.dump(dct, f, indent=4)
        
        result = True
    except:
        result = False
    finally:
        return result

def parse_markdown(markdown_dct,metadata_dct):
    """ Takes markdown, parses it and returns a dictionary.

    Takes markdown and metadata information and parses it according
    to predefined header values and structure based on the terraform
    documentation syntax, creates a dictionary of the key->value pairs
    and returns it.

    Args:
        markdown_dct (dict): dictionary of name/markdown
        metadata_dct (dict): dictionary of metadata related to this markdown

    Returns:
        result (bool): whether the file oepration was successful.
    """

    # Take the markdown dictionary and tease out name and text.
    name = markdown_dct.get('name')
    markdown = markdown_dct.get('markdown')

    # Create a temporary dictionary from header.
    try:
        tmp_dct = yaml.load(markdown.split("---")[1],
                        Loader=yaml.FullLoader)

        # Prefix the name with the provider.
        name = tmp_dct.get('layout') + '_' + name
    except:
        logger(traceback.format_exc())
        tmp_dct = {}
        dct = {}

    # Give default status of ASSESS.
    dct = {name: {'status': 'ASSESS'}}
    
    # Add all fields in tmp_dict to dct.
    dct[name].update(tmp_dct)
    
    # Create the sub maps in dictionary
    dct[name].update({'arguments': {}})
    dct[name].update({'attributes': {}})
    dct[name].update({'timeouts': {}})
    dct[name].update({'usage': {}})
    dct[name].update({'import': {}})
    dct[name].update({'hcl_url': {}})

    # Process the text in the markdown
    try:
        # Extract Arguments
        
        for arg in re.split("## Argument* Reference", 
                            markdown, 
                            flags=re.IGNORECASE)[1].\
                                split("##")[0].\
                                split("\n"):
            
            # Look for lines that denote bullets
            if arg.startswith('* `'): 
                
                # Better yet if they have a set of parenthesis
                if len(arg.split(") ")) > 1:
                   
                    # Get whether this is a required or optional argument
                    required = True if (
                                        arg.split("(")[1].split(")")[0] 
                                        == 'Required') \
                               else False
                    
                    # Override the hashicorp data, it isnt reliable.
                    # The above code works if they ever get a correct
                    # list of what is required and not.  Until then ...
                    required = False
                    
                    # Parse the line and add to dictionary
                    dct[name]['arguments'].update({arg.split("`")[1] : {
                                    "description" : arg.split(") ")[1],
                                    "required" : required,
                                    "policy" : "",
                                    "notes" : ""
                                    }})
                    
                    # Get the argument name
                    arg_name = arg.split("`")[1]
            
            # Not a bullet?  Then lets see if it is a special note.    
            elif arg.startswith('->'):
                
                # Parse the note line into fields and add to dictionary.
                dct[name]['arguments'][arg_name]['notes'] \
                    = re.split("\*\*NOTE:\*\*", arg, flags=re.IGNORECASE)
        
    except Exception:
        logger(markdown)
        logger(repr(traceback.format_exc()))
        return dct

    try:
        # Extract Attributes
        for attr in re.split("## Attribute* Reference", 
                            markdown, 
                            flags=re.IGNORECASE)[1].\
                    split("##")[0].\
                    split("\n"):
            
            # Look for bullets
            if attr.startswith('* `'):
                
                # Parse the line and add fields to dictionary
                dct[name]['attributes'].update({attr.split("`")[1] : {
                    "description" : attr.split("- ")[1]
                    }})
    except Exception:
        logger(markdown)
        logger(repr(traceback.format_exc()))

    try:
        # Extract Timeouts
        for timeouts in re.split("## Timeout*", 
                            markdown, 
                            flags=re.IGNORECASE)[1].\
                    split("##")[0].\
                    split("\n"):
            
            # Look for bullets
            if timeouts.startswith('* `'): 
                if len(timeouts.split(") ")) > 1:
                    dct[name]['timeouts'].update({timeouts.split("`")[1] : {
                                    "description" : timeouts.split(") ")[1],
                                    "required" : False,
                                    "timeout" : int(timeouts.split("(")[1].
                                                split(")")[0].split()[2]),
                                    }})
    except Exception:
        logger(markdown)
        logger(repr(traceback.format_exc()))
    
    try:
        # Extract Usage
        usage = re.split("## Example* Usage", 
                            markdown, 
                            flags=re.IGNORECASE)[1].\
                    split("##")[0].\
                    split("```hcl")[1].\
                    split("```")[0]

        dct[name].update({'usage': base64.b64encode(usage.encode())})
    except Exception:
        logger(markdown)
        logger(repr(traceback.format_exc()))

    try:
        # Extract Import
        imports = re.split("## Import*", 
                            markdown, 
                            flags=re.IGNORECASE)[1].\
                    split("```shell")[0].\
                    split("```")[0]
        
        dct[name].update({'import':base64.b64encode(imports.encode())})
    except Exception:
        logger(markdown)
        logger(repr(traceback.format_exc()))
    
    try:
        # Add Hashicorp Url
        html_url = metadata_dct.get('html_url')
        dct[name].update({'hcl_url': base64.b64encode(html_url.encode())})
    except:
        logger(markdown)
        logger(repr(traceback.format_exc()))

    return dct

def get_markdown(url):
    """ Get and return markdown from url

    This version will take a url and return a dictionary that contains the
    name and markdown.

    Args:
        url (string): web url to fetch markdown from

    Returns:
        dct (dict): dictionary containing name & markdown kv.
    """
    try:
        name = url.split("/")[-1].split(".")[0]
        request = requests.get(url)
        markdown = request.content.decode('utf8').strip('\n')
    
        dct = {'name': name,
               'markdown' : markdown
            }
    except:
        dct = {}
    finally:
        return dct

def process_resource(resource_dct):
    """ Process resource dictionary and create files

    This version will take a resource dictionary, get the markdown,
    process it into fields, merge with the yaml, write a new yaml,
    json and doc format.

    Args:
        resource_dct (dict): dictionary of info about the resource

    """
    try:
        # Fetch markdown from url
        markdown_dct = get_markdown(
                        resource_dct.get("download_url"))
    
        # Parse the markdown into fields
        dct = parse_markdown(markdown_dct,resource_dct)
    
        # Should only be one key but we don't know what it is
        # so lets loop and get a name.
        for name in dct.keys():

            # Get the provider from the 'layout field'
            provider = dct[name].get('layout')
        
            # Create the filenames for the yaml & json
            yaml_file = 'config/'+provider+'/'+name+'.yml'
            json_file = 'data/'+provider+'/'+name+'.json'
        
            # Do the open / merge / write op with the yaml.
            yaml_dct = open_yaml(yaml_file)
            merged_dct = merge_dictionaries(dct,yaml_dct)
            write_yaml(yaml_file,merged_dct)
        
            # Now remove the binary fields and write the json.
            delete_keys_from_dict(merged_dct,
                                  ['usage',
                                  'import',
                                  'hcl_url'
                                ])
            write_json(json_file,merged_dct)
    except:
        tmp = {}

def get_resources(provider_lst):
    """ Grabs a json blob from the github API for each provider in list

    This version will take a url and grab the json information from
    it.

    Args:
        url (dict): url to go after.

    """

    for provider in provider_lst:
        url_pre = "https://api.github.com/repos/terraform-providers/"\
                  "terraform-provider-"
        url_post = "/contents/website/docs/r"

        url = url_pre + provider + url_post
    
        # Loop through all resources at url
        for resource_dct in requests.get(url).json():
            process_resource(resource_dct)
       
def get_providers():
    
    dct = {}
    # Handle Githubs Pagination
    x = 1
    url = 'https://api.github.com/users/terraform-providers/repos?per_page=100&page='
    while requests.get(url+str(x)).json():
        
        for provider_dct in requests.get(url+str(x)).json():
            
            if 'terraform-provider' in provider_dct.get("name"):
                name = provider_dct.get("name").split('-')[2]
                description = provider_dct.get("description")
                html_url = provider_dct.get("url")
                status = "disabled"
                dct.update({name: 
                                {'description': description,
                                 'status' : status,
                                 'url' : html_url
                                }})

        x = x + 1
    
    # Process the providers, merge and write yaml/json
    lst = process_provider(dct)
    
    # Return the list
    return lst

def process_provider(provider_dct):
    
    yaml_file = 'config/providers.yaml'
    json_file = 'data/providers.json'
    yaml_dct = open_yaml(yaml_file)
    merged_dct = merge_dictionaries(provider_dct,yaml_dct)
    write_yaml(yaml_file,merged_dct)
    write_json(json_file,merged_dct)

    # Create a list of active providers
    lst = []
    for provider in merged_dct:
        if (merged_dct[provider].get('status') == 'enabled'):
            lst.append(provider)
    
    return lst

def logger(msg):
    global debug
    if debug:
        #print(msg)
        with open("debug.log", "a") as myfile:
            myfile.write(msg)

def yaml_to_json():
    for dirpath, subdirs, files in os.walk("."):
        for f in files:
            if f.endswith(".yml") or f.endswith(".yaml"):
                
                file_path = os.path.join(dirpath, f)
                # Read in the yaml
                with open(file_path, 'r') as stream:
                    try:
                        dct = yaml.safe_load(stream)
                    except Exception:
                        traceback.print_exc()
                        continue
                
                # Remove the binary
                delete_keys_from_dict(dct,
                                  ['usage',
                                  'import',
                                  'hcl_url'
                                ])
                
                # Spit out the json
                json_file = file_path.replace(".yml",".json")
                json_file = json_file.replace(".yaml",".json")
                json_file = json_file.replace("config","data")

                with open(json_file, 'w') as f:
                    try:
                        json.dump(dct, f, indent=4)
                    except:
                        traceback.print_exc()
                        continue

debug=True

#providers_lst = get_providers()

#get_resources(providers_lst)

yaml_to_json()

# This section is for debugging markdown processing failures by referencing markdown files directly.

#debug_dct = {
# 'download_url': 'https://raw.githubusercontent.com/terraform-providers/terraform-provider-azurerm/master/website/docs/r/resource_group.html.markdown'
# 'html_url': 'www.google.com'
# }
#process_resource(debug_dct)