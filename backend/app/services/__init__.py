"""Business rules. Routes in app/api/ stay thin and call these functions.

Services raise `ServiceError` subclasses (errors.py); a handler in
app/main.py turns them into JSON error responses with the right status code.
"""
