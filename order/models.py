from django.db import models
from django.core.urlresolvers import reverse


class Group(models.Model):
    name = models.CharField(max_length=255)
    enclosure = models.BooleanField(default=False, verbose_name='Einlage bezahlt')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('order_group_update', args=[self.pk])


class Unit(models.Model):
    name = models.CharField(max_length=255, unique=True)
    order_name = models.CharField(max_length=255, blank=True)
    divisor = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name

    @property
    def price(self):
        return self.name

    @property
    def order(self):
        return self.order_name or self.name


class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    unit = models.ForeignKey(Unit, verbose_name='Einheit')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preis')  # TODO: use a custom Integerfield
    available = models.BooleanField(default=True, verbose_name='Verfügbar')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('order_product_update', args=[self.pk])

    @property
    def multiplier(self):
        return self.price / self.unit.divisor


class Bundle(models.Model):
    start = models.DateTimeField(auto_now_add=True)
    open = models.BooleanField(default=True)

    class Meta:
        get_latest_by = 'start'

    def __str__(self):
        return "Bestellung vom {}".format(self.start.strftime('%d.%m.%Y'))

    def get_absolute_url(self):
        return reverse('order_bundle_detail', args=[self.pk])

    def price_for_group(self, group, delivered=False):
        """
        Returns the full price for all products for a group.
        """
        query = self.orders.filter(group=group).select_related('product__unit')
        if delivered:
            return sum(order.product.multiplier * order.get_delivered() for order in query)
        else:
            return sum(order.product.multiplier * order.amount for order in query)

    def price_for_all(self, delivered=False):
        query = self.orders.select_related('product__unit')
        if delivered:
            return sum(order.product.multiplier * order.get_delivered() for order in query)
        else:
            return sum(order.product.multiplier * order.amount for order in query)


class Order(models.Model):
    group = models.ForeignKey(Group)
    product = models.ForeignKey(Product)
    amount = models.PositiveIntegerField(default=0, blank=True)
    delivered = models.PositiveIntegerField(null=True, blank=True)
    bundle = models.ForeignKey(Bundle, related_name='orders')

    class Meta:
        unique_together = ('group', 'product', 'bundle')

    def __str__(self):
        # TODO: nicht auf foreignkeys verweisen
        return "{:<10} {:5} x {}".format("%s:" % self.group, self.amount, self.product)

    def get_delivered(self):
        return self.delivered if self.delivered is not None else self.amount
