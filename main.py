import os
import time
from typing import Any, Optional, Union

import requests
from colorama import Fore, init
from dotenv import load_dotenv
from faker import Faker

load_dotenv(dotenv_path="./.env")

JSONResponseType = Union[dict[str, Any], list[dict[str, Any]]]


class EnvironmentVariableNotSet(BaseException):
    """Raised when an environment variable is not set."""

    pass


class MozioAPIClient:
    BASE_URL = os.getenv("MOZIO_API_BASE_URL")
    API_KEY = os.getenv("MOZIO_API_KEY")
    POLL_MAX_REQUESTS = 20

    def __init__(self) -> None:
        if not MozioAPIClient.BASE_URL:
            raise EnvironmentVariableNotSet("MOZIO_API_BASE_URL environment variable is not set.")

        if not MozioAPIClient.API_KEY:
            raise EnvironmentVariableNotSet("MOZIO_API_KEY environment variable is not set.")

        self.base_url = MozioAPIClient.BASE_URL.rstrip("/") + "/"
        self.headers = {"API-KEY": MozioAPIClient.API_KEY}

    def search(self, payload: dict) -> JSONResponseType:
        """Handles the v2_search_create endpoint.

        Read more:
        https://api-testing.mozio.com/v2/docs/#tag/v2/operation/v2_search_create
        """
        url = f"{self.base_url}search/"
        response = requests.post(url, headers=self.headers, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.json())

        return response.json()

    def poll_search(self, search_id: str) -> JSONResponseType:
        """Handles the Poll Search endpoint.

        Read more:
        https://api-testing.mozio.com/v2/docs/#tag/v2/operation/v2_search_poll_retrieve
        """
        url = f"{self.base_url}search/{search_id}/poll/"
        response = requests.get(url, headers=self.headers, timeout=10)
        if not response.ok:
            raise Exception(response.json())

        return response.json()

    def book(self, payload: dict) -> JSONResponseType:
        """Handles the v2_reservations_create endpoint.

        Read more:
        https://api-testing.mozio.com/v2/docs/#tag/v2/operation/v2_reservations_create
        """
        url = f"{self.base_url}reservations/"
        response = requests.post(url, headers=self.headers, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.json())

        return response.json()

    def poll_reservation(self, search_id: str) -> JSONResponseType:
        """Handles the v2_reservations_poll_retrieve endpoint.

        Read more:
        https://api-testing.mozio.com/v2/docs/#tag/v2/operation/v2_reservations_poll_retrieve
        """
        url = f"{self.base_url}reservations/{search_id}/poll/"
        response = requests.get(url, headers=self.headers, timeout=10)
        if not response.ok:
            raise Exception(response.json())

        return response.json()

    def cancel(self, reservation_id: str) -> bool:
        """Handles the v2_reservations_destroy endpoint.

        Read more:
        https://api-testing.mozio.com/v2/docs/#tag/v2/operation/v2_reservations_destroy
        """
        url = f"{self.base_url}reservations/{reservation_id}"
        response = requests.delete(url, headers=self.headers, timeout=10)
        if not response.ok:
            raise Exception(response.json())

        return True

    def search_and_gather_results(self, search_payload: dict) -> tuple[str, list[Optional[dict[str, Any]]]]:
        """Searches and gathers the results from the poll search endpoint.

        Calls the search endpoint and then calls the poll search endpoint with the obtained search_id
        until the search results are all gathered, sleeping for 2 seconds between each call, with a maximum
        of MozioAPIClient.POLL_MAX_REQUESTS calls.

        Args:
            search_payload (dict): The search payload to be used in the search endpoint.

        Returns:
            tuple[str, list[Optional[dict[str, Any]]]]: The search_id and the list of results.

        Raises:
            Exception: If the search poll requests exceeded the limit of MozioAPIClient.POLL_MAX_REQUESTS.
        """
        print("Calling the search endpoint...", end=" ")
        search_response = self.search(search_payload)
        print(Fore.GREEN + "Done")

        print("Calling the poll search endpoint...", end=" ")

        search_id = search_response["search_id"]
        all_poll_results = []

        for search_poll_requests_counter in range(1, MozioAPIClient.POLL_MAX_REQUESTS + 1):
            poll_search_response = mozio.poll_search(search_id)
            all_poll_results.extend(poll_search_response["results"])

            has_more_results = poll_search_response["more_coming"]
            if not has_more_results:
                print(Fore.GREEN + "Done" + Fore.YELLOW + f" ({search_poll_requests_counter} search poll requests)")
                break

            time.sleep(2)
        else:
            raise Exception(f"The search poll requests exceeded the limit of {MozioAPIClient.POLL_MAX_REQUESTS}.")

        return search_id, all_poll_results

    def book_and_get_status(self, search_id: str, book_payload: dict) -> Optional[str]:
        """Books and gets the status of the reservation.

        Calls the book endpoint and then calls the poll_reservation endpoint until the reservation
        status is either failed or completed, sleeping for 2 seconds between each call, with a maximum
        of MozioAPIClient.POLL_MAX_REQUESTS calls.

        Args:
            search_id (str): The search_id to be used in the poll_reservation endpoint.
            book_payload (dict): The book payload to be used in the book endpoint.

        Returns:
            Optional[str]: The reservation_id if the reservation is completed, otherwise None.

        Raises:
            Exception: If the reservation poll requests exceeded the limit of MozioAPIClient.POLL_MAX_REQUESTS.
        """
        print("Calling the booking (reservation) endpoint...", end=" ")
        self.book(book_payload)

        reservation_id = None
        for reservation_poll_requests_counter in range(1, MozioAPIClient.POLL_MAX_REQUESTS + 1):
            poll_reservation_response = self.poll_reservation(search_id)
            poll_reservation_status = poll_reservation_response.get("status", "").lower()

            is_pending_reservation = poll_reservation_status == "pending"
            is_completed_reservation = poll_reservation_status == "completed"

            if is_pending_reservation:
                time.sleep(2)
            elif is_completed_reservation:
                reservation = poll_reservation_response["reservations"][0]
                confirmation_number = reservation["confirmation_number"]
                reservation_id = reservation["id"]
                print(
                    Fore.GREEN
                    + "Done"
                    + Fore.YELLOW
                    + f" ({reservation_poll_requests_counter} reservation poll requests)"
                )
                print(
                    Fore.CYAN + f"\t- Confirmation Number: {confirmation_number}\n\t- Reservation ID: {reservation_id}"
                )
                break
            else:
                print(Fore.RED + "Failed" + Fore.YELLOW + f" (Status: {poll_reservation_status})")
                break
        else:
            raise Exception(f"The reservation poll requests exceeded the limit of {MozioAPIClient.POLL_MAX_REQUESTS}.")
        return reservation_id


if __name__ == "__main__":
    init(autoreset=True)

    fake = Faker(locale="en_US")
    mozio = MozioAPIClient()

    # Search with the following payload
    search_payload = {
        "start_address": "44 Tehama Street, San Francisco, CA, USA",
        "end_address": "SFO",
        "mode": "one_way",
        "pickup_datetime": "2023-12-01 15:30",
        "num_passengers": 2,
        "currency": "USD",
        "campaign": "Abdulrahman Alfawal",
    }

    search_id, all_search_results = mozio.search_and_gather_results(search_payload)
    if not all_search_results:
        raise Exception("No results found with the given search payload.")

    # Book
    # Pick the cheapest vehicle available and book it.
    cheapest_vehicle = min(
        all_search_results,
        key=lambda vehicle: float(vehicle["total_price"]["total_price"]["value"]),
    )
    book_payload = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "country_code_name": "US",
        "phone_number": "(855) 980 5669",
        "airline_iata_code": "UA",
        "flight_number": "1201",
        "result_id": cheapest_vehicle["result_id"],
        "search_id": search_id,
        # "provider": "Dummy External Provider",
    }

    reservation_id = mozio.book_and_get_status(search_id, book_payload)

    # Cancel
    if not reservation_id:
        print(Fore.CYAN + "Skipping the cancellation.")
    else:
        print("Calling the cancellation endpoint...", end=" ")
        has_been_cancelled = mozio.cancel(reservation_id)
        if has_been_cancelled:
            print(Fore.GREEN + "Done")
        else:
            print(Fore.RED + "Failed")
