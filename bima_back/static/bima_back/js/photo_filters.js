
$(document).ready(function(){

  // variables
  var filter_dropdown = '.filter-dropdown';
  var filters_menu = '.dropdown-menu.filters';
  var filter_form = '#filter_form';
  var add_filter_button = '#add-filter';
  var name_input = '#filter_name';
  var remove_filter = '.remove-filter';
  var required_span = '#filter_form span';
  var error_message = '#filter-error';

  function success(data){
    $(filter_dropdown).html(data);
    $('#filterModal').modal('hide');
    $(name_input).val('');
  }

  function success_remove(data){
    $(filter_dropdown).html(data);
  }

  function add_error(){
    $(error_message).removeClass('hidden');
  }

  // add filter
  $(document).on('click', add_filter_button, function(){
    var name = $(name_input).val();
    if(!name){
      $(required_span).removeClass('hidden');
    } else {
      var url = $(filter_form).attr('data-add-filter-url');
      $.ajax({
        url: url,
        data : { name : name, filter: window.location.href },
        success: function(data){success(data)},
        error: add_error
      });
    }
  });

  // remove filter
  $(document).on('click', remove_filter, function(){
    var url = $(this).attr('data-remove-filter-url');
    $.ajax({
      url: url,
      success: function(data){success_remove(data)}
    });
  });

});
