import unittest
import sys
import os
from schema import Schema, And, Use, Optional, SchemaError 

sys.path.append(os.path.abspath('/home/sanaz/viraweb123/odoo-iot/vw-gateway/extensions/attendence/zktec'))
import zktec_connector

ATTENDANCE_TELEMETRY_SCHEMA = Schema({
    "ts": And(int),
    "values": {
        "user_id": And(int),
        "timestamp":  And(str, len),
        "punch": And(str, len),
        "device_name":  And(str, len),
    }
})


class TestStringMethods(unittest.TestCase):

    def test_schema(self):
        data = {
            'telemetry': [{
                "ts": 1,
                "values": {
                    "user_id": 2,
                    "timestamp":  "2023-10-3 10:20:05",
                    "punch": "in",
                    "device_name":  "test", }},
                {
                "ts": 2,
                "values": {
                    "user_id": 3,
                    "timestamp":  "2023-10-4 10:20:05",
                    "punch": "out",
                    "device_name":  "test2"}}
            ]
        }
        valid_date = zktec_connector.ATTENDANCE_TELEMETRY_SCHEMA.validate(data)
        self.assertIsNotNone(valid_date)

    def test_schema_invalid(self):
        data = {
            'telemetry': [{
                "ts": 1,
                "values": {
                    "user_id": "2",
                    "timestamp":  "2023-10-3 10:20:05",
                    "punch": "in",
                    "device_name":  "test",}},
                {
                "ts": 2,
                "values": {
                    "timestamp":  "2023-10-4 10:20:05",
                    "punch": "out",
                    "device_name":  "test2"}}
                ]}
        with self.assertRaises(SchemaError):
            zktec_connector.ATTENDANCE_TELEMETRY_SCHEMA.validate(data)


if __name__ == '__main__':
    unittest.main()
