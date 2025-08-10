import csv
import tempfile
import os

from django.test import TestCase

from ledger.command_loader import buildTransactions
from ledger.models import RawCSV, RawTransaction

"""
Testing all the callings of loader management command

[X]loader.loadCSV(options['filename'][0])
[ ]loader.buldTransactions()
[ ]loader.buildStrikeInfo()
[ ]loader.updateLedger()

"""

rows = [
    ['Date', 'Action', 'Symbol', 'Description', 'Quantity', 'Price', 'Fees & Comm', 'Amount'],
    ['07/25/2025', 'Sell to Open', 'T 08/22/2025 29.00 C', 'CALL AT&T INC $29 EXP 08/22/25', '15', '$0.34', '$9.95', '$500.05'],
    ['07/25/2025', 'Buy to Open', 'LCID 09/19/2025 2.50 P', 'PUT LUCID GROUP INC $2.5 EXP 09/19/25', '10', '$0.21', '$6.61', '-$216.61']
]

flatten_rows = lambda lst: '\n'.join([','.join(row) for row in lst])
TRANSACTION_COUNT = 2

def loadRows():
    # Creates a RawCSV record to read from
    record = RawCSV()
    record.filename = "test"
    record.data = flatten_rows(rows)
    record.ingested = False
    record.save()


class loadCSVTestCase(TestCase):
    """
        Since we don't read in a file, we fake it here with loadRows()
    """
    def setUp(self):
        loadRows()

    def test_1_csv_load(self):
        r = RawCSV.objects.all()[0]

        self.assertEqual(r.filename, "test")
        self.assertEqual(r.ingested, False)
        self.assertEqual(len(RawCSV.objects.all()), 1)

    def tearDown(self):
        pass


class buildTransactionTestCase(TestCase):

    def setUp(self):
        loadRows()
        buildTransactions()
        
    def test_1_buildTransaction(self):
        ## We load the CSV and Build the RawTransaction objects
        self.assertEqual(len(RawTransaction.objects.all() ), TRANSACTION_COUNT)

    def test_2