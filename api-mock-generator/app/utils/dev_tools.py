import csv
import json
import os
from datetime import datetime

class Consts:
    name= "name"
    no_of_paths = "no_of_paths"
    no_of_methods = "no_of_methods"
    length_of_spec = "length_of_spec"
    length_of_cleaned_spec = "length_of_cleaned_spec"
    user_msg_length = "user_msg_length"
    sys_msg_length = "sys_msg_length"
    length_of_output_schema = "length_of_output_schema"
    response_length = "response_length"
    response_time = "response_time"
    is_response_schema_valid_1 = "is_response_schema_valid_1"
    is_response_schema_valid_2 = "is_response_schema_valid_2"
    syntax_errors = "syntax_errors"
    deployment_success = "deployment_success"
    deployment_errors = "deployment_errors"
    passed_enpoint_count = "passed_enpoint_count"
    failed_enpoint_count = "failed_enpoint_count"


class DebugRecord:
    def __init__(self, data=None):
        self.record = data if data is not None else {}  # Changed to instance variable
        self.timestamp = datetime.now()  # Changed to instance variable

    def add(self, key, value):
        self.record[key] = value
        self.timestamp = datetime.now()

    def get(self, key):
        return self.record.get(key, None)
    
    def get_all(self):
        return self.record
    
    def get_timestamp(self):
        return self.timestamp
    
    def remove(self, key):
        if key in self.record:
            del self.record[key]
            self.timestamp = datetime.now()
    
    def clear(self):
        self.record.clear()
        self.timestamp = datetime.now()

    def save(self, file_path="records.csv"):
            file_exists = os.path.isfile(file_path)
            headers = list(self.record.keys())
    
            # Read existing headers if the file exists
            if file_exists:
                with open(file_path, mode="r", newline="") as file:
                    reader = csv.DictReader(file)
                    existing_headers = reader.fieldnames or []
                    # Preserve the order of existing headers and add new ones at the end
                    headers = existing_headers + [header for header in headers if header not in existing_headers]
    
            # Write to the CSV file
            with open(file_path, mode="a", newline="") as file:  # Changed mode to "a" for appending
                writer = csv.DictWriter(file, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()  # Write headers if the file is new
                # Ensure all columns are written, filling missing ones with empty strings
                row = {header: self.record.get(header, "") for header in headers}
                writer.writerow(row)

rec = DebugRecord()

def records_from_spec(open_api_spec):
    #convert to json
    open_api_spec = json.loads(open_api_spec)
    rec.add(Consts.name, open_api_spec.get('info', {}).get('title', ''))
    rec.add(Consts.no_of_paths, len(open_api_spec.get('paths', {})))
    
    # Count the total number of methods by iterating through each path
    no_of_methods = sum(len(path_methods) for path_methods in open_api_spec.get('paths', {}).values())
    rec.add(Consts.no_of_methods, no_of_methods)

    rec.add(Consts.length_of_spec, len(str(open_api_spec)))
