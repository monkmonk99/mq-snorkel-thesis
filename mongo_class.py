import pymongo
import subprocess
import json
import sys
import os

print(os.environ['proj_dir'])

class Mongo:
    
    def setup_ssh(self):
        sshProc = subprocess.Popen(["ssh", "-tt", "-i", os.environ['proj_dir'] + "/snorkel-storage.pem", "-L", "27017:localhost:27017", "ubuntu@snorkel-video-collection-storage.mqu.cloud"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        return sshProc
    
    def __init__(self, db_name=None, collection_name=None):
        self.sshProc = self.setup_ssh()
        self.client = pymongo.MongoClient('mongodb://localhost:27017/')
        if db_name is None:
            self.db = self.client.get_database("videos")
        else:
            self.db = self.client.get_database(db_name)
        if collection_name is None:
            self.collection = self.db.get_collection("all")
        else:
            self.collection = self.db.get_collection(collection_name)
        
    # define functions for with statements
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.sshProc.kill()
    
    def close(self):
        self.sshProc.kill()

if __name__ == "__main__":
    with Mongo() as mongo:
        print(mongo.client.list_databases())