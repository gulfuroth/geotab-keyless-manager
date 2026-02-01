Deployment README
Prerequisites
Python 3.8+

Flask and Requests libraries.

A Geotab Keyless tenant and service account credentials.

Installation
Extract the files: Ensure app.py is in the root directory and index.html is inside a folder named templates.

Install Dependencies:

Bash

#>pip install flask requests
Run the Application:

Bash

#>python app.py
Access the Tool: Open your browser and go to http://127.0.0.1:5000.

Database
On the first run, the tool will automatically create a vehicles.db (SQLite) file in your directory. This file stores your fleet list, persistent settings, and audit logs. Do not delete this file unless you want to reset the application.