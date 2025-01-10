import os
import re
import requests
import argparse
import logging
from logging import Logger

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

def find_resources(response: dict, resource_name: str, invalid_resource: dict, logger: Logger) -> list:
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
    """
    resources = []
    if response.get('results'):
        for result in response['results']:
            # extracting the ID of the resource which is pointed to
            prev_resource_id = extract_resource_id(result['url'])  # this will return None for the faulty url/resource
            # if the resource id "points" to itself, then it's the head 
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
        logger.error(f"No resources found for {resource_name}")
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


def get_invalid_resources(ckan: RemoteCKAN, dataset_id: str, logger: Logger) -> list:
    """
    Identifies invalid resources in a CKAN dataset.

    Parameters:
        ckan (RemoteCKAN): An authenticated CKAN client used to interact with the CKAN instance.
        dataset_id (str): The unique identifier of the dataset to check for invalid resources.
        logger (Logger): A logger instance for logging messages.

    Returns:
        list: A list of invalid resources, each represented as a `Resource` object.

    Notes:
        - A resource is considered invalid if its URL cannot be validated with a HEAD request.
        - Logs the dataset name, ID, and the number of invalid resources if any are found.
    """
    invalid_resources = []
    dataset = ckan.action.package_show(id=dataset_id)
    for resource in dataset.get("resources", []):
        # to find the faulty resources, check if the url is valid
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
        logger.info(f"Dataset: {dataset['name']}")
        logger.info(f"Dataset id: {dataset_id}")
        logger.info(f"Found {len(invalid_resources)} invalid resources")
        return invalid_resources
    else:
        return []
        

def update_resources(ckan: RemoteCKAN, invalid_resources: list, logger: Logger):
    """
    Updates the URLs of invalid resources in a CKAN dataset.

    This function iterates over a list of invalid resources, finds the associated 
    faulty and last valid resource, generates a corrected URL, and updates the resource
    in CKAN if the URL is valid.

    Parameters:
        ckan (RemoteCKAN): An authenticated CKAN client used to interact with the CKAN instance.
        invalid_resources (List): A list of invalid resources to be updated. Each resource is 
                                  expected to have details such as `resource_name`.
        logger (Logger): A logger instance to log messages during the process.
    
    Notes:
        - Uses `requests.head` to validate the corrected URL.
        - Logs errors for resources that cannot be fixed or updated.
    """
    for invalid_resource in tqdm(invalid_resources, desc="Updating resources"):
        resource_name = invalid_resource.resource_name.lower()
        response = ckan.action.resource_search(query=f"name:{resource_name}")
        resources = find_resources(response, resource_name, invalid_resource, logger)
        faulty_res, last_res = find_faulty_and_last_resource(resources)
        
        if faulty_res is None or last_res is None:
            logger.error(f"Could not find faulty or last resource for {resource_name} ({invalid_resource.resource_id})")
            continue
        response = ckan.action.resource_show(id=faulty_res.predecessor)  
        fixed_url = create_correct_url(response, faulty_res)
        
        r = requests.head(fixed_url)
        try:
            if r.status_code == 302 or r.status_code == 200:
                updated_resource = {
                    "id": faulty_res.resource_id,
                    "url": fixed_url
                }
                _ = ckan.action.resource_patch(
                    **updated_resource
                )
                logger.info(f"Resource {resource_name} ({invalid_resource.resource_id}) updated successfully.")
                logger.info(f"New url: {fixed_url}")
            else:
                logger.error(f"Resource {resource_name} ({invalid_resource.resource_id})could not be fixed new url.")
                logger.error(f"New url: {fixed_url}")
                logger.error(f"Status code: {r.status_code}")
        except Exception as e:
            logger.error(f"Not able to update resource {resource_name}: {e}")
            logger.error(f"New url: {fixed_url}")
            continue

def main():
    load_dotenv(dotenv_path="utils/fix-resource-urls/.env")
    ckan_site_url = os.getenv("CKAN_SITE_URL")
    api_key = os.getenv("CKAN_USER_API_KEY")
    log_file_path = os.getenv("LOG_FILE_PATH", "fix_resources.log")  # Default if not provided
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    logging.basicConfig(
        level=logging.INFO, 
        format='[%(levelname)s] %(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler("utils/fix-resource-urls/fix_resources.log", mode='w'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()

    ckan = RemoteCKAN(ckan_site_url, apikey=api_key)
    
    if ckan_site_url == "https://data.coat.no":
        logger.warning("You are running this script on the production server.")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_id", help="The dataset ID to fix")
    args = parser.parse_args()

    dataset = ckan.action.package_show(id=args.dataset_id)
    if dataset.get("private"):
        invalid_resources = get_invalid_resources(ckan=ckan, dataset_id=args.dataset_id, logger=logger)
        if invalid_resources:
            update_resources(ckan=ckan, invalid_resources=invalid_resources, logger=logger)
        else:
            logger.warning(f"No invalid resources found for dataset {args.dataset_id}")
    else:
        logger.error(f"Dataset is not private ({args.dataset_id})")
        
        

if __name__ == "__main__":
    main()