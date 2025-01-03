import os
import re
import requests
import argparse
from tqdm import tqdm

from ckanapi import RemoteCKAN
from dotenv import load_dotenv


class Resource:
    """
    Represents a resource in a linked sequence, such as those used in CKAN datasets.

    A `Resource` object contains details about a resource's ID, name, URL, and its relationship
    to other resources in a sequence. This includes pointers to its predecessor (`predecessor`) and
    successor (`successor`) resources and whether it is the "head" of the sequence.

    Attributes:
        resource_id (str): The unique identifier for the resource.
        resource_name (str): The name of the resource.
        resource_url (str): The URL of the resource.
        predecessor (str, optional): The ID of the preceding resource in the sequence. Defaults to `None`.
        head (bool, optional): Indicates if this resource is the "head" of the sequence. Defaults to `False`.
        successor (str, optional): The ID of the succeeding resource in the sequence. Defaults to `None`.

    Methods:
        __str__():
            Returns a string representation of the resource, including its attributes.
    """

    def __init__(self, resource_id: str, resource_name: str, resource_url: str, dataset_id: str, predecessor: str = None, head: bool = False, successor: str = None):
        """
        Initializes a new `Resource` instance.

        Args:
            resource_id (str): The unique identifier for the resource.
            resource_name (str): The name of the resource.
            resource_url (str): The URL of the resource.
            predecessor (str, optional): The ID of the preceding resource in the sequence. Defaults to `None`.
            head (bool, optional): Indicates if this resource is the "head" of the sequence. Defaults to `False`.
            successor (str, optional): The ID of the succeeding resource in the sequence. Defaults to `None`.
        """
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.resource_url = resource_url
        self.head = head
        self.predecessor = predecessor
        self.successor = successor
        self.dataset_id = dataset_id

    def __str__(self) -> str:
        """
        Returns a string representation of the resource.

        The string includes the resource's ID, name, predecessor ID (`predecessor`), whether it's the head,
        and the ID of its successor.

        Returns:
            str: A formatted string containing the resource's attributes.
        """
        return (f"Resource ID: {self.resource_id}\n"
                f"Resource Name: {self.resource_name}\n"
                f"predecessor: {self.predecessor}\n"
                f"Head: {self.head}\n"
                f"Successor: {self.successor}\n")
   

def extract_resource_id(url):
    """
    Extracts the resource ID from a CKAN resource URL.

    Args:
        url (str): The CKAN resource URL.

    Returns:
        str: The extracted resource ID, or None if not found.
    """
    try:
        match = re.search(r'/resource/([a-f0-9\-]+)/', url)
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        print(f"Error extracting resource ID: {e}")
        return None

def find_resources(response: dict, resource_name: str, invalid_resource: dict) -> list:
    """
    Extracts and constructs a list of `Resource` objects from a CKAN API response.

    This function parses the `response` from a CKAN resource search to identify and construct
    resources based on their IDs, names, URLs, and relationships to other resources. It also
    determines if a resource is the "head" of the chain by checking if it points to itself.

    Args:
        response (dict): The response dictionary from the CKAN API, which includes a `results` key
                         containing details of the resources.
        resource_name (str): The name of the resource to find, used for logging or debugging purposes.

    Returns:
        list: A list of `Resource` objects, each representing a resource in the response. If no
              resources are found, an empty list is returned.

    Notes:
        - The function assumes a helper function `extract_resource_id(url: str)` is available to extract 
          the resource ID from a URL.
        - The `Resource` class is expected to have a constructor with attributes for `id`, `name`, 
          `url`, `predecessor`, and `head`.

    Example:
        >>> response = {
        ...     "results": [
        ...         {"id": "1234", "name": "example.txt", "url": "http://example.com/resource/5678"},
        ...         {"id": "5678", "name": "example2.txt", "url": "http://example.com/resource/5678"}
        ...     ]
        ... }
        >>> resources = find_resources(response, "example.txt")
        >>> for resource in resources:
        ...     print(resource)
    """
    resources = []
    if response.get('results'):
        for result in response['results']:
            # extracting the ID of the resource which is pointed to
            prev_resource_id = extract_resource_id(result['url'])  # this will return None for the faulty url/resource
            # if the resource id "points" to itself, then it's the head 
            # because that is how the urls work in ckan
            r = Resource(
                resource_id= result['id'], 
                resource_name=result['name'],
                resource_url=result['url'],
                dataset_id=result['package_id'],
            )
            if result['id'] == prev_resource_id:
                r.predecessor = None
                r.head = True
                resources.append(r)
            else:
                r.predecessor = prev_resource_id
                r.head = False
                resources.append(r)
                resources.append(r)
        
        # BUG? if id of invalid resource is not in the list of resources, then add the invalid resource to the list of resources
        if invalid_resource.resource_id not in [res.resource_id for res in resources]:
            resources.append(invalid_resource)
        return resources
    else:
        print(f"No resources found for {resource_name}")
        return []

def find_faulty_and_last_resource(resources: list) -> tuple:
    """
    Identifies the faulty and last resources in a list of `Resource` objects and fixes their pointers.

    This function processes a list of `Resource` objects to determine relationships between them
    by setting the `successor` attribute. It then identifies:
    - The "faulty" resource, which is neither the head nor has a valid `predecessor` pointer.
    - The "last" resource in the sequence, which has no `successor`.

    Once identified, the function updates the `predecessor` pointer of the faulty resource to point to
    the last resource and sets the `successor` pointer of the last resource to point to the faulty resource.

    Args:
        resources (list): A list of `Resource` objects. Each `Resource` object must have the attributes
                          `resource_id`, `predecessor`, `successor`, and `head`.

    Returns:
        tuple: A tuple containing two `Resource` objects:
               - `faulty_res`: The faulty resource with a fixed `predecessor` pointer.
               - `last_res`: The last resource with a fixed `successor` pointer.

    Example:
        >>> resources = [
        ...     Resource("1234", "example1.txt", "http://example.com/resource/1234", predecessor=None, head=True),
        ...     Resource("5678", "example2.txt", "http://example.com/resource/5678", predecessor="1234", head=False),
        ...     Resource("9999", "example3.txt", "http://example.com/resource/9999", predecessor=None, head=False)
        ... ]
        >>> faulty_res, last_res = find_faulty_and_last_resource(resources)
        >>> print(faulty_res)
        >>> print(last_res)
    """
    # finding the successors of each resource
    predecessor_map = {res.predecessor: res for res in resources if res.predecessor is not None}
    for res in resources:
        if res.resource_id in predecessor_map:
            res.successor = predecessor_map[res.resource_id].resource_id


    # identify the faulty resource
    faulty_res = next((res for res in resources if res.predecessor is None and res.head is False), None)
    # identify the last resource
    last_res = next((res for res in resources if res.successor is None), None)
    
    # fix pointers for the faulty and last resources
    if faulty_res and last_res:
        faulty_res.predecessor = last_res.resource_id
        last_res.successor = faulty_res.resource_id
    return faulty_res, last_res


def create_correct_url(response, faulty_res: Resource) -> str:
    """
    Generates a corrected URL for a resource based on its `predecessor` attribute.

    This function retrieves the dataset ID associated with the resource using 
    CKAN's `resource_show` method and constructs a new URL for the resource.

    Args:
        faulty_res (Resource): The resource object that contains details about the resource,
                               including its `predecessor` ID and `resource_name`.

    Returns:
        str: The corrected URL for the resource in the format:
             "https://data.coat.no/dataset/{dataset_id}/resource/{resource_id}/download/{resource_name}"

    """
    # finding the package id for the previous resource
    resource_name = faulty_res.resource_name.lower()
    dataset_id = response['package_id']
    resource_id = faulty_res.predecessor

    # create the new URL
    new_url = f"https://data.coat.no/dataset/{dataset_id}/resource/{resource_id}/download/{resource_name}"
    return new_url


def get_invalid_resources(ckan: RemoteCKAN, dataset_id: str) -> list:
    invalid_resources = []
    dataset = ckan.action.package_show(id=dataset_id)
    for resource in dataset.get("resources", []):
        resource_url = resource.get("url", "")
        try:
            r = requests.head(resource_url)
        except Exception as _:
            r = Resource(
                resource_id=resource.get("id"),
                resource_name=resource.get("name"),
                resource_url=resource_url,
                dataset_id=dataset_id
            )
            invalid_resources.append(r)
    

    if len(invalid_resources) > 0:
        print(f"Dataset {dataset['name']}")
        print(f"Dataset id: {dataset_id}")
        print(f"Found {len(invalid_resources)} invalid resources")
        return invalid_resources
    else:
        return []
        

def update_resources(ckan, invalid_resources):
    for invalid_resource in tqdm(invalid_resources[:3], desc="Updating resources"):
        resource_name = invalid_resource.resource_name.lower()
        response = ckan.action.resource_search(query=f"name:{resource_name}")
        resources = find_resources(response, resource_name, invalid_resource)
        faulty_res, last_res = find_faulty_and_last_resource(resources)
        
        if faulty_res is None or last_res is None:
            print(f"Could not find faulty or last resource for {resource_name}")
            continue
        response = ckan.action.resource_show(id=faulty_res.predecessor)  
        fixed_url = create_correct_url(response, faulty_res)
        
        # use 302, because that's the http response when it's correct
        r = requests.head(fixed_url)
        if r.status_code == 302:
            updated_resource = {
                "id": faulty_res.resource_id,
                "url": fixed_url
            }
            _ = ckan.action.resource_patch(
                **updated_resource
            )
        else:
            print(f"Resource {resource_name} could not be fixed")

def main():
    load_dotenv()
    ckan_site_url = os.getenv("CKAN_SITE_URL")
    token = os.getenv("CKAN_USER_API_TOKEN")
    ckan = RemoteCKAN(ckan_site_url, apikey=token)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_id", help="The dataset ID to fix")
    args = parser.parse_args()
    #dataset_id = ''
    invalid_resources = get_invalid_resources(ckan=ckan, dataset_id=args.dataset_id)
    update_resources(ckan=ckan, invalid_resources=invalid_resources)
    

if __name__ == "__main__":
    main()