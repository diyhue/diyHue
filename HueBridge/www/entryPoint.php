<?php

require_once('bridge-config.php');

global $con;
$con = mysqli_connect($dbip, $dbuser, $dbpass, $dbname);
if (mysqli_connect_errno()) {
    echo 'Failed to connect to MySQL: '.mysqli_connect_error();
}


function update_light($light, $data)
{
    global $con;
    $array_data = json_decode($data, true);
    $query_light_status = mysqli_query($con, "SELECT ip, strip_light_nr FROM lights WHERE id = $light;");
    $row_light_status = mysqli_fetch_assoc($query_light_status);
    $url = "http://$row_light_status[ip]/set?light=$row_light_status[strip_light_nr]";
    foreach ($array_data as $key => $value) {
      if ($key == "xy") {
          $url .= "&x=$value[0]&y=$value[1]";
        } else {
          $url .= "&$key=$value";
        }
    }

    error_log($url);
    #error_log($url);
    $ch = curl_init();

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 3);

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
        #error_log("mysql: INSERT INTO `users`(`username`, `devicetype`, `last_use_date`, `create_date`) VALUES ('".$new_user."',".$data['devicetype']."',NOW(),NOW());");
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
    #error_log($_SERVER['REQUEST_METHOD'].' '.implode('/', $url).' RESPONSE: '.json_encode($output_array, JSON_UNESCAPED_SLASHES));
}

echo json_encode($output_array, JSON_UNESCAPED_SLASHES);
mysqli_close($con);
?>
