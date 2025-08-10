"""
Loader management commands.

I put them in the folder for the app, not in the management / commmands folder, easier.
"""
import csv, hashlib, datetime
from decimal import Decimal
from io import StringIO
import logging

from django.core.exceptions import ObjectDoesNotExist

from ledger.models import RawCSV, RawTransaction, Ledger

logger = logging.getLogger(__name__)

#  these are the actions we know how to process so far
OPTION_ACTIONS = ["Buy to Close", "Sell to Open", "Assigned", "Expired"]

NON_ACTIONS = ["MoneyLink Transfer", 
                "Non-Qualified Div", "Qualified Dividend",
                "Buy", "Reinvest Dividend", "Reinvest Shares",
                "Sell", "Tax Withholding"
            ]


def schwab_date(datestr):
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


def loadCSV(filename):
    logger.info(f"loading CSV {filename}")
    
    with open(filename,"r") as f:
        temp = RawCSV()
        temp.filename = filename
        temp.data = f.read()
        temp.ingested = False
        temp.save()


def buildTransactions():
    """
    Converts from CSV into records in our Table
    """
    logger.info(f'building Transactions from CSV')
    logger.info(f"found {RawCSV.objects.filter(ingested=False).count()} records")
    for csvrow in RawCSV.objects.filter(ingested=False):

        with StringIO(csvrow.data) as csvfile:
            reader = csv.DictReader(csvfile)
    
            for row in reader:
                # see if we have to add this record, or if it's already there based on the hashid
                hash = hash_row("".join(row.values() ) )
                try:
                    RawTransaction.objects.get(hashID=hash)
                except ObjectDoesNotExist:

                    logging.debug(f"Adding {row}")
                    
                    record = RawTransaction()

                    record.transactionDate  = schwab_date(row['Date'])
                    record.action           = row['Action']
                    record.symbol           = row['Symbol']
                    record.description      = row['Description']
                    record.quantity         = float(row['Quantity'].replace(",",""))  if row['Quantity'] != "" else 0
                    record.price            = float(row['Price'].replace("$","")) if row['Price'] != "" else 0
                    record.extrafees        = 0
                    record.totalAmount      = float(row['Amount'].replace("$","")) if row['Amount'] != "" else 0

                    record.hashID           = hash

                    logger.debug(f"Saving Row {record}")
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

    This is the meat of the program for now, make ledgers for tracking how we did on option sales
    """
    logger.debug("updateLedger")

    OPTIONS_OPEN = [ OPTION_ACTIONS[1] ]
    OPTIONS_CLOSE = [ OPTION_ACTIONS[0] + OPTION_ACTIONS[2] + OPTION_ACTIONS[3] ]

    for row in RawTransaction.objects.filter(ingested=False).order_by("transactionDate"):
        logger.debug(f"matching {row}")
        
        if row.action in OPTION_ACTIONS:
            logger.debug(f'Not ingested {row}')

            # We either have a record or not.
            # if we do, then possibly add this to the ledger, but if qty==0 then close it
            # if we don't, make a new ledger
            l, created = Ledger.objects.get_or_create(symbol=row.symbol, status="Open")

            logger.debug(f"{row.action}")

            # We've sold an option, might be the first one for this "symbol" or adding to it
            if row.action in OPTIONS_OPEN:
                if created:
                    l.opened = row.transactionDate
                    l.investedAmount = row.totalAmount
                    l.status = "Open"

                l.closedAmount += row.totalAmount
                l.quantity += row.quantity

            if row.action in OPTIONS_CLOSE:
                if created:
                    l.opened = row.transactionDate
                    l.status = "Open"

                l.closed = row.transactionDate
                l.closedAmount += row.totalAmount
                l.quantity -= row.quantity

            # if we have balanced out our qty, most likely we are done, so close this ledger
            if l.quantity == 0:
                l.status = "Closed"

            l.save()

            #  attach this leedger entry to the transaction, for the 1:N relation
            row.ledgerEntry = l
            row.ingested = True
            row.save()
