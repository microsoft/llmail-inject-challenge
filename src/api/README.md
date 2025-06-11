# API Server
The API server is designed to run on Azure Function Apps and (generally) employs one function per
API operation (which you'll find in the various folders here).

The API can be tested by doing the following:

1. Ensure that you have both Azurite and the Azure Function CLI installed on your machine.
2. Ensure that you have installed all of the required dependencies using `pip install -r requirements.txt`. *You will need Python version: 3.7-3.11. Python 3.12 will not work.*
3. Ensure that you are running Azurite (start it from the CLI using `azurite` or start it in VSCode by clicking on the `[Azure Table Service]` and `[Azure Queue Service]` tray buttons).
4. Set the `TEST_E2E="1"` environment variable.
5. Copy the `src/api/local.settings.example.json` file to `src/api/local.settings.json`.
6. Run `func start` from within the `src/api` directory to start your local test instance.
7. Run `pytest src/api` to run the API test suite (including the full API end to end tests if you set `TEST_E2E="1"` in your environment).