from unittest.mock import MagicMock, patch
import pytest
import json

from django.core.exceptions import ObjectDoesNotExist

from order import views
from order.models import Unit, Product


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
        view.request = request = rf.get('/', {})
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
