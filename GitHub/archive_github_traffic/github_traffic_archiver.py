import os
import json
import requests
import datetime
import time
import logging
import yaml
from dataclasses import dataclass
from typing import List, Tuple, Dict


def load_json_data(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def save_json_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def get_today_iso_date():
    now = datetime.datetime.now(datetime.timezone.utc).date()
    iso_timestamp = f"{now.isoformat()}T00:00:00Z"
    return iso_timestamp


class DateLogger:
    def __init__(self, name: str = "DateLogger", log_dir: str = "logs", log_file: str = "app.log", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False 

        if not self.logger.handlers:
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, log_file)

            formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            # Console Handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # File Handler
            file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger


class ConfigLoader:
    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = config_path
        self.repo_metadata: List[Tuple[str, str, str]] = []
        self.remote_database_metadata: Dict[str, str] = {}
        self.local_database_metadata: Dict[str, str] = {}
        self.load_config()

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.repo_metadata = [
            (item['username'], item['repository'], item['token'])
            for item in config.get('repo_metadata', [])
        ]
        assert self.repo_metadata, "repo_metadata is required in config.yaml"
    
        self.remote_database_metadata = config.get('remote_database_metadata', None)
        assert self.remote_database_metadata is not None, "remote_database_metadata is required in config.yaml"
        
        self.local_database_metadata = config.get('local_database_metadata',
                                                  {'path': 'traffic_data'})

        self.archiver_period = config.get('archiver_period', 7)  # Default to 7 days if not specified

# All traffic data refers to clones

@dataclass
class TrafficData:
    timestamp: str
    count: int
    uniques: int
    log2online_db: bool = False

@dataclass
class NOCODBRecord:
    Repository: str
    Username: str
    Link: str
    Date: str
    Count: int
    Uniques: int
    
    def load_from_traffic_data(self, traffic_data: TrafficData, owner: str, repo: str):
        self.Repository = repo
        self.Username = owner
        self.Link = f"https://github.com/{owner}/{repo}"
        self.Date = datetime.datetime.fromisoformat(
            traffic_data.timestamp.replace('Z', '+00:00')).strftime("%Y-%m-%d")
        self.Count = traffic_data.count
        self.Uniques = traffic_data.uniques
        
    @classmethod
    def from_traffic_data(cls, traffic_data: TrafficData, owner: str, repo: str):
        return cls(
            Repository=repo,
            Username=owner,
            Link=f"https://github.com/{owner}/{repo}",
            Date=datetime.datetime.fromisoformat(
                traffic_data.timestamp.replace('Z', '+00:00')
            ).strftime("%Y-%m-%d"),
            Count=traffic_data.count,
            Uniques=traffic_data.uniques
        )

class GitHubTraffic:
    def __init__(self, owner, repo, token):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.uid = f"{owner}/{repo}"

    def get_clone_traffic(self):
        """
        Get the clone traffic data for the repository.
        
        Returns:
            dict: The clone traffic data if successful, or a message indicating failure.
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/traffic/clones"
        
        # Set the headers for authentication (if provided)
        headers = {}
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        # Add the date range for traffic data (up to the last 14 days)
        today = datetime.datetime.now(datetime.timezone.utc)
        since_date = (today - datetime.timedelta(days=14)).isoformat()
        # Define parameters
        params = {
            'per': 'day',  # Traffic data per day
            'since': since_date  # Start date for the traffic query (last 14 days)
        }
        # Make the GET request to the GitHub API
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return {"error": "Failed to fetch data", "status_code": response.status_code, "message": response.json()}


class GitHubTrafficDataBase:
    def __init__(self, repo_metadata, database_path):
        self.repo_metadata = repo_metadata
        self.database_path = database_path
        self.repo_traffic = [GitHubTraffic(owner, repo, token) for owner, repo, token in repo_metadata]
        
    def load_traffic_data(self):
        """
        Load traffic data for all repositories in the metadata.
        
        Returns:
            list: A list of dictionaries containing traffic data for each repository.
        """
        self.traffic_data = {}
        for repo in self.repo_traffic:
            repo_uid = repo.uid
            repo_path = os.path.join(self.database_path, repo_uid)
            repo_clones_path = os.path.join(repo_path, "clones.json")
            if os.path.exists(repo_clones_path):
                clones_data = load_json_data(os.path.join(repo_path, "clones.json"))
                self.traffic_data[repo_uid] = {data['timestamp']: TrafficData(**data) for data in clones_data}
        
    def update_traffic_data(self, repo_uid: str, data: Dict[str, TrafficData]):
        """
        Update the traffic data for a specific repository.
        
        Args:
            repo_uid (str): The unique identifier for the repository.
            data (dict): The traffic data to update.
        """
        if repo_uid not in self.traffic_data:
            self.traffic_data[repo_uid] = {}
        for timestamp, traffic_data_item in data.items():
            if timestamp not in self.traffic_data[repo_uid]:
                self.traffic_data[repo_uid][timestamp] = traffic_data_item
    
    def save_traffic_data(self):
        """
        Save the traffic data to the database.
        """
        for repo_uid, data in self.traffic_data.items():
            repo_path = os.path.join(self.database_path, repo_uid)
            if not os.path.exists(repo_path):
                os.makedirs(repo_path)
            repo_clones_path = os.path.join(repo_path, "clones.json")
            save_json_data(repo_clones_path, [data[timestamp].__dict__ for timestamp in data]) 

    def prepare_record(self):
        records2log = []
        for repo_uid, data in self.traffic_data.items():
            owner, repo = repo_uid.split('/')
            records = [NOCODBRecord.from_traffic_data(data[timestamp],owner,repo)
                       for timestamp in data if not data[timestamp].log2online_db]
            records2log += records
        return records2log
    
    def mark_traffic_data(self, records: List[NOCODBRecord]):
        for record in records:
            owner, repo = record.Username, record.Repository
            repo_uid = f"{owner}/{repo}"
            timestamp = record.Date + 'T00:00:00Z'
            assert timestamp in self.traffic_data[repo_uid]
            self.traffic_data[repo_uid][timestamp].log2online_db = True


class NOCODBLogger:
    def __init__(self, nocodb_url, table_id, nocodb_token):
        self.nocodb_url = nocodb_url
        self.table_id = table_id
        self.nocodb_token = nocodb_token
        self.url = f"{self.nocodb_url}/api/v2/tables/{self.table_id}/records"
        self.headers = {
            "Content-Type": "application/json",
            "xc-token": self.nocodb_token
        }
        
    def create_record(self, record_data: List[NOCODBRecord]):
        """
        Create a record in NOCODB.
        
        Args:
            data (list): The data to create a record for.
        
        Returns:
            dict: The response from NOCODB.
        """
        response = requests.post(self.url, headers=self.headers,
                    json=[record.__dict__ for record in record_data])
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return {"error": "Server not found", "status_code": response.status_code}
        else:
            return {"error": "Failed to create record", "status_code": response.status_code, "message": response.json()}


class GitHubTrafficArchiver:
    def __init__(self, repo_metadata, local_database_metadata, remote_database_metadata, logger_metadata=None,
                 archiver_period=7):
        self.github_traffic_db = GitHubTrafficDataBase(repo_metadata,
                                                       local_database_metadata['path'])
        self.nocodb_logger = NOCODBLogger(remote_database_metadata['url'],
                                          remote_database_metadata['table_id'],
                                          remote_database_metadata['token'])
        
        self.logger = DateLogger(name="GitHubTrafficArchiver", log_dir="logs",
            log_file="github_traffic_archiver.log") if logger_metadata is None else DateLogger(**logger_metadata)
        self.logger = self.logger.get_logger()
        
        self.archiver_period = archiver_period # unit: days
        self.last_archived_date = None     
    
    def fetch_traffic_data(self):
        for repo in self.github_traffic_db.repo_traffic:
            repo_uid = repo.uid
            clone_traffic = repo.get_clone_traffic()
            if 'error' not in clone_traffic:
                today = get_today_iso_date()
                clone_traffic_data = {data['timestamp']: TrafficData(**data) for data in clone_traffic['clones'] if data['timestamp'] < today}
                self.github_traffic_db.update_traffic_data(repo_uid, clone_traffic_data)
                self.logger.info(f"Fetched traffic data for {repo_uid}: {clone_traffic_data}")
            else:
                self.logger.error(f"Failed to fetch traffic data for {repo_uid}: {clone_traffic['error']}")
    
    def archive_traffic_data(self):
        """
        Archive traffic data for all repositories in the metadata.
        
        Returns:
            list: A list of dictionaries containing archived traffic data for each repository.
        """
        self.github_traffic_db.load_traffic_data()
        self.fetch_traffic_data()
        records2log = self.github_traffic_db.prepare_record()
        if len(records2log) > 0:
            response = self.nocodb_logger.create_record(records2log)
            if 'error' not in response:
                self.github_traffic_db.mark_traffic_data(records2log)
                self.logger.info(f"Archived traffic data for {len(records2log)} records: {response}")
            else:
                self.logger.error(f"Failed to archive traffic data: {response['error']}")
        self.github_traffic_db.save_traffic_data()
        self.logger.info(f"Saved traffic data for {len(self.github_traffic_db.traffic_data)} repositories") 
        
    def spin(self):
        """
        Spin the archiver to archive traffic data for all repositories.
        
        Returns:
            list: A list of dictionaries containing archived traffic data for each repository.
        """
        while True:
            if self.last_archived_date is None or (datetime.datetime.now(datetime.timezone.utc).date() - self.last_archived_date).days >= self.archiver_period:
                self.archive_traffic_data()
                self.last_archived_date = datetime.datetime.now(datetime.timezone.utc).date()
            time.sleep(60 * 60 * 24)  # Sleep for 24 hours
            
            
if __name__ == "__main__":
    cfg = ConfigLoader('config.yaml')
    
    archiver_period = 7  # Archive every 7 days
    github_traffic_archiver = GitHubTrafficArchiver(cfg.repo_metadata, cfg.local_database_metadata, cfg.remote_database_metadata,
                                                    archiver_period = archiver_period)
    github_traffic_archiver.spin()
