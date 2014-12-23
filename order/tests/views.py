import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import PermissionDenied

from order import views
from order.models import Product


class TestBundleDetailView:
    def test_get_active_group(self, rf):
        """
        Test without any data to a group.
        """
        request = rf.get('/')
        request.session = MagicMock()
        request.session.get.return_value = None
        view = views.BundleDetailView()

        assert view.get_active_group(request) is None

    def test_get_active_group_session(self, rf):
        """
        Test with group data in session.
        """
        request = rf.get('/')
        request.session = MagicMock()
        request.session.get.return_value = 1
        view = views.BundleDetailView()

        with patch('order.models.Group.objects') as group_manager:
            group_manager.get.return_value = 'My test group'

            assert view.get_active_group(request) == 'My test group'
            group_manager.get.assert_called_once_with(pk=1)

    def test_get_active_group_GET(self, rf):
        """
        Test with group data in Get Argument.
        """
        request = rf.get('/?group=1')
        request.session = MagicMock()
        view = views.BundleDetailView()

        with patch('order.views.GroupChooseForm') as mock_form:
            group_mock = MagicMock()
            group_mock.pk = 99

            mock_form.is_valid.return_value = True
            mock_form().cleaned_data.get.return_value = group_mock

            assert view.get_active_group(request) == group_mock
            # TODO: test 99 in session

    @patch('order.models.Order.objects')
    @patch('order.models.Product.objects')
    def test_ajax(self, product_manager, order_manager, rf):
        """
        Test to send order data via ajax
        """
        order_mock = MagicMock()
        order_manager.get_or_create.return_value = (order_mock, None)
        product_manager.get.return_value = 'My test product'
        request = rf.post('/?group=1', {'product': 1, 'amount': 300})
        view = views.BundleDetailView()
        view.object = bundle_mock = MagicMock()
        view.active_group = group_mock = MagicMock()
        bundle_mock.price_for_group.return_value = 666.6666

        response = view.ajax(request)

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == {'price_for_group': '666.67'}
        assert order_mock.amount == 300
        order_mock.save.assert_called_with()
        order_manager.get_or_create.assert_called_with(
            product='My test product', bundle=bundle_mock, group=group_mock)

    @patch('order.models.Product.objects')
    def test_ajax_no_product(self, product_manager, rf):
        """
        Test to send order data via ajax, unkonwn product.
        """
        product_manager.get.side_effect = Product.DoesNotExist('Product does not exist')
        view = views.BundleDetailView()
        view.active_group = MagicMock()
        request = rf.post('/?group=1', {'product': 1, 'amount': 300})

        response = view.ajax(request)

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == {'error': 'product 1 not found'}

    def test_ajax_wrong_data(self, rf):
        """
        Test to send data via ajax, but without data.
        """
        view = views.BundleDetailView()
        request = rf.post('/', {})

        response = view.ajax(request)

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == {'error': 'no product data in request'}

    def test_get(self, rf):
        """
        Test the normal get method.
        """
        view = views.BundleDetailView()
        view.request = request = rf.get('/')
        request.session = MagicMock()
        request.session.get.return_value = False
        bundle_mock = MagicMock()
        bundle_mock.price_for_group.return_value = 333.333
        view.get_object = MagicMock(return_value=bundle_mock)

        response = view.get(request)

        assert response.status_code == 200

    def test_post(self, rf):
        view = views.BundleDetailView()
        view.request = request = rf.post('/', {})
        request.session = MagicMock()
        request.session.get.return_value = False
        bundle_mock = MagicMock()
        bundle_mock.price_for_group.return_value = 333.333
        view.get_object = MagicMock(return_value=bundle_mock)

        response = view.post(request)

        assert response.status_code == 200

    def test_post_on_closed_bundles(self, rf):
        view = views.BundleDetailView()
        view.request = request = rf.post('/', {})
        request.session = MagicMock()
        request.session.get.return_value = False
        bundle_mock = MagicMock()
        bundle_mock.open = False
        view.get_object = MagicMock(return_value=bundle_mock)

        with pytest.raises(PermissionDenied):
            view.post(request)


class TestBundleOrderView:
    def test_get_products(self, rf):
        product1, product2, order1, order2, order3 = (MagicMock() for __ in range(5))
        order1.product = order2.product = product1
        order3.product = product2
        order1.amount, order2.amount, order3.amount = (1, 2, 4)
        product1.name, product2.name = ('zzz', 'aaa')
        product1.multiplier, product2.multiplier = (2, 4)
        view = views.BundleOrderView()
        view.request = rf.get('/')
        view.object = MagicMock()
        view.object.orders.all().select_related.return_value = [order1, order2, order3]

        products = view.get_products()

        assert products == [product2, product1]
        assert product1.amount == 3
        assert product2.amount == 4
        assert product1.order_price == 6
        assert product2.order_price == 16


class TestBundleOutputView:
    @patch('order.models.Group.objects')
    @patch('order.models.Order.objects')
    @patch('order.models.Product.objects')
    def test_ajax(self, product_manager, order_manager, group_manager, rf):
        """
        Test to send order data via ajax
        """
        order_mock = MagicMock()
        product_manager.get.return_value = 'My test product'
        group_manager.get.return_value = 'My test group'
        order_manager.get_or_create.return_value = (order_mock, None)
        order_manager.filter().aggregate.return_value = {'delivered': 999}
        request = rf.post('/', {'product': 1, 'group': 1, 'delivered': 300})
        view = views.BundleOutputView()
        view.object = MagicMock()
        view.object.price_for_group.return_value = 500
        view.object.price_for_all.return_value = 1000

        response = view.ajax(request)

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == {
            'price_for_group': '500.00',
            'price_for_all': '1000.00',
            'product_delivered': 999}
        assert order_mock.delivered == '300'
        order_mock.save.assert_called_with()
        order_manager.get_or_create.assert_called_with(
            product='My test product', bundle=view.object, group='My test group')

    @patch('order.models.Product.objects')
    def test_ajax_no_product(self, product_manager, rf):
        """
        Test to send order data via ajax, unkonwn product.
        """
        product_manager.get.side_effect = Product.DoesNotExist('Product does not exist')
        view = views.BundleOutputView()
        request = rf.post('/', {'product': 1, 'group': 1, 'delivered': 300})

        response = view.ajax(request)

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == {'error': 'Group or product not found'}

    def test_ajax_wrong_data(self, rf):
        """
        Test to send data via ajax, but without data.
        """
        view = views.BundleOutputView()
        request = rf.post('/', {})

        response = view.ajax(request)

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == {'error': 'No product or group data in request'}

    def test_get_context_data(self, rf):
        product = [MagicMock(name='p0'), MagicMock(name='p1'), MagicMock(name='p2')]
        order = [MagicMock(name='o0'), MagicMock(name='o1'), MagicMock(name='o2')]
        # Group1 orders product0 and 1
        # Group2 orders product0
        # Noone orders product2
        order[0].group = order[1].group = 'Group1'
        order[2].group = 'Group2'
        order[0].product = order[2].product = product[0]
        order[1].product = product[1]
        for i in range(3):
            order[i].get_delivered.return_value = (i + 1) * 2
            order[i].amount = (i + 1) * 2
            order[i].product.multiplier = 1
            product[i].name = 'product%d' % i

        view = views.BundleOutputView()
        view.object = MagicMock()
        view.object.orders.all().select_related.return_value = order

        context = view.get_context_data()

        assert context == {
            'groups': {'Group1': [{product[1]: order[1],
                                   product[0]: order[0]},
                                  6],
                       'Group2': [{product[0]: order[2]},
                                  6]},
            'object': view.object,
            'price_for_all': 12,
            'products': [product[0], product[1]],
            'view': view}
        assert context['products'][0].delivered == 8
        assert context['products'][1].delivered == 4
