
$(document).ready(function(){

  // element variables
  var csrf_input = $("input[name='csrfmiddlewaretoken']");
  var submit_button = $("form[action='.'] button[type='submit']");  // not flickr submit
  var image_input = $("#id_image");
  var image_input_div = $(".image-input-div");
  var messages_div = $("#message");
  var progress_div = $(".upload-progress");
  var progress_bar_div = $(".progress");
  var progress_bar = $(".progress-bar");
  var image_thumbnail_div = $("#image-thumbnail");
  var upload_id_hidden = $("#id_upload_id");
  var success_alert = $(".file-success");
  var error_div = $("#error-message");
  var drag_info = $(".infoDrag");
  var max_file_size = parseInt(image_input.attr('data-max-file-size'))*1000000; // MB to bytes
  var max_photo_size = parseInt(image_input.attr('data-max-photo-file-size'))*1000000; // MB to bytes
  var chunk_size = parseInt(image_input.attr('data-chunk-size'));

  // chunk variables
  var uploading_photo = 1;
  var total_photos = 0;
  var md5 = "";
  var csrf = csrf_input[0].value;
  var form_data = [{"name": "csrfmiddlewaretoken", "value": csrf}];

  submit_button.attr("disabled", "disabled");

  function calculate_md5(file, chunk_size, chunk_complete, data) {
    var slice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
    var chunks = Math.ceil(file.size / chunk_size);
    var current_chunk = 0;
    var spark = new SparkMD5.ArrayBuffer();

    function onload(e) {
      spark.append(e.target.result);  // append chunk
      current_chunk++;
      if (current_chunk < chunks) {
        read_next_chunk();
      } else {
        md5 = spark.end();

        // Callback called once the md5 hash operation is finished
        if (chunk_complete) {
          chunk_complete(md5, data);
        }
      }
    }
    function read_next_chunk() {
      var reader = new FileReader();
      reader.onload = onload;
      var start = current_chunk * chunk_size,
      end = Math.min(start + chunk_size, file.size);
      reader.readAsArrayBuffer(slice.call(file, start, end));
    }
    read_next_chunk();
  }

  function visuals_before_upload(){
    submit_button.removeAttr("disabled");
    image_input_div.addClass("hidden");
    messages_div.empty();
    progress_div.removeClass("hidden");
    progress_div.find('.photo-current').text(uploading_photo);
    progress_div.find('.photo-total').text(total_photos);
    progress_bar_div.removeClass("hidden");
    progress_bar.attr("aria-valuenow", 0);
    progress_bar.css("width", 0 + "%");
    success_alert.removeClass("hidden");
    drag_info.addClass("hidden");
  }

  function visuals_success(data){
    // progress_bar_div.addClass("hidden");
    uploading_photo += 1;
    if (uploading_photo <= total_photos){
      progress_div.find('.photo-current').text(uploading_photo);
    } else {
      progress_div.addClass("hidden");
      progress_bar_div.addClass("hidden");
      image_input_div.removeClass("hidden");
    }
    var message = '<p>' + data.message + '</p>';
    messages_div.append(message);
  }

  function visuals_error(message_attr){
    image_input_div.removeClass("hidden");
    progress_div.addClass("hidden");
    progress_bar_div.addClass("hidden");
    error_div.removeClass("hidden");
    success_alert.addClass("hidden");
    var error_message = error_div.attr(message_attr);
    error_div.find("p").text(error_message);
  }

  // Callback that handles the final step of the chunk recording
  function chunk_complete(md5, data){
    $.ajax({
      type: "POST",
      url: image_input.attr("data-chunk-complete-url"),
      data: {
        csrfmiddlewaretoken: csrf,
        upload_id: data.result.upload_id,
        md5: md5
      },
      dataType: "json",
      success: function(data) {
        form_data.splice(1);
        visuals_success(data);
      }
    });
  }

  function image_thumbnail(data){
    loadImage(
        data.files[0],
        function (img) {
          if (img.type === "error") {
            var dummy_image = image_thumbnail_div.attr("data-dummy-image");
            img = '<img src=' + dummy_image + ' width="150" height="120"/>'
          }
          var div = $('<div/>', {
            class: "col-sm-3 col-lg-2",
            html: img
          });
          div.append('<p>' + data.files[0].name + '</p>');
          var delete_title = image_input.attr('data-delete-title');
          div.append('<button type="button" class="btn btn-default delete-photo" data-photo="'+ data.result.upload_id +'" aria-label="Cancel">' + delete_title + ' <i class="icon fa fa-trash"></i></button>');
          image_thumbnail_div.append(div);
        },
        {
          // maxWidth: 200, minWidth: 200,
          // maxHeight: 150, minHeight: 150
        } // Options
      );
  }

  function generic_thumbnail(data){
    var dummy_image = image_thumbnail_div.attr("data-dummy-image");
    img = '<img src=' + dummy_image + ' width="150" height="120"/>';
    var div = $('<div/>', {
      class: "col-sm-3 col-lg-2",
      html: img
    });
    div.append('<p>' + data.files[0].name + '</p>');
    var delete_title = image_input.attr('data-delete-title');
    div.append('<button type="button" class="btn btn-default delete-photo" data-photo="'+ data.result.upload_id +'" aria-label="Cancel">' + delete_title + ' <i class="icon fa fa-trash"></i></button>');
    image_thumbnail_div.append(div);
  }

  image_input.fileupload({
    url: image_input.attr("data-chunk-url"),
    dataType: "json",
    maxChunkSize: chunk_size,
    formData: form_data,
    limitMultiFileUploads: 1,
    sequentialUploads: true,
    singleFileUploads: true,
    add: function(e, data) { // Called before starting upload
      total_photos = data.originalFiles.length;

      // If this is the second file you're uploading we need to remove the
      // old upload_id and just keep the csrftoken (which is always first).
      form_data.splice(1);

      // validations
      var file = data.files[0];
      var imageFileTypesAccepted = /(\.|\/)(gif|jpe?g|png|tif?f)$/i; // Removed .psd, .eps and .ai
      if(imageFileTypesAccepted.test(file.name) && max_photo_size > 0 && file.size > max_photo_size) {
        visuals_error("data-max-photo-file-size-message");
        return;
      } else if(file.size > max_file_size) {
        visuals_error("data-max-size-message");
        return;
      }

      var acceptFileTypes = /(\.|\/)(gif|jpe?g|png|tif?f|psd|eps|ai|mov|mpeg4|mp4|avi|wmv|mpegps|flv|3gpp|webm|aiff|wav|flac|alac|ogg|mp2|mp3|aac|amr|wma|pdf)$/i;
      if(!acceptFileTypes.test(file.name)) {
        visuals_error("data-file-type-message");
        return;
      }

      visuals_before_upload();
      calculate_md5(data.files[0], chunk_size);
      data.submit();
    },
    chunkdone: function (e, data) { // Called after uploading each chunk
      if (form_data.length < 2) {
        form_data.push(
          {"name": "upload_id", "value": data.result.upload_id}
        );
      }

      // If is the last chunk, remove the upload_id from the form request
      if (data.loaded == data.total) {
        form_data.splice(1);
      }

      var progress = parseInt(data.loaded / data.total * 100.0, 10);
      progress_bar.attr("aria-valuenow", progress);
      progress_bar.css("width", progress+ "%");
    },
    done: function (e, data) { // Called when the file has completely uploaded
      calculate_md5(data.files[0], data.files[0].size, chunk_complete, data);
      var thumbnailType = /(\.|\/)(gif|jpe?g|png)$/i;
      if (thumbnailType.test(data.files[0].name)){
        image_thumbnail(data);
      } else {
        generic_thumbnail(data);
      }
    },
    error: function (e, data) {
      visuals_error("data-error-message");
    }
  });

  $('body').on('click', '.delete-photo', function(){
    upload_id_hidden.val("");
    success_alert.addClass("hidden");
    image_input_div.removeClass("hidden");
    $(this).parent().remove();
    if(!$('.delete-photo').length && progress_div.hasClass("hidden")){
      drag_info.removeClass("hidden");
    }
  });

  // before submit, copy upload ids in upload_id_hidden
  submit_button.click(function(){
    var ids = "";
    // get photos upload ids
    var elements = image_thumbnail_div.find('button');
    $.each( elements, function( key, element ) {
      if(ids){
        ids += ',';
      }
      ids += element.getAttribute("data-photo");
    });
    upload_id_hidden.val(ids);
    return true;
  });

}); // ready
