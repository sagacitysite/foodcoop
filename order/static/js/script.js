$(function() {
  var csrftoken = $.cookie('csrftoken');
  function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }
  function sameOrigin(url) {
    // test that a given url is a same-origin URL
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
      (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
      // or any other URL that isn't scheme relative or absolute i.e relative.
      !(/^(\/\/|http:|https:).*/.test(url));
  }
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
        // Send the token to same-origin, relative URLs only.
        // Send the token only if the method warrants CSRF protection
        // Using the CSRFToken value acquired earlier
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    }
  });

  // Order Table
  $('.amount-input input').change(function() {
    var self = $(this);
    $.ajax({
      url: ORDER_AJAX_URL,
      type: 'POST',
      dataType: 'json',
      data: {
        product: self.parent().children('.amount-input-product').html(),
        amount: self.val(),
      },
      success: function(data) {
        $('#order_costs').html(data['price_for_group']);
      }
    });
  });

  // Output Table
  $('.output-input').change(function() {
    var self = $(this);
    var group = self.parent().children('.group').html();
    var product = self.parent().children('.product').html();
    $.ajax({
      url: OUTPUT_AJAX_URL,
      type: 'POST',
      dataType: 'json',
      data: {
        group: group,
        product: product,
        delivered: self.val(),
      },
      success: function(data) {
        $('#price-' + group).html(data['price_for_group']);
        $('#order_costs').html(data['price_for_all']);
        $('#product-delivered-' + product).html(data['product_delivered']);
      }
    });
  });

});
