# django-ledger - Keep track of Schwab Option transactions

## Importing transactions from CLI

```
manage.py loader {filename}
```

## Processing without loading
There might be times when you modify records in Admin but need to reprocess them

```
manage.py process
```

The program will create a hash for each imported transaction and allow you to import the same CSV without duplicating the data.  The CSV table will hold the records, but the transactions themselves will not be duplicated


## CSV format
From Schwab.com, Transaction History, export to CSV

```
Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
6/22/2026,Sell to Open,SLV 07/06/2026 65.00 C,CALL ISHR SILVER TR $65 EXP 07/06/26,10,$0.46 ,$6.66 ,$453.34 
6/23/2026,Buy to Close,SLV 07/06/2026 65.00 C,CALL ISHR SILVER TR $65 EXP 07/06/26,10,$0.14 ,$6.62 ,($146.62)
```

# Models

**RawCSV** - Holds the contents of all CSV importd for processing

**Ledger** - The ultimate goal of this project, tell us how well we did on an option transactions

**RawTransaction** - The CSV converted to a tabular format, then a pass to update meta fields 


# Tests
The tests/ folder has a series of .CSV files to prove the ledger feature works

```
manage.py test
```

# Misc.

## Time Formula (from Co-Pilot)

```
Daily Profit Percentage=(Profit/Days) / Investment) × 100
```
Using this formula, we can calculate the daily profit percentage for your examples:
1. $1000 profit in 10 days using $100000:
	• Daily profit: 1000/10=100
	• Daily profit percentage: (100/100000)×100=0.1%
2. $1000 profit in 10 days using $20000:
	• Daily profit: 1000/10=100
	• Daily profit percentage: (100/20000)×100=0.5%
