from django.db import models


class BaseModel(models.Model):
    '''
    Defines some of the base models common fields and functions, mainly save() so we can
    track when the record was updated or created.
    
    Might be worth checking out https://github.com/WiserTogether/django-base-model

    '''
    cdate = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Date Created")     
    mdate = models.DateTimeField(auto_now=True, null=True, verbose_name="Date Modified")
    
    class Meta:
        abstract = True
        
class RawCSV(BaseModel):
    filename = models.CharField(max_length=100, db_index=True)
    data = models.TextField(blank=True, null=True)
    
    ingested = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.filename}-{self.ingested}"


class StockLedger(BaseModel):
    symbol          = models.CharField(max_length=50)
    quantity        = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    investedAmount  = models.DecimalField(max_digits=20, decimal_places=3, default=0, blank=True)
    status          = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.symbol} - {self.quantity}"


class OptionLedger(BaseModel):
    symbol      = models.CharField(max_length=50)

    opened       = models.DateField(blank=True, null=True)
    closed       = models.DateField(blank=True, null=True)
    status       = models.CharField(max_length=10, blank=True, null=True)
    closedAmount = models.DecimalField(max_digits=20, decimal_places=3, default=0)
    investedAmount = models.DecimalField(max_digits=20, decimal_places=3, default=0)
    quantity     = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    def __str__(self):
        return f"{self.symbol}"

    def profit(self):
        return self.investedAmount - self.closedAmount

    def perc_profit(self):
        if self.investedAmount != 0:
            return f"{(self.closedAmount / self.investedAmount)*100:.2f}"
    
    @property
    def days_between(self):
        if self.opened and self.closed:
            return (self.closed - self.opened).days
        
        return 0

    def time_profit(self):
        # Daily Profit Percentage=(Profit/Days) / Investment) × 100
        days = max(self.days_between,1)

        if self.status == "Closed" and self.investedAmount != 0:
            return f"{( ((self.investedAmount - self.closedAmount)/days) / self.investedAmount) * 100:.2f}"
        else:
            return f"N/A"
    

class RawTransaction(BaseModel):
    # Same fields as Schwab CVS
    transactionDate = models.DateField(db_index=True)
    action          = models.CharField(max_length=50)
    symbol          = models.CharField(max_length=50)
    description     = models.CharField(max_length=50)
    quantity        = models.DecimalField(max_digits=10, decimal_places=3)
    price           = models.DecimalField(max_digits=10, decimal_places=3)
    extrafees       = models.DecimalField(max_digits=10, decimal_places=3)
    totalAmount     = models.DecimalField(max_digits=20, decimal_places=3)

    # Most of these have null=True since we don't define them on initial insert / update
    strikeSymbol    = models.CharField(max_length=10, null=True)
    strikeDate      = models.DateField(null=True, blank=True)
    strikePrice     = models.DecimalField(max_digits=10,decimal_places=3, null=True)
    strikeSide      = models.CharField(max_length=1, blank=True, null=True)     # P or C
    
    # used to make sure we don't ingest a transaction more than once
    hashID          = models.CharField(max_length=50)

    ingested        = models.BooleanField(default=False)
    processed       = models.BooleanField(default=False)

    OptionledgerEntry     = models.ForeignKey(OptionLedger, null=True, blank=True, on_delete=models.SET_NULL)
    StockledgerEntry      = models.ForeignKey(StockLedger, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return f"{self.transactionDate} - {self.action} - {self.description}"



