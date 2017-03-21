<?php

$dbip = '192.168.10.111';
$dbname = 'hue';
$dbuser = 'hue';
$dbpass = 'hue123';
$ip_addres = '192.168.10.13';
$gateway = '192.168.10.1';
$mac = '12:1F:CF:F6:90:75';

global $con;
$con = mysqli_connect($dbip, $dbuser, $dbpass, $dbname);
if (mysqli_connect_errno()) {
    echo 'Failed to connect to MySQL: '.mysqli_connect_error();
}

function convert_xy($x, $y, $brightness_raw)
{
    $Y = $brightness_raw / 255.0;

    $z = 1.0 - $x - $y;

    $X = ($Y / $y) * $x;
    $Z = ($Y / $y) * $z;

    // sRGB D65 conversion
    $r =  $X * 1.656492 - $Y * 0.354851 - $Z * 0.255038;
    $g = -$X * 0.707196 + $Y * 1.655397 + $Z * 0.036152;
    $b =  $X * 0.051713 - $Y * 0.121364 + $Z * 1.011530;

    if ($r > $b && $r > $g && $r > 1.0) {
        // red is too big
        $g = $g / $r;
        $b = $b / $r;
        $r = 1.0;
    }
    else if ($g > $b && $g > $r && $g > 1) {
        // green is too big
        $r = $r / $g;
        $b = $b / $g;
        $g = 1.0;
    }
    else if ($b > $r && $b > $g && $b > 1) {
        // blue is too big
        $r = $r / $b;
        $g = $g / $b;
        $b = 1;
    }

    // Apply gamma correction
    $r = $r <= 0.0031308 ? 12.92 * $r : (1.0 + 0.055) * pow($r, (1.0 / 2.4)) - 0.055;
    $g = $g <= 0.0031308 ? 12.92 * $g : (1.0 + 0.055) * pow($g, (1.0 / 2.4)) - 0.055;
    $b = $b <= 0.0031308 ? 12.92 * $b : (1.0 + 0.055) * pow($b, (1.0 / 2.4)) - 0.055;

    if ($r > $b && $r > $g) {
        // red is biggest
        if ($r > 1) {
            $g = $g / $r;
            $b = $b / $$r;
            $r = 1;
        }
    }
    else if ($g > $b && $g > $r) {
        // green is biggest
        if ($g > 1) {
            $r = $r / $g;
            $b = $b / $g;
            $g = 1;
        }
    }
    else if ($b > $r && $b > $g) {
        // blue is biggest
        if ($b > 1) {
            $r = $r / $b;
            $g = $g / $b;
            $b = 1;
        }
    }

    $r = $r < 0 ? 0 : $r;
    $g = $g < 0 ? 0 : $g;
    $b = $b < 0 ? 0 : $b;

    return array((int) ($r * 255), (int) ($g * 255), (int) ($b * 255));
}

function convert_ct($mirek, $bri)
{
    $hectemp = 10000 / $mirek;
    if ($hectemp <= 66) {
        $r = 255;
        $g = 99.4708025861 * log($hectemp) - 161.1195681661;
        $b = $hectemp <= 19 ? 0 : (138.5177312231 * log($hectemp - 10) - 305.0447927307);
    } else {
        $r = 329.698727446 * pow(hectemp - 60, -0.1332047592);
        $g = 288.1221695283 * pow(hectemp - 60, -0.0755148492);
        $b = 255;
    }
    $r = $r > 255 ? 255 : $r;
    $g = $g > 255 ? 255 : $g;
    $b = $b > 255 ? 255 : $b;

    return array((int)$r * ($bri / 255), (int)$g * ($bri / 255), (int)$b * ($bri / 255));
}

function update_light($light, $data)
{
    global $con;
    $array_data = json_decode($data, true);
    $query_light_status = mysqli_query($con, "SELECT state, bri, xy, ct, colormode, ip, strip_light_nr FROM lights WHERE id = $light;");
    $row_light_status = mysqli_fetch_assoc($query_light_status);
    $url = "http://$row_light_status[ip]/";

    if (isset($array_data['on']) && count($array_data) == 1) {
        if ($array_data['on'] == false) {
            $url .= 'off';
            if (is_numeric($row_light_status['strip_light_nr'])) {
                $url .= '?light='.$row_light_status['strip_light_nr'];
            }
        } else {
            $url .= 'on';
            if (is_numeric($row_light_status['strip_light_nr'])) {
                $url .= '?light='.$row_light_status['strip_light_nr'];
            }
        }
    } else {
      if (isset($array_data['bri'])) {
        $bri = $array_data['bri'];
      } else {
        $bri = $row_light_status['bri'];
      }
      if (isset($array_data['xy'])) {
        $rgb = convert_xy($array_data['xy'][0], $array_data['xy'][1], $bri);
      } else if (isset($array_data['ct'])) {
        $rgb = convert_ct($array_data['ct'], $bri);
      } elseif ($row_light_status['colormode'] == 'xy') {
        $xy = json_decode($row_light_status['xy'], true);
        $rgb = convert_xy($xy[0], $xy[1], $bri);
      } elseif ($row_light_status['colormode'] == 'ct') {
        $rgb = convert_ct($row_light_status['ct'], $bri);
      }
      $url .= "set?r=$rgb[0]&g=$rgb[1]&b=$rgb[2]";
      if (is_numeric($row_light_status['strip_light_nr'])) {
          $url .= '&light='.$row_light_status['strip_light_nr'];
      }
      if (isset($array_data['transitiontime'])) {
        $url .= '&fade='.$row_light_status['transitiontime'];
      }
    }
    error_log($url);
    $ch = curl_init();

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);

    $result = curl_exec($ch);

    curl_close($ch);
}

$url = (explode('/', $_SERVER['REQUEST_URI']));
$output_array = array();
$print_entire_config = false;
if (count($url) > 2 && !empty($url['2'])) {
    $query_users = mysqli_query($con, "SELECT * FROM users WHERE username = '".$url['2']."';");
    $row_cnt = $query_users->num_rows;
    if ($row_cnt == 0) {
        if ($url['2'] == 'config' || $url['3'] == 'config') {
            $output_array = array(
                'name' => 'hue emulator',
                'datastoreversion' => 59,
                'swversion' => '01036659',
                'apiversion' => '1.15.0',
                'mac' => $mac,
                'bridgeid' => '121FCFF69075',
                'factorynew' => false,
                'replacesbridgeid' => null,
                'modelid' => 'BSB001',
            );
        } else {
            $output_array[] = array(
                'error' => array(
                    'type' => 1,
                    'address' => $url['3'],
                    'description' => 'unauthorized user',
                ),
            );
        }
    } elseif (isset($url['3'])) {
        if ($url['3'] == 'config') {
            require 'config.php';
        } elseif ($url['3'] == 'lights') {
            require 'lights.php';
        } elseif ($url['3'] == 'groups') {
            require 'groups.php';
        } elseif ($url['3'] == 'schedules') {
            require 'schedules.php';
        } elseif ($url['3'] == 'rules') {
            require 'rules.php';
        } elseif ($url['3'] == 'scenes') {
            require 'scenes.php';
        } elseif ($url['3'] == 'sensors') {
            require 'sensors.php';
        } elseif ($url['3'] == 'resourcelinks') {
            require 'resourcelinks.php';
        } elseif ($url['3'] == 'capabilities') {
            require 'capabilities.php';
        }
    } else {
        $print_entire_config = true;
        require 'lights.php';
        require 'groups.php';
        require 'config.php';
        require 'schedules.php';
        require 'scenes.php';
        require 'sensors.php';
        require 'rules.php';
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    if (isset($data['devicetype'])) {
        $new_user = hash('ripemd160', $data['devicetype']);
        error_log("mysql: INSERT INTO `users`(`username`, `devicetype`, `last_use_date`, `create_date`) VALUES ('".$new_user."',".$data['devicetype']."',NOW(),NOW());");
        mysqli_query($con, "INSERT INTO `users`(`username`, `devicetype`, `last_use_date`, `create_date`) VALUES ('".$new_user."','".$data['devicetype']."',NOW(),NOW());");
        $output_array[] = array(
            'success' => array(
                'username' => $new_user,
            ),
        );
    }
} elseif ($url['1'] == 'description.xml') {
    require 'description.php';
}
if ($_SERVER['REQUEST_METHOD'] == 'PUT' || $_SERVER['REQUEST_METHOD'] == 'POST' || $_SERVER['REQUEST_METHOD'] == 'GETTTT') {
    error_log($_SERVER['REQUEST_METHOD'].' '.implode('/', $url).' RESPONSE: '.json_encode($output_array, JSON_UNESCAPED_SLASHES));
}

echo json_encode($output_array, JSON_UNESCAPED_SLASHES);
mysqli_close($con);
?>

