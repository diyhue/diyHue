
/* toggle lights/groups topbar */
function toggleLights(x) {
  x.classList.toggle("fas fa-lightbulb");
}
/* END toggle lights/groups topbar */

function postData(t) {
  var e = new XMLHttpRequest;
  e.timeout = 2000;
  e.open("PUT", "/state", !0);
  e.setRequestHeader("Content-Type", "application/json");
  console.log(JSON.stringify(t)), e.send(JSON.stringify(t));
}

/* collapse sidebar */
$(document).ready(function() {
  $('#sidebarCollapse').on('click', function() {
    $('.sidebar').toggleClass('active');
  });
/* end collapse sidebar */


  $('.slideContainer').change( function() {
            var element = $(this).parent().attr('id').split("_")[1]
            postData({
              "group": element,
              "action": {
                "bri": $(this).children().val()
              }
            });
        });

  $(function() {
    $(".switchContainer").change(function() {
      var element = $(this).parent().attr('id').split("_")[1]
      if ($(":checkbox:eq(0)", this).attr("checked", "checked").prop('checked')) {
        $(this).parent().removeClass( "textLight" ).addClass( "textDark" );
        postData({
          "group": element,
          "action": {
            "on": true
          }
        });
      } else {
        $(this).parent().removeClass( "textDark" ).addClass( "textLight" );
        postData({
          "group": element,
          "action": {
            "on": false
          }
        })
      }
    });
  });

  $(function updateStatus() {
    $.ajax({
      type: 'GET',
      url: "/state",
      dataType: "json",
      success: function(data) {
        if (!data) {
          return;
        }
        for (var key in data) {
          if (data[key]["on"]) {
            var step = 100 / data[key]["lights"].length;
            var style = "linear-gradient(90deg, ";
            for (var i = 0; i < data[key]["lights"].length; i++) {
              var rgb = "rgba(255,212,93,1)";
              if (data[key]["lights"][i]["colormode"] == "xy") {
                rgb = cieToRGB(data[key]["lights"][i]["xy"][0], data[key]["lights"][i]["xy"][1], 254)
              }
              else if (data[key]["lights"][i]["colormode"] == "ct") {
                rgb = colorTemperatureToRGB(data[key]["lights"][i]["ct"])
              }
              style = style + rgb + ' ' + step * (i + 1) + '%,';
            }
            style = style.slice(0, -1) + ')';

            $("#group_" + key).css({
              "background": style
            });
            $("#group_" + key).find('.switchContainer').children().children().prop( "checked", true )
            console.log(style);
          } else {
            $("#group_" + key).css({
              "background": "rgba(39, 39, 39,1)"
            });
            $("#group_" + key).find('.switchContainer').children().children().prop( "checked", false )
          }
        }
        console.log('update state done');
        //console.log(data);
      },
      error: function() {
        console.log('error getting state');
      },
      timeout: 1000
    });
    setTimeout(updateStatus, 1000);
  });


});


function cieToRGB(x, y, brightness) {
  //Set to maximum brightness if no custom value was given (Not the slick ECMAScript 6 way for compatibility reasons)
  if (brightness === undefined) {
    brightness = 254;
  }

  var z = 1.0 - x - y;
  var Y = (brightness / 254).toFixed(2);
  var X = (Y / y) * x;
  var Z = (Y / y) * z;

  //Convert to RGB using Wide RGB D65 conversion
  var red = X * 1.656492 - Y * 0.354851 - Z * 0.255038;
  var green = -X * 0.707196 + Y * 1.655397 + Z * 0.036152;
  var blue = X * 0.051713 - Y * 0.121364 + Z * 1.011530;

  //If red, green or blue is larger than 1.0 set it back to the maximum of 1.0
  if (red > blue && red > green && red > 1.0) {

    green = green / red;
    blue = blue / red;
    red = 1.0;
  } else if (green > blue && green > red && green > 1.0) {

    red = red / green;
    blue = blue / green;
    green = 1.0;
  } else if (blue > red && blue > green && blue > 1.0) {

    red = red / blue;
    green = green / blue;
    blue = 1.0;
  }

  //Reverse gamma correction
  red = red <= 0.0031308 ? 12.92 * red : (1.0 + 0.055) * Math.pow(red, (1.0 / 2.4)) - 0.055;
  green = green <= 0.0031308 ? 12.92 * green : (1.0 + 0.055) * Math.pow(green, (1.0 / 2.4)) - 0.055;
  blue = blue <= 0.0031308 ? 12.92 * blue : (1.0 + 0.055) * Math.pow(blue, (1.0 / 2.4)) - 0.055;


  //Convert normalized decimal to decimal
  red = Math.round(red * 255);
  green = Math.round(green * 255);
  blue = Math.round(blue * 255);

  if (isNaN(red))
    red = 0;

  if (isNaN(green))
    green = 0;

  if (isNaN(blue))
    blue = 0;

  return "rgba(" + red + "," + green + "," + blue + ",1)";
  }



  function colorTemperatureToRGB(mireds) {

    var hectemp = 20000.0 / mireds;

    var red, green, blue;

    if (hectemp <= 66) {

      red = 255;
      green = 99.4708025861 * Math.log(hectemp) - 161.1195681661;
      blue = hectemp <= 19 ? 0 : (138.5177312231 * Math.log(hectemp - 10) - 305.0447927307);


    } else {

      red = 329.698727446 * Math.pow(hectemp - 60, -0.1332047592);
      green = 288.1221695283 * Math.pow(hectemp - 60, -0.0755148492);
      blue = 255;

    }

    red = red > 255 ? 255 : red;
    green = green > 255 ? 255 : green;
    blue = blue > 255 ? 255 : blue;

    return "rgba(" + red + "," + green + "," + blue + ",1)";


    }
