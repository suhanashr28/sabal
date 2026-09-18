class APIError(Exception):
 def __init__(self, message, status=400):
  self.message, self.status = message, status
  super().__init__(message)
