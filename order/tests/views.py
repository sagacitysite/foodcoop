from unittest.mock import MagicMock, patch

from order import views


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
