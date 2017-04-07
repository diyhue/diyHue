<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_rules = mysqli_query($con, "SELECT *, DATE_FORMAT(created, '%Y-%m-%dT%T') AS created_conv FROM rules;");
        while ($row_rules = mysqli_fetch_assoc($query_rules)) {
            $rules_array[$row_rules['id']] = array(
                    'name' => $row_rules['name'],
                    //'owner' => $row_rules['owner'],
                    'created' => $row_rules['created_conv'],
                    //'lasttriggered' => (($row_rules['lasttriggered'] == "0000-00-00 00:00:00")?"none":$row_rules['lasttriggered']),
                    //'timestriggered' => (int)$row_rules['timestriggered'],
                    'status' => $row_rules['status'],
                    'recycle' => (bool)$row_rules['recycle'],
                    'conditions' => json_decode($row_rules['conditions']),
                    'actions' => json_decode($row_rules['actions'])
                );
        }
        if (isset($rules_array)) {
            if ($print_entire_config) {
                $output_array['rules'] = $rules_array;
            } else {
                $output_array = $rules_array;
            }
        } else {
            if ($print_entire_config) {
                $output_array['rules'] = new stdClass();
            } else {
                $output_array = new stdClass();
            }
        }
    } elseif (is_numeric($url['4'])) {
        $query_rules = mysqli_query($con, "SELECT *, DATE_FORMAT(created, '%Y-%m-%dT%T') AS created_conv FROM rules WHERE id = '".$url['4']."';");
        $row_rules = mysqli_fetch_assoc($query_rules);
        $output_array = array(
            'name' => $row_rules['name'],
            'owner' => $row_rules['owner'],
            'created' => $row_rules['created_conv'],
            'lasttriggered' => (($row_rules['lasttriggered'] == "0000-00-00 00:00:00")?"none":$row_rules['lasttriggered']),
            'timestriggered' => (int)$row_rules['timestriggered'],
            'status' => $row_rules['status'],
            'recycle' => (bool)$row_rules['recycle'],
            'conditions' => json_decode($row_rules['conditions']),
            'actions' => json_decode($row_rules['conditions'])
        );
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), false);
    error_log("RULES PUT: " .json_encode($data, JSON_UNESCAPED_SLASHES));
    $update_string = 'UPDATE rules SET ';
    foreach ($data as $key => $value) {
        $url_response = implode('/', array_slice($url, 3));
        $output_array[] = array(
            'success' => array(
                '/'.$url_response.'/'.$key => $value,
            ),
        );
        if (is_array($value)) {
            $value = json_encode($value);
        }
        $update_string .= $key." = '".$value."',";
    }
    $update_string = rtrim($update_string, ',');
    $update_string .= ' WHERE id = '.$url['4'];
    $update_rules = mysqli_query($con, $update_string);
    error_log($update_string);
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log("RULES POST:".json_encode($data, JSON_UNESCAPED_SLASHES));
    error_log("QUERY POST: INSERT INTO `rules`(`name`, `status`, `owner`, `recycle`, `conditions`, `actions`) VALUES ('".$data['name']."','".((isset($data['status']))?$data['status']:"enabled")."','".$url['2']."',".((isset($data['recycle']) && $data['recycle'] == false)?"0":"1").",'".json_encode($data['conditions'], true)."','".json_encode($data['actions'], true)."');");
    mysqli_query($con, "INSERT INTO `rules`(`name`, `status`, `owner`, `recycle`, `conditions`, `actions`) VALUES ('".$data['name']."','".((isset($data['status']))?$data['status']:"enabled")."','".$url['2']."',".((isset($data['recycle']) && $data['recycle'] == false)?"0":"1").",'".json_encode($data['conditions'], true)."','".json_encode($data['actions'], true)."');");
    $output_array[] = array(
        'success' => array(
            'id' => (string) mysqli_insert_id($con),
        ),
    );
}
