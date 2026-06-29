"""
All management commands here for clarity
"""
import csv, hashlib, datetime
from decimal import Decimal
from io import StringIO
from decimal import Decimal
from enum import StrEnum
import re

import logging

from django.core.exceptions import ObjectDoesNotExist

from ledger.models import RawCSV, RawTransaction, Ledger

logger = logging.getLogger(__name__)

class Action(StrEnum):
    BTC = "Buy to Close"
    STO = "Sell to Open"
    ASSIGNED = "Assigned"
    EXPIRED = "Expired"

# ACTION_MLTRANSFER = "MoneyLink Transfer"
# ACTION_NQD = "Non-Qualified Div"
# ACTION_QD = "Qualified Dividend"
# ACTION_BUY = "Buy"
# ACTION_REINVESTDIV = "Reinvest Dividend"
# ACTION_REINVESTSH = "Reinvest Shares"
# ACTION_SELL = "Sell"
# ACTION_TAXES = "Tax Withholding"

# NON_OPTIONS = [ACTION_MLTRANSFER, ACTION_NQD, ACTION_QD, ACTION_BUY, ACTION_REINVESTDIV, ACTION_REINVESTSH, ACTION_SELL, ACTION_TAXES]


def dollars_to_decimal(s: str) -> Decimal:
    s = s.strip()
    s = s.replace("(", "-").replace(")", "")  # accounting negatives
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    return Decimal(cleaned)

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
    logger.debug(f"loading CSV {filename}")
    
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
    logger.debug(f'building Transactions from CSV')

    for csvrow in RawCSV.objects.filter(ingested=False):

        with StringIO(csvrow.data) as csvfile:
            reader = csv.DictReader(csvfile)
    
            for row in reader:
                # see if we have to add this record, or if it's already there based on the hashid
                hash = hash_row("".join(row.values() ) )
                try:
                    RawTransaction.objects.get(hashID=hash)
                    logger.debug(f"duplicate {row}")
                except ObjectDoesNotExist:

                    logging.debug(f"Adding {row}")
                    
                    record = RawTransaction()

                    record.transactionDate  = schwab_date(row['Date'].strip())
                    record.action           = row['Action'].strip()
                    record.symbol           = row['Symbol'].strip()
                    record.description      = row['Description'].strip()
                    record.quantity         = float(dollars_to_decimal(row['Quantity']))  if row['Quantity'] != "" else 0
                    record.price            = float(dollars_to_decimal(row['Price'])) if row['Price'] != "" else 0
                    record.extrafees        = 0
                    record.totalAmount      = float(dollars_to_decimal(row['Amount']) ) if row['Amount'] != "" else 0

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
    logger.debug("Building Strike Info")

    for row in RawTransaction.objects.filter(processed = False):
        logger.debug(f"Processing {row}")

        # if row.action in OPTION_ACTIONS:
        if row.action in Action._value2member_map_:

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

    for row in RawTransaction.objects.filter(ingested=False).order_by("transactionDate"):
        logger.debug(f"matching {row}")
        
        # are any options actions in what's in row.action?
        if row.action in Action._value2member_map_:
            # We either have a record or not.
            # if we do, then possibly add this to the ledger, but if qty==0 then close it
            # if we don't, make a new ledger
            l, created = Ledger.objects.get_or_create(symbol=row.symbol, status="Open")

            logger.debug(f"{row.action}")

            # We've sold an option, might be the first one for this "symbol" or adding to it
            match row.action:
                case Action.STO:
                    if created:
                        l.opened = row.transactionDate
                        l.investedAmount = row.totalAmount
                        l.status = "Open"

                    l.closedAmount += row.totalAmount
                    l.quantity += row.quantity

                case Action.BTC | Action.ASSIGNED | Action.EXPIRED :

                    logger.debug(f'{row.action} - {row}\n, {l}')

                    # if created:
                    #     l.opened = row.transactionDate
                    #     l.status = "Open"

                    l.closed = row.transactionDate
                    if row.action == Action.ASSIGNED or row.action == Action.EXPIRED:
                        l.closedAmount = 0
                        l.status = "Closed"
                        l.quantity = 0
                    else:
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

def main():
    # loader.loadCSV(options['filename'][0])
    buildTransactions()
    buildStrikeInfo()
    updateLedger()

def process():
    buildTransactions()
    buildStrikeInfo()
    updateLedger()
