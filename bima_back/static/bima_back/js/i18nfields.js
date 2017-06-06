/*
File: i18nfields

Plugin to transform translatable inputs in tabs

Use guide:

    <script src="path/to/i18nfields.js"></script>

    $(function() {
        $('form').i18nfields({default_language: '{{LANGUAGE_CODE}}'});
    });

*/

( function($) {
  var _i18nfields_options;
  $.fn.i18nfields = function(options, args) {
    _i18nfields_options = jQuery.extend({}, options);
    if ($('.i18nfield').length) {
      initialize();
    }
  };

  function initialize() {
    /* format form-language-tabs */
    var containerSelector = '.form-language-tabs';
    var tabs_container = $('<div class="language-content"/>')
      .append($('<ul/>').addClass('nav nav-tabs'))
      .append($('<div/>').addClass('tab-content'));
    $(containerSelector).append(tabs_container);


    // set tabbs
    $(containerSelector).each(function (containerIndex, element) {
      $(_i18nfields_options.languages).each(function(languageIndex, [code, name]) {
        $('<li/>').prop('id', 'tab_' + code + '_' + containerIndex)
          .append($('<a data-toggle="tab" />').text(name).prop('href', '#' + code + '_' + containerIndex))
          .appendTo($(element).find('ul.nav.nav-tabs'));

        $('<div/>').addClass('tab-pane row').prop('id', code + '_' + containerIndex)
          .appendTo($(element).find('div.tab-content'));
      });
    });

    var inputs = $('.i18nfield');
    $(_i18nfields_options.languages).each(function(index, [code, name]) {
      inputs.filter('[id$='+code+']').each(function (idx, element) {
        var field = $(element).parent('div[id$=_' + code + ']');
        field.appendTo(field.parent().find(containerSelector).find('div.tab-content .tab-pane.row[id^=' + code + '_]'));
      });

    });

    /* active tabs of the default language */
    $(containerSelector).find('ul li[id^=tab_' + _i18nfields_options.defaultLanguage + ']').addClass('active');
    $(containerSelector).find('div.row[id^=' + _i18nfields_options.defaultLanguage + '_]').addClass('active');

    /* clean 'form-language-tabs' which has not elements */
    $(containerSelector).find('.language-content').has('.tab-pane.row:empty').remove()
  }

})(jQuery);
