import pytest

from order.models import Group, Unit, Product, Bundle


@pytest.fixture
def bundle_db():
    db = {}
    db['me'] = me = Group.objects.create(name='My Group')
    other = Group.objects.create(name='Other Group')
    liter = Unit.objects.create(name='Liter')
    db['kilo'] = kilo = Unit.objects.create(name='Kilo', divisor=1000)
    milk = Product.objects.create(name='milk', price=1.53, unit=liter)
    rice = Product.objects.create(name='rice', price=0.78, unit=kilo)
    db['bundle'] = bundle = Bundle.objects.create()
    bundle.orders.create(group=me, product=milk, amount=3)
    bundle.orders.create(group=me, product=rice, amount=800, delivered=500)
    bundle.orders.create(group=other, product=milk, amount=4)
    bundle.orders.create(group=other, product=rice, amount=1800, delivered=1500)
    return db

@pytest.mark.django_db
class TestBundle:
    def test_price_for_group(self, bundle_db):
        assert "{:.2f}".format(bundle_db['bundle'].price_for_group(bundle_db['me'])) == '5.21'

    def test_price_for_group_delivered(self, bundle_db):
        assert "{:.2f}".format(bundle_db['bundle'].price_for_group(bundle_db['me'], delivered=True)) == '4.98'

    def test_price_for_all(self, bundle_db):
        assert "{:.2f}".format(bundle_db['bundle'].price_for_all()) == '12.74'

    def test_price_for_all_delivered(self, bundle_db):
        assert "{:.2f}".format(bundle_db['bundle'].price_for_all(delivered=True)) == '12.27'

    def test_has_unknown_price_true(self, bundle_db):
        apple = Product.objects.create(name='apple', unit=bundle_db['kilo'])
        bundle_db['bundle'].orders.create(group=bundle_db['me'], product=apple, amount=3)
        assert bundle_db['bundle'].has_unknown_price() == True

    def test_has_unknown_price_false(self, bundle_db):
        assert not bundle_db['bundle'].has_unknown_price()

    def test_has_unknown_price_not_in_group(self, bundle_db):
        apple = Product.objects.create(name='apple', unit=bundle_db['kilo'])
        assert not bundle_db['bundle'].has_unknown_price(bundle_db['me'])

    def test_has_unknown_price_group_did_not_order(self, bundle_db):
        apple = Product.objects.create(name='apple', unit=bundle_db['kilo'])
        bundle_db['bundle'].orders.create(group=bundle_db['me'], product=apple, amount=0)
        assert not bundle_db['bundle'].has_unknown_price(bundle_db['me'])

    def test_has_unknown_price_group_not_delivered(self, bundle_db):
        apple = Product.objects.create(name='apple', unit=bundle_db['kilo'])
        bundle_db['bundle'].orders.create(group=bundle_db['me'], product=apple, amount=5, delivered=0)
        assert not bundle_db['bundle'].has_unknown_price(bundle_db['me'], delivered=True)

    def test_has_unknown_price_in_group(self, bundle_db):
        apple = Product.objects.create(name='apple', unit=bundle_db['kilo'])
        bundle_db['bundle'].orders.create(group=bundle_db['me'], product=apple, amount=3)
        assert bundle_db['bundle'].has_unknown_price(bundle_db['me'])

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
