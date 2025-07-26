"""
All management commands here for clarity
"""
import csv, hashlib, datetime
from decimal import Decimal
from io import StringIO
import logging

from django.core.exceptions import ObjectDoesNotExist

from ledger.models import RawCSV, RawTransaction, Ledger

logger = logging.getLogger(__name__)

#  these are the actions we know how to process so far
OPTION_ACTIONS = ["Buy to Close", "Sell to Open", "Assigned"]

NON_ACTIONS = ["MoneyLink Transfer", 
                "Non-Qualified Div", "Qualified Dividend",
                "Buy", "Reinvest Dividend", "Reinvest Shares",
                "Sell", "Tax Withholding"
            ]

def loadCSV(filename):
    with open(filename,"r") as f:
        temp = RawCSV()
        temp.filename = filename
        temp.data = f.read()
        temp.ingested = False
        temp.save()


def schwabDate(datestr):
    # converts an incoming transaction date to the right date
    # some transactions have a "<date1> as of <date2>" entry for some stupid reason, when the date of the transaction
    # is date2, lame

    d = None
    if "as of" in datestr:
        # return the last 10 digits from the string
        d = datestr[-10:]
    else:
        d = datestr[:10]

    return datetime.datetime.strptime(d,"%m/%d/%Y")


def hash_row(row):
    """Generate a unique SHA-256 hash for a gi8ven row."""
    # row_string = ",".join(row)  # Convert row to a string

    return hashlib.sha256(row.encode()).hexdigest()


def buldTransactions():
    """
    Converts from CSV into records in our Table
    """
    for csvrow in RawCSV.objects.filter(ingested=False):

        with StringIO(csvrow.data) as csvfile:
            reader = csv.DictReader(csvfile)
    
            for row in reader:
                # see if we have to add this record, or if it's already there based on the hashid

                hash = hash_row("".join(row.values() ) )
                try:
                    RawTransaction.objects.get(hashID=hash)
                except ObjectDoesNotExist:

                    logging.info(f"Adding {row}")
                    
                    record = RawTransaction()

                    record.transactionDate  = schwabDate(row['Date'])
                    record.action           = row['Action']
                    record.symbol           = row['Symbol']
                    record.description      = row['Description']
                    record.quantity         = float(row['Quantity'].replace(",",""))  if row['Quantity'] != "" else 0
                    record.price            = float(row['Price'].replace("$","")) if row['Price'] != "" else 0
                    # record.extrafees        = float(row['Fees & Comm'])
                    record.extrafees        = 0
                    record.totalAmount      = float(row['Amount'].replace("$","")) if row['Amount'] != "" else 0

                    record.hashID           = hash

                    logger.info("Saving Row")
                    record.save()

        csvrow.ingested = True
        csvrow.processed = False
        csvrow.save()


def buildStrikeInfo():
    """
    Goes through all the transactions and builds the strike information for options, everything that isn't already processed.
    """
    logger.info("Building Strike Info")

    for row in RawTransaction.objects.filter(processed = False):
        logger.debug(f"Processing {row}")

        if row.action in OPTION_ACTIONS:
            parts = row.symbol.split(" ") # Break out the parts of the symbol for an option action [symbol,date, price, P or C]
            logger.debug(f"Parts: {parts}")

            # Parts: ['IWM', '06/12/2025', '210.00', 'P']
            row.strikeSymbol    = parts[0]
            row.strikeDate      = datetime.datetime.strptime(parts[1],"%m/%d/%Y")
            row.strikePrice     = parts[2]
            row.strikeSide      = parts[3]

            row.processed = True

        # # Determine which other reords we can mark as processed?
        # if row.action in NON_ACTIONS:
        #     row.processed = True

        row.save()


def updateLedger():
    """
    Creates or updates ledgers on anything that's not processed


    Need to close when qty is 0 after BTC is subtracted from STO

    """

    # Dooh, have to run twice since closes might be before the opens in the CSV
    # for loop in range(2):

    for row in RawTransaction.objects.filter(ingested=False).order_by("transactionDate"):
        # logger.info(f"matching {row}")
        
        # STO or BTC for now
        if row.action in OPTION_ACTIONS:
            logger.info(f'Not ingested {row}')

            l, created = Ledger.objects.get_or_create(symbol=row.symbol, status="Open")

            logger.info(f"{row.action}")

            if row.action == OPTION_ACTIONS[1]:     # STO
                if created:
                    l.opened = row.transactionDate
                    l.investedAmount = row.totalAmount
                    l.status = "Open"

                l.closedAmount += row.totalAmount
                l.quantity += row.quantity

            if (row.action == OPTION_ACTIONS[0] or row.action == OPTION_ACTIONS[2]):     # BTC or assigned
                if created:
                    l.opened = row.transactionDate
                    l.status = "Open"

                l.closed = row.transactionDate
                l.closedAmount += row.totalAmount
                l.quantity -= row.quantity

            if l.quantity == 0:
                l.status = "Closed"

            l.save()

            row.ledgerEntry = l
            row.ingested = True
            row.save()
