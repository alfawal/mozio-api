# Mozio API Client Python Script

This Python script interacts with the Mozio API to perform a series of operations, such as searching for transportation services, booking a ride, and cancelling a reservation. The script is well-documented and easy to follow, and it requires the use of environment variables for the Mozio API key and base URL.

_You can also check out [this PR](https://github.com/alfawal/mozio-api/pull/1) that was pushed after submitting. An alternative way (my preferred) to handle operations._

## Prerequisites

Before running this script, ensure you have the following prerequisites:

1. Python 3.11 installed on your system.

## Setup

1. Clone this repository to your local machine.

```bash
git clone https://github.com/alfawal/mozio-api.git
```

2. Navigate to the project directory.

```bash
cd mozio-api
```

3. Create a new virtual environment.

```bash
python3 -m venv venv
```

4. Activate the virtual environment.

   - MacOS/Linux:

   ```bash
   source venv/bin/activate
   ```

   - Windows (Command Prompt (CMD)):

   ```bash
   venv\Scripts\activate
   ```

5. Install the required Python packages.

```bash
pip3 install -r requirements.txt
```

## Configuration

Adjust the environment variables in the `.env` file.

## How to Run

Simply execute the script using Python:

```bash
python3 main.py
```

Example output:

```bash
Calling the search endpoint... Done
Calling the poll search endpoint... Done (2 search poll requests)
Calling the booking (reservation) endpoint... Done (2 reservation poll requests)
	- Confirmation Number: SRYDE2500112777
	- Reservation ID: aba394f448fa4da0b15221baf1dcd4a1
Calling the cancellation endpoint... Done
```

## Script Flow

1. The script imports the required modules, initializes necessary environment variables, and defines custom exceptions.
2. The `MozioAPIClient` class is defined, which serves as a wrapper around the Mozio API endpoints. It handles authentication, API calls, and error handling.
3. The script instantiates a `Faker` object to generate fake data and initializes the Mozio API client.
4. The script performs the following steps:

   a. **Search:** The script calls the Mozio API to search for available transportation services. It provides relevant search parameters, such as start and end addresses, pickup date and time, number of passengers, currency, and campaign name. The API call returns a search ID and other search-related details.

   b. **Poll Search:** The script calls the poll search endpoint to retrieve the search results for the previously obtained search ID. It collects all the results from multiple API calls, waiting for two seconds between each call, until no more results are available, or the limit of retries is reached (20).

   c. **Book:** The script picks the cheapest vehicle available from the search results and uses it to book a ride. It generates fake user data, such as first name, last name and email. The script also provides an airline IATA code, flight number, phone number, and the selected vehicle's result ID and search ID.

   d. **Poll Reservation:** The script calls the poll reservation endpoint to check the status of the booking made earlier. It waits for two seconds between each call and continues polling (the limit of retries is 20) until the reservation status changes from "pending" to either "completed" or any other status indicating failure.

   e. **Cancel:** If the reservation was successful, the script calls the cancellation endpoint to cancel the reservation, using the reservation ID obtained from the booking step.
