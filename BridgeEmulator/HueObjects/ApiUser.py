from datetime import datetime, timezone

class ApiUser():
    def __init__(self, username, name, client_key, create_date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), last_use_date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")):
        self.username = username
        self.name = name
        self.client_key = client_key
        self.create_date = create_date
        self.last_use_date = last_use_date

    def getV1Api(self):
        return {"name": self.name, "create date": self.create_date, "last use date": self.last_use_date}

    def save(self):
        return {"name": self.name, "client_key": self.client_key, "create_date": self.create_date, "last_use_date": self.last_use_date}
