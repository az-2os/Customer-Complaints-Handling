"""
This module is a CFPB API client that allows you to interact with the CFPB (Consumer Financial Protection Bureau) API.

It provides functions to retrieve data from the CFPB API, such as consumer complaints, financial products, and more.

Usage:
    - Import the module: `import cfpb_api_client`
    - Initialize the client: `client = cfpb_api_client.CFPBAPIClient()`
    - Use the client's methods to interact with the CFPB API

Note: Make sure to install the required dependencies before using this module.

Dependencies:
    - requests: HTTP library for making API requests

"""

import requests
import json


class CFPBApiClient:
    # Some common company names for financial institutions in correct format for easy search
    COMPANY_NAMES = [
        "JPMORGAN CHASE & CO.",
        "BANK OF AMERICA, NATIONAL ASSOCIATION",
        "CITIBANK, N.A.",
        "WELLS FARGO & COMPANY",
        "U.S. BANCORP",
        "PNC Bank N.A.",
        "GOLDMAN SACHS BANK USA",
        "TRUIST FINANCIAL CORPORATION",
        "CAPITAL ONE FINANCIAL CORPORATION",
        "TD BANK US HOLDING COMPANY",
    ]


    def __init__(self):
        self.base_url = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
        # You can also initialize common headers or authentication tokens here if needed


    def search_complaints(self, **kwargs):
        """
        Search for complaints against financial institutions in the CFPB database.

        Parameters:
        - search_term (str): Return results containing a specific term.
        - field (str): Specify the field to be searched with "search_term".
        - frm (int): Results offset to return results starting from a specific index.
        - size (int): Limit the size of the results.
        - sort (str): Order to sort the results.
        - format (str): Format of the returned data (e.g., "json", "csv").
        - has_narrative (bool): Filter results by whether they have a narrative or not. (e.g. true/false in string format)
        - no_aggs (bool): Include aggregations in result or not.
        - no_highlight (bool): Include highlight of search term in result or not.
        - company (list[str]): Filter results by company names.
        - company_public_response (list[str]): Filter results by types of public response.
        - company_received_max (str): Return results with date < this value.
        - company_received_min (str): Return results with date >= this value.
        - and so on for all other parameters as outlined in the API documentation here (https://cfpb.github.io/ccdb5-api/documentation/#/Complaints/get_).
        
        Returns:
        A JSON object containing the search results or an error message.
        """
        valid_params = ["search_term", "field", "frm", "size", "sort", "format", "no_aggs", "no_highlight",
                        "company", "company_public_response", "company_received_max", "company_received_min",
                        "company_response", "consumer_consent_provided", "consumer_disputed", "date_received_max",
                        "date_received_min", "has_narrative", "issue", "product", "state", "submitted_via", "tags",
                        "timely", "zip_code"]
        
        # Filter out invalid parameters
        params = {k: v for k, v in kwargs.items() if k in valid_params}
        print("Search Complaints\n", json.dumps(params, indent=2))
        
        # print out invalid parameters
        invalid_params = [k for k in kwargs.keys() if k not in valid_params]
        if invalid_params:
            print(f"Invalid parameters: {invalid_params}")

        response = requests.get(self.base_url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch data", "status_code": response.status_code}


    def get_complaint(self, complaintId):
        """
        Retrieve a specific complaint from the CFPB database.

        Parameters:
        - complaintId (str): The ID of the complaint to retrieve.

        Returns:
        A JSON object containing the complaint details or an error message.
        """
        url = f"{self.base_url}/{complaintId}"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch data", "status_code": response.status_code}
        

    def get_trend(self, **kwargs):
        """
        Retrieves trend data based on various filters from the API.

        Parameters:
        - search_term (str): Return results containing a specific term.
        - field (str): Specify the field to be searched with "search_term". Defaults to "complaint_what_happened".
        - company (list[str]): Filter results by company names.
        - company_public_response (list[str]): Filter results by types of public response.
        - company_received_max (str): Return results with date < this value.
        - company_received_min (str): Return results with date >= this value.
        - company_response (list[str]): Filter results by types of response by the company.
        - consumer_consent_provided (list[str]): Filter results by types of consumer consent provided.
        - consumer_disputed (list[str]): Filter results by consumer dispute status.
        - date_received_max (str): Return results with date < this value.
        - date_received_min (str): Return results with date >= this value.
        - focus (list[str]): Focus charts for products and issues on specified products or companies.
        - has_narrative (list[str]): Filter results by the presence of a narrative.
        - issue (list[str]): Filter results by specific issues or subissues.
        - lens (str): Data lens for viewing complaint trends. Required parameter.
        - product (list[str]): Filter results by product types.
        - state (list[str]): Filter results by state.
        - submitted_via (list[str]): Filter results by submission method.
        - sub_lens (str): Sub-lens for viewing trends.
        - sub_lens_depth (int): Depth for sub-lens trend aggregations.
        - tags (list[str]): Filter results by tags.
        - timely (list[str]): Filter results by timeliness of the response.
        - trend_depth (int): Depth for trend aggregations.
        - trend_interval (str): Time interval for trends aggregations. Required parameter.
        - zip_code (list[str]): Filter results by zip code.
        For full details see: (https://cfpb.github.io/ccdb5-api/documentation/#/Trends/get_trends)

        Returns:
        A JSON object containing the trend data or an error message.
        """
        valid_params = ["search_term", "field", "company", "company_public_response", "company_received_max",
                        "company_received_min", "company_response", "consumer_consent_provided", "consumer_disputed",
                        "date_received_max", "date_received_min", "focus", "has_narrative", "issue", "lens",
                        "product", "state", "submitted_via", "sub_lens", "sub_lens_depth", "tags", "timely",
                        "trend_depth", "trend_interval", "zip_code"]
        
        # Filter out invalid parameters
        params = {k: v for k, v in kwargs.items() if k in valid_params}
        print("Get Trend\n", json.dumps(params, indent=2))
        
        # print out invalid parameters
        invalid_params = [k for k in kwargs.keys() if k not in valid_params]
        if invalid_params:
            print(f"Invalid parameters: {invalid_params}")

        # Use trends endpoint
        response = requests.get(self.base_url + 'trends/', params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch data", "status_code": response.status_code}

# Usage example
if __name__ == "__main__":
    client = CFPBApiClient()
    # search_results = client.search_cfpb_complaints(
    #     company=client.COMPANY_NAMES[0],
    #     has_narrative="true",
    #     size=25,
    #     sort="created_date_desc",
    # )
    # print(search_results['hits']['hits'][0]['_source']['complaint_what_happened'])
    trend = client.get_trend(
        company=client.COMPANY_NAMES[0],
        has_narrative="true",
        lens='overview',
        trend_interval="month",
    )
    print(trend)

