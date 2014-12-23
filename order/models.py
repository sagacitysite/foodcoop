from django.core.urlresolvers import reverse
from django.db import models


class Group(models.Model):
    """
    Representing a Group that orders food.
    """

    name = models.CharField(max_length=255)
    """
    Name to represent the group.

    Will be shown at any place where the group is represented in the website.
    Is used for the default ordering of a list of groups.
    """

    enclosure = models.BooleanField(default=False, verbose_name="Einlage bezahlt")
    """
    Only groups that have given a enclosure can order food. This attribute saves
    the state of this payment. If it is False, the group can not order food.
    """

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Returns the default url for the object. A Group does not have a DetailView,
        so the url UpdateView is returned instead.
        """
        return reverse('order_group_update', args=[self.pk])


class Unit(models.Model):
    """
    A model representing a Unit in which the food is ordered.

    E.G. KG, Liter etc.

    The model differs between the unit for the price and the unit for the order.
    For example, the price could be in KG but you should order in Gram. In this
    case the divisor attribute has to be an integer, which can be used to calculate
    the price for the order. In the example above, it would be 1000.

    To show the name of a unit, you should not use the db-values, but the attributes
    self.price and self.order.
    """

    name = models.CharField(max_length=255, unique=True)
    """
    Name for the Unit. If order- and price-unit differce. This is the attribute
    for the price.
    """

    order_name = models.CharField(max_length=255, blank=True)
    """
    Name of the unit shound behinde the a order.
    """

    divisor = models.PositiveIntegerField(default=1)
    """
    Integer used to calculate the price for a order
    """

    def __str__(self):
        return self.name

    @property
    def price(self):
        """
        Shows the name of the unit for a price.

        This is always the db-value self.name
        """
        return self.name

    @property
    def order(self):
        """
        Shows the name of the unit for an order.

        This is self.name if the name for price and order are the same, else
        it is the db-field order_name.
        """
        return self.order_name or self.name


class Product(models.Model):
    """
    Model to representing a product (food).
    """

    name = models.CharField(max_length=255, unique=True)
    """
    The Name of the product.

    Lists of products are soted by this field.
    """

    unit = models.ForeignKey(Unit, verbose_name="Einheit")
    """
    The unit in which the product is ordered.
    """

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                blank=True, verbose_name="Preis")  # TODO: use a custom Integerfield
    """
    Price of one unit of the product.
    """

    available = models.BooleanField(default=True, verbose_name="Verfügbar")
    """
    Flag to save, if the product can be ordered. If False, it will not be shound
    in the order-table.
    """

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Returns the UpdateView for a product, because there is no DetailView
        for a product.
        """
        return reverse('order_product_update', args=[self.pk])

    @property
    def multiplier(self):
        """
        Returns a value to calculate the price for the order.

        For example by a price of 1 EUR for a KG, it returns 0.001 (EUR for Gram)
        """
        if self.price is None:
            return 0
        return self.price / self.unit.divisor


class Bundle(models.Model):
    """
    Model to represent all orders from each group for a specific time.
    """

    start = models.DateTimeField(auto_now_add=True)
    """
    Time of the order/bundle.

    Sort-attribute for a list of bundles.
    """

    open = models.BooleanField(default=True)
    """
    Flag to show, if there can still be orders, or if the time for orders is
    finished. If open == False, no more orders can be added.
    """

    class Meta:
        get_latest_by = 'start'

    def __str__(self):
        return "Bestellung vom {}".format(self.start.strftime('%d.%m.%Y'))

    def get_absolute_url(self):
        return reverse('order_bundle_detail', args=[self.pk])

    def has_unknown_price(self, group=None, delivered=False):
        """
        Returns True or False, if there is a relevant product in the bundle,
        which has no price.

        if group is set to a group, relevant products are only those, ordered
        from the group.

        if delivered is True, products where nothing was delivered are ignored
        """
        kwargs = {'delivered': 0} if delivered else {'amount': 0}
        query = self.orders.exclude(**kwargs).filter(product__price=None)
        if group is None:
            return query.exists()
        else:
            return query.filter(group=group).exists()

    def has_unknown_price_delivered(self):
        """
        Method for the template where the attribute delivered can not be set
        """
        return self.has_unknown_price(delivered=True)

    def price_for_group(self, group, delivered=False):
        """
        Returns the full price for all products for a specific group.

        This software differes between the order of a group, and the amount of
        products that are actual delivered. If the attribute delivered is False,
        the order-price is returned. If delivered is True, the price is shouwn,
        that the group has to pay.
        """
        # TODO: Maybe this has to be done in JS, so the method can be deleted.
        query = self.orders.filter(group=group).select_related('product__unit')
        if delivered:
            return sum(order.product.multiplier * order.get_delivered() for order in query)
        else:
            return sum(order.product.multiplier * order.amount for order in query)

    def price_for_all(self, delivered=False):
        """
        Returns the price for all groups.

        For the attribute delivered, see the method price_for_group.
        """
        # TODO: Maybe this has to be done in JS
        query = self.orders.select_related('product__unit')
        if delivered:
            return sum(order.product.multiplier * order.get_delivered() for order in query)
        else:
            return sum(order.product.multiplier * order.amount for order in query)


class Order(models.Model):
    """
    Model representing the order of one group for one product for one bundle.
    """

    group = models.ForeignKey(Group)
    product = models.ForeignKey(Product)
    bundle = models.ForeignKey(Bundle, related_name='orders')

    amount = models.PositiveIntegerField(default=0, blank=True)
    delivered = models.PositiveIntegerField(null=True, blank=True)
    """
    The model differentiate between the amount ordered and the amount that was
    actual delivered.

    The attribute delivered should not be used directly, but with the method
    get_delivered.
    """

    class Meta:
        unique_together = ('group', 'product', 'bundle')

    def __str__(self):
        # TODO: nicht auf foreignkeys verweisen
        return "{:<10} {:5} x {}".format("%s:" % self.group, self.amount, self.product)

    def get_delivered(self):
        """
        Returns the db-value delivered if it is not None, else the db-value
        amount.
        """
        return self.delivered if self.delivered is not None else self.amount
