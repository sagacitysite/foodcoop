import pytest

from order.models import Group, Unit, Product, Bundle


@pytest.mark.django_db
class TestBundle:
    def test_Bundle_price_for_group(self):
        me = Group.objects.create(name='My Group')
        liter = Unit.objects.create(name='Liter')
        kilo = Unit.objects.create(name='Kilo', divisor=1000)
        milk = Product.objects.create(name='milk', price=1.53, unit=liter)
        rice = Product.objects.create(name='rice', price=0.78, unit=kilo)
        bundle = Bundle.objects.create()
        bundle.orders.create(group=me, product=milk, amount=3)
        bundle.orders.create(group=me, product=rice, amount=800)

        assert "{:.2f}".format(bundle.price_for_group(me)) == '5.21'


@pytest.mark.django_db
class TestUnit:
    def test_name(self):
        test_unit = Unit.objects.create(name='MyTestName')

        assert str(test_unit) == 'MyTestName'
        assert test_unit.price == 'MyTestName'
        assert test_unit.order == 'MyTestName'

    def test_order_name(self):
        test_unit = Unit.objects.create(name='MyTestName', order_name='OtherName')

        assert str(test_unit) == 'MyTestName'
        assert test_unit.price == 'MyTestName'
        assert test_unit.order == 'OtherName'
