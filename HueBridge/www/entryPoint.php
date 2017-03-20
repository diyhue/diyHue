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
    $brightness = $brightness_raw / 255.0;
    $bright_y = $brightness / $y;
    $X = $x * $bright_y;
    $Z = (1 - $x - $y) * $bright_y;

  // convert to RGB (0.0-1.0) color space
    $R = $X * 1.4628067 - $brightness * 0.1840623 - $Z * 0.2743606;
    $G = -$X * 0.5217933 + $brightness * 1.4472381 + $Z * 0.0677227;
    $B = $X * 0.0349342 - $brightness * 0.0968930 + $Z * 1.2884099;

  // apply inverse 2.2 gamma
    $inv_gamma = 1.0 / 2.4;
    $linear_delta = 0.055;
    $linear_interval = 1 + $linear_delta;
    $r = $R <= 0.0031308 ? 12.92 * $R : $linear_interval * pow($R, $inv_gamma) - $linear_delta;
    $g = $G <= 0.0031308 ? 12.92 * $G : $linear_interval * pow($G, $inv_gamma) - $linear_delta;
    $b = $B <= 0.0031308 ? 12.92 * $B : $linear_interval * pow($B, $inv_gamma) - $linear_delta;

    return array((int) ($r * 255), (int) ($g * 255), (int) ($b * 255));
}

function convert_ct($mirek)
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

    return array($r, $g, $b);

    //return 'setleds?r='.(int) $r.'&g='.(int) $g.'&b='.(int) $b.'&fade=100';
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
        if (isset($array_data['xy']) || isset($array_data['bri']) && $row_light_status['colormode'] == 'xy') {
            if (isset($array_data['xy'])) {
                $rgb = convert_xy($array_data['xy'][0], $array_data['xy'][1], $row_light_status['bri']);
            } else {
                $xy = json_decode($row_light_status['xy'], true);
                $rgb = convert_xy($xy[0], $xy[1], $array_data['bri']);
            }
            if (is_numeric($row_light_status['strip_light_nr'])) {
                $url .= 'set?light='.$row_light_status['strip_light_nr'];
            }
            $url .= "&r=$rgb[0]&g=$rgb[1]&b=$rgb[2]";
        } elseif (isset($array_data['ct']) || isset($array_data['bri']) && $row_light_status['colormode'] == 'ct') {
            if (isset($array_data['ct'])) {
                $rgb = convert_ct($array_data['ct']);
            } else {
                $rgb = convert_ct($row_light_status['ct']);
            }
            if (isset($array_data['bri'])) {
                $r = $rgb[0] * ($array_data['bri'] / 255);
                $g = $rgb[1] * ($array_data['bri'] / 255);
                $b = $rgb[2] * ($array_data['bri'] / 255);
            } else {
                $r = $rgb[0] * ($row_light_status['bri'] / 255);
                $g = $rgb[1] * ($row_light_status['bri'] / 255);
                $b = $rgb[2] * ($row_light_status['bri'] / 255);
            }
            if (is_numeric($row_light_status['strip_light_nr'])) {
                $url .= 'set?light='.$row_light_status['strip_light_nr'];
            }
            $url .= "&r=$r&g=$g&b=$b";
        }
    }
    error_log($url);
    $ch = curl_init();

    curl_setopt($ch, CURLOPT_URL, $url);
//    curl_setopt($ch, CURLOPT_POST, true);
//    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
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
    if (rand(1, 5) != 1) {
        $output_array[] = array(
            'error' => array(
                'address' => '',
                'description' => 'link button not pressed',
                'type' => 101,
            ),
        );
    } elseif (isset($data['devicetype'])) {
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
