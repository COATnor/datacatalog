$(".coatcustom-select2").select2();
$("#field-tag_string-wrapper").on("change", function (e) {$("#field-tag_string").val(e.val.toString(',')); })
$("#field-tag_string").val($("#field-tag_string-wrapper").val().toString(','));
