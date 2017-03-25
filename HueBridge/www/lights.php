<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_lights = mysqli_query($con, 'SELECT * FROM lights;');
        while ($row_lights = mysqli_fetch_assoc($query_lights)) {
            $lights_array[$row_lights['id']] = array(
                'state' => array(
                    'on' => (bool) $row_lights['state'],
                    'bri' => intval($row_lights['bri']),
                    'hue' => intval($row_lights['hue']),
                    'sat' => intval($row_lights['sat']),
                    'xy' => json_decode($row_lights['xy']),
                    'ct' => intval($row_lights['ct']),
                    'alert' => $row_lights['alert'],
                    'effect' => $row_lights['effect'],
                    'colormode' => $row_lights['colormode'],
                    'reachable' => true
                ),
                'type' => $row_lights['type'],
                'name' => $row_lights['name'],
                'modelid' => $row_lights['modelid'],
                'swversion' => $row_lights['swversion'],
                'uniqueid' => $row_lights['uniqueid']
            );
        }
        if (isset($lights_array)) {
            if ($print_entire_config) {
                $output_array['lights'] = $lights_array;
            } else {
                $output_array = $lights_array;
            }
        } else {
            if ($print_entire_config) {
                $output_array['groups'] = new stdClass();
            } else {
                $output_array = array();
            }
        }
    } elseif (is_numeric($url['4'])) {
        $query_light  = mysqli_query($con, "SELECT * FROM lights WHERE id = '" . $url['4'] . "';");
        $row_light    = mysqli_fetch_assoc($query_light);
        $output_array = array(
            'type' => $row_light['type'],
            'name' => $row_light['name'],
            'uniqueid' => $row_light['uniqueid'],
            'modelid' => $row_light['modelid'],
            'state' => array(
                'on' => (bool) $row_light['state'],
                'bri' => intval($row_light['bri']),
                'hue' => intval($row_light['hue']),
                'sat' => intval($row_light['sat']),
                'xy' => json_decode($row_light['xy']),
                'ct' => intval($row_light['ct']),
                'alert' => $row_light['alert'],
                'effect' => $row_light['effect'],
                'colormode' => $row_light['colormode'],
                'reachable' => true
            )
        );
    } else {
        $query_new_lights = mysqli_query($con, 'SELECT id, name FROM lights WHERE new = 1;');
        while ($row_new_lights = mysqli_fetch_assoc($query_new_lights)) {
            $output_array[$row_new_lights['id']] = array(
                'name' => $row_new_lights['name']
            );
        }
        $output_array['lastscan'] = gmdate("Y-m-d\TH:i:s");
        $query_remove_new_flag    = mysqli_query($con, 'UPDATE lights SET new = 0 WHERE new = 1;');
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $raw_data = file_get_contents('php://input');
    update_light($url['4'], $raw_data);
    $data          = json_decode($raw_data, true);
    #error_log("LIGHTS PUT: " . json_encode($data));
    $update_string = 'UPDATE lights SET ';
    foreach ($data as $key => $value) {
        $url_response   = implode('/', array_slice($url, 3));
        $output_array[] = array(
            'success' => array(
                '/' . $url_response . '/' . $key => $value
            )
        );
        if ($key == 'on') {
            $key = 'state';
        }
        if (is_array($value)) {
            $value = json_encode($value);
        }
        if ($key == 'xy' || $key == 'ct' || $key == 'hue') {
            $update_string .= "colormode = '" . $key . "',";
        }
        #error_log($key . '|' . $value);
        $update_string .= $key . " = '" . $value . "',";
    }
    $update_string = rtrim($update_string, ',');
    $update_string .= ' WHERE id = ' . $url['4'];
    $update_lights = mysqli_query($con, $update_string);
    #error_log($update_string);
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST' && !isset($url['4'])) {
    $output_array[] = array(
        'success' => array(
            '/lights' => 'Searching for new devices'
        )
    );
    $network_ips = shell_exec("nmap  $gateway/24 -p80 --open -n | grep report | cut -d ' ' -f5");
    $ips_array = explode("\n", $network_ips);
    foreach($ips_array as $ip){
        $url = "http://$ip/detect";
        $ch  = curl_init();

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 1);

        $result = curl_exec($ch);
        if (!empty($result)) {
            $data = json_decode($result, true);
            if (is_array($data) && isset($data['hue'])) {
                error_log("$ip is a hue " . $data['hue']);
                $new_light     = mysqli_query($con, "SELECT ip FROM lights WHERE uniqueid LIKE '".$data['mac']."%' LIMIT 1;");
                $row_cnt       = $new_light->num_rows;
                $row_new_light = mysqli_fetch_assoc($new_light);
                if ($row_cnt > 0) {
                    if ($row_new_light['ip'] == $ip) {
                        error_log("this is already present with correct ip");
                    } else {
                        error_log("fix ip for address ".$data['mac']." new ip is $ip");
                        $query_update_lights = mysqli_query($con, "UPDATE lights SET ip = '$ip' WHERE uniqueid LIKE '".$data['mac']."%';");
                    }
                } else {
                    for ($i = 1; $i <= $data['lights']; ++$i) {
                        if ($data['hue'] == "strip") {
                            mysqli_query($con, "INSERT INTO `lights`(`ct`, `colormode`, `type`, `name`, `uniqueid`, `modelid`, `swversion`, `ip`, `strip_light_nr`) VALUES ('461', 'ct', 'Extended color light','Hue ".$data['type']." ".$data['hue']." Light $i','".$data['mac']."-".$i."','LCT001','66009461', '$ip', '$i');");
                            error_log("INSERT INTO `lights`(`ct`, `colormode`, `type`, `name`, `uniqueid`, `modelid`, `swversion`, `ip`, `strip_light_nr`) VALUES ('461', 'ct', 'Extended color light','Hue ".$data['type']." ".$data['hue']." Light $i','".$data['mac']."-".$i."','LCT001','66009461', '$ip', '$i');");
                        }
                    }
                }
            }
            curl_close($ch);
        }
    }
}
?>
