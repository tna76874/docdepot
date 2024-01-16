# DocDepot - Depot for Files

### *API and Client*

This repository contains a simple file deposition API, "Depose Files," built using Flask. Additionally, there is a Python client, "DocDepot Client," that interacts with the API. Below is the documentation for both the API and the client.

## Depose Files API

### Getting Started

Follow these instructions to set up and run the Depose Files API on your local machine.

#### Prerequisites

Make sure you have Python 3.x installed on your machine.

#### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/tna76874/docdepot.git
   ```

2. Change to the project directory:

   ```
   cd docdepot
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

#### Usage

- Set environment variables:

  - `DOCDEPOT_API_KEY`: API key for authentication (default is "test").
  - `DOCDEPOT_SHOW_INFO`: Show additional information in HTML templates (default is "False").
  - `DOCDEPOT_SHOW_RESPONSE_TIME`: Show response time in HTML templates (default is "False").
  - `DOCDEPOT_SHOW_TIMESTAMP`: Show timestamp in HTML templates (default is "False").

- Run the application:

  ```
  python docdepot.py
  ```

  The API will be accessible at http://127.0.0.1:5000/.

### API Endpoints

- **POST /api/add_document**: Add a new document.
- **POST /api/generate_token**: Generate a new token for a document.
- **DELETE /api/delete_token**: Delete a token.
- **DELETE /api/delete_user**: Delete a user and associated documents, tokens, and files.
- **PUT /api/update_token_valid_until**: Update the 'valid_until' date of a token.
- **GET /api/average_time_for_all_users**: Retrieve the average time span for each user between document upload time and the first token event.
- **POST /api/rename_users**: Rename users.

#### Retrieving Documents

Access documents using their unique tokens:

- **GET /document/{token}**: Retrieve and serve the requested document.
- **GET /{token}**: Render the index page with document information.

## Building and Running with Docker

```bash
docker-compose up -d
```

The DocDepot API will be accessible at [http://localhost:5000](http://localhost:5000/).

## DocDepot Client

### Usage

The DocDepot Client is a Python script that interacts with the Depose Files API. You can use it to perform various actions such as uploading a document, generating tokens, deleting tokens or users, updating token validity, and retrieving average times for all users.

#### Prerequisites

Make sure you have Python 3.x installed on your machine.

#### Installation

1. Clone the repository as described above.
2. `pip install .`
3. Set the following environment variables:
   - `DOCDEPOT_API_KEY`: API key for authentication.
   - `DOCDEPOT_API_HOST`: Host URL for the Depose Files API (default is "[http://localhost:5000](http://localhost:5000/)").

#### Usage

Use the script from the command line with the following options:

```bash
ddclient --action <action> [additional options]
```

**Available Actions:**

- `upload`: Upload a PDF document.
- `generate_token`: Generate a new token for a document ID.
- `delete_token`: Delete a token.
- `delete_user`: Delete a user and associated documents, tokens, and files.
- `update_token_valid_until`: Update the 'valid_until' date of a token.
- `get_average_times`: Retrieve the average time span for each user between document upload time and the first token event.

**Additional Options:**

- `--host`: DocDepot server host URL (default is "[http://localhost:5000](http://localhost:5000/)").
- `--document_id`: Document ID for token-related actions.
- `--token_value`: Token value for token-related actions.
- `--valid_until`: New valid_until value for the `update_token_valid_until` action.
- `--user_uid`: User UID for user-related actions.
- `--file_path`: Path to the PDF file for the `upload` action.

**Example Usage:**

```bash
ddclient --action upload --title "My Document" --filename "document.pdf" --user_uid "user123" --file_path "/path/to/document.pdf"
```

This will upload a document to the Depose Files API.

For more information on available actions and options, run:

```bash
ddclient --help
```

### Contributing

Feel free to contribute to the project by opening issues or creating pull requests.

### License

This project is licensed under the GNU General Public License (GPL) version 3 - see the [LICENSE](LICENSE) file for details. 
