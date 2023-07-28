import os
import time
from typing import Any, Union

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
    def __init__(self) -> None:
        self.api_key = os.getenv("MOZIO_API_KEY")
        if not self.api_key:
            raise EnvironmentVariableNotSet(
                "The MOZIO_API_KEY environment variable is not set and is required to run this script."
            )
        self.base_url = (
            # Add a trailing slash to the base URL if it doesn't have one
            env_base_url.rstrip("/") + "/"
            if (env_base_url := os.getenv("MOZIO_API_BASE_URL"))
            else None
        )
        if not self.base_url:
            raise EnvironmentVariableNotSet(
                "The MOZIO_API_BASE_URL environment variable is not set and is required to run this script."
            )
        self.headers = {"API-KEY": self.api_key}

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


if __name__ == "__main__":
    init(autoreset=True)

    fake = Faker(locale="en_US")
    mozio = MozioAPIClient()

    # Search
    search_payload = {
        "start_address": "44 Tehama Street, San Francisco, CA, USA",
        "end_address": "SFO",
        "mode": "one_way",
        "pickup_datetime": "2023-12-01 15:30",
        "num_passengers": 2,
        "currency": "USD",
        "campaign": "Abdulrahman Alfawal",
    }

    print("Calling the search endpoint...", end=" ")
    search_response = mozio.search(search_payload)
    print(Fore.GREEN + "Done")

    # Use the search_id from the search response in the poll_search method.
    # Call the poll search endpoint and collect the results from it until
    # the "more_coming" field is False, sleeping for 2 seconds between each call.
    # Limit the number of calls to 5.
    print("Calling the poll search endpoint...", end=" ")

    search_id = search_response["search_id"]
    has_more_results = True
    all_poll_results = []
    search_poll_requests_counter = 0

    while has_more_results:
        if search_poll_requests_counter > 20:
            raise Exception("The search poll requests counter exceeded the limit of 20.")
        search_poll_requests_counter += 1

        poll_search_response = mozio.poll_search(search_id)
        all_poll_results.extend(poll_search_response["results"])

        has_more_results = poll_search_response["more_coming"]
        if has_more_results:
            time.sleep(2)

    print(Fore.GREEN + "Done" + Fore.YELLOW + f" ({search_poll_requests_counter} search poll requests)")

    # Book
    # Pick the cheapest vehicle available.
    cheapest_vehicle = min(
        all_poll_results,
        key=lambda vehicle: vehicle["total_price"]["total_price"]["value"],
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

    print("Calling the booking (reservation) endpoint...", end=" ")
    book_response = mozio.book(book_payload)
    is_pending_reservation = True
    confirmation_number, reservation_id = "", ""
    reservation_poll_requests_counter = 0

    # Call the poll_reservation endpoint and check the status of the reservation
    # until it's either completed or failed, sleeping for 2 seconds between each call.
    # Limit the number of calls to 5.
    while is_pending_reservation:
        if reservation_poll_requests_counter > 20:
            raise Exception("The reservation poll requests counter exceeded the limit of 20.")
        reservation_poll_requests_counter += 1
        poll_reservation_response = mozio.poll_reservation(search_id)
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
                Fore.GREEN + "Done" + Fore.YELLOW + f" ({reservation_poll_requests_counter} reservation poll requests)"
            )
            print(Fore.CYAN + f"\t- Confirmation Number: {confirmation_number}\n\t- Reservation ID: {reservation_id}")
        else:
            print(Fore.RED + "Failed" + Fore.YELLOW + f" (Status: {poll_reservation_status})")

    # Cancel
    if not confirmation_number or not reservation_id:
        print(Fore.CYAN + "Skipping the cancellation.")
    else:
        print("Calling the cancellation endpoint...", end=" ")
        has_been_cancelled = mozio.cancel(reservation_id)
        if has_been_cancelled:
            print(Fore.GREEN + "Done")
        else:
            print(Fore.RED + "Failed")
