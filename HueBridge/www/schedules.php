<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_schedules = mysqli_query($con, "SELECT *, DATE_FORMAT(created, '%Y-%m-%dT%T') AS created_conv FROM schedules;");
        while ($row_schedules = mysqli_fetch_assoc($query_schedules)) {
            $schedules_array[$row_schedules['id']] = array(
                    'name' => $row_schedules['name'],
                    'description' => $row_schedules['description'],
                    'command' => json_decode($row_schedules['command'], true),
                    'localtime' => $row_schedules['local_time'],
                    'created' => $row_schedules['created_conv'],
                    'autodelete' => (bool) $row_schedules['autodelete'],
                    'status' => $row_schedules['status'],
                    'recycle' => (bool) $row_schedules['recycle'],
                );

        }
        if (isset($schedules_array)) {
            if ($print_entire_config) {
                $output_array['schedules'] = $schedules_array;
            } else {
                $output_array = $schedules_array;
            }
        } else {
            if ($print_entire_config) {
                $output_array['schedules'] = new stdClass();
            } else {
                $output_array = new stdClass();
            }
        }
    } elseif (is_numeric($url['4'])) {
        $query_schedules = mysqli_query($con, "SELECT *,  DATE_FORMAT(created, '%Y-%m-%dT%T') AS created_conv FROM schedules WHERE id = '".$url['4']."';");
        $row_schedules = mysqli_fetch_assoc($query_schedules);
        $output_array = array(
            'name' => $row_schedules['name'],
            'description' => $row_schedules['description'],
            'command' => json_decode($row_schedules['command'], true),
            'localtime' => $row_schedules['local_time'],
            'created' => $row_schedules['created_conv'],
            'autodelete' => (bool) $row_schedules['autodelete'],
            'status' => $row_schedules['status'],
            'recycle' => (bool) $row_schedules['recycle'],
        );
        if (substr($row_schedules['local_time'], 0, 1) == "P" || substr($row_schedules['local_time'], 0, 1) == "R") {
            $schedules_array['starttime'] = $row_schedules['created_conv'];
        }
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), false);
    error_log("SCHEDULES PUT" . json_encode($data));
    $update_string = "UPDATE schedules SET ";
    foreach ($data as $key => $value) {
        $url_response = implode('/', array_slice($url, 3));
        $output_array[] = array(
            'success' => array(
                '/'.$url_response.'/'.$key => $value,
            ),
        );
        if ($key == 'localtime') {
            $key = 'local_time';
        }
        if (is_array($value) || is_object($value)) {
            $value = json_encode($value);
        }
        $update_string .= $key . " = '" . $value . "',";
    }
    $update_string = rtrim($update_string, ',');
    $update_string .= " WHERE id = ".$url['4'];
    $update_schedules = mysqli_query($con, $update_string);
    error_log($update_string);
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log('SCHEDULES POST:'.json_encode($data));
    mysqli_query($con, "INSERT INTO `schedules`(`name`, `description`, `command`, `local_time`, `created`, `autodelete`, `status`, `recycle`) VALUES ('".$data['name']."','".$data['description']."','".json_encode($data['command'], JSON_UNESCAPED_SLASHES )."','".$data['localtime']."','".gmdate("Y-m-d H:i:s")."','".$data['autodelete']."','".$data['status']."',".((isset($data['recycle']))?1:0).");");
    $output_array[] = array(
        'success' => array(
            'id' => (string) mysqli_insert_id($con),
        ),
    );
} elseif ($_SERVER['REQUEST_METHOD'] == 'DELETE') {
    error_log('scheduler delete');
    mysqli_query($con, 'DELETE FROM `schedules` WHERE id = '.$url['4'].';');
    $output_array[] = array(
        'success' => '/schedules/'.$url['4'].' deleted',
    );
}
