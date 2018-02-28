
$(document).ready(function(){

  // element variables
  var csrf_input = $("input[name='csrfmiddlewaretoken']");
  var submit_button = $("button[type='submit']");
  var image_div = $('#image');
  var image_input = $('#id_image');
  var upload_id = $("#id_upload_id");
  var max_photo_size = parseInt(image_input.attr('data-max-file-size'))*1000000; // MB to bytes
  var chunk_size = parseInt(image_input.attr('data-chunk-size'));

  // chunk variables
  var md5 = "";
  var csrf = csrf_input[0].value;
  var form_data = [{"name": "csrfmiddlewaretoken", "value": csrf}];

  function visuals_before_upload(){
    image_div.find('p').remove();
    image_div.append('<img src="' + image_input.attr("data-loading-gif") + '"/>');
    submit_button.attr("disabled", "disabled");
  }

  function visuals_success(data){
    image_div.find('img').remove();
    upload_id.val(data.upload_id);
    image_div.append('<p>' + data.message + '</p>');
    submit_button.removeAttr("disabled");
  }

  function visuals_error(message_attr){
    image_div.find('img').remove();
    image_div.append('<p>' + image_input.attr(message_attr) + '</p>');
    submit_button.removeAttr("disabled");
    upload_id.val("");
  }

  function calculate_md5(file) {
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

  image_input.fileupload({
    url: image_input.attr("data-chunk-url"),
    dataType: "json",
    maxChunkSize: chunk_size,
    formData: form_data,
    add: function(e, data) { // Called before starting upload
      // If this is the second file you're uploading we need to remove the
      // old upload_id and just keep the csrftoken (which is always first).
      form_data.splice(1);

      // validations
      var file = data.files[0];
      if(file.size > max_photo_size){
        visuals_error("data-max-size-message");
        return;
      }
      var acceptFileTypes = /(\.|\/)(gif|jpe?g|png|tif?f|psd|mov|mpeg4|mp4|avi|wmv|mpegps|flv|3gpp|webm|aiff|wav|flac|alac|ogg|mp2|mp3|aac|amr|wma|pdf)$/i;
      if(!acceptFileTypes.test(file.name)) {
        visuals_error("data-file-type-message");
        return;
      }

      visuals_before_upload();
      calculate_md5(data.files[0]);
      data.submit();
    },
    chunkdone: function (e, data) { // Called after uploading each chunk
      if (form_data.length < 2) {
        form_data.push(
          {"name": "upload_id", "value": data.result.upload_id}
        );
      }
    },
    done: function (e, data) { // Called when the file has completely uploaded
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
          visuals_success(data);
        }
      });
    },
    error: function(data) {
      visuals_error("data-error-msg");
    }
  });

}); // ready
