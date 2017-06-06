
$(document).ready(function(){

  // variables
  var cart_div = $("#photo-cart");
  var add_photo_link = $(".photo-cart-add");
  var cart_badge = $(".basket a span.badge");
  var remove_photo_class = '.remove-photo';
  var remove_all_class = '.empty-cart';
  var message_p_selector =  "#photo-cart p.message";
  var message_p = $(message_p_selector);
  var error_message = message_p.attr('data-error');
  var size_message = message_p.attr('data-size');
  var max_photos = parseInt(message_p.attr('data-max'));
  var no_photos_message = $("#no-photos-in-cart");
  var delete_cart_button = $(".empty-cart");
  var edit_cart_button = $(".edit-cart");
  var cart_slide = $("#cart_slide");

  cart_badge.text($(remove_photo_class).length);

  // error
  function action_error(){
    $(message_p_selector).text(error_message);
  }

  // add a photo to the cart
  add_photo_link.click(function(){

    var $this = $(this);
    $(message_p_selector).text("");

    // add the photo if it hasn't been added before
    if (!$this.hasClass("added")){
      // check there are less than 10 photos in the cart
      if ($(remove_photo_class).length == max_photos){
        $(message_p_selector).text(size_message);
        cart_badge.addClass("danger");
      } else {

        var url = $this.attr("data-url");
        var photo_title = $this.attr("data-title");
        var photo_id = $this.attr("data-photo");
        var photo_thumbnail = $this.attr("data-thumbnail");

        $.ajax({
          url: url,
          data : { title : photo_title, thumbnail : photo_thumbnail, id: photo_id },
          success: function(data){add_success(data)},
          error: action_error
        });

        // add photo success
        function add_success(data){
          $this.addClass("added");
          no_photos_message.addClass("hidden");
          delete_cart_button.removeClass("hidden");
          edit_cart_button.removeClass("hidden");
          cart_slide.html(data);
          cart_badge.text($(remove_photo_class).length);
        }

      } // else
    }

  }); // photo cart add

  // remove photo from the cart
  $(document).on('click', remove_photo_class, function(){
    $(message_p_selector).text("");
    var $this = $(this);
    var photo_id = $this.attr('data-photo');
    var url = cart_div.attr('data-remove-url');
    $.ajax({
      url: url + photo_id + "/",
      success: function(data){remove_success(data)},
      error: action_error
    });

    function remove_success(data){
      cart_slide.html(data);
      $(".photo-cart-add[data-photo='"+ photo_id +"']").removeClass("added");
      var cart_photos = $(remove_photo_class).length;
      cart_badge.removeClass("danger");
      cart_badge.text(cart_photos);
      if(!cart_photos){
        no_photos_message.removeClass("hidden");
        delete_cart_button.addClass("hidden");
        edit_cart_button.addClass("hidden");
      }
    }

  }); // photo cart remove

  // remove all photos
  $(document).on('click', remove_all_class, function(){
    $(message_p_selector).text("");
    var url = cart_div.attr('data-remove-url');
    var photos_objects = $(remove_photo_class);
    var photos_ids = "";

    $.each( photos_objects, function( key, photo ) {
      var photo_id = photo.getAttribute('data-photo');
      photos_ids += photo_id + ",";
    });  // each

    $.get({
      url: url + "?ids=" + photos_ids,
      success: function(data){clear_success(data)},
      error: action_error
    });

    function clear_success(data){
      cart_slide.html(data);
      add_photo_link.removeClass("added");
      no_photos_message.removeClass("hidden");
      delete_cart_button.addClass("hidden");
      edit_cart_button.addClass("hidden");
      cart_badge.text("0");
      cart_badge.removeClass("danger");
    }

  }); // remove all

  // close cart
  $(document).on('click', '.close-cart', function(){
    cart_slide.removeClass('control-sidebar-open');
  });

}); // ready
