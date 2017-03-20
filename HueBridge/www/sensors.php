<?php
if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_sensors = mysqli_query($con, 'SELECT * FROM sensors;');
        while ($row_sensors = mysqli_fetch_assoc($query_sensors)) {
            $sensors_array[$row_sensors['id']] = array(
                'type' => $row_sensors['type'],
                'state' => json_decode($row_sensors['state']),
                'name' => $row_sensors['name'],
                'modelid' => $row_sensors['modelid'],
                'manufacturername' => $row_sensors['manufacturername'],
                'swversion' => $row_sensors['swversion'],
                'recycle' => (bool) $row_sensors['recycle']
            );
            if (!empty($row_sensors['uniqueid'])) {
                $sensors_array[$row_sensors['id']]['uniqueid'] = $row_sensors['uniqueid'];
            }
            if (empty($row_sensors['config'])) {
                $sensors_array[$row_sensors['id']]['config'] = json_decode('{"on": true}');
            } else {
                $sensors_array[$row_sensors['id']]['config'] = json_decode($row_sensors['config']);
            }
        }
        if (isset($sensors_array)) {
            if ($print_entire_config) {
                $output_array['sensors'] = $sensors_array;
            } else {
                $output_array = $sensors_array;
            }
        } else {
            if ($print_entire_config) {
                $output_array['sensors'] = new stdClass();
            } else {
                $output_array = new stdClass();
            }
        }
    } elseif (is_numeric($url['4'])) {
        $query_sensor = mysqli_query($con, "SELECT * FROM sensors WHERE id = '" . $url['4'] . "';");
        $row_sensor   = mysqli_fetch_assoc($query_sensor);
        $output_array = array(
            'type' => $row_sensor['type'],
            'state' => json_decode($row_sensor['state']),
            'name' => $row_sensor['name'],
            'modelid' => $row_sensor['modelid'],
            'manufacturername' => $row_sensor['manufacturername'],
            'swversion' => $row_sensor['swversion'],
            'recycle' => (bool) $row_sensor['recycle']
        );
        if (!empty($row_sensors['uniqueid'])) {
            $output_array['uniqueid'] = $row_sensor['uniqueid'];
        }
        if (empty($row_sensors['config'])) {
            $output_array['config'] = json_decode('{"on": true}');
        } else {
            $output_array['config'] = json_decode($row_sensor['config']);
        }
    } else {
        $query_new_sensors = mysqli_query($con, "SELECT id, name FROM sensors WHERE new = 1;");
        while ($row_new_sensors   = mysqli_fetch_assoc($query_new_sensors)) {
              $output_array[$row_new_sensors['id']] = array('name' => $row_new_sensors['name']);
            }
        $output_array['lastscan'] = gmdate("Y-m-d\TH:i:s");
        $query_remove_new_flag = mysqli_query($con, "UPDATE sensors SET new = 0 WHERE new = 1;");
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), false);
    error_log('SENSORS PUT: ' . json_encode($data));
    $update_string = 'UPDATE sensors SET ';
    foreach ($data as $key => $value) {
        $output_array[] = array(
            'success' => array(
                $url['3'] . '/' . $url['4'] . '/' . $url['5'] . '/' . $key => $value
            )
        );
        if ($key == 'on') {
            $key = 'state';
        }
        if (is_array($value)) {
            $value = json_encode($value);
        }
        error_log($key . '|' . $value);
        $update_string .= $key . " = '" . $value . "',";
    }
    $update_string = rtrim($update_string, ',');
    $update_string .= ' WHERE id = ' . $url['4'];
    $update_sensors = mysqli_query($con, $update_string);
    error_log($update_string);
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data           = json_decode(file_get_contents('php://input'), true);
    error_log('SENSORS POST:' . json_encode($data));
    if (empty($data)) {
        $output_array[] = array(
            'success' => array(
                '/sensors' => "Searching for new devices"
            )
        );
    } else {
        mysqli_query($con, "INSERT INTO `sensors`(`type`, `state`, `name`, `modelid`, `manufacturername`, `uniqueid`, `swversion`, `recycle`) VALUES ('" . $data['type'] . "','" . json_encode($data['state']) . "','" . $data['name'] . "','" . $data['modelid'] . "','" . $data['manufacturername'] . "','" . $data['uniqueid'] . "','" . $data['swversion'] . "'," . ((isset($data['recycle'])) ? 1 : 0) . ");");
        $output_array[] = array(
            'success' => array(
                'id' => (string) mysqli_insert_id($con)
            )
        );
    }
}
?>
