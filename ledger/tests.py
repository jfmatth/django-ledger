import csv
import tempfile
import os

from django.test import TestCase

from ledger.command_loader import loadCSV
from ledger.models import RawCSV

def create_temp_csv(rows):
    temp_file = tempfile.NamedTemporaryFile(mode='w+', newline='', suffix='.csv', delete=False)
    writer = csv.writer(temp_file)
    for row in rows:
        writer.writerow(row)
    temp_file.close()
    return temp_file

    def test_csv_processing(self):
        rows = [
            ['Name', 'Age', 'City'],
            ['Alice', '30', 'New York'],
            ['Bob', '25', 'Los Angeles']
        ]
        temp_csv = self.create_temp_csv(rows)

        # Example: pass temp_csv.name to your CSV processing function
        result = my_csv_parser(temp_csv.name)
        self.assertEqual(result, expected_output)

        temp_csv.close()



# Create your tests here.
class csvTestCase(TestCase):
    tempCSV = None

    def setUp(self):
        rows = [
                ['Date', 'Action', 'Symbol', 'Description', 'Quantity', 'Price', 'Fees & Comm', 'Amount'],
                ['07/25/2025', 'Sell to Open', 'T 08/22/2025 29.00 C', 'CALL AT&T INC $29 EXP 08/22/25', '15', '$0.34', '$9.95', '$500.05'],
                ['07/25/2025', 'Buy to Open', 'LCID 09/19/2025 2.50 P', 'PUT LUCID GROUP INC $2.5 EXP 09/19/25', '10', '$0.21', '$6.61', '-$216.61']
            ]
        self.tempCSV = create_temp_csv(rows)
    
    def test_1_csv_load(self):
        loadCSV(self.tempCSV.name)

        ## at this point, the DB should have the record for the loaded CSV and it's data
        r = RawCSV.objects.all()[0]

        self.assertEqual(r.filename, self.tempCSV.name)
        self.assertEqual(r.ingested, False)

    def test_2_other(self):
        pass

    def tearDown(self):
        os.remove(self.tempCSV.name)

