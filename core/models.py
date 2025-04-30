from django.db import models

from django.contrib.auth.models import AbstractUser

from decimal import Decimal
import itertools
# Create your models here.


class User(AbstractUser):
    default_currency =  models.ForeignKey("Currency", on_delete=models.CASCADE, null=True)


    # def transaction_records(self):
    #     return itertools.chain(
    #         self.transaction_records_creator, self.transaction_records_target
    #     )


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