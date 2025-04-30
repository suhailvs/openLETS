from django.db import models

from django.contrib.auth.models import AbstractUser

from decimal import Decimal
import itertools
# Create your models here.
DATE_FMT = "%Y-%m-%d %H:%M:%S"
currency_field = lambda **kwargs: models.ForeignKey(
    "Currency", on_delete=models.CASCADE, related_name="+", **kwargs
)

class CurrencyMixin(models.Model):
    """A MixIn for models with currency.

    Adds a currency field and a value field.
    Adds two properties for getting value.
    """

    class Meta:
        abstract = True

    currency = currency_field()
    value = models.IntegerField(default=0)

    @property
    def value_repr(self):
        return self.currency.value_repr(self.value)

    @property
    def value_str(self):
        return self.currency.value_of(self.value)


class DictableModel(object):
    """A mixin that adds a to_dict method to a model."""

    def to_dict(self):
        """Return a dict of field name to field serializable value."""
        return dict(
            (field.name, self.serializable_value(field.name))
            for field in self._meta.fields
        )
    
class User(AbstractUser):
    default_currency = currency_field(null=True, blank=True)
    def transaction_records(self):
        return itertools.chain(
            self.transaction_records_creator, self.transaction_records_target
        )


class Currency(models.Model):
    """A currency that can be used for exchange."""

    name = models.CharField(max_length=255)
    description = models.TextField()
    decimal_places = models.IntegerField(default=0)
    default = models.BooleanField(default=False)
    time_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def value_of(self, value):
        """The decimal value of 'value' in this currency."""
        if not self.decimal_places:
            return Decimal(value)
        return Decimal(value) / (10**self.decimal_places)

    def value_repr(self, value):
        return ("%%.%df %%s" % self.decimal_places) % (self.value_of(value), self)
    

class Balance(CurrencyMixin, models.Model):
    """A balance between two people."""
    # users
    users = models.ManyToManyField(
        "user", through="UserBalance", blank=True, related_name="balances"
    )
    time_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Balance of {self.value_repr} credited to {self.credited}, debt from {self.debted}"

    @property
    def credited(self):
        return self.userbalance_set.get(credited=True).user

    @property
    def debted(self):
        return self.userbalance_set.get(credited=False).user


class UserBalance(models.Model):
    """A join table to link User to one of their Balances."""

    user = models.ForeignKey("user", on_delete=models.CASCADE)
    balance = models.ForeignKey("Balance", on_delete=models.CASCADE)
    credited = models.BooleanField()

    def __str__(self):
        return "UserBalance for {self.user} and {self.balance}"

    @property
    def other_user(self):
        """Get the user on the other side of this balance."""
        return self.balance.users.exclude(id=self.user.id).get()

    @property
    def relative_value(self):
        value = self.balance.value
        return self.balance.currency.value_of(value if self.credited else -value)

    @property
    def relative_value_repr(self):
        value = self.balance.value
        value = value if self.credited else -value
        return self.balance.currency.value_repr(value)

    def export_data(self):
        return {
            "user": "%s" % self.other_user,
            "balance": {
                "currency": "%s" % self.balance.currency,
                "value": "%s" % self.relative_value,
            },
            "last_updated": self.balance.time_updated.strftime(DATE_FMT),
        }


class ExchangeRate(models.Model):
    """A rate of exchange between two currencies, offered by a user."""

    user = models.ForeignKey("User", on_delete=models.CASCADE)
    source_currency = currency_field()
    dest_currency = currency_field()
    source_rate = models.IntegerField()
    dest_rate = models.IntegerField()
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "source_currency", "dest_currency")

    def __str__(self):
        return f"{self.user} Exchange Rate: {self.source_repr} to {self.dest_repr}"

    @property
    def source_repr(self):
        return self.source_currency.value_repr(self.source_rate)

    @property
    def dest_repr(self):
        return self.dest_currency.value_repr(self.dest_rate)

    @property
    def source_value(self):
        return self.source_currency.value_of(self.source_rate)

    @property
    def dest_value(self):
        return self.dest_currency.value_of(self.dest_rate)

    def export_data(self):
        return {
            "source": {
                "currency": f"{self.source_currency}",
                "rate": f"{self.source_value}",
            },
            "destination": {
                "currency": f"{self.dest_currency}",
                "rate": f"{self.dest_value}",
            },
            "time_created": self.time_created.strftime(DATE_FMT),
        }


class Transaction(models.Model):
    """A transaction between two people."""

    time_confirmed = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        confirmed = "-"
        if self.time_confirmed:
            confirmed = self.time_confirmed.strftime(DATE_FMT)
        return "Transaction of {self.provider_record.value_repr} from {self.provider} to {self.receiver} confirmed at {confirmed}"
        

    @property
    def currency(self):
        """Get the currency of a resolved transaction."""
        if not self.time_confirmed:
            raise ValueError("Transaction not yet resolved.")
        return self.transaction_records.all()[0].currency

    @property
    def value(self):
        if not self.time_confirmed:
            raise ValueError("Transaction not yet resolved.")
        return self.transaction_records.all()[0].value

    @property
    def user(self):
        """Get the users participating in the transaction."""
        return [record.user for record in self.transaction_records.all()]

    @property
    def provider_record(self):
        return self.transaction_records.get(from_receiver=False)

    @property
    def receiver_record(self):
        return self.transaction_records.get(from_receiver=True)

    @property
    def provider(self):
        return self.provider_record.creator_user

    @property
    def receiver(self):
        return self.receiver_record.creator_user


class TransactionRecord(DictableModel, CurrencyMixin, models.Model):
    """
    A record of the transaction submitted by a user. A transaction is not
    complete until confirmed by both parties having submitted their own
    transaction record.
    """

    transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.CASCADE,
        related_name="transaction_records",
        null=True,
        blank=True,
    )
    creator_user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="transaction_records_creator"
    )
    target_user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="transaction_records_target",
    )
    from_receiver = models.BooleanField()
    rejected = models.BooleanField(default=False)
    transaction_time = models.DateTimeField()
    time_created = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Transaction Record (by {self.creator_user}) {self.value_repr} from {self.provider} to {self.receiver} at {self.time_created.strftime(DATE_FMT)}"
       

    @property
    def provider(self):
        """Returns the user who is the provider in the transaction."""
        return self.creator_user if not self.from_receiver else self.target_user

    @property
    def receiver(self):
        return self.creator_user if self.from_receiver else self.target_user

    @property
    def status(self):
        if self.rejected:
            return "rejected"
        trans = self.transaction
        return "confirmed" if trans and trans.time_confirmed else "pending"

    @property
    def transaction_type(self):
        """The type of transaction relative to the user who created this record."""
        return "charge" if self.from_receiver else "payment"

    @property
    def targets_transaction_type(self):
        """The type of transaction relative to the target user."""
        return "payment" if self.from_receiver else "charge"

    @property
    def other_transaction_record(self):
        if not self.transaction:
            raise ValueError("No transaction yet.")
        return self.transaction.transaction_records.exclude(id=self.id).get()

    @property
    def time_confirmed(self):
        return self.transaction.time_confirmed

    def export_data(self):
        time_confirmed = None
        if self.status == "confirmed":
            time_confirmed = self.transaction.time_confirmed.strftime(DATE_FMT)

        return {
            "user": f"{self.target_user}",
            "transfer_type": "Transaction",
            "status": self.status,
            "transaction_type": self.transaction_type,
            "amount": {
                "value": f"{self.value_str}",
                "currency": f"{self.currency}",
            },
            "time": self.transaction_time.strftime(DATE_FMT),
            "time_confirmed": time_confirmed,
        }

class Resolution(CurrencyMixin, models.Model):
    """A resolution of debts between a circle of users."""

    users = models.ManyToManyField(
        "User", through="UserResolution", blank=True, related_name="resolutions"
    )
    time_confirmed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        confirmed = "-"
        if self.time_confirmed:
            confirmed = self.time_confirmed.strftime(DATE_FMT)
        return f"Resolution of {self.value_repr} between {', '.join(str(p) for p in self.users.all())} confirmed at {confirmed}"
        

    @property
    def provider(self):
        return self.userresolution_set.get(credited=False).user

    @property
    def receiver(self):
        return self.userresolution_set.get(credited=True).user


class UserResolution(models.Model):
    """A join table to link User to one of their Resolutions."""

    user = models.ForeignKey("User", on_delete=models.CASCADE)
    resolution = models.ForeignKey("Resolution", on_delete=models.CASCADE)
    credited = models.BooleanField()

    def __str__(self):
        return "UserResolution for {self.user} and {self.resolution}"

    @property
    def other_user(self):
        """Get the user on the other side of this balance."""
        return self.resolution.users.exclude(id=self.user.id).get()

    target_user = other_user

    @property
    def relative_value(self):
        value = self.resolution.value
        return self.resolution.currency.value_of(value if self.credited else -value)

    @property
    def relative_value_repr(self):
        value = self.resolution.value
        value = value if self.credited else -value
        return self.resolution.currency.value_repr(value)

    @property
    def transaction_time(self):
        return self.resolution.time_confirmed

    time_confirmed = transaction_time

    status = "resolved"

    @property
    def transaction_type(self):
        """The type of transaction relative to this user."""
        return "charge" if self.credited else "payment"

    @property
    def value_repr(self):
        return self.resolution.value_repr

    def export_data(self):
        return {
            "user": f"{self.other_user}",
            "transfer_type": "Resolution",
            "transaction_type": self.transaction_type,
            "amount": {
                "value": f"{self.resolution.value_str}",
                "currency": f"{self.resolution.currency}",
            },
            "time": self.transaction_time.strftime(DATE_FMT),
        }
