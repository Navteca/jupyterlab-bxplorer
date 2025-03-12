class Error(Exception):
    pass

class ODSourceNotFound(Error):
    def __init__(self, od_source):
        self.od_source = od_source
        super().__init__(self.od_source)

    def __str__(self):
        return f"The source {self.od_source} has not been found."


class GitHubAPICallRateLimitExceeded(Error):
    def __init__(self, od_source):
        self.od_source = od_source
        super().__init__(self.od_source)

    def __str__(self):
        return f"The API call rate  for {self.od_source} has been exceeded."


class BucketIsNotAccessibleError(Error):
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        super().__init__(self.bucket_name)

    def __str__(self):
        return f"The bucket {self.bucket_name} is not accessible."